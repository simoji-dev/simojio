import PySide2.QtWidgets as QtWidgets
import PySide2.QtCore as QtCore
import PySide2.QtGui as QtGui

from simoji.lib.CompleteLayer import CompleteLayer
from simoji.lib.gui.Dialogs import select_from_combobox
from simoji.lib.enums.LayerType import LayerType
from simoji.lib.gui.layers.LayerWidget import LayerWidget
from simoji.lib.gui.layers.LayerHeaderWidget import LayerHeaderWidget

from typing import Callable
import copy


class LayerStackWidget(QtWidgets.QMainWindow):

    float_par_added_sig = QtCore.Signal(QtWidgets.QWidget)

    def __init__(self):

        super().__init__()

        self.current_module = None

        self.setDockOptions(QtWidgets.QMainWindow.AnimatedDocks)
        self.setCorner(QtCore.Qt.Corner.TopLeftCorner, QtCore.Qt.TopDockWidgetArea)
        self.setCorner(QtCore.Qt.Corner.BottomLeftCorner, QtCore.Qt.BottomDockWidgetArea)

        self.layer_types = []
        self.layer_list = []
        self.layerWidget_dockWidget_dict = {}
        self.layerHeader_layerWidget_dict = {}

        self.layer_type_default_colors = {
            LayerType.STANDARD: (200, 200, 0, 100),
            LayerType.COHERENT: (0, 200, 0, 100),
            LayerType.SEMI: (255, 255, 255, 100),
            LayerType.SUBSTRATE: (0, 0, 200, 50),
            LayerType.ELECTRODE: (0, 0, 0, 100),
            LayerType.INTERFACE: (200, 200, 0, 100),
            LayerType.TRANSPORT: (0, 200, 200, 100)
        }

        central_widget = QtWidgets.QWidget()
        central_widget.setMaximumWidth(0)
        self.setCentralWidget(central_widget)

        # set context menu policy
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.on_context_menu)

        # create context menu
        self.popMenu = QtWidgets.QMenu(self)

        # create context menu actions
        self.add_action = QtWidgets.QAction("add layer", self)
        self.add_context_menu_action(self.add_action, self.add_layer_clicked)

        self.collapse_all_action = QtWidgets.QAction("collapse all", self)
        self.add_context_menu_action(self.collapse_all_action, self._collapse_all_clicked)

        self.remove_all_action = QtWidgets.QAction("remove all", self)
        self.add_context_menu_action(self.remove_all_action, self._remove_all_clicked)

    def set_layer_list(self, layer_list: list):

        # delete existing layers
        for layer_widget in self.layerWidget_dockWidget_dict:
            dockwidget = self.layerWidget_dockWidget_dict[layer_widget]
            self.removeDockWidget(dockwidget)
            dockwidget.deleteLater()

        self.layerWidget_dockWidget_dict = {}
        self.layer_list = []
        self.layer_types = []

        # check for right positions of semi layers
        # -> the stack should always have a semi layer at the first and last position and nowhere else
        # -> if the semi layers will be shown, depends on the module

        corrected_layer_list = []
        for idx, layer in enumerate(layer_list):
            if layer.layer_type is LayerType.SEMI:
                if idx in [0, len(layer_list) - 1]:
                    corrected_layer_list.append(layer)
            else:
                corrected_layer_list.append(layer)

        if len(layer_list) == 0:
            corrected_layer_list = [
                CompleteLayer(name="top semi", layer_type=LayerType.SEMI, enabled=True,
                              color=self.layer_type_default_colors[LayerType.SEMI]),
                CompleteLayer(name="bottom semi", layer_type=LayerType.SEMI, enabled=True,
                              color=self.layer_type_default_colors[LayerType.SEMI])
            ]
        else:
            if layer_list[0].layer_type is not LayerType.SEMI:
                corrected_layer_list = [CompleteLayer(name="top semi", layer_type=LayerType.SEMI, enabled=True,
                                                      color=self.layer_type_default_colors[LayerType.SEMI])] + corrected_layer_list
            if (layer_list[-1].layer_type is not LayerType.SEMI) or (len(layer_list) == 1):
                corrected_layer_list.append(CompleteLayer(name="bottom semi", layer_type=LayerType.SEMI, enabled=True,
                                                          color=self.layer_type_default_colors[LayerType.SEMI]))

        # add new layers
        for idx, layer in enumerate(corrected_layer_list):
            self.add_layer(layer, idx)
            if layer.layer_type not in self.layer_types:
                self.layer_types.append(layer.layer_type)

    def get_layer_list(self) -> list:

        layers_unsorted = []
        for layer_widget in self.layerWidget_dockWidget_dict:
            layers_unsorted.append([self.layerWidget_dockWidget_dict[layer_widget].y(), layer_widget.get_layer()])

        try:
            self.layer_list = [item[1] for item in sorted(layers_unsorted)]
        except:
            # It can happen that layers have never been shown but still are present because they are defined in a module
            # that was not selected yet. In this case their y-position is always zero and you end up having multiple
            # layers at position zero which makes it impossible to store the layers in a sorted list. To avoid this,
            # all layer-widgets have to be shown once and after that their y-positions are read.
            for layer_widget in self.layerWidget_dockWidget_dict:
                self.layerWidget_dockWidget_dict[layer_widget].show()
            layers_unsorted = []
            for layer_widget in self.layerWidget_dockWidget_dict:
                layers_unsorted.append([self.layerWidget_dockWidget_dict[layer_widget].y(), layer_widget.get_layer()])

            for layer_widget in self.layerWidget_dockWidget_dict:
                if layer_widget.layer.layer_type not in [layer.layer_type for layer in self.current_module.available_layers]:
                    self.layerWidget_dockWidget_dict[layer_widget].hide()

        return self.layer_list

    def set_module(self, module):
        self.current_module = copy.deepcopy(module)

        available_layer_types = [layer.layer_type for layer in module.available_layers]
        for layer_widget in self.layerWidget_dockWidget_dict:
            layer_widget.set_module(module)
            dockwidget = self.layerWidget_dockWidget_dict[layer_widget]
            if layer_widget.layer.layer_type in available_layer_types:
                dockwidget.show()
            else:
                dockwidget.hide()

    def add_layer(self, layer: CompleteLayer, idx=-1):

        layer_copy = copy.deepcopy(layer)

        self.layer_list.append(layer_copy)

        # create layer widget + connect signals
        layer_widget = LayerWidget(layer_copy)
        layer_widget.add_layer_sig.connect(self.add_layer_clicked)
        layer_widget.rename_layer_sig.connect(self.rename_layer)
        if layer_copy.layer_type is not LayerType.SEMI:
            layer_widget.del_layer_sig.connect(self.del_layer)
        layer_widget.set_color_sig.connect(self.set_dockwidget_titlebar_widget)
        layer_widget.float_par_added_sig.connect(self.float_par_added)
        layer_widget.collapse_all_sig.connect(self._collapse_all_clicked)
        layer_widget.remove_all_sig.connect(self._remove_all_clicked)

        # create dock widget and fill it with layer widget
        if layer_copy.layer_type is LayerType.SEMI:
            dockWidget = self.get_dockwidget(layer_copy.name, layer_widget, movable=False)
            if idx == 0:
                self.addDockWidget(QtCore.Qt.TopDockWidgetArea, dockWidget)
            else:
                self.addDockWidget(QtCore.Qt.BottomDockWidgetArea, dockWidget)
        else:
            dockWidget = self.get_dockwidget(layer_copy.name, layer_widget, movable=True)
            self.addDockWidget(QtCore.Qt.LeftDockWidgetArea, dockWidget)

        # store assignment layer_widget - dock_widget
        self.layerWidget_dockWidget_dict.update({layer_widget: dockWidget})

        return layer_widget

    def add_layer_clicked(self):

        available_types = [layer.layer_type for layer in self.current_module.available_layers
                           if (isinstance(layer.layer_type, LayerType) and layer.layer_type is not LayerType.SEMI)]
        selected_item, ok = select_from_combobox(parent=self,
                                                 combobox_items=available_types,
                                                 title="Add layer",
                                                 text="Choose layer type to be added:")
        if ok:
            new_layer = self.get_default_layer(LayerType(selected_item))
            new_layer.set_module(self.current_module)
            layer_widget = self.add_layer(new_layer, idx=-1)
            layer_widget.set_module(self.current_module)

    def rename_layer(self, widget: LayerWidget):
        dockWidget = self.layerWidget_dockWidget_dict[widget]
        entered_name, okPressed = QtWidgets.QInputDialog.getText(self, "Rename layer", "Enter layer name:",
                                                                 QtWidgets.QLineEdit.Normal, dockWidget.windowTitle())
        if okPressed:
            widget.layer.name = entered_name
            dockWidget.setWindowTitle(entered_name)
            layer_header = LayerHeaderWidget(widget.layer)
            layer_header.minimize_sig.connect(self.arrow_button_clicked)
            self.layerHeader_layerWidget_dict.update({layer_header: widget})
            dockWidget.setTitleBarWidget(layer_header)

    def _collapse_all_clicked(self):
        for layer_widget in self.layerWidget_dockWidget_dict:
            dockWidget = self.layerWidget_dockWidget_dict[layer_widget]
            dockWidget.titleBarWidget().set_parameters_minimized(True)
            layer_widget.hide_parameters()

    def _remove_all_clicked(self):

        layer_widget_remove = []
        for layer_widget in self.layerWidget_dockWidget_dict:
            if layer_widget.layer.layer_type is not LayerType.SEMI:         # keep semi layers (always there)
                dockwidget = self.layerWidget_dockWidget_dict[layer_widget]
                self.removeDockWidget(dockwidget)
                dockwidget.deleteLater()
                layer_widget.deleteLater()
                layer_widget_remove.append(layer_widget)
                del self.layer_list[self.layer_list.index(layer_widget.layer)]

        for layer_widget in layer_widget_remove:
            del self.layerWidget_dockWidget_dict[layer_widget]

    def get_default_layer(self, layer_type: LayerType) -> CompleteLayer:

        color = (0, 0, 0, 200)
        if layer_type in self.layer_type_default_colors:
            color = self.layer_type_default_colors[layer_type]

        layer = CompleteLayer(name='layer', layer_type=layer_type, enabled=True, color=color)
        layer.set_module(self.current_module)
        return layer

    def del_layer(self, widget: LayerWidget):
        dockwidget = self.layerWidget_dockWidget_dict[widget]
        self.removeDockWidget(dockwidget)
        dockwidget.deleteLater()
        widget.deleteLater()
        del self.layerWidget_dockWidget_dict[widget]
        del self.layer_list[self.layer_list.index(widget.layer)]

    def get_dockwidget(self, name: str, widget: QtWidgets.QWidget, movable=True) -> QtWidgets.QDockWidget:

        dockWidget = QtWidgets.QDockWidget(self)
        if movable:
            dockWidget.setFeatures(QtWidgets.QDockWidget.DockWidgetMovable)
        else:
            dockWidget.setFeatures(QtWidgets.QDockWidget.NoDockWidgetFeatures)
        dockWidget.setWindowTitle(name)
        dockWidget.setStyleSheet("QDockWidget {border: None;}")
        dockWidget.setWidget(widget)
        dockWidget.setAllowedAreas(QtCore.Qt.LeftDockWidgetArea)
        layer_header = LayerHeaderWidget(widget.layer)
        layer_header.minimize_sig.connect(self.arrow_button_clicked)
        self.layerHeader_layerWidget_dict.update({layer_header: widget})
        dockWidget.setTitleBarWidget(layer_header)

        return dockWidget

    def on_context_menu(self, point):
        # show context menu
        self.popMenu.exec_(self.mapToGlobal(point))

    def add_context_menu_action(self, action: QtWidgets.QAction, connected_method: Callable):
        action.triggered.connect(connected_method)
        self.popMenu.addAction(action)

    def set_dockwidget_titlebar_widget(self, widget: LayerWidget):
        dockWidget = self.layerWidget_dockWidget_dict[widget]
        layer_header = LayerHeaderWidget(widget.layer)
        layer_header.minimize_sig.connect(self.arrow_button_clicked)
        self.layerHeader_layerWidget_dict.update({layer_header: widget})
        dockWidget.setTitleBarWidget(layer_header)

    def float_par_added(self, widget: QtWidgets.QWidget):
        self.float_par_added_sig.emit(widget)

    def arrow_button_clicked(self, header_widget: QtWidgets.QGroupBox):
        parameters_widget = self.layerHeader_layerWidget_dict[header_widget]
        parameters_widget.parameters_minimized = not parameters_widget.parameters_minimized
        if parameters_widget.parameters_minimized:
            parameters_widget.hide_parameters()
        else:
            parameters_widget.show_parameters()

        header_widget.set_parameters_minimized(parameters_widget.parameters_minimized)





