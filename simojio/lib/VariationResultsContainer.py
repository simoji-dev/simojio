
class VariationResultsContainer:

    def __init__(self):

        self.row_names = list()                 # ["variation set 1"]

        self.variable_names = list()            # ["VAR_0", "VAR_1"]
        self.variable_values_list = list()      # [[10, 0.1], [20, 0.1]]

        self.result_names = list()              # ["efficiency"]
        self.variation_results_list = list()    # [[40], [50]] -> e.g. calculated efficiency for given variable set

        self.update_idx = 0
        self.plot_flag = True

    def get_nb_of_variations(self) -> int:
        return len(self.variable_values_list)
