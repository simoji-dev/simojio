import PySide6.QtWidgets as QtWidgets

from simojio.lib.gui.optimization_settings.OptimizationSettingsWidget import OptimizationSettingsWidget
from simojio.lib.OptimizationSettingsContainer import OptimizationSettingsContainer
from simojio.lib.abstract_modules import AbstractModule


class OptimizationSettingsScrollWidget(QtWidgets.QScrollArea):

    def __init__(self, show_sample_related_settings=True):
        super().__init__()

        self.optimization_settings_widget = OptimizationSettingsWidget(show_sample_related_settings)
        self.setWidget(self.optimization_settings_widget)
        self.setWidgetResizable(True)

    def get_settings_container(self) -> OptimizationSettingsContainer:
        return self.optimization_settings_widget.get_settings()

    def set_settings_container(self, opt_container: OptimizationSettingsContainer):
        self.optimization_settings_widget.update_settings(opt_container)

    def enable_solver_settings(self, enable: bool):
        self.optimization_settings_widget.enable_solver_settings(enable)

    def set_module(self, module: AbstractModule):
        self.optimization_settings_widget.set_module(module)