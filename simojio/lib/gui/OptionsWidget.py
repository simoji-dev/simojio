import PySide2.QtWidgets as QtWidgets
from simojio.lib.gui.decoration.QHLine import QHLine


class OptionsWidget(QtWidgets.QWidget):
    """Collection of options separated into sub-categories"""

    def __init__(self):
        super().__init__()

        self.category_layout_dict = {}      # {category name: layout}
        self.option_widget_dict = {}        # {option name: widget}
        self.option_label_widget_dict = {}  # {option name: label widget}

        self.label_minimum_width = 200

        self.layout = QtWidgets.QVBoxLayout()
        layout_v = QtWidgets.QVBoxLayout()

        layout_v.addLayout(self.layout)
        layout_v.addStretch(1)
        self.setLayout(layout_v)

    def add_category(self, category_name: str):
        if category_name in self.category_layout_dict:
            raise ValueError("Category name already exists.")

        category_layout = QtWidgets.QVBoxLayout()

        # make category header with category name and line that fills the rest of the horizontal space
        header_layout = QtWidgets.QHBoxLayout()
        header_label = QtWidgets.QLabel("<html><b>" + category_name + "<\b><html>")
        header_label.setMaximumWidth(header_label.sizeHint().width())

        fill_line = QHLine()

        header_layout.addWidget(header_label)
        header_layout.addWidget(fill_line)

        # add space above header to better separate categories
        top_space = 0
        if len(self.category_layout_dict) > 0:
            top_space = 20
        header_layout.setContentsMargins(0, top_space, 0, 10)
        category_layout.addLayout(header_layout)

        # add category layout to options widget and store its reference in the dictionary
        self.layout.addLayout(category_layout)
        self.category_layout_dict.update({category_name: category_layout})

    def add_option_to_category(self, category_name: str, option_label: str, option_widget: QtWidgets.QWidget):

        if not category_name in self.category_layout_dict:
            self.add_category(category_name)

        option_layout = QtWidgets.QHBoxLayout()
        option_label_widget = QtWidgets.QLabel(option_label)
        option_label_widget.setMinimumWidth(self.label_minimum_width)
        option_layout.addWidget(option_label_widget)
        option_layout.addWidget(option_widget)
        option_layout.addStretch(1)
        self.category_layout_dict[category_name].addLayout(option_layout)

        self.option_widget_dict.update({option_label: option_widget})
        self.option_label_widget_dict.update({option_label: option_label_widget})

    def get_options(self) -> dict:
        """Return dict of labels and current values"""

        options_value_dict = {}
        for option_label in self.option_widget_dict:
            option_widget = self.option_widget_dict[option_label]
            option_value = None

            if isinstance(option_widget, QtWidgets.QLineEdit):
                option_value = option_widget.text()
            elif isinstance(option_widget, QtWidgets.QCheckBox):
                option_value = option_widget.isChecked()
            elif isinstance(option_widget, QtWidgets.QComboBox):
                option_value = option_widget.currentText()
            elif isinstance(option_widget, QtWidgets.QPushButton):
                option_value = option_widget.isChecked()
            else:
                raise ValueError("Widget type " +  str(option_widget) + "not yet implemented!")

            options_value_dict.update({option_label: option_value})

        return options_value_dict

    def enable_category(self, category_name: str, enable: bool):

        if not category_name in self.category_layout_dict:
            raise ValueError("Category '" + category_name + "' not defined!")
        else:
            # Note: category layout consists of header layout and option layouts
            category_layout = self.category_layout_dict[category_name]
            for i in range(category_layout.count()):
                sub_layout = category_layout.itemAt(i).layout()
                for j in range(sub_layout.count()):
                    try:
                        sub_layout.itemAt(j).widget().setEnabled(enable)
                    except:
                        pass