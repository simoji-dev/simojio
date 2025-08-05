import PySide6.QtCore as QtCore
import multiprocessing as mp
from typing import List, Dict, Optional

from simojio.lib.enums.ExecutionMode import ExecutionMode
from simojio.lib.module_executor.LeaveNode import LeaveNode
from simojio.lib.module_executor.SampleLeaveNode import SampleLeaveNode
from simojio.lib.VariationContainer import VariationContainer
from simojio.lib.ModuleInputContainer import ModuleInputContainer
from simojio.lib.module_executor.SingleModuleProcess import SingleModuleProcess
from simojio.lib.module_executor.ProcessManager import ProcessManager
from simojio.lib.GlobalSettingsContainer import GlobalSettingsContainer
from simojio.lib.module_executor.shared_functions import get_optimization_settings


class SeparateProcessesThread(QtCore.QThread):

    def __init__(self):
        super().__init__()

        self.leave_groups = list()
        self.process_manager = None
        self.module_name = None
        self.sample_variation_dict = dict()
        self.global_settings = GlobalSettingsContainer()
        self.stop_queue = None

        self.leave_variables_dict = dict()

    def configure(self, leave_groups: List[List[LeaveNode]], process_manager: ProcessManager, module_name: str,
                  sample_variation_dict: dict, global_settings: GlobalSettingsContainer, stop_queue: mp.Queue):

        self.leave_groups = leave_groups
        self.process_manager = process_manager
        self.module_name = module_name
        self.sample_variation_dict = sample_variation_dict
        self.global_settings = global_settings
        self.stop_queue = stop_queue

    def run(self):
        self._run_separate_processes(self.leave_groups, self.sample_variation_dict)

    def _run_separate_processes(self, leave_groups: List[List[LeaveNode]],
                                sample_variation_dict: Dict[str, Optional[VariationContainer]]):

        sample_leaves = []
        for leave_group in leave_groups:
            for leave in leave_group:
                if isinstance(leave, SampleLeaveNode):
                    sample_leaves.append(leave)

        for leave in sample_leaves:
            evaluation_set_idx = leave.sample.current_evaluation_set_index
            variation_idx = leave.sample.current_variation_index

            variation_container = sample_variation_dict[leave.sample.name]
            var_names = variation_container.get_varied_variables_names(evaluation_set_idx)
            var_values = variation_container.get_varied_variables_values(evaluation_set_idx)
            self.leave_variables_dict.update(
                {leave: {var_names[idx]: var_values[idx] for idx in range(len(var_names))}})

            if self.global_settings.execution_mode is ExecutionMode.SINGLE:
                input_container = variation_container.get_input_container_single(evaluation_set_idx)
                self._start_single_process(leave, input_container)
            elif self.global_settings.execution_mode is ExecutionMode.VARIATION:
                input_container = variation_container.get_input_container_variation(evaluation_set_idx, variation_idx)
                self._start_single_process(leave, input_container)
            elif self.global_settings.execution_mode is ExecutionMode.OPTIMIZATION:
                self._start_optimization_process(leave, variation_container)

        #  end all processes by passing the poison pill
        for leave in sample_leaves:
            leave.input_queue.put(None)

    def _start_single_process(self, leave: SampleLeaveNode, input_container: ModuleInputContainer):

        single_module_process = SingleModuleProcess()
        self.process_manager.start_process(single_module_process.run, self.module_name, input_container,
                                           leave.result_queue, leave.save_path, leave.optimization_queue,
                                           leave.global_queue, self.stop_queue)

    def _start_optimization_process(self, leave: SampleLeaveNode, variation_container: VariationContainer):
        evaluation_set_idx = leave.sample.current_evaluation_set_index
        opt_value_name, method, maximize, max_iter = get_optimization_settings(leave.sample, self.global_settings)

        single_module_process = SingleModuleProcess()
        self.process_manager.start_process(single_module_process.run_optimization, self.module_name,
                                           leave.result_queue, leave.save_path, leave.optimization_queue,
                                           leave.global_queue, self.stop_queue, variation_container, evaluation_set_idx,
                                           opt_value_name, method, maximize, max_iter)