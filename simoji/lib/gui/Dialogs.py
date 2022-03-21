import PySide2.QtWidgets as QtWidgets
import PySide2.QtGui as QtGui
import PySide2.QtCore as QtCore
import os


def get_save_file_path(parent: QtWidgets.QWidget, caption: str, default_dir: str, filter=None):

    success = False
    filter = filter
    caption = caption

    try:
        selection, type = QtWidgets.QFileDialog.getSaveFileName(parent, dir=default_dir, filter=filter,
                                                                caption=caption)
    except:
        selection, type = QtWidgets.QFileDialog.getSaveFileName(parent, dir=os.getcwd(), filter=filter,
                                                                caption=caption)

    if not str(selection) == '':  # empty str means 'cancel' clicked -> keep old value
        success = True

    return selection, success


def get_open_file_path(parent: QtWidgets.QWidget, caption: str, default_dir: str, filter=None):

    success = False
    filter = filter
    caption = caption

    if os.path.isfile(default_dir):
        default_dir = os.path.split(default_dir)[0]
    elif not os.path.exists(default_dir):
        default_dir = os.getcwd()

    selection, type = QtWidgets.QFileDialog.getOpenFileName(parent, dir=default_dir, filter=filter,
                                                                caption=caption)

    if not str(selection) == '':  # empty str means 'cancel' clicked -> keep old value
        success = True

    return selection, success


def get_open_dir_path(parent: QtWidgets.QWidget, caption: str, default_dir: str):

    success = False
    caption = caption

    if os.path.isfile(default_dir):
        default_dir = os.path.split(default_dir)[0]
    elif not os.path.exists(default_dir):
        default_dir = os.getcwd()

    selection = QtWidgets.QFileDialog.getExistingDirectory(parent, dir=default_dir, caption=caption)

    if not str(selection) == '':  # empty str means 'cancel' clicked -> keep old value
        success = True

    return selection, success


def select_from_combobox(parent: QtWidgets.QWidget, combobox_items: list, title: str, text: str):
    selected_item, ok = QtWidgets.QInputDialog.getItem(parent, title, text, combobox_items, 0, False)
    return selected_item, ok


def warning(parent: QtWidgets.QWidget, text: str) -> bool:
    button = QtWidgets.QMessageBox.warning(parent, "simoji warning", text,
                                         QtWidgets.QMessageBox.Ok | QtWidgets.QMessageBox.Cancel,
                                         QtWidgets.QMessageBox.Ok)
    if button is QtWidgets.QMessageBox.Ok:
        return True
    else:
        return False

