import numpy as np
from typing import *

from simoji.lib.Sample import Sample
from simoji.lib.GlobalSettingsContainer import GlobalSettingsContainer
from simoji.lib.VariationResultsContainer import VariationResultsContainer
from simoji.lib.VariablesValuesContainer import VariablesValuesContainer
from simoji.lib.ExpressionsValuesContainer import ExpressionsValuesContainer
from simoji.lib.parameters.Expression import Expression
from simoji.lib.VariationContainerDataset import VariationContainerDataset
from simoji.lib.ModuleInputContainer import ModuleInputContainer


class VariationContainer:
    """Holds the variation grid for each dataset given in sample"""

    def __init__(self, sample: Sample, global_settings: GlobalSettingsContainer):

        self.variation_container_dataset_list = []

        nb_datasets = len(sample.get_experimental_datasets())
        for i in range(nb_datasets):
            self.variation_container_dataset_list.append(VariationContainerDataset(sample, global_settings, i))

    def get_input_container_single(self, dataset_idx: int) -> ModuleInputContainer:
        return self.variation_container_dataset_list[dataset_idx].get_input_container_for_single()

    def get_input_container_variation(self, dataset_idx: int, variation_idx: int) -> ModuleInputContainer:
        return self.variation_container_dataset_list[dataset_idx].get_input_container_for_variation(variation_idx)

    def get_input_container_optimization(self, dataset_idx: int, variable_values: List[float]):
        return self.variation_container_dataset_list[dataset_idx].get_input_container_for_optimization(variable_values)

    def get_variation_grid(self, dataset_idx: int) -> list:
        return self.variation_container_dataset_list[dataset_idx].get_variation_grid()

    def get_varied_variables_values(self, dataset_idx) -> List[float]:
        return self.variation_container_dataset_list[dataset_idx].get_varied_variables_values()

    def get_varied_variables_names(self, dataset_idx) -> List[str]:
        return self.variation_container_dataset_list[dataset_idx].get_varied_variables_names()

    def get_varied_variables_bounds(self, dataset_idx) -> List[Tuple[float]]:
        return self.variation_container_dataset_list[dataset_idx].get_varied_variables_bounds()

