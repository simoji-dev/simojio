# from PySide6.QtWidgets import QApplication, QWidget
#
# # Only needed for access to command line arguments
# import sys
#
# # You need one (and only one) QApplication instance per application.
# # Pass in sys.argv to allow command line arguments for your app.
# # If you know you won't use command line arguments QApplication([]) works too.
# app = QApplication(sys.argv)
#
# # Create a Qt widget, which will be our window.
# window = QWidget()
# window.show()  # IMPORTANT!!!!! Windows are hidden by default.
#
# # Start the event loop.
# app.exec()
#
# # Your application won't reach here until you exit and the event
# # loop has stopped.



# -*- coding: utf-8 -*-
__version__ = "2.0.0"
__author__ = "elmogit"

if __name__ == '__main__':

    import PySide6.QtWidgets as QtWidgets
    import PySide6.QtGui as QtGui
    import sys
    import os
    from simojio.lib.icon_path import icon_path

    # change working directory to path of this main.py file, important for executables which are run in temp dir
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    app = QtWidgets.QApplication(sys.argv)  # must be constructed before pixmap
    app.setApplicationVersion(__version__)

    QtGui.QFontDatabase.addApplicationFont(os.path.join('lib', 'fonts', 'OpenSans-VariableFont.ttf'))
    font = QtGui.QFont("OpenSans")
    font.setPointSize(10)
    # font.setStyleHint(QtGui.QFont.Monospace)
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

    from simojio.lib.gui.MainWindow import MainWindow

    multiprocessing.set_start_method('spawn')   # Set spawn method for all OS, in Linux it would be fork by default
    if platform.system() == 'Windows':
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("simoji_v" + __version__)  # to show icon in bar

    # write product info
    info_dict = {
        "name": "simojio",
        "version": __version__
    }

    json_file = open("product-info.json", 'w', encoding='utf-8')
    json.dump(info_dict, json_file, sort_keys=True, indent=4)
    json_file.close()

    # run simojio
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
        sys.exit(app.exec())
    else:
        raise NotImplementedError("Execution of simojio without GUI not yet implemented")
