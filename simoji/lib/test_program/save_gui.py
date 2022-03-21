import PySide2.QtWidgets as QtWidgets
import PySide2.QtCore as QtCore
import PySide2.QtGui as QtGui

import sys, os


class MainWindow(QtWidgets.QMainWindow):
    """Window with several dockwidgets."""

    def __init__(self):
        super().__init__()

        color_list = ["red", "green", "blue"]

        for idx, color in enumerate(color_list):
            name = "dock" + str(idx)
            self.add_dock_widget(name , QtCore.Qt.LeftDockWidgetArea, color)

    def add_dock_widget(self, name: str, area: QtCore.Qt.DockWidgetArea, color: str):
        """Add a new dock widget to the main window"""

        dock = QtWidgets.QDockWidget()
        dock.setWindowTitle(name)
        dock.setWidget(QtWidgets.QWidget())
        dock.setObjectName(name)
        dock.objectName()
        dock.setStyleSheet("background-color: " + color)

        self.addDockWidget(area, dock)


class MainTabWindow(QtWidgets.QMainWindow):
    """Window with tabs that include dock widgets."""

    def __init__(self):
        super().__init__()

        self.settings = QtCore.QSettings(os.path.join("gui.ini"), QtCore.QSettings.IniFormat)

        self.tab_widget = QtWidgets.QTabWidget()
        self.setCentralWidget(self.tab_widget)

        main1 = MainWindow()
        main2 = MainWindow()

        self.tab_widget.addTab(main1, "tab1")
        self.tab_widget.addTab(main2, "tab2")

        self.restore_gui()

    def closeEvent(self, e) -> None:

        self.save_gui()
        self.close()

    def save_gui(self):

        for idx in range(self.tab_widget.count()):
            tab_name = "tab" + str(idx)

            dock_list = self.tab_widget.widget(idx).findChildren(QtWidgets.QDockWidget)
            for dock_widget in dock_list:
                dock_widget.setObjectName(tab_name + dock_widget.windowTitle())

            self.settings.setValue(tab_name + "_geometry", self.tab_widget.widget(idx).saveGeometry())
            self.settings.setValue(tab_name + "_state", self.tab_widget.widget(idx).saveState())

        self.settings.setValue('geometry', self.saveGeometry())
        self.settings.setValue('state', self.saveState())

    def restore_gui(self):

        for idx in range(self.tab_widget.count()):
            dock_list = self.tab_widget.widget(idx).findChildren(QtWidgets.QDockWidget)
            for dock_widget in dock_list:
                dock_widget.setObjectName("tab" + str(idx) + dock_widget.windowTitle())

        self.restoreGeometry(self.settings.value('geometry'))
        self.restoreState(self.settings.value('state'))

        for idx in range(self.tab_widget.count()):
            tab_name = "tab" + str(idx)
            self.tab_widget.widget(idx).restoreGeometry(self.settings.value(tab_name + "_geometry"))
            self.tab_widget.widget(idx).restoreState(self.settings.value(tab_name + "_state"))


if __name__ == "__main__":

    app = QtWidgets.QApplication(sys.argv)
    ex = MainTabWindow()
    ex.show()
    sys.exit(app.exec_())

