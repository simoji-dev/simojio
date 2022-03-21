import multiprocessing as mp
import os
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator
import copy
from typing import *
from PySide2.QtCore import Signal
import PySide2.QtCore as QtCore
from anytree import search
from anytree.exporter import UniqueDotExporter
from scipy.optimize import minimize

from simoji.lib.plotter.MainPlotWindow import MainPlotWindow
from simoji.lib.ModuleLoader import ModuleLoader
from simoji.lib.abstract_modules import AbstractModule
from simoji.lib.ProcessManager import ProcessManager
from simoji.lib.GlobalSettingsContainer import GlobalSettingsContainer
from simoji.lib.Sample import Sample
from simoji.lib.enums.ExecutionMode import ExecutionMode
from simoji.lib.enums.ParameterCategory import ParameterCategory
from simoji.lib.enums.LayerType import LayerType
from simoji.lib.ModuleInputContainer import ModuleInputContainer
from simoji.lib.PlotContainer import PlotContainer

from simoji.lib.VariationContainer import VariationContainer
from simoji.lib.VariationResultsContainer import VariationResultsContainer
from simoji.lib.VariablesValuesContainer import VariablesValuesContainer
from simoji.lib.ExpressionsValuesContainer import ExpressionsValuesContainer
from simoji.lib.OptimizationResultsContainer import OptimizationResultsContainer
from simoji.lib.BasicFunctions import write_to_ini, check_expression, start_stop_step_to_list
from simoji.lib.MyNode import MyNode


class ModuleExecutor(QtCore.QThread):

    execution_stopped_sig = Signal()
    plot_window_visibility_changed_sig = Signal(bool)

    def __init__(self, plot_window: MainPlotWindow, module_loader: ModuleLoader):

        super().__init__()

        self.plot_window = plot_window
        self.module_loader = module_loader
        self.process_manager = ProcessManager(nb_parallel_processes=None)

        self.global_settings = None
        self.sample_list = None
        self.save_path = None

        self.module_name = None
        self.parameter_categories = list()
        self.module_has_dataset_parameters = bool()

        self.data_set_prefix = "data_set_"
        self.variable_set_prefix = "var_set_"
        self.overview_prefix = "overview"
        self.global_tab_name = "global"

        self.timer = QtCore.QTimer()
        self.timer.setInterval(100)

        self.coupled_optimization_thread = CoupledOptimizationThread()

    def configure(self, global_settings: GlobalSettingsContainer, sample_list: List[Sample], save_path: str):

        self.global_settings = global_settings
        self.sample_list = [sample for sample in sample_list if sample.enable]
        self.save_path = save_path

        # -- evaluate module --
        self.module_name = self.global_settings.module_path[-1].rstrip(".py")

        # check for which categories (generic, dataset, layer) parameters are defined in the module
        self.parameter_categories = self.module_loader.get_parameter_categories(self.module_name)
        self.module_has_dataset_parameters = (ParameterCategory.DATASET in self.parameter_categories)

    def run(self):

        self.timer.stop()

        tree, sample_variation_dict = self._resolve_sample_list(self.global_settings, self.sample_list)
        tree, leave_groups = self._delete_incomplete_branches_and_extract_leaves(tree)
        tree.name = self.module_name

        try:
            UniqueDotExporter(tree, nodeattrfunc=lambda n: 'label="%s"' % n.name).to_picture(
                os.path.join(self.save_path, self.module_name + "_tree.png"))
            # RenderTreeGraph(tree).to_picture(os.path.join(self.save_path, self.module_name + "_tree.png"))
        except Exception as e:
            print(e)
            print("Saving execution tree as png didn't work. Need to install graphviz?")

        self.plot_window.reset()
        self.plot_window.root_save_path = self.save_path
        self.plot_window.show()
        self.plot_window_visibility_changed_sig.emit(True)
        self.plot_window.initialize_tabs(tree)

        has_global_tab = self.global_settings.execution_mode in [ExecutionMode.VARIATION,
                                                                 ExecutionMode.COUPLED_OPTIMIZATION]

        self.timer.timeout.connect(lambda: self._update_results(leave_groups, has_global_tab))
        self.timer.start()

        for leave_group in leave_groups:
            for leave in leave_group:
                leave.optimization_queue = mp.Queue()

        self._run_processes(leave_groups, sample_variation_dict)

    def _resolve_sample_list(self, global_settings: GlobalSettingsContainer,
                             sample_list: List[Sample]) -> Tuple[MyNode, Dict[str, Optional[VariationContainer]]]:
        """
        A sample might contain several input data sets and/or is supposed to be run with different variable sets in
        variation mode. Hence, a single sample needs to be resolved into several copies with exactly one configuration.
        :param global_settings:
        :param sample_list:
        :return:
        """

        # -- evaluate samples --
        sample_variation_dict = dict()         # {sample.name: variation_container)
        for sample in sample_list:
            sample.set_module(self.module_loader.load_module(self.module_name))
            variation_container = VariationContainer(sample, global_settings)
            sample_variation_dict.update({sample.name: variation_container})

        # -- create input tree (structure = tab structure in results window) --
        root = MyNode(name=self.module_name)

        if global_settings.execution_mode is ExecutionMode.COUPLED_OPTIMIZATION:
            # either with or without datasets (no variations), loop through common datasets first

            # module with dataset parameters
            if self.module_has_dataset_parameters:
                nb_common_datasets = min([len(sample.get_experimental_datasets()) for sample in sample_list])
                if nb_common_datasets > 0:
                    for dataset_idx in range(nb_common_datasets):
                        dataset_name = self.data_set_prefix + str(dataset_idx)
                        dataset_node = MyNode(name=dataset_name, parent=root)

                        global_queue = mp.Queue()
                        self._add_single_node(name=self.global_tab_name, parent_node=dataset_node, sample=None,
                                              result_queue=global_queue)
                        for sample in sample_list:
                            self._add_single_node(name=sample.name, parent_node=dataset_node, sample=sample,
                                                  dataset_idx=dataset_idx, global_queue=global_queue)

            # module without dataset parameters
            else:
                global_queue = mp.Queue()
                self._add_single_node(name=self.global_tab_name, parent_node=root, sample=None,
                                      result_queue=global_queue)
                for sample in sample_list:

                    self._add_single_node(name=sample.name, parent_node=root, sample=sample, global_queue=global_queue)
        else:
            for sample_idx, sample in enumerate(sample_list):
                sample_node = MyNode(name=sample.name, parent=root)

                # module with dataset parameters
                if self.module_has_dataset_parameters:
                    nb_datasets = len(sample.get_experimental_datasets())   # nb_datasets=0 -> skip sample
                    if nb_datasets > 0:
                        for dataset_idx in range(nb_datasets):
                            dataset_name = self.data_set_prefix + str(dataset_idx)
                            dataset_node = MyNode(name=dataset_name, parent=sample_node)

                            # with variation
                            if global_settings.execution_mode is ExecutionMode.VARIATION:
                                self._add_variation_nodes(parent_node=dataset_node, sample=sample,
                                                          variation_container=sample_variation_dict[sample.name],
                                                          dataset_idx=dataset_idx)
                            # without variation
                            else:
                                self._add_single_node(name=dataset_name, parent_node=sample_node, sample=sample,
                                                      dataset_idx=dataset_idx, update_node=dataset_node)
                # module without dataset parameters
                else:
                    # with variation
                    if global_settings.execution_mode is ExecutionMode.VARIATION:
                        self._add_variation_nodes(parent_node=sample_node, sample=sample,
                                                  variation_container=sample_variation_dict[sample.name])
                    # without variation
                    else:
                        self._add_single_node(name=sample.name, parent_node=root, sample=sample, update_node=sample_node)

        return root, sample_variation_dict

    def _add_variation_nodes(self, parent_node: MyNode, sample: Sample, variation_container: VariationContainer,
                             dataset_idx=0):

        nb_variations = len(variation_container.get_variation_grid(dataset_idx))
        if nb_variations > 0:
            global_queue = mp.Queue()
            self._add_single_node(name=self.overview_prefix, parent_node=parent_node, sample=None,
                                  result_queue=global_queue)
            for variation_idx in range(nb_variations):
                self._add_single_node(name=self.variable_set_prefix + str(variation_idx), parent_node=parent_node,
                                      sample=sample, dataset_idx=dataset_idx, variation_idx=variation_idx,
                                      global_queue=global_queue)

    def _add_single_node(self, name: str, parent_node: MyNode, sample: Optional[Sample], dataset_idx=0, variation_idx=0,
                         result_queue: Optional[mp.Queue]=None, global_queue: Optional[mp.Queue]=None,
                         update_node: Optional[MyNode]=None):
        if sample is None:
            sample_copy = sample
        else:
            sample.current_dataset_index = dataset_idx
            sample.current_variation_index = variation_idx
            sample_copy = copy.deepcopy(sample)
        input_queue = mp.JoinableQueue()

        if result_queue is None:
            result_queue = mp.Queue()

        if update_node is None:
            update_node = MyNode(name=name, parent=parent_node, sample=sample_copy, input_queue=input_queue,
                                 result_queue=result_queue, global_queue=global_queue)
        else:
            update_node.parent = parent_node
            update_node.sample = sample_copy
            update_node.input_queue = input_queue
            update_node.result_queue = result_queue
            update_node.global_queue = global_queue

        return update_node

    def _delete_incomplete_branches_and_extract_leaves(self, tree: MyNode) -> Tuple[MyNode, List[Tuple[MyNode]]]:

        # get leave level
        leave_level = 2     # 1st level is root, 2nd level is sample level (which is always present)
        if self.module_has_dataset_parameters:
            leave_level += 1
        if self.global_settings.execution_mode is ExecutionMode.VARIATION:
            leave_level += 1

        # delete branches that do not reach the leave level
        nodes = search.findall(tree, maxlevel=leave_level - 1)
        for node in nodes:
            if node.is_leaf:
                node.parent = None

        # all_leave_nodes = search.findall(tree, filter_=lambda node: len(node.path) == leave_level)

        # group leaves that have the same parent branch
        leave_parents = search.findall(tree, filter_=lambda node: len(node.path) == leave_level - 1)
        leave_groups = [leave_parent.children for leave_parent in leave_parents]

        return tree, leave_groups

    def _update_results(self, leave_groups, has_global_tab: bool):

        for leave_group in leave_groups:
            for leave_node in leave_group:
                try:
                    result = leave_node.result_queue.get_nowait()
                    self.plot_window.process_result(result, leave_node)

                    # todo:
                    # optimization_result = leave_node.optimization_queue.get()
                    # print(optimization_result)
                    # self.plot_window.process_result(optimization_result, leave_group[0])
                except:
                    pass

        if not any([p.is_alive() for p in self.process_manager.process_list]):
            self.execution_stopped_sig.emit()

    def terminate_execution(self, emit_stop_signal=True):
        if emit_stop_signal:
            self.execution_stopped_sig.emit()
        # self.process_manager.terminate_all_processes()
        self.coupled_optimization_thread.terminate()
        self.timer.stop()
        self.terminate()

    def _create_single_process(self, leave: MyNode, variation_results: VariationResultsContainer,
                               variation_idx: int, is_optimization_process=False, is_variation_process=False,
                               variation_container: Optional[VariationContainer]=None,
                               global_queue: Optional[mp.Queue]=None):

        # make sample pickle-able by unsetting the module from the parameter containers
        leave.sample.generic_parameters._current_module = None
        for dataset in leave.sample.exp_dataset_list:
            dataset._current_module = None
        for layer in leave.sample.layer_list:
            layer._current_module = None

        if is_optimization_process:
            opt_value_name, method, maximize, maximum_number_of_iterations = self._get_optimization_settings(
                                                                                        leave.sample,
                                                                                        self.global_settings)
            optimization_process = OptimizationProcess()
            self.process_manager.start_process(optimization_process.run, self.module_name, leave.save_path,
                                               variation_container, leave.sample.current_dataset_index,
                                               leave.result_queue, leave.optimization_queue,
                                               opt_value_name, method, maximize, maximum_number_of_iterations,
                                               variation_results, variation_idx)
        else:
            single_module_process = SingleModuleProcess()
            self.process_manager.start_process(single_module_process.run, self.module_name, leave.input_queue,
                                               leave.result_queue, leave.save_path, leave.optimization_queue,
                                               leave.global_queue,
                                               variation_results, variation_idx)

    def _get_optimization_settings(self, sample: Sample, global_settings: GlobalSettingsContainer):

        opt_value_name = sample.optimization_settings.name_of_value_to_be_optimized

        if global_settings.use_global_optimization_settings:
            method = global_settings.optimization_settings.current_solver
            maximize = global_settings.optimization_settings.maximize
            maximum_number_of_iterations = global_settings.optimization_settings.maximum_number_of_iterations
        else:
            method = sample.optimization_settings.current_solver
            maximize = sample.optimization_settings.maximize
            maximum_number_of_iterations = sample.optimization_settings.maximum_number_of_iterations

        return opt_value_name, method, maximize, maximum_number_of_iterations

    def _run_processes(self, leave_groups: List[Tuple[MyNode]],
                       sample_variation_dict: Dict[str, Optional[VariationContainer]]):

        if self.global_settings.execution_mode is ExecutionMode.COUPLED_OPTIMIZATION:
            self.coupled_optimization_thread.configure(leave_groups, self.process_manager, self.module_name,
                                                       sample_variation_dict, self.global_settings)
            self.coupled_optimization_thread.start()
        else:
            for leave_group in leave_groups:
                if self.global_settings.execution_mode is ExecutionMode.VARIATION:
                    sample = leave_group[1].sample
                    variation_container = sample_variation_dict[sample.name]
                    dataset_idx = sample.current_dataset_index
                    variables_names = variation_container.get_varied_variables_names(dataset_idx)
                    variation_grid = variation_container.get_variation_grid(dataset_idx)

                    variation_results = VariationResultsContainer()
                    variation_results.variable_names = variables_names
                    variation_results.variable_values_list = variation_grid
                    variation_results.variation_results_list = [[]] * len(variation_grid)

                for leave_idx, leave in enumerate(leave_group):
                    if leave.sample is not None:

                        dataset_idx = leave.sample.current_dataset_index
                        variation_idx = leave_idx - 1   # if variation, there is an overview leave 1st
                        variation_container = sample_variation_dict[leave.sample.name]

                        if self.global_settings.execution_mode is not ExecutionMode.VARIATION:
                            variation_results = VariationResultsContainer()
                            variables_names = variation_container.get_varied_variables_names(dataset_idx)
                            variation_grid = [variation_container.get_varied_variables_values(dataset_idx)]

                            variation_results.variable_names = variables_names
                            variation_results.variable_values_list = variation_grid
                            variation_results.variation_results_list = [[]] * len(variation_grid)

                        if self.global_settings.execution_mode is ExecutionMode.SINGLE:
                            self._create_single_process(leave, variation_results, variation_idx=0)
                            input_container = variation_container.get_input_container_single(dataset_idx)
                            leave.input_queue.put(input_container)
                        elif self.global_settings.execution_mode is ExecutionMode.VARIATION:
                            self._create_single_process(leave, variation_results, variation_idx)
                            input_container = variation_container.get_input_container_variation(dataset_idx,
                                                                                                variation_idx)
                            leave.input_queue.put(input_container)
                        elif self.global_settings.execution_mode is ExecutionMode.OPTIMIZATION:
                            self._create_single_process(leave, variation_results, variation_idx, is_optimization_process=True,
                                                        variation_container=variation_container)

                    leave.input_queue.put(None)     # kill process by passing the poison pill

    def _send_variation_results(self, variation_container: VariationContainer, dataset_idx: int,
                                global_queue: mp.Queue):
        variation_results = VariationResultsContainer()
        variation_results.variable_names = variation_container.get_varied_variables_names(dataset_idx)
        variation_results.variable_values_list = variation_container.get_variation_grid(dataset_idx)
        variation_results.result_names = list()
        variation_results.variation_results_list = [[]]
        variation_results.update_idx = 0    # We only show the current value in the first line (idx 0)
        variation_results.plot_flag = False

        global_queue.put(variation_results)


class CoupledOptimizationThread(QtCore.QThread):

    def __init__(self):
        super().__init__()

        self.leave_groups = list()
        self.process_manager = None
        self.module_name = None
        self.sample_variation_dict = dict()
        self.global_settings = GlobalSettingsContainer()

        self.variation_results_list = list()
        self.do_initialization_list = list()

        self.variable_values_store = []
        self.optimization_values = []

    def configure(self, leave_groups: List[Tuple[MyNode]], process_manager: ProcessManager, module_name: str,
                  sample_variation_dict: dict, global_settings: GlobalSettingsContainer):

        self.leave_groups = leave_groups
        self.process_manager = process_manager
        self.module_name = module_name
        self.sample_variation_dict = sample_variation_dict
        self.global_settings = global_settings

    def run(self):

        for leave_group in self.leave_groups:
            self._optimize_single_leave_group(leave_group)

    def _optimize_single_leave_group(self, leave_group: Tuple[MyNode]):
        # leave_group = [global, sample1, sample2,..]
        # if there are no data sets, it is only 1 leave group

        # we need to construct a single list of input variables from all samples, global variables need to be there only
        # once whereas sample variables need to be treated as independent even if they have the same name
        variable_names_list = []
        variable_values_list = []
        variable_bounds_list = []
        sample_variables_idx_dict = {}

        global_variable_names = list(self.global_settings.global_variables.get_values().keys())

        # start all sub processes
        global_queue = leave_group[0].result_queue
        for leave_idx in range(len(leave_group) - 1):
            leave = leave_group[leave_idx + 1]  # first leave is global leave

            variation_container = self.sample_variation_dict[leave.sample.name]
            dataset_idx = leave.sample.current_dataset_index
            variables_names = variation_container.get_varied_variables_names(dataset_idx)
            variable_values = variation_container.get_varied_variables_values(dataset_idx)
            variable_bounds = variation_container.get_varied_variables_bounds(dataset_idx)

            sample_variables_idx_list = []
            for idx, variable_name in enumerate(variables_names):
                if variable_name not in global_variable_names:
                    variable_name += " (" + leave.sample.name + ")"
                if variable_name not in variable_names_list:
                    variable_names_list.append(variable_name)
                    variable_values_list.append(variable_values[idx])
                    variable_bounds_list.append(variable_bounds[idx])
                sample_variables_idx_list.append(variable_names_list.index(variable_name))
            sample_variables_idx_dict.update({leave.sample.name: sample_variables_idx_list})

            variation_results = VariationResultsContainer()
            variation_results.variable_names = variables_names
            variation_results.variable_values_list = [variable_values]
            variation_results.variation_results_list = [[]]

            variation_idx = 0

            single_module_process = SingleModuleProcess()
            self.process_manager.start_process(single_module_process.run, self.module_name, leave.input_queue,
                                               leave.result_queue, leave.save_path, leave.optimization_queue,
                                               None, variation_results, variation_idx, False)

        method = self.global_settings.optimization_settings.current_solver
        maximum_number_of_iterations = self.global_settings.optimization_settings.maximum_number_of_iterations
        maximize = self.global_settings.optimization_settings.maximize
        optimized_value_name = ", ".join([leave.sample.optimization_settings.name_of_value_to_be_optimized
                                          + " (" + leave.sample.name + ")" for leave in leave_group[1:]])

        self.do_initialization_list = [True for i in range(len(leave_group) - 1)]

        result = minimize(self._optimization_fct,
                          x0=np.array(variable_values_list),
                          method=method,
                          options={'maxiter': maximum_number_of_iterations},
                          bounds=variable_bounds_list,
                          args=(leave_group, variable_names_list, sample_variables_idx_dict, 'global optimization value',
                                maximize))
        # show results
        results_container = OptimizationResultsContainer()
        results_container.set_results(optimized_value_name=optimized_value_name,
                                      variable_names=variable_names_list,
                                      variable_bounds=variable_bounds_list,
                                      solver_name=method,
                                      maximize=maximize,
                                      results_obj=result)
        global_queue.put(results_container)

        # kill all processes
        for leave in leave_group:
            leave.input_queue.put(None)  # kill process by passing the poison pill

    def _optimization_fct(self, all_variable_values, leave_group: Tuple[MyNode], variable_names_list,
                          sample_variables_idx_dict, global_optimized_value_name, maximize) -> float:

        optimization_value = 0.
        for leave_idx in range(len(leave_group) - 1):
            leave = leave_group[leave_idx + 1]
            variation_container = self.sample_variation_dict[leave.sample.name]
            dataset_idx = leave.sample.current_dataset_index

            variable_values = [all_variable_values[idx] for idx in sample_variables_idx_dict[leave.sample.name]]
            if self.do_initialization_list[leave_idx]:
                input_container = variation_container.get_input_container_single(dataset_idx)
                self.do_initialization_list[leave_idx] = False
            else:
                input_container = variation_container.get_input_container_optimization(dataset_idx, variable_values)

            leave.input_queue.put(input_container)
            optimization_dict = leave.optimization_queue.get()
            optimization_value_name = leave.sample.optimization_settings.name_of_value_to_be_optimized
            optimization_value_single = optimization_dict[optimization_value_name]
            optimization_value += optimization_value_single

            variation_results_single = VariationResultsContainer()
            variation_results_single.variable_names = variation_container.get_varied_variables_names(dataset_idx)
            variation_results_single.variable_values_list = [variable_values]
            variation_results_single.variation_results_list = [[optimization_value_single]]
            variation_results_single.result_names = [optimization_value_name]
            variation_results_single.plot_flag = False

            leave.result_queue.put(variation_results_single)

        variation_results = VariationResultsContainer()
        variation_results.variable_names = variable_names_list
        variation_results.variable_values_list = [all_variable_values]
        variation_results.variation_results_list = [[optimization_value]]
        variation_results.result_names = [global_optimized_value_name]
        variation_results.plot_flag = False

        leave_group[0].result_queue.put(variation_results)

        self._plot_optimization_steps(optimization_value, global_optimized_value_name, all_variable_values,
                                      variable_names_list, leave_group[0].result_queue)

        if maximize:
            return -optimization_value
        else:
            return optimization_value

    def _plot_optimization_steps(self, current_optimization_value, optimization_value_name, variable_values,
                                 variable_names, queue, save=True, is_variation_step_independent_plot=False,
                                 title_prefix="optimization"):

        self.variable_values_store.append(variable_values)
        self.optimization_values.append(current_optimization_value)

        if len(variable_names) == 2:
            x = np.array(self.variable_values_store).T[0]
            y = np.array(self.variable_values_store).T[1]

            fig, ax = plt.subplots()

            im = ax.scatter(x, y, c=self.optimization_values, s=100)

            ax.set_xlabel(variable_names[0])
            ax.set_ylabel(variable_names[1])
            ax.set_title(title_prefix + " steps")

            cb = fig.colorbar(im, label=optimization_value_name, ax=ax, use_gridspec=True, cmap='viridis')

            plot_container = PlotContainer(fig=fig, title=title_prefix + " steps 2d", save=save,
                                           is_variation_step_independent_plot=is_variation_step_independent_plot)

            queue.put(plot_container)
            plt.close(fig)

        else:
            for idx, values in enumerate(np.array(self.variable_values_store).T):
                fig, ax = plt.subplots()

                im = ax.scatter(values, self.optimization_values, c=range(len(values)), cmap='cool', label="optimization value")
                ax.set_xlabel(variable_names[idx])
                ax.set_ylabel(optimization_value_name)
                ax.set_title("optimization steps " + variable_names[idx])
                ax.legend()

                cb = fig.colorbar(im, label="optimization step", ax=ax, use_gridspec=True)
                cb.ax.yaxis.set_major_locator(MaxNLocator(integer=True))

                plot_container = PlotContainer(fig=fig, title="optimization steps " + variable_names[idx],
                                               save=save,
                                               is_variation_step_independent_plot=is_variation_step_independent_plot)
                queue.put(plot_container)
                plt.close(fig)


class OptimizationProcess:

    def __init__(self):

        self.single_module_process = SingleModuleProcess()
        self.result_queue = None
        self.optimization_values = []
        self.variable_values_store = []

    def run(self, module_name: str, save_path: str, variation_container: VariationContainer, dataset_idx: int,
            result_queue: mp.Queue, optimization_queue: mp.Queue, optimization_value_name: str, method: str,
            maximize: bool, maximum_number_of_iterations: int, variation_results: VariationResultsContainer,
            variation_idx: int):

        self.result_queue = result_queue

        # initialize with all parameters
        input_container = variation_container.get_input_container_single(dataset_idx)
        self.single_module_process.initialize_module(module_name, result_queue, save_path)
        self.single_module_process.optimization_queue = optimization_queue
        self.single_module_process.result_queue = result_queue
        optimization_dict = self.single_module_process.configure_and_run_module(input_container, variation_results,
                                                                                variation_idx)

        variable_bounds = variation_container.get_varied_variables_bounds(dataset_idx)

        # optimize with sending changed parameters only
        initial_variable_values = variation_container.get_varied_variables_values(dataset_idx)
        result = minimize(self._optimization_fct,
                          x0=np.array(initial_variable_values),
                          method=method,
                          options={'maxiter': maximum_number_of_iterations},
                          bounds=variable_bounds,
                          args=(variation_container, dataset_idx, optimization_value_name, maximize,
                                variation_results, variation_idx))

        # show results
        results_container = OptimizationResultsContainer()
        results_container.set_results(optimized_value_name=optimization_value_name,
                                      variable_names=variation_container.get_varied_variables_names(dataset_idx),
                                      variable_bounds=variable_bounds,
                                      solver_name=method,
                                      maximize=maximize,
                                      results_obj=result)
        self.result_queue.put(results_container)

    def _optimization_fct(self, variable_values: List[float], variation_container: VariationContainer,
                          dataset_idx: int, optimization_value_name: str, maximize: bool,
                          variation_results: VariationResultsContainer, variation_idx: int):

        input_container = variation_container.get_input_container_optimization(dataset_idx, variable_values)
        variation_results.variable_values_list = [variable_values]
        optimization_dict = self.single_module_process.configure_and_run_module(input_container, variation_results,
                                                                                variation_idx)

        optimization_value = optimization_dict[optimization_value_name]
        variable_names = variation_container.get_varied_variables_names(dataset_idx)

        self._plot_optimization_steps(current_optimization_value=optimization_value,
                                      optimization_value_name=optimization_value_name,
                                      variable_values=variable_values,
                                      variable_names=variable_names,
                                      queue=self.result_queue)

        if maximize:
            return -optimization_value
        else:
            return optimization_value

    def _plot_optimization_steps(self, current_optimization_value, optimization_value_name, variable_values,
                                 variable_names, queue, save=True, is_variation_step_independent_plot=False,
                                 title_prefix="optimization"):

        self.variable_values_store.append(variable_values)
        self.optimization_values.append(current_optimization_value)

        if len(variable_names) == 2:
            x = np.array(self.variable_values_store).T[0]
            y = np.array(self.variable_values_store).T[1]

            fig, ax = plt.subplots()

            im = ax.scatter(x, y, c=self.optimization_values, s=100)

            ax.set_xlabel(variable_names[0])
            ax.set_ylabel(variable_names[1])
            ax.set_title(title_prefix + " steps")

            cb = fig.colorbar(im, label=optimization_value_name, ax=ax, use_gridspec=True, cmap='viridis')

            plot_container = PlotContainer(fig=fig, title=title_prefix + " steps 2d", save=save,
                                           is_variation_step_independent_plot=is_variation_step_independent_plot)

            queue.put(plot_container)
            plt.close(fig)

        else:
            for idx, values in enumerate(np.array(self.variable_values_store).T):
                fig, ax = plt.subplots()

                im = ax.scatter(values, self.optimization_values, c=range(len(values)), cmap='cool', label="optimization value")
                ax.set_xlabel(variable_names[idx])
                ax.set_ylabel(optimization_value_name)
                ax.set_title("optimization steps " + variable_names[idx])
                ax.legend()

                cb = fig.colorbar(im, label="optimization step", ax=ax, use_gridspec=True)
                cb.ax.yaxis.set_major_locator(MaxNLocator(integer=True))

                plot_container = PlotContainer(fig=fig, title="optimization steps " + variable_names[idx],
                                               save=save,
                                               is_variation_step_independent_plot=is_variation_step_independent_plot)
                queue.put(plot_container)
                plt.close(fig)


class SingleModuleProcess:

    def __init__(self):

        self.module = None
        self.optimization_queue = None
        self.result_queue = None
        self.global_queue = None
        self.send_single_values = True

    def run(self, module_name: str, input_queue: mp.Queue,
            result_queue: mp.Queue, save_path: str, optimization_queue: mp.Queue,
            global_queue: Optional[mp.Queue]=None, variation_results=None, variation_idx=None, send_single_values=True):

        process_name = mp.current_process().name
        self.initialize_module(module_name, result_queue, save_path)
        self.optimization_queue = optimization_queue
        self.result_queue = result_queue
        self.global_queue = global_queue
        self.send_single_values = send_single_values

        while True:
            next_task = input_queue.get()
            if next_task is None:
                # Poison pill means shutdown
                print('%s: Exiting' % process_name)
                input_queue.task_done()
                break
            # print('%s: %s' % (process_name, next_task))

            if isinstance(next_task, ModuleInputContainer):
                self.configure_and_run_module(next_task, variation_results, variation_idx)

            input_queue.task_done()

    def configure_and_run_module(self, next_task: ModuleInputContainer, variation_results: VariationResultsContainer,
                                 variation_idx: int):

        try:
            self.module.configure_generic_parameters(next_task.generic_parameters)
        except:
            pass

        try:
            self.module.configure_experimental_parameters(next_task.dataset_parameters)
        except:
            pass

        try:
            self.module.configure_layers(next_task.layer_parameters_list, next_task.layer_type_list)
        except:
            pass

        try:
            self.module.run_reader()
        except:
            pass

        try:
            self.module.run_simulator()
        except:
            pass

        try:
            self.module.calc_optimization_value()
        except:
            pass

        optimization_dict = self.module.get_optimization_dict()
        self.optimization_queue.put(optimization_dict)

        # send current values to overview tab
        if (len(optimization_dict.values()) > 0) or (len(variation_results.variable_names) > 0):
            variation_results.result_names = list(optimization_dict.keys())
            variation_results.variation_results_list[variation_idx] = list(optimization_dict.values())
            variation_results.update_idx = variation_idx
            variation_results.plot_flag = True
            if self.global_queue is not None:
                self.global_queue.put(variation_results)

            # send current values to current tab
            if self.send_single_values:
                variation_results_single = copy.deepcopy(variation_results)
                variation_results_single.variable_values_list = [variation_results.variable_values_list[variation_idx]]
                variation_results_single.variation_results_list = [list(optimization_dict.values())]
                variation_results_single.update_idx = 0 # We only show the current value in the first line (idx 0)
                variation_results_single.plot_flag = False

                self.result_queue.put(variation_results_single)

        return optimization_dict

    def _send_variation_results(self, results_dict: dict, variable_names: List[str], variable_values: List[float]):
        variation_results = VariationResultsContainer()
        variation_results.variable_names = variable_names
        variation_results.variable_values_list = [variable_values]
        variation_results.result_names = list(results_dict.keys())
        variation_results.variation_results_list = [list(results_dict.values())]
        variation_results.update_idx = 0    # We only show the current value in the first line (idx 0)
        variation_results.plot_flag = False

        self.result_queue.put(variation_results)

    def initialize_module(self, module_name: str, result_queue: mp.Queue, save_path: str):

        module_loader = ModuleLoader()
        self.module = copy.deepcopy(module_loader.load_module(module_name))
        self.module.queue = result_queue
        self.module._simoji_save_dir = save_path
        self.module.__init__()

    def _initialize_module_and_sample(self, module_name: str, sample: Sample, result_queue: mp.Queue, save_path: str):

        # initialize module
        module_loader = ModuleLoader()
        module = copy.deepcopy(module_loader.load_module(module_name))

        # pass module to sample before the queue is set in order to keep it serializable (pickle)
        sample.set_module(module)
        # sample.generic_parameters.set_module(module)
        # for dataset in sample.exp_dataset_list:
        #     dataset.set_module(module)
        #
        # for layer in sample.layer_list:
        #     layer.set_module(module)

        module.queue = result_queue
        module._simoji_save_dir = save_path
        module.__init__()

    def _configure_module(self, module_name: str, global_settings: GlobalSettingsContainer, sample: Sample,
                          result_queue: mp.Queue, save_path: str,
                          parameter_categories: List[ParameterCategory]) -> AbstractModule:

        # initialize module
        module_loader = ModuleLoader()
        module = copy.deepcopy(module_loader.load_module(module_name))

        sample.set_module(module)
        # sample.generic_parameters.set_module(module)
        # for dataset in sample.exp_dataset_list:
        #     dataset.set_module(module)
        #
        # for layer in sample.layer_list:
        #     layer.set_module(module)

        module.queue = result_queue
        module._simoji_save_dir = save_path
        module.__init__()

        # get current values of global free parameters
        global_variables_and_expressions = self._get_free_parameter_values_dict(
            global_variables=global_settings.global_variables,
            global_expressions=global_settings.global_expressions)

        # check present parameter types
        has_generic_parameters = ParameterCategory.GENERIC in parameter_categories
        has_dataset_parameters = ParameterCategory.DATASET in parameter_categories
        has_layer_parameters = any([isinstance(category, LayerType) for category in parameter_categories])

        # get and set generic parameters
        if has_generic_parameters:
            generic_pars = sample.get_parameters_values(ParameterCategory.GENERIC, global_variables_and_expressions,
                                                        replace_free_parameters=True)
            module.configure_generic_parameters(generic_pars)

        # get and set layer parameters
        if has_layer_parameters:
            layers = sample.get_parameters_values(ParameterCategory.LAYER,
                                                  global_variables_and_expressions,
                                                  replace_free_parameters=True)
            layer_parameters_list = []
            layer_type_list = []
            for layer in layers:
                layer_parameters_list.append(layer.parameters)
                layer_type_list.append(layer.layer_type)

            module.configure_layers(layer_parameters_list, layer_type_list)

        if has_dataset_parameters:
            dataset_pars = sample.get_parameters_values(ParameterCategory.DATASET,
                                                        global_variables_and_expressions,
                                                        replace_free_parameters=True)[sample.current_dataset_index]
            module.configure_experimental_parameters(dataset_pars)

        return module

    def _get_free_parameter_values_dict(self, global_variables: VariablesValuesContainer,
                                        global_expressions: ExpressionsValuesContainer) -> dict:

        variables_dict = {key: global_variables.get_values()[key][0] for key in global_variables.get_values().keys()}
        expressions_dict = global_expressions.get_values()

        global_parameters_dict = {}
        global_parameters_dict.update(variables_dict)

        for key in expressions_dict.keys():
            success, eval_str = check_expression(expressions_dict[key], variables_dict)
            eval_float = None
            try:
                eval_float = float(eval_str)
            except:
                success = False

            if success:
                global_parameters_dict.update({key: eval_float})
            else:
                raise ValueError("Expression '" + key + "' cannot be evaluated successfully. Check expression!")

        return global_parameters_dict

    def _update_module_parameters(self, variation_container: VariationContainer, dataset_idx: int):
        varied_variables, varied_global_variables, varied_in_generic_checked, varied_in_dataset_checked, \
        varied_in_layers_checked = variation_container.get_varied_variables(dataset_idx)


if __name__ == "__main__":
    pass