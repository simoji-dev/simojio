from typing import List, Dict


class SingleLeaveResultsContainer:

    def __init__(self, leave_name: str, variable_names: List[str], variable_values: List[float]):

        self.leave_name = leave_name
        self.variable_names = variable_names
        self.variable_values = variable_values
        self.results_dict = {}

    def set_variable_values(self, variable_values: List[float]):
        self.variable_values = variable_values

    def set_results_dict(self, results_dict: Dict[str, float]):
        self.results_dict.update(results_dict)
