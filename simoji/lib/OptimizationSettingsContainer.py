
class OptimizationSettingsContainer():
    """Contains optimization mode settings of simoji"""

    def __init__(self, include_sample_related_settings: bool):

        self.include_sample_related_settings = include_sample_related_settings

        # sample related settings
        self.name_of_value_to_be_optimized = None

        # solver related settings
        self.maximize = False
        self.list_of_solvers = ["Nelder-Mead",
                                "Powell",
                                "CG",
                                "BFGS",
                                # "Newton-CG",      # Jacobian required as input
                                "L-BFGS-B",
                                "TNC",
                                # "COBYLA",         # doesn't change coordinate but only the value
                                "SLSQP",
                                "trust-constr",
                                # "dogleg",         # Jacobian required as input
                                # "trust-ncg",      # Jacobian required as input
                                # "trust-exact",    # Jacobian required as input
                                # "trust-krylov"    # Jacobian required as input
                                ]

        self.current_solver = self.list_of_solvers[0]
        self.maximum_number_of_iterations = 1000
        self.plot_every_steps = 1

        # todo: add further parameters
        # self.precision = 1.e-9
        # self.maximum_number_of_iterations = 1000

        # define keys for storing the properties in the settings file
        self.maximize_key = "maximize"
        self.name_of_value_to_be_optimized_key = "name_of_value_to_be_optimized"
        self.current_solver_key = "solver"
        self.maximum_number_of_iterations_key = "maximum_number_of_iterations"
        self.plot_every_steps_key = "plot_every_steps"

    def get_properties_as_dict(self) -> dict:
        """
        Return dictionary of properties to store in settings file
        :return:
        """

        property_dict = {}

        if self.include_sample_related_settings:
            property_dict.update({
                self.name_of_value_to_be_optimized_key: self.name_of_value_to_be_optimized
            })

        property_dict.update({
            self.maximize_key: self.maximize,
            self.current_solver_key: self.current_solver,
            self.maximum_number_of_iterations_key: self.maximum_number_of_iterations,
            self.plot_every_steps_key: self.plot_every_steps
        })

        return property_dict

    def set_properties_from_dict(self, property_dict: dict):

        if self.include_sample_related_settings:
            if self.name_of_value_to_be_optimized_key in property_dict:
                self.name_of_value_to_be_optimized = property_dict[self.name_of_value_to_be_optimized_key]

        if self.maximize_key in property_dict:
            if isinstance(property_dict[self.maximize_key], bool):
                self.maximize = property_dict[self.maximize_key]

        if self.current_solver_key in property_dict:
            if isinstance(property_dict[self.current_solver_key], str):
                if property_dict[self.current_solver_key] in self.list_of_solvers:
                    self.current_solver = property_dict[self.current_solver_key]

        if self.maximum_number_of_iterations_key in property_dict:
            if isinstance(property_dict[self.maximum_number_of_iterations_key], int):
                self.maximum_number_of_iterations = property_dict[self.maximum_number_of_iterations_key]

        if self.plot_every_steps_key in property_dict:
            if isinstance(property_dict[self.plot_every_steps_key], int):
                self.plot_every_steps = property_dict[self.plot_every_steps_key]