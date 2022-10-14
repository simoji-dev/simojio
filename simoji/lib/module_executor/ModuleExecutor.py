import multiprocessing as mp
from typing import *
from PySide2.QtCore import Signal
import PySide2.QtCore as QtCore

from simoji.lib.plotter.MainPlotWindow import MainPlotWindow
from simoji.lib.ModuleLoader import ModuleLoader
from simoji.lib.module_executor.ProcessManager import ProcessManager
from simoji.lib.GlobalSettingsContainer import GlobalSettingsContainer
from simoji.lib.Sample import Sample
from simoji.lib.enums.ExecutionMode import ExecutionMode
from simoji.lib.CallbackContainer import CallbackContainer

from simoji.lib.module_executor.CoupledOptimizationThread import CoupledOptimizationThread
from simoji.lib.module_executor.SampleListResolver import SampleListResolver
from simoji.lib.module_executor.SampleLeaveNode import SampleLeaveNode
from simoji.lib.module_executor.GlobalLeaveNode import GlobalLeaveNode
from simoji.lib.module_executor.LeaveNode import LeaveNode
from simoji.lib.module_executor.shared_functions import save_tree, show_callback
from simoji.lib.module_executor.LeaveGroupResultsContainer import LeaveGroupResultsContainer
from simoji.lib.module_executor.CurrentVariablesAndResultsContainer import CurrentVariablesAndResultsContainer
from simoji.lib.module_executor.SeparateProcessesThread import SeparateProcessesThread


class ModuleExecutor(QtCore.QObject):
    execution_stopped_sig = Signal()
    plot_window_visibility_changed_sig = Signal(bool)

    def __init__(self, plot_window: MainPlotWindow, module_loader: ModuleLoader,
                 nb_parallel_processes: Optional[int] = None):

        super().__init__()

        self.plot_window = plot_window
        self.module_loader = module_loader
        self.process_manager = ProcessManager(nb_parallel_processes=nb_parallel_processes)

        self.global_settings = None
        self.sample_list = None
        self.save_path = None

        self.module_name = None
        self.parameter_categories = list()
        self.module_has_evaluation_set_parameters = bool()
        self.is_coupled_mode = bool()

        self.leave_variables_dict = {}
        self.leave_group_results_container = LeaveGroupResultsContainer()

        self.timer = QtCore.QTimer()
        self.timer.setInterval(100)

        self.coupled_optimization_thread = CoupledOptimizationThread()
        self.separate_processes_thread = SeparateProcessesThread()
        self.stop_queue = mp.Queue()

    def configure(self, global_settings: GlobalSettingsContainer, sample_list: List[Sample], save_path: str):

        self.global_settings = global_settings
        self.sample_list = [sample for sample in sample_list if sample.enable]
        self.save_path = save_path

        # -- evaluate module --
        self.module_name = self.global_settings.module_path[-1].rstrip(".py")
        self.is_coupled_mode = self.global_settings.execution_mode is ExecutionMode.COUPLED_OPTIMIZATION
        self.leave_group_results_container.configure(self.global_settings.execution_mode)

    def run(self):

        self.timer.stop()

        sample_list_resolver = SampleListResolver(self.module_loader)
        tree, leave_groups, sample_variation_dict = sample_list_resolver.resolve(self.sample_list, self.global_settings)

        # Check if at least one evaluation set is given per sample (if module has evaluation set parameters)
        if sample_list_resolver.module_has_evaluation_set_parameters:
            self._check_if_any_evaluation_sets(leave_groups)

        save_tree(tree=tree, save_path=self.save_path)

        for leave_group in leave_groups:
            self.leave_group_results_container.add_leave_group(leave_group, sample_variation_dict)

        self.plot_window.reset()
        self.plot_window.root_save_path = self.save_path
        self.plot_window.show()
        self.plot_window_visibility_changed_sig.emit(True)
        self.plot_window.initialize_tabs(tree)

        self.timer.timeout.connect(lambda: self._update_results(leave_groups))
        self.timer.start()

        if self.is_coupled_mode:
            self.coupled_optimization_thread.configure(leave_groups, self.process_manager, self.module_name,
                                                       sample_variation_dict, self.global_settings, self.stop_queue)
            self.coupled_optimization_thread.start()
        else:
            self.separate_processes_thread.configure(leave_groups, self.process_manager, self.module_name,
                                                     sample_variation_dict, self.global_settings, self.stop_queue)
            self.separate_processes_thread.start()

    def terminate_execution(self, emit_stop_signal=True):

        if emit_stop_signal:
            self.execution_stopped_sig.emit()
        for i in range(2 * self.process_manager.get_nb_processes()):  # factor 2 just to make sure we cache all
            self.stop_queue.put('STOP')
        self.separate_processes_thread.exit()
        self.coupled_optimization_thread.exit()
        self.timer.stop()

    def _update_results(self, leave_groups: List[List[LeaveNode]]):

        for leave_group in leave_groups:
            for leave_node in leave_group:
                if isinstance(leave_node, SampleLeaveNode) or isinstance(leave_node, GlobalLeaveNode):

                    try:
                        result = leave_node.result_queue.get_nowait()

                        if isinstance(result, CurrentVariablesAndResultsContainer):
                            if isinstance(leave_node, SampleLeaveNode):
                                leave_node.optimization_queue.put(result)
                            results_dict = result.results_dict
                            self.leave_group_results_container.set_results_dict(leave_node, results_dict)
                            variable_values = result.variable_values

                            if variable_values is not None:
                                self.leave_group_results_container.set_variable_values(leave_node, variable_values)
                            results_global, results_single = self.leave_group_results_container.get_results(
                                leave_node)

                            # only send if any input (variable values or any results)
                            if (len(results_single.variable_names) > 0) or (len(results_dict) > 0):
                                self.plot_window.process_result(results_single, leave_node)
                                self.plot_window.process_result(results_global, leave_group[0])
                        elif isinstance(result, CallbackContainer):
                            result.leave_path = "/".join([leave.name for leave in leave_node.ancestors]
                                                         + [leave_node.name])
                            self._show_callback(result)
                        else:  # Plots, Optimization results
                            self.plot_window.process_result(result, leave_node)
                    except:
                        pass

        if not any([p.is_alive() for p in self.process_manager.process_list]):
            self.execution_stopped_sig.emit()

    def _show_callback(self, callback_container: CallbackContainer):
        show_callback(self.parent(), callback_container)

    def _check_if_any_evaluation_sets(self, leave_groups):

        filled_samples = []
        for leave_group in leave_groups:
            for leave in leave_group:
                if isinstance(leave, SampleLeaveNode):
                    filled_samples.append(leave.sample.name)

        empty_samples = [sample.name for sample in self.sample_list if sample.name not in filled_samples]

        self._show_callback(CallbackContainer(title="Missing input parameters",
                                              message="No evaluation set given in sample(s): '"
                                                      + ", ".join(empty_samples)))


if __name__ == "__main__":
    pass
