from scipy.optimize import OptimizeResult


class OptimizationResultsContainer:

    def __init__(self):

        # basic results
        self.optimized_value_name = None
        self.optimized_value = None
        self.variable_dict = {}
        self.solver_name = None
        self.success = False
        self.maximize = False

        # all results returned by the solver
        self.results_dict = {}

        # variables_and_expressions that are at of the boundary values
        self.variables_out_of_bounds_dict = {}

    def set_results(self, optimized_value_name: str, variable_names: list, variable_bounds: list, solver_name: str,
                    maximize: bool, results_obj: OptimizeResult):

        # if maximize, the negative function (-f) is minimized -> replace 'fun' value in results
        self.maximize = maximize
        if self.maximize:
           results_obj.fun = - results_obj.fun

        # optimized value
        self.optimized_value_name = optimized_value_name
        self.optimized_value = results_obj.fun

        # variables_and_expressions
        for idx, var_name in enumerate(variable_names):
            try:
                var_value = results_obj.x[idx]
            except:
                var_value = [results_obj.x][idx]

            # check, if variables_and_expressions are within bounds
            if (var_value >= max(variable_bounds[idx])) or (var_value <= min(variable_bounds[idx])):
                self.variables_out_of_bounds_dict.update({var_name: var_value})

            self.variable_dict.update({var_name: var_value})

        # solver and success bool
        self.solver_name = solver_name
        self.success = results_obj.success

        # complete results dict
        for key in results_obj.keys():
            value = results_obj.get(key)
            self.results_dict.update({key: value})



