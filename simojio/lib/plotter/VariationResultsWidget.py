import csv

import PySide6.QtWidgets as QtWidgets
from simojio.lib.VariationResultsContainer import VariationResultsContainer
from simojio.lib.BasicFunctions import *


class VariationResultsWidget(QtWidgets.QWidget):

    def __init__(self, variation_results_container: VariationResultsContainer):
        super().__init__()

        self.layout = QtWidgets.QVBoxLayout()
        self.setLayout(self.layout)

        self.variation_results_container = variation_results_container

        self.nb_var_names = len(self.variation_results_container.variable_names)
        self.horizontal_header_list = self.variation_results_container.variable_names + \
                                      self.variation_results_container.result_names
        nb_cols = len(self.horizontal_header_list)
        nb_rows = len(self.variation_results_container.variable_values_list)
        self.vertical_header_list = variation_results_container.row_names

        self.table_widget = QtWidgets.QTableWidget(nb_rows, nb_cols, self)
        self.table_widget.setHorizontalHeaderLabels(self.horizontal_header_list)
        self.table_widget.setVerticalHeaderLabels(self.vertical_header_list)

        for idx_set, variable_set in enumerate(self.variation_results_container.variable_values_list):
            for idx_val, variable_value in enumerate(variable_set):
                variable_item = QtWidgets.QTableWidgetItem(str(variable_value))
                self.table_widget.setItem(idx_set, idx_val, variable_item)

        self.table_widget.resizeRowsToContents()
        self.layout.addWidget(self.table_widget)

    def update_variation_results_widget(self, variation_results_container: VariationResultsContainer):
        """
        Update result values that appear in the line with index 'idx'
        :param variation_results_container
        :return:
        """

        self.variation_results_container = variation_results_container

        # update variable values
        for idx_set, variable_set in enumerate(self.variation_results_container.variable_values_list):
            for idx_val, variable_value in enumerate(variable_set):
                variable_item = QtWidgets.QTableWidgetItem(str(variable_value))
                self.table_widget.setItem(idx_set, idx_val, variable_item)

        # update result values
        row_idx = variation_results_container.update_idx
        result_line = variation_results_container.variation_results_list[row_idx]
        for col_idx, value in enumerate(result_line):
            result_item = QtWidgets.QTableWidgetItem(str(value))
            self.table_widget.setItem(row_idx, col_idx + self.nb_var_names, result_item)

        self.table_widget.resizeRowsToContents()
        self.table_widget.setWordWrap(False)

    def save_data(self, save_path):

        def write_to_csv(path):
            with open(path, 'w') as stream:
                writer = csv.writer(stream)

                # write header
                writer.writerow(["variation set"] + self.horizontal_header_list)

                # write content
                for row in range(self.table_widget.rowCount()):
                    rowdata = [self.vertical_header_list[row]]
                    for column in range(self.table_widget.columnCount()):
                        item = self.table_widget.item(row, column)
                        if item is not None:
                            rowdata.append(item.text())
                        else:
                            rowdata.append('')
                    writer.writerow(rowdata)

        base_path, filename = os.path.split(save_path)
        filename += ".csv"

        write_to_csv(os.path.join(base_path, filename))
