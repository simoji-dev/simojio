from typing import List, Dict, Optional

from simojio.lib.module_executor.LeaveNode import LeaveNode
from simojio.lib.enums.ExecutionMode import ExecutionMode
from simojio.lib.VariationContainer import VariationContainer
from simojio.lib.VariationResultsContainer import VariationResultsContainer
from simojio.lib.module_executor.SingleLeaveResultsContainer import SingleLeaveResultsContainer
from simojio.lib.module_executor.SampleLeaveNode import SampleLeaveNode


class LeaveGroupResultsContainer:

    def __init__(self):
        self.leave_group_list = []
        self.leave_global_idx_dict = {}
        self.leave_group_idx_dict = {}
        self.global_results_list = []           # [[SingleLeaveResultsContainer]]
        self.global_leaves_list = []
        self.is_variation_mode = False          # execution_mode is ExecutionMode.VARIATION

    def configure(self, execution_mode: ExecutionMode):
        self.is_variation_mode = execution_mode is ExecutionMode.VARIATION

    def add_leave_group(self, leave_group: List[LeaveNode],
                        sample_variation_dict: Dict[str, Optional[VariationContainer]]):

        self.leave_group_list.append(leave_group)
        single_leave_results_list = []
        for idx, leave in enumerate(leave_group):
            self.leave_global_idx_dict.update({leave: len(self.global_results_list)})

            if isinstance(leave, SampleLeaveNode):
                self.leave_group_idx_dict.update({leave: idx - 1})      # tab0 is global

                variation_container = sample_variation_dict[leave.sample.name]
                variable_names = variation_container.get_varied_variables_names(leave.sample.current_evaluation_set_index)
                variable_values = variation_container.get_varied_variables_values(leave.sample.current_evaluation_set_index)
                if self.is_variation_mode:
                    variation_grid = variation_container.get_variation_grid(leave.sample.current_evaluation_set_index)
                    variable_values = variation_grid[idx - 1]

                single_leave_results = SingleLeaveResultsContainer(leave.name, variable_names, variable_values)
                single_leave_results_list.append(single_leave_results)
            else:
                self.global_leaves_list.append(leave)

        self.global_results_list.append(single_leave_results_list)

    def set_variable_values(self, leave: LeaveNode, variable_values: List[float]):
        single_results_container = self._get_single_results_container(leave)
        single_results_container.set_variable_values(variable_values)

    def set_results_dict(self, leave: LeaveNode, result_dict: Dict[str, float]):
        single_results_container = self._get_single_results_container(leave)
        single_results_container.set_results_dict(result_dict)

    def get_results(self, leave):

        variation_results_single = VariationResultsContainer()
        variation_results_global = VariationResultsContainer()

        global_idx = self.leave_global_idx_dict[leave]
        group_idx = self.leave_group_idx_dict[leave]

        single_results_container = self.global_results_list[global_idx][group_idx]
        variable_names = list(single_results_container.variable_names)
        result_names = list(single_results_container.results_dict.keys())

        variation_results_single.row_names = [leave.name]
        variation_results_single.update_idx = 0
        variation_results_single.plot_flag = False
        variation_results_single.variable_names = variable_names
        variation_results_single.variable_values_list = [single_results_container.variable_values]
        variation_results_single.result_names = result_names
        variation_results_single.variation_results_list = [single_results_container.results_dict.values()]

        variation_results_global.row_names = [l.name for l in self.leave_group_list[global_idx]][1:]
        variation_results_global.update_idx = group_idx
        variation_results_global.plot_flag = True
        if self.is_variation_mode:
            variation_results_global.variable_names = variable_names
        else:
            variation_results_global.variable_names = []
        variation_results_global.result_names = result_names

        variable_values = []
        result_values = []
        for results_container in self.global_results_list[global_idx]:
            result_values.append(list(results_container.results_dict.values()))
            if self.is_variation_mode:
                variable_values.append(list(results_container.variable_values))
            else:
                variable_values.append([])

        variation_results_global.variation_results_list = result_values
        variation_results_global.variable_values_list = variable_values

        return variation_results_global, variation_results_single

    def get_global_leave(self, leave: SampleLeaveNode):
        return self.global_leaves_list[self.leave_global_idx_dict[leave]]

    def _get_single_results_container(self, leave: LeaveNode) -> SingleLeaveResultsContainer:
        idx_global = self.leave_global_idx_dict[leave]
        idx_group = self.leave_group_idx_dict[leave]
        single_results_container = self.global_results_list[idx_global][idx_group]
        return single_results_container
