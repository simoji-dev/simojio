import PySide2.QtCore as QtCore
from typing import List, Tuple
import numpy as np
from scipy.optimize import minimize
import multiprocessing as mp

from simojio.lib.GlobalSettingsContainer import GlobalSettingsContainer
from simojio.lib.MyNode import MyNode
from simojio.lib.OptimizationResultsContainer import OptimizationResultsContainer

from simojio.lib.module_executor.ProcessManager import ProcessManager
from simojio.lib.module_executor.SingleModuleProcess import SingleModuleProcess
from simojio.lib.module_executor.SampleLeaveNode import SampleLeaveNode
from simojio.lib.module_executor.LeaveNode import LeaveNode
from simojio.lib.module_executor.shared_functions import plot_optimization_steps, get_optimization_settings
from simojio.lib.ModuleLoader import ModuleLoader
from simojio.lib.abstract_modules.Fitter import Fitter


class CoupledOptimizationThread(QtCore.QThread):

    def __init__(self):
        super().__init__()

        self.leave_groups = list()
        self.process_manager = None
        self.module_name = None
        self.sample_variation_dict = dict()
        self.global_settings = GlobalSettingsContainer()
        self.stop_queue = None

        self.variation_results_list = list()
        self.do_initialization_list = list()

        self.variable_values_store = []
        self.optimization_values = []

    def configure(self, leave_groups: List[List[LeaveNode]], process_manager: ProcessManager, module_name: str,
                  sample_variation_dict: dict, global_settings: GlobalSettingsContainer, stop_queue: mp.Queue):

        self.leave_groups = leave_groups
        self.process_manager = process_manager
        self.module_name = module_name
        self.sample_variation_dict = sample_variation_dict
        self.global_settings = global_settings
        self.stop_queue = stop_queue

    def run(self):

        for leave_group in self.leave_groups:
            self._optimize_single_leave_group(leave_group)

    def _optimize_single_leave_group(self, leave_group: Tuple[MyNode]):
        # leave_group = [global, sample1, sample2,..]
        # if there are no evaluation sets, it is only 1 leave group

        self.variable_values_store = []
        self.optimization_values = []

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
            evaluation_set_idx = leave.sample.current_evaluation_set_index
            variables_names = variation_container.get_varied_variables_names(evaluation_set_idx)
            variable_values = variation_container.get_varied_variables_values(evaluation_set_idx)
            variable_bounds = variation_container.get_varied_variables_bounds(evaluation_set_idx)

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

            single_module_process = SingleModuleProcess()
            self.process_manager.start_process(single_module_process.run_coupled, self.module_name, leave.input_queue,
                                               leave.result_queue, leave.save_path, leave.optimization_queue,
                                               leave.global_queue, self.stop_queue)

        method = self.global_settings.optimization_settings.current_solver
        maximum_number_of_iterations = self.global_settings.optimization_settings.maximum_number_of_iterations
        maximize = self.global_settings.optimization_settings.maximize
        if isinstance(ModuleLoader().load_module(self.module_name), Fitter):
            maximize = False

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
            if isinstance(leave, SampleLeaveNode):
                leave.input_queue.put(None)  # kill process by passing the poison pill

    def _optimization_fct(self, all_variable_values, leave_group: Tuple[MyNode], variable_names_list,
                          sample_variables_idx_dict, global_optimized_value_name, maximize) -> float:

        optimization_value = 0.
        for leave_idx in range(len(leave_group) - 1):
            leave = leave_group[leave_idx + 1]
            variation_container = self.sample_variation_dict[leave.sample.name]
            evaluation_set_idx = leave.sample.current_evaluation_set_index

            variable_values = [all_variable_values[idx] for idx in sample_variables_idx_dict[leave.sample.name]]
            if self.do_initialization_list[leave_idx]:
                input_container = variation_container.get_input_container_single(evaluation_set_idx)
                self.do_initialization_list[leave_idx] = False
            else:
                input_container = variation_container.get_input_container_optimization(evaluation_set_idx, variable_values)

            # here the module is executed with the current input parameters and returns the optimization results
            leave.input_queue.put([input_container, variable_values])
            while True:
                # loop over get() with timeout to give main process entry point for termination
                try:
                    current_variables_and_results = leave.optimization_queue.get(timeout=3000)
                    break
                except:
                    pass
            optimization_dict = current_variables_and_results.results_dict

            optimization_value_name = leave.sample.optimization_settings.name_of_value_to_be_optimized
            optimization_value_single = optimization_dict[optimization_value_name]
            optimization_value += optimization_value_single

        self.variable_values_store.append(all_variable_values)
        self.optimization_values.append(optimization_value)

        plot_optimization_steps(self.optimization_values, global_optimized_value_name, self.variable_values_store,
                                variable_names_list, leave_group[0].result_queue)

        if maximize:
            return -optimization_value
        else:
            return optimization_value
