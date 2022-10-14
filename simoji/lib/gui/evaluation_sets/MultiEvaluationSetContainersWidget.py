import PySide2.QtWidgets as QtWidgets
import PySide2.QtCore as QtCore
from PySide2.QtCore import Signal
from typing import List, Callable

from simoji.lib.ParameterContainer import ParameterContainer
from simoji.lib.enums.ParameterCategory import ParameterCategory
from simoji.lib.gui.evaluation_sets.EvaluationSetContainerWidget import EvaluationSetContainerWidget


class MultiEvaluationSetContainersWidget(QtWidgets.QMainWindow):
    """Contains multiple parameter container widgets that can be moved around as dock widgets."""

    add_parameter_container_sig = Signal()
    float_par_added_sig = QtCore.Signal(QtWidgets.QWidget)

    def __init__(self):

        super().__init__()

        self._current_module = None

        self.parameter_container_list = []
        self.dock_widget_list = []

        self.window_title_prefix = "evaluation_set_"
        self.auto_rename_container_widgets = True

        self.setDockOptions(QtWidgets.QMainWindow.AnimatedDocks)

        # context menu
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.on_context_menu)
        self.popMenu = QtWidgets.QMenu(self)

        # create context menu actions
        self.add_action = QtWidgets.QAction("add evaluation set", self)
        self.add_context_menu_action(self.add_action, self._add_evaluation_set_clicked)

        self.remove_all_action = QtWidgets.QAction("remove all", self)
        self.add_context_menu_action(self.remove_all_action, self._remove_all_clicked)

    def set_parameter_container_list(self, parameter_container_list: List[ParameterContainer]):

        # replace current list of ParameterContainers
        self.parameter_container_list = self._edit_parameter_container_list(parameter_container_list)

        # remove previous widgets
        for dock_widget in self.dock_widget_list:
            self.removeDockWidget(dock_widget)
            dock_widget.deleteLater()

        self.dock_widget_list = []

        # add new dock widgets
        for parameter_container in parameter_container_list:
            self._add_dockwidget(parameter_container)

    def add_parameter_container(self, parameter_container: ParameterContainer):
        self._add_dockwidget(parameter_container)

    def get_parameter_container_list(self) -> List[ParameterContainer]:

        try:
            dockwidgets_position_list = sorted([[dock_widget.y(), dock_widget] for dock_widget in self.dock_widget_list])
            sorted_dockwidgets = [item[1] for item in dockwidgets_position_list]
        except:
            sorted_dockwidgets = self.dock_widget_list

        self.parameter_container_list = []
        for dock_widget in sorted_dockwidgets:
            self.parameter_container_list.append(dock_widget.widget().get_parameter_container())

        return self.parameter_container_list

    def set_module(self, module):

        self._current_module = module

        for dock_widget in self.dock_widget_list:
            dock_widget.widget().set_module(module)

    @staticmethod
    def _edit_parameter_container_list(parameter_container_list: List[ParameterContainer]) -> List[
        ParameterContainer]:
        return parameter_container_list

    def _add_dockwidget(self, parameter_container: ParameterContainer):

        parameter_container_widget = EvaluationSetContainerWidget()
        parameter_container_widget.set_parameter_container(parameter_container)
        parameter_container_widget.delete_evaluation_set_sig.connect(self._delete_container)
        parameter_container_widget.add_evaluation_set_sig.connect(self._add_evaluation_set_clicked)
        parameter_container_widget.float_par_added_sig.connect(self.float_par_added)
        parameter_container_widget.duplicate_evaluation_set_sig.connect(self._duplicate_container)
        parameter_container_widget.remove_all_sig.connect(self._remove_all_clicked)

        try:
            for item in self.dock_widget_context_menu_list:
                parameter_container_widget.add_context_menu_action(item[0], item[1])
        except:
            pass

        title = self.window_title_prefix + str(len(self.dock_widget_list))
        dock_widget = self._get_dockwidget(title=title, widget=parameter_container_widget)

        self.addDockWidget(QtCore.Qt.LeftDockWidgetArea, dock_widget)
        self.dock_widget_list.append(dock_widget)

    def _get_dockwidget(self, title: str, widget: QtWidgets.QWidget, movable=True) -> QtWidgets.QDockWidget:

        dockWidget = QtWidgets.QDockWidget(self)
        if movable:
            dockWidget.setFeatures(QtWidgets.QDockWidget.DockWidgetMovable)
        else:
            dockWidget.setFeatures(QtWidgets.QDockWidget.NoDockWidgetFeatures)
        dockWidget.setWindowTitle(title)
        dockWidget.setStyleSheet("QDockWidget {border: None;}")
        dockWidget.setWidget(widget)
        dockWidget.topLevelChanged.connect(self.rename_evaluation_sets)
        dockWidget.setAllowedAreas(QtCore.Qt.LeftDockWidgetArea)

        return dockWidget

    def rename_evaluation_sets(self):

        if self.auto_rename_container_widgets:
            positions_dockwidget_list = sorted([[dockwidget.y(), dockwidget] for dockwidget in self.dock_widget_list])
            sorted_dockwidgets = [dockwidget for (pos, dockwidget) in positions_dockwidget_list]

            for idx in range(len(sorted_dockwidgets)):
                sorted_dockwidgets[idx].setWindowTitle(self.window_title_prefix + str(idx))

    def on_context_menu(self, point):
        self.popMenu.exec_(self.mapToGlobal(point))

    def add_context_menu_action(self, action: QtWidgets.QAction, connected_method: Callable):
        action.triggered.connect(connected_method)
        self.popMenu.addAction(action)

    def _delete_container(self, parameter_container_widget: EvaluationSetContainerWidget):

        idx = -1
        for idx, dock_widget in enumerate(self.dock_widget_list):
            if dock_widget.widget() is parameter_container_widget:
                break

        if idx >= 0:
            self.removeDockWidget(self.dock_widget_list[idx])
            self.dock_widget_list[idx].deleteLater()
            del self.dock_widget_list[idx]

        self.rename_evaluation_sets()

    def _duplicate_container(self, parameter_container: ParameterContainer):

        parameter_container.set_module(self._current_module)
        self.add_parameter_container(parameter_container)
        self.set_module(self._current_module)

    def _add_evaluation_set_clicked(self):
        parameter_container = ParameterContainer(ParameterCategory.EVALUATION_SET)
        parameter_container.set_module(self._current_module)
        self.add_parameter_container(parameter_container)
        self.set_module(self._current_module)

    def _remove_all_clicked(self):
        """Remove all data sets"""

        for dock_widget in self.dock_widget_list:
            self.removeDockWidget(dock_widget)
            dock_widget.deleteLater()
        self.dock_widget_list = []

    def float_par_added(self, widget: QtWidgets.QWidget):
        self.float_par_added_sig.emit(widget)




