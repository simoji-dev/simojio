import PySide2.QtGui as QtGui
import PySide2.QtCore as QtCore

from simojio.lib.BasicFunctions import *
from simojio.lib.gui.Dialogs import *
from simojio.lib.gui.decoration.QHLine import QHLine
from simojio.lib.plotter.SaveDataFileFormats import SaveDataFileFormats


class SavePathDialog(QtWidgets.QDialog):

    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self.setWindowTitle("Select save path!")
        self.setMinimumWidth(400)

        self.root_save_path = os.path.abspath("SimulationResults")
        if not os.path.exists(self.root_save_path):
            self.root_save_path = os.getcwd()

        self.module_name = ""
        self.execution_mode = ""

        # root path
        path_label = QtWidgets.QLabel("Root path:")
        self.root_path_edit = QtWidgets.QLineEdit(self.root_save_path)
        self.root_path_edit.setReadOnly(True)
        self.open_path_button = QtWidgets.QPushButton(QtGui.QIcon(icon_path("open.svg")), "")
        self.open_path_button.clicked.connect(self._get_new_save_path)
        self.root_path_key = "root_path"

        path_layout = QtWidgets.QHBoxLayout()
        path_layout.addWidget(path_label)
        path_layout.addWidget(self.root_path_edit)
        path_layout.addWidget(self.open_path_button)

        # time stamp
        self.time_stamp_checkbox = QtWidgets.QCheckBox("time stamp")
        self.time_stamp_checkbox.setChecked(True)
        self.time_stamp_checkbox.toggled.connect(self._update_current_dir_name)
        self.time_stamp_key = "time_stamp"

        # module name
        self.module_name_checkbox = QtWidgets.QCheckBox("module name")
        self.module_name_checkbox.setChecked(True)
        self.module_name_checkbox.toggled.connect(self._update_current_dir_name)
        self.module_name_key = "module_name"

        # execution mode
        self.execution_mode_checkbox = QtWidgets.QCheckBox("execution mode")
        self.execution_mode_checkbox.setChecked(True)
        self.execution_mode_checkbox.toggled.connect(self._update_current_dir_name)
        self.execution_mode_key = "execution_mode"

        # zip results
        self.zip_results_checkbox = QtWidgets.QCheckBox("zip results")
        self.zip_results_checkbox.setChecked(True)
        self.zip_results_key = "zip_results"

        # suffix
        suffix_label = QtWidgets.QLabel("Suffix:")
        self.suffix_edit = QtWidgets.QLineEdit("")
        self.suffix_edit.textChanged[str].connect(self._update_current_dir_name)
        suffix_layout = QtWidgets.QHBoxLayout()
        suffix_layout.addWidget(suffix_label)
        suffix_layout.addWidget(self.suffix_edit)
        self.suffix_key = "suffix"

        # file format
        file_format_label = QtWidgets.QLabel("File format:")
        self.file_format_combo = QtWidgets.QComboBox()
        self.file_format_combo.addItems([file_format.value for file_format in SaveDataFileFormats])
        file_format_layout = QtWidgets.QHBoxLayout()
        file_format_layout.addWidget(file_format_label)
        file_format_layout.addWidget(self.file_format_combo)
        file_format_layout.addStretch(1)
        self.file_format_key = "file_format"

        # current directory name
        myFont = QtGui.QFont()
        myFont.setBold(True)

        self.current_dir_str = QtWidgets.QLabel()
        self.current_dir_str.setFont(myFont)

        # ok and cancel buttons
        QBtn = QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel

        self.buttonBox = QtWidgets.QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

        # add everything to the layout
        self.layout = QtWidgets.QVBoxLayout()

        self.layout.addLayout(path_layout)
        self.layout.addWidget(self.time_stamp_checkbox)
        self.layout.addWidget(self.module_name_checkbox)
        self.layout.addWidget(self.execution_mode_checkbox)
        self.layout.addWidget(self.zip_results_checkbox)
        self.layout.addLayout(suffix_layout)
        self.layout.addLayout(file_format_layout)
        self.layout.addWidget(QHLine())
        self.layout.addWidget(self.current_dir_str)
        self.layout.addWidget(QHLine())

        self.layout.addWidget(self.buttonBox)
        self.setLayout(self.layout)

        self._update_current_dir_name()

    def set_module_name(self, module_name: str):
        self.module_name = module_name
        self._update_current_dir_name()

    def set_execution_mode(self, execution_mode: str):
        self.execution_mode = execution_mode
        self._update_current_dir_name()

    def _get_new_save_path(self):
        path, success = get_open_dir_path(self, caption="Select save path", default_dir=self.root_save_path)
        if success:
            self.root_save_path = path
            self.root_path_edit.setText(self.root_save_path)

    def set_root_path(self, path: str):
        if os.path.exists(path) and os.path.isdir(path):
            self.root_path_edit.setText(path)
            self.root_save_path = path
        elif os.path.exists(self.root_save_path) and os.path.isdir(self.root_save_path):
            self.root_path_edit.setText(self.root_save_path)
        else:
            self.root_save_path = os.getcwd()
            self.root_path_edit.setText(self.root_save_path)

    def get_current_save_path(self) -> str:
        self.set_root_path(self.root_save_path)
        root_path = self.root_path_edit.text()

        return os.path.join(root_path, self._get_current_dir_name(time_stamp_dummy=False))

    def get_file_format(self) -> SaveDataFileFormats:
        return SaveDataFileFormats(self.file_format_combo.currentText())

    def get_zip_results(self) -> bool:
        return self.zip_results_checkbox.isChecked()

    def get_preferences(self):
        preferences_dict = {
            self.root_path_key: self.root_path_edit.text(),
            self.time_stamp_key: self.time_stamp_checkbox.isChecked(),
            self.module_name_key: self.module_name_checkbox.isChecked(),
            self.execution_mode_key: self.execution_mode_checkbox.isChecked(),
            self.zip_results_key: self.get_zip_results(),
            self.suffix_key: self.suffix_edit.text(),
            self.file_format_key: self.file_format_combo.currentText()
        }
        return preferences_dict

    def set_preferences(self, preferences_dict: dict):
        try:
            self.set_root_path(preferences_dict[self.root_path_key])
        except:
            pass
        try:
            self.time_stamp_checkbox.setChecked(bool(preferences_dict[self.time_stamp_key]))
        except:
            pass
        try:
            self.module_name_checkbox.setChecked(bool(preferences_dict[self.module_name_key]))
        except:
            pass
        try:
            self.execution_mode_checkbox.setChecked(bool(preferences_dict[self.execution_mode_key]))
        except:
            pass
        try:
            self.zip_results_checkbox.setChecked(preferences_dict[self.zip_results_key])
        except:
            pass
        try:
            self.suffix_edit.setText(preferences_dict[self.suffix_key])
        except:
            pass
        try:
            self.file_format_combo.setCurrentText(preferences_dict[self.file_format_key])
        except:
            pass

    def _get_current_dir_name(self, time_stamp_dummy=True) -> str:
        dir_name_elements = []

        if self.time_stamp_checkbox.isChecked():
            if time_stamp_dummy:
                time_stamp = "[time-stamp]"
            else:
                time_stamp = get_time_stamp()
            dir_name_elements.append(time_stamp)

        if self.module_name_checkbox.isChecked():
            dir_name_elements.append(self.module_name)

        if self.execution_mode_checkbox.isChecked():
            dir_name_elements.append(self.execution_mode + "-mode")

        if self.suffix_edit.text() != "":
            dir_name_elements.append(self.suffix_edit.text())

        # at least one field needs to be filled to not get an empty file name
        if len(dir_name_elements) == 0:
            self.time_stamp_checkbox.setChecked(True)
            dir_name_elements.append(get_time_stamp())
            ok = warning(self, "Directory name must not be empty! Time stamp added.")

        return "_".join(dir_name_elements)

    def _update_current_dir_name(self):
        current_name = self._get_current_dir_name()
        zip_str = ""
        if self.get_zip_results():
            zip_str = ".zip"
        self.current_dir_str.setText("-> root_path" + os.path.sep + current_name + zip_str)

        self.sizeHint().width()
        self.resize(QtCore.QSize(self.sizeHint().width(), self.sizeHint().height()))

    def get_suffix(self) -> str:
        return self.suffix_edit.text()

