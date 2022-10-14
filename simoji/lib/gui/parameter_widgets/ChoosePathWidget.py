import PySide2.QtGui as QtGui

from simoji.lib.gui.parameter_widgets.ParameterWidget import ParameterWidget
from simoji.lib.parameters.PathParameter import PathParameter

from simoji.lib.BasicFunctions import *
from simoji.lib.gui.Dialogs import *


class ChoosePathWidget(ParameterWidget):

    def __init__(self, parameter: PathParameter, is_sub_parameter=False):

        super().__init__(parameter, is_sub_parameter)

        self.parameter = parameter

        try:
            path = convert_list_to_path_str(parameter.value)
        except:
            path = os.getcwd()

        self.value_widget = QtWidgets.QLineEdit(path)
        self.value_widget.setReadOnly(True)
        self.add_value_widget(self.value_widget)

        self.open_file_dialog_button = QtWidgets.QPushButton(QtGui.QIcon(icon_path('open.svg')), "")
        self.open_file_dialog_button.clicked.connect(self._open_dialog)
        self.add_value_widget(self.open_file_dialog_button)

    def set_content(self, content):
        content, success = self.parameter.set_value(content)
        self.value_widget.setText(convert_list_to_path_str(content))

    def get_content(self):
        return convert_path_str_to_list(self.value_widget.text())

    def _open_dialog(self):

        try:
            default_dir = convert_list_to_path_str(self.parameter.value)
        except:
            default_dir = os.getcwd()

        if self.parameter.select_files:
            selection, success = get_open_file_path(self, "Select file path",
                                                    default_dir=default_dir)
        else:
            selection, success = get_open_dir_path(self, "Select file path",
                                                   default_dir=default_dir)

        if success:
            self.parameter.set_value(convert_path_str_to_list(selection))
            self.value_widget.setText(selection)

