import multiprocessing as mp
from typing import List, Tuple, Dict, Optional
from anytree import search
import copy

from simoji.lib.Sample import Sample
from simoji.lib.GlobalSettingsContainer import GlobalSettingsContainer
from simoji.lib.module_executor.MyNode import MyNode
from simoji.lib.module_executor.ForkNode import ForkNode
from simoji.lib.module_executor.SampleLeaveNode import SampleLeaveNode
from simoji.lib.module_executor.GlobalLeaveNode import GlobalLeaveNode
from simoji.lib.VariationContainer import VariationContainer
from simoji.lib.enums.ExecutionMode import ExecutionMode
from simoji.lib.ModuleLoader import ModuleLoader
from simoji.lib.enums.ParameterCategory import ParameterCategory
from simoji.lib.abstract_modules import Calculator
from simoji.lib.CallbackContainer import CallbackContainer


class SampleListResolver:

    def __init__(self, module_loader: ModuleLoader):

        self.module_loader = module_loader
        self.module_name = None
        self.module_has_evaluation_set_parameters = bool()
        self.is_variation_mode = bool()

        self.evaluation_set_prefix = "evaluation_set_"
        self.variable_set_prefix = "variable_set_"
        self.overview_prefix = "overview"
        self.global_tab_name = "global"

        self.make_global_tab = True

    def resolve(self, sample_list: List[Sample], global_settings: GlobalSettingsContainer):

        self.module_name = global_settings.module_path[-1].rstrip(".py")
        module = ModuleLoader().load_module(self.module_name)
        self.make_global_tab = isinstance(module, Calculator)

        # check for which categories (generic, evaluation set, layer) parameters are defined in the module
        parameter_categories = self.module_loader.get_parameter_categories(self.module_name)
        self.module_has_evaluation_set_parameters = (ParameterCategory.EVALUATION_SET in parameter_categories)
        self.is_variation_mode = global_settings.execution_mode is ExecutionMode.VARIATION

        tree, sample_variation_dict = self._resolve_sample_list(global_settings, sample_list)
        tree, leaves = self._delete_incomplete_branches_and_extract_leaves(tree)
        tree.name = self.module_name

        return tree, leaves, sample_variation_dict

    def _resolve_sample_list(self, global_settings: GlobalSettingsContainer,
                             sample_list: List[Sample]) -> Tuple[MyNode, Dict[str, Optional[VariationContainer]]]:
        """
        A sample might contain several evaluation sets and/or is supposed to be run with different variable sets in
        variation mode. Hence, a single sample needs to be resolved into several copies with exactly one configuration.
        :param global_settings:
        :param sample_list:
        :return:
        """

        # -- evaluate samples --
        sample_variation_dict = dict()  # {sample.name: variation_container)
        for sample in sample_list:
            sample.set_module(self.module_loader.load_module(self.module_name))
            variation_container = VariationContainer(sample, global_settings)
            sample_variation_dict.update({sample.name: variation_container})

        # -- create input tree (structure = tab structure in plot window) --
        root = MyNode(name=self.module_name)
        sample_names = [sample.name for sample in sample_list]

        if global_settings.execution_mode is ExecutionMode.COUPLED_OPTIMIZATION:
            if self.module_has_evaluation_set_parameters:
                nb_common_evaluation_sets = min([len(sample.get_evaluation_sets()) for sample in sample_list])
                for evaluation_set_idx in range(nb_common_evaluation_sets):
                    fork_node = self._create_fork_node(parent_node=root,
                                                       name=self._get_evaluation_set_name(evaluation_set_idx))
                    sample_copy_list = [self._set_sample_indices_and_make_copy(sample,
                                                                               evaluation_set_idx=evaluation_set_idx)
                                        for sample in sample_list]
                    self._create_leave_group_nodes(parent_node=fork_node, leave_name_list=sample_names,
                                                   sample_list=sample_copy_list)
            else:
                self._create_leave_group_nodes(parent_node=root, leave_name_list=sample_names, sample_list=sample_list)

        else:
            if self.is_variation_mode or self.module_has_evaluation_set_parameters:
                for sample in sample_list:
                    sample_node = self._create_fork_node(parent_node=root, name=sample.name)
                    variation_container = sample_variation_dict[sample.name]

                    if self.module_has_evaluation_set_parameters:
                        nb_evaluation_sets = len(sample.get_evaluation_sets())

                        if self.is_variation_mode:
                            for evaluation_set_idx in range(nb_evaluation_sets):
                                evaluation_set_node = self._create_fork_node(parent_node=sample_node,
                                                                             name=self._get_evaluation_set_name(
                                                                                 evaluation_set_idx))
                                variation_names, variation_samples = self._get_variation_names_and_sample_copies(
                                    variation_container=variation_container, sample=sample,
                                    evaluation_set_idx=evaluation_set_idx
                                )

                                self._create_leave_group_nodes(parent_node=evaluation_set_node,
                                                               leave_name_list=variation_names,
                                                               sample_list=variation_samples,
                                                               force_make_global_tab=True)
                        else:
                            evaluation_set_names, evaluation_set_samples = self._get_evaluation_set_names_and_sample_copies(
                                nb_evaluation_sets=nb_evaluation_sets, sample=sample
                            )
                            self._create_leave_group_nodes(parent_node=sample_node,
                                                           leave_name_list=evaluation_set_names,
                                                           sample_list=evaluation_set_samples)
                    else:  # without evaluation sets
                        if self.is_variation_mode:
                            variation_names, variation_samples = self._get_variation_names_and_sample_copies(
                                variation_container=variation_container, sample=sample
                            )

                            self._create_leave_group_nodes(parent_node=sample_node,
                                                           leave_name_list=variation_names,
                                                           sample_list=variation_samples,
                                                           force_make_global_tab=True)
            else:
                self._create_leave_group_nodes(parent_node=root, leave_name_list=sample_names,
                                               sample_list=sample_list)

        return root, sample_variation_dict

    def _get_evaluation_set_names_and_sample_copies(self, nb_evaluation_sets: int,
                                                    sample: Sample) -> Tuple[List[str], List[Sample]]:
        name_list = []
        sample_list = []

        for evaluation_set_idx in range(nb_evaluation_sets):
            name_list.append(self._get_evaluation_set_name(evaluation_set_idx))
            sample_list.append(self._set_sample_indices_and_make_copy(sample=sample,
                                                                      evaluation_set_idx=evaluation_set_idx))

        return name_list, sample_list

    def _get_variation_names_and_sample_copies(self, variation_container: VariationContainer, sample: Sample,
                                               evaluation_set_idx=0) -> Tuple[List[str], List[Sample]]:
        name_list = []
        sample_list = []

        nb_variations = len(variation_container.get_variation_grid(evaluation_set_idx))

        for variation_idx in range(nb_variations):
            name_list.append(self._get_variation_name(variation_idx))
            sample_list.append(self._set_sample_indices_and_make_copy(sample=sample,
                                                                      evaluation_set_idx=evaluation_set_idx,
                                                                      variation_idx=variation_idx))
        return name_list, sample_list

    @staticmethod
    def _set_sample_indices_and_make_copy(sample: Sample, evaluation_set_idx=0, variation_idx=0):
        sample.current_evaluation_set_index = evaluation_set_idx
        sample.current_variation_index = variation_idx
        return copy.deepcopy(sample)

    def _get_evaluation_set_name(self, evaluation_set_idx: int):
        return self.evaluation_set_prefix + str(evaluation_set_idx)

    def _get_variation_name(self, variation_idx: int):
        return self.variable_set_prefix + str(variation_idx)

    @staticmethod
    def _create_fork_node(parent_node: MyNode, name: str) -> ForkNode:
        return ForkNode(name=name, parent=parent_node)

    def _create_leave_group_nodes(self, parent_node: MyNode, leave_name_list: List[str], sample_list: List[Sample],
                                  force_make_global_tab=False):

        global_queue = None
        if self.make_global_tab or force_make_global_tab:
            global_queue = mp.Queue()
            GlobalLeaveNode(name=self.global_tab_name, parent=parent_node, result_queue=global_queue)

        for idx, name in enumerate(leave_name_list):
            SampleLeaveNode(name=name, parent=parent_node, sample=sample_list[idx], global_queue=global_queue)

    def _delete_incomplete_branches_and_extract_leaves(self, tree: MyNode) -> Tuple[MyNode, List[List[MyNode]]]:

        # get leave level
        leave_level = 2  # 1st level is root, 2nd level is sample level (which is always present)
        if self.module_has_evaluation_set_parameters:
            leave_level += 1
        if self.is_variation_mode:
            leave_level += 1

        # delete branches that do not reach the leave level
        nodes = search.findall(tree, maxlevel=leave_level - 1)
        for node in nodes:
            if node.is_leaf:
                node.parent = None

        # group leaves that have the same parent branch
        leave_parents = search.findall(tree, filter_=lambda node: len(node.path) == leave_level - 1)
        leave_groups = [leave_parent.children for leave_parent in leave_parents]

        return tree, leave_groups
