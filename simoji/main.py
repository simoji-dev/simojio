# -*- coding: utf-8 -*-
__version__ = "2.0.0"
__author__ = "elmogit"

if __name__ == '__main__':

    import PySide2.QtWidgets as QtWidgets
    import PySide2.QtGui as QtGui
    import sys
    import os
    from simoji.lib.icon_path import icon_path

    # change working directory to path of this main.py file, important for executables which are run in temp dir
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    app = QtWidgets.QApplication(sys.argv)  # must be constructed before pixmap
    app.setApplicationVersion(__version__)

    QtGui.QFontDatabase.addApplicationFont(os.path.join('lib', 'fonts', 'OpenSans-VariableFont.ttf'))
    font = QtGui.QFont("OpenSans")
    font.setPointSize(10)
    font.setStyleHint(QtGui.QFont.Monospace)
    app.setFont(font)

    pixmap = QtGui.QPixmap(icon_path("simoji_logo_with_background.svg"))
    splash = QtWidgets.QSplashScreen(pixmap)
    splash.show()
    splash.showMessage("Loading..")

    # load further packages after splash is shown to reduce 'dead' time
    import multiprocessing
    import platform
    import ctypes
    import argparse
    import json

    from simoji.lib.gui.MainWindow import MainWindow

    # multiprocessing.set_start_method('spawn')       # Set spawn method for all OS, in Linux it would be fork by default
    if platform.system() == 'Windows':
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("simoji_v" + __version__)  # to show icon in bar

    # write product info
    info_dict = {
        "name": "simoji",
        "version": __version__
    }

    json_file = open("product-info.json", 'w', encoding='utf-8')
    json.dump(info_dict, json_file, sort_keys=True, indent=4)
    json_file.close()

    # run simoji
    multiprocessing.freeze_support()
    parser = argparse.ArgumentParser()

    parser.add_argument("--setting", help="Type path of setting file to be evaluated (e.g. 'settings/OLED.json').",
                        action="store", default=os.path.join('settings', 'latest_setting.json'))
    parser.add_argument("--enable_gui", help="Switch GUI on/off (y/n).",
                        action="store", default="y")

    args, unknown = parser.parse_known_args()

    if args.enable_gui == "y":
        ex = MainWindow(args.setting, app)
        splash.finish(ex)
        sys.exit(app.exec_())
    else:
        raise NotImplementedError("Execution of simoji without GUI not yet implemented")
