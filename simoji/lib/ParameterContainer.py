from simoji.lib.enums.ParameterCategory import ParameterCategory
from simoji.lib.enums.LayerType import LayerType
from simoji.lib.parameters import *

import copy
from typing import *


class ParameterContainer:
    """
    Container for multiple parameters each having a unique name.

    A parameter is preferably stored as an object. It can be either directly added as object or the object is extracted
    from the objects defined in the currently set module.

    If a parameter is added via its content, e.g. {parameter_name: parameter_content}, it is checked whether already an
    object with this name exists. If yes, the object is set to the new values. If no, the content is stored in the
    _parameter_content_dict. The content may be a single value or a list of values.

    If the current_module is changed, it is checked whether the new module contains parameter objects that ar not yet
    known. If so, they are added to the _parameter_objects_dict and they are set to the values stored in the
    _parameter_content_dict if there are any.
    """

    def __init__(self, category: Union[ParameterCategory, LayerType]):

        self._category = category
        self._current_module = None

        self._parameter_objects_dict = {}  # {"parameter_name": parameter_object}
        self._parameter_content_dict = {}  # {"parameter_name": parameter_content}

    def set_parameter_object(self, parameter: Union[SingleParameter, NestedParameter]):
        """Check if parameter name already exists. If yes, try to overwrite the present values. If no, just add."""

        if parameter.name in self._parameter_objects_dict:
            content = None
            if isinstance(parameter, SingleParameter):
                content = parameter.value
            elif isinstance(parameter, NestedParameter):
                content = parameter.get_parameter_values_list()
            self._update_parameter_object_content(parameter.name, content)
        else:
            self._parameter_objects_dict.update({parameter.name: parameter})

    def set_parameter_via_content(self, parameter_name: str, content):

        if parameter_name in self._parameter_objects_dict:
            self._update_parameter_object_content(parameter_name, content)
        else:
            self._parameter_content_dict.update({parameter_name: content})

    def set_parameters(self, parameters_dict: dict):
        """Add or update multiple parameters given via content (value or values list) or as object."""

        for parameter_name in parameters_dict:
            if isinstance(parameters_dict[parameter_name], Parameter):
                self.set_parameter_object(parameters_dict[parameter_name])
            else:
                self.set_parameter_via_content(parameter_name, parameters_dict[parameter_name])

    def set_module(self, module):

        self._current_module = copy.deepcopy(module)

        parameter_list = self._get_module_parameters()

        for parameter in parameter_list:
            new_par = copy.deepcopy(parameter)
            par_name = parameter.name

            if par_name in self._parameter_objects_dict:
                previous_par = self._parameter_objects_dict[par_name]

                if isinstance(previous_par, SingleParameter) and isinstance(new_par, SingleParameter):
                    new_par.set_value(previous_par.value)
                if isinstance(previous_par, NestedParameter) and isinstance(new_par, NestedParameter):
                    new_par.set_parameter_values(previous_par.get_parameter_values_list())

            elif par_name in self._parameter_content_dict:
                if isinstance(new_par, SingleParameter):
                    new_par.set_value(self._parameter_content_dict[par_name])
                elif isinstance(new_par, NestedParameter):
                    new_par.set_parameter_values(self._parameter_content_dict[par_name])

            self._parameter_objects_dict.update({par_name: new_par})

    def get_all_parameters_content(self) -> dict:
        """Get content (value or list of values) of all parameters that have been added"""

        parameters_content = {}
        parameters_content.update(self._parameter_content_dict)
        parameters_content.update(self._get_parameter_objects_content())

        return parameters_content

    def get_all_parameter_objects(self) -> List[Union[SingleParameter, NestedParameter]]:
        return list(self._parameter_objects_dict.values())

    def get_module_parameters(self) -> List[Union[SingleParameter, NestedParameter]]:
        """Get parameter objects that belong to the current module"""

        default_module_parameters = self._get_module_parameters()

        current_parameters = []
        for parameter in default_module_parameters:
            if parameter.name in self._parameter_objects_dict:
                current_parameters.append(self._parameter_objects_dict[parameter.name])
            else:
                current_parameters.append(parameter)
        return current_parameters

    def get_module_values(self, var_and_epxr_values_dict: Optional[dict]=None, replace_free_parameters=True) -> dict:
        """
        :param var_and_epxr_values_dict: {name: value} has to be given if replace_free_parameters is True
        :return: module_values
        """

        module_values = {}

        for par_obj in self.get_module_parameters():
            par_name = par_obj.name
            if isinstance(par_obj, SingleParameter):
                module_values.update({par_name: par_obj.value})
            elif isinstance(par_obj, FloatParameter):
                if replace_free_parameters:
                    if par_obj.is_set_to_free_parameter.value:
                        if par_obj.free_par.value not in var_and_epxr_values_dict:
                            raise ValueError("Parameter value '" + str(par_obj.free_par.value)
                                             + "' not given as variable or expression")
                        module_values.update({par_name: var_and_epxr_values_dict[par_obj.free_par.value]})
                    else:
                        module_values.update({par_name: par_obj.float_par.value})
                else:
                    # module_values.update({par_name: par_obj})
                    if par_obj.is_set_to_free_parameter.value:
                        module_values.update({par_name: par_obj})
                    else:
                        module_values.update({par_name: par_obj.float_par.value})
            elif isinstance(par_obj, NestedParameter):
                module_values.update({par_name: par_obj.get_parameter_values_list()})
            elif isinstance(par_obj, MultivalueParameter):
                module_values.update({par_name: par_obj.get_parameter_values_list()})

        return module_values

    def get_used_free_parameters(self) -> (list, list):

        free_parameters_list = []           # ["VAR_0", "EXPR_1"]
        parameter_allocation_list = []      # [("angle": "VAR_0"), ..]
        for parameter_name in self._parameter_objects_dict:
            parameter = self._parameter_objects_dict[parameter_name]
            if isinstance(parameter, FloatParameter):
                if parameter.is_set_to_free_parameter.value:
                    value = parameter.get_current_value()
                    parameter_allocation_list.append((parameter.name, value))
                    if value not in free_parameters_list:
                        free_parameters_list.append(value)

        return free_parameters_list, parameter_allocation_list

    def _update_parameter_object_content(self, parameter_name, content):

        existing_parameter = self._parameter_objects_dict[parameter_name]
        if isinstance(existing_parameter, SingleParameter):
            existing_parameter.set_value(content)
        elif isinstance(existing_parameter, NestedParameter):
            existing_parameter.set_parameter_values(content)

    def _get_parameter_objects_content(self) -> dict:

        content_dict = {}

        for parameter_name in self._parameter_objects_dict:
            content = None
            parameter_object = self._parameter_objects_dict[parameter_name]

            if isinstance(parameter_object, SingleParameter):
                content = parameter_object.value
            elif isinstance(parameter_object, NestedParameter):
                content = parameter_object.get_parameter_values_list()

            content_dict.update({parameter_name: content})

        return content_dict

    def _get_module_parameters(self) -> List[Parameter]:
        parameter_list = []
        if self._current_module is not None:
            if self._category is ParameterCategory.GENERIC:
                parameter_list = self._current_module.generic_parameters
            elif self._category is ParameterCategory.EVALUATION_SET:
                parameter_list = self._current_module.evaluation_set_parameters
            else:
                layer_types_of_module = [layer.layer_type for layer in self._current_module.available_layers]
                if self._category in layer_types_of_module:
                    layer_type_idx = layer_types_of_module.index(self._category)
                    parameter_list = self._current_module.available_layers[layer_type_idx].parameters
        return parameter_list

