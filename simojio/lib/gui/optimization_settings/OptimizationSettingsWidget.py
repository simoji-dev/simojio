import PySide2.QtWidgets as QtWidgets
import PySide2.QtGui as QtGui
from PySide2.QtCore import Signal

from simojio.lib.OptimizationSettingsContainer import OptimizationSettingsContainer
from simojio.lib.gui.OptionsWidget import OptionsWidget
from simojio.lib.abstract_modules import AbstractModule, Calculator, Fitter


class OptimizationSettingsWidget(OptionsWidget):
    global_toggled_sig = Signal(OptimizationSettingsContainer)

    def __init__(self, show_sample_related_settings=True):

        super().__init__()

        self.optimization_settings_container = OptimizationSettingsContainer(show_sample_related_settings)

        self.show_sample_related_settings = show_sample_related_settings
        self.current_module = None

        # -- sample related settings --
        if show_sample_related_settings:
            self.sample_related_options_header_str = "Sample related settings:"
            self.add_category(self.sample_related_options_header_str)

            # value to be optimized
            self.value_to_be_optimized_label = "value to be optimized:"
            self.value_to_be_optimized_combo = QtWidgets.QComboBox()
            self.value_to_be_optimized_combo.activated[str].connect(self._update_name_of_value_to_be_optimized)

            # add options to category
            self.add_option_to_category(category_name=self.sample_related_options_header_str,
                                        option_label=self.value_to_be_optimized_label,
                                        option_widget=self.value_to_be_optimized_combo)

        # -- solver related settings --
        self.solver_related_options_header_str = "Solver related settings:"
        self.add_category(self.solver_related_options_header_str)

        # solver
        self.solver_label = "solver:"
        self.solver_combo = QtWidgets.QComboBox()
        self.solver_combo.activated[str].connect(self._update_solver)

        # maximize
        self.maximize_label = "maximize:"
        self.maximize_checkbox = QtWidgets.QCheckBox('')
        self.maximize_checkbox.setChecked(False)

        # maximum number of iterations
        self.max_number_of_iterations_label = "maximum number of iterations"
        self.max_number_of_iterations_edit = QtWidgets.QLineEdit(self)
        self.max_number_of_iterations_edit.setValidator(QtGui.QIntValidator(1, 1000000, self))

        # plot every steps
        self.plot_every_steps_label = "plot every steps:"
        self.plot_every_steps_edit = QtWidgets.QComboBox()
        self.first_and_last_text = "first and last"
        self.plot_every_steps_edit.addItems(["1", "2", "5", "10", "50", "100", self.first_and_last_text])

        # add options to category
        self.add_option_to_category(category_name=self.solver_related_options_header_str,
                                    option_label=self.solver_label,
                                    option_widget=self.solver_combo)

        self.add_option_to_category(category_name=self.solver_related_options_header_str,
                                    option_label=self.maximize_label,
                                    option_widget=self.maximize_checkbox)

        self.add_option_to_category(category_name=self.solver_related_options_header_str,
                                    option_label=self.max_number_of_iterations_label,
                                    option_widget=self.max_number_of_iterations_edit)

        self.add_option_to_category(category_name=self.solver_related_options_header_str,
                                    option_label=self.plot_every_steps_label,
                                    option_widget=self.plot_every_steps_edit)

    def set_module(self, module: AbstractModule):
        """Update list of optimization value names"""

        self.current_module = module
        self.enable_maximize_checkbox()

        if self.show_sample_related_settings:
            previous_value = self.value_to_be_optimized_combo.currentText()
            new_values = []
            if isinstance(module, Calculator) or isinstance(module, Fitter):
                new_values = list(module.get_results_dict().keys())
            self.value_to_be_optimized_combo.clear()
            self.value_to_be_optimized_combo.addItems(new_values)
            if previous_value in new_values:
                self.value_to_be_optimized_combo.setCurrentText(previous_value)

    def _update_name_of_value_to_be_optimized(self, name_of_value_to_be_optimized: str):
        self.optimization_settings_container.name_of_value_to_be_optimized = name_of_value_to_be_optimized

    def _update_solver(self, solver_name: str):
        self.optimization_settings_container.current_solver = solver_name

    def update_settings(self, opt_set_container: OptimizationSettingsContainer):
        self.optimization_settings_container = opt_set_container

        # -- sample related settings --
        if self.show_sample_related_settings:

            # value to be optimized
            self.value_to_be_optimized_combo.clear()
            self.value_to_be_optimized_combo.addItem(opt_set_container.name_of_value_to_be_optimized)

        # -- solver related settings --
        # maximize
        self.maximize_checkbox.setChecked(opt_set_container.maximize)

        # solver
        self.solver_combo.clear()
        self.solver_combo.addItems(opt_set_container.list_of_solvers)
        current_idx = self.solver_combo.findText(opt_set_container.current_solver)
        self.solver_combo.setCurrentIndex(current_idx)

        # maximum number of iterations
        self.max_number_of_iterations_edit.setText(str(opt_set_container.maximum_number_of_iterations))

        # plot every steps
        if opt_set_container.plot_every_steps < 1e3:
            self.plot_every_steps_edit.setCurrentText(str(opt_set_container.plot_every_steps))
        else:
            self.plot_every_steps_edit.setCurrentText(self.first_and_last_text)

    def get_settings(self) -> OptimizationSettingsContainer:
        """Read current values from widgets and store in optimization_settings_container"""

        if self.show_sample_related_settings:
            self.optimization_settings_container.name_of_value_to_be_optimized = self.value_to_be_optimized_combo.currentText()

        self.optimization_settings_container.maximize = self.maximize_checkbox.isChecked()
        self.optimization_settings_container.maximum_number_of_iterations = int(
            self.max_number_of_iterations_edit.text())
        if self.plot_every_steps_edit.currentText() == self.first_and_last_text:
            self.optimization_settings_container.plot_every_steps = 1e6
        else:
            self.optimization_settings_container.plot_every_steps = int(self.plot_every_steps_edit.currentText())

        return self.optimization_settings_container

    def enable_solver_settings(self, enable: bool):
        self.enable_category(self.solver_related_options_header_str, enable)

    def enable_maximize_checkbox(self):
        if isinstance(self.current_module, Fitter):
            self.maximize_checkbox.hide()
            self.option_label_widget_dict[self.maximize_label].hide()
        else:
            self.maximize_checkbox.show()
            self.option_label_widget_dict[self.maximize_label].show()
