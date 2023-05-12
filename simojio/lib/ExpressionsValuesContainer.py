from simojio.lib.parameters.Expression import Expression
import copy


class ExpressionsValuesContainer:

    def __init__(self):

        self.parameters = {}
        self.default_expression = Expression(name="default expression", value="1.")

    def set_values(self, value_dict: dict):

        for par_name in value_dict:
            try:
                parameter = copy.deepcopy(self.default_expression)
                parameter.name = par_name
                values, success = parameter.set_value(value_dict[par_name])
                value_dict.update({par_name: parameter})
            except:
                pass

        self.parameters.update(value_dict)

        # delete parameters that are not in value_dict
        del_pars = []
        for par_name in self.parameters:
            if par_name not in value_dict:
                del_pars.append(par_name)

        for par_name in del_pars:
            del self.parameters[par_name]

    def get_values(self) -> dict:
        return {par_name: self.parameters[par_name].get_value() for par_name in self.parameters}

    def get_parameters(self) -> list:
        return [self.parameters[name] for name in self.parameters]
