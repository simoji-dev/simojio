from typing import *

from simoji.lib.Sample import Sample
from simoji.lib.GlobalSettingsContainer import GlobalSettingsContainer
from simoji.lib.VariationContainerEvaluationSet import VariationContainerEvaluationSet
from simoji.lib.ModuleInputContainer import ModuleInputContainer


class VariationContainer:
    """Holds the variation grid for each evaluation set given in sample"""

    def __init__(self, sample: Sample, global_settings: GlobalSettingsContainer):

        self.variation_container_evaluation_set_list = []
        self.any_evaluation_set_in_sample = False

        nb_evaluation_sets = len(sample.get_evaluation_sets())
        if nb_evaluation_sets > 0:
            self.any_evaluation_set_in_sample = True

        # Note: We make at least one list entry since we always pass an evaluation_set_idx to the get methods
        for i in range(nb_evaluation_sets or 1):
            self.variation_container_evaluation_set_list.append(VariationContainerEvaluationSet(sample, global_settings, i))

    def get_input_container_single(self, evaluation_set_idx: int) -> ModuleInputContainer:
        return self.variation_container_evaluation_set_list[evaluation_set_idx].get_input_container_for_single()

    def get_input_container_variation(self, evaluation_set_idx: int, variation_idx: int) -> ModuleInputContainer:
        return self.variation_container_evaluation_set_list[evaluation_set_idx].get_input_container_for_variation(variation_idx)

    def get_input_container_optimization(self, evaluation_set_idx: int, variable_values: List[float]):
        return self.variation_container_evaluation_set_list[evaluation_set_idx].get_input_container_for_optimization(variable_values)

    def get_variation_grid(self, evaluation_set_idx: int) -> list:
        return self.variation_container_evaluation_set_list[evaluation_set_idx].get_variation_grid()

    def get_varied_variables_values(self, evaluation_set_idx) -> List[float]:
        return self.variation_container_evaluation_set_list[evaluation_set_idx].get_varied_variables_values()

    def get_varied_variables_names(self, evaluation_set_idx) -> List[str]:
        return self.variation_container_evaluation_set_list[evaluation_set_idx].get_varied_variables_names()

    def get_varied_variables_bounds(self, evaluation_set_idx) -> List[Tuple[float]]:
        return self.variation_container_evaluation_set_list[evaluation_set_idx].get_varied_variables_bounds()

