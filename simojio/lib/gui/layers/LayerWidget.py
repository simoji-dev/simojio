import PySide2.QtWidgets as QtWidgets
import PySide2.QtGui as QtGui
from PySide2.QtCore import Signal

from simojio.lib.CompleteLayer import CompleteLayer
from simojio.lib.enums.LayerType import LayerType
from simojio.lib.gui.parameter_container_widgets.ParameterContainerWidget import ParameterContainerWidget


class LayerWidget(ParameterContainerWidget):

    add_layer_sig = Signal(CompleteLayer)
    rename_layer_sig = Signal(CompleteLayer)
    del_layer_sig = Signal(CompleteLayer)
    set_color_sig = Signal(QtWidgets.QGroupBox)
    collapse_all_sig = Signal()
    remove_all_sig = Signal()

    def __init__(self, layer: CompleteLayer):

        super().__init__()

        self.layer = layer
        self.set_parameter_container(layer)

        self.parameters_minimized = False

        self.set_color(layer.color)

        # create context menu actions
        self.add_action = QtWidgets.QAction("add layer", self)
        self.add_context_menu_action(self.add_action, self.add_clicked)

        self.rename_action = QtWidgets.QAction("rename layer", self)
        self.add_context_menu_action(self.rename_action, self.rename_clicked)

        self.collapse_all_action = QtWidgets.QAction("collapse all", self)
        self.add_context_menu_action(self.collapse_all_action, self._collapse_all_clicked)

        self.remove_all_action = QtWidgets.QAction("remove all", self)
        self.add_context_menu_action(self.remove_all_action, self._remove_all_clicked)

        if self.layer.layer_type is not LayerType.SEMI:
            self.delete_action = QtWidgets.QAction("delete layer", self)
            self.add_context_menu_action(self.delete_action, self.delete_clicked)

        self.set_color_action = QtWidgets.QAction("set color", self)
        self.add_context_menu_action(self.set_color_action, self.open_color_dialog)

    def add_clicked(self):
        self.add_layer_sig.emit(self.layer)

    def rename_clicked(self):
        self.rename_layer_sig.emit(self)

    def delete_clicked(self):
        self.del_layer_sig.emit(self)

    def _collapse_all_clicked(self):
        self.collapse_all_sig.emit()

    def _remove_all_clicked(self):
        self.remove_all_sig.emit()

    def open_color_dialog(self):
        opt = QtWidgets.QColorDialog.ShowAlphaChannel
        initial_color = QtGui.QColor(*self.layer.color)
        title = 'Select layer color'
        color = QtWidgets.QColorDialog.getColor(initial=initial_color, parent=self, title=title, options=opt)
        self.set_color(color.toTuple())

    def set_color(self, color: tuple):
        self.layer.color = color
        self.setStyleSheet("QGroupBox { border: None; background-color: rgba" + str(self.layer.color) + ";}")
        self.set_color_sig.emit(self)

    def get_color(self) -> tuple:
        return self.layer.color

    def get_layer(self) -> CompleteLayer:
        self.layer.set_parameters(self.get_parameter_container().get_all_parameters_content())
        return self.layer

    def hide_parameters(self):
        self.parameters_minimized = True
        self.setMaximumHeight(0)
        for widget in self.widget_dict.values():
            widget.hide()

    def show_parameters(self):
        self.parameters_minimized = False
        self.setMaximumHeight(1000)
        for widget in self.widget_dict.values():
            widget.show()
