from typing import Dict, Optional, List


class CurrentVariablesAndResultsContainer:

    def __init__(self, results_dict: Dict[str, float], variable_values: Optional[List[float]]=None):

        self.results_dict = results_dict
        self.variable_values = variable_values
