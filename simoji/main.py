# -*- coding: utf-8 -*-
__version__ = "0.1.0"
__author__ = "christian.haenisch@tu-dresden.de"


if __name__ == '__main__':

    import PySide2.QtWidgets as QtWidgets
    import PySide2.QtGui as QtGui

    import sys, os

    # change working directory to path of this main.py file
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    app = QtWidgets.QApplication(sys.argv)  # must be constructed before pixmap
    app.setApplicationVersion(__version__)

    # plot window possible
    # splash screen during startup
    from simoji.lib.icon_path import icon_path

    pixmap = QtGui.QPixmap(icon_path("simoji_logo_with_background.svg"))
    splash = QtWidgets.QSplashScreen(pixmap)
    splash.show()

    # app.processEvents()
    splash.showMessage("Loading..")

    import multiprocessing
    multiprocessing.set_start_method('spawn')
    import platform
    import ctypes

    if platform.system() == 'Windows':
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("simoji_v" + __version__)

    from simoji.lib.ModuleLoader import ModuleLoader
    from simoji.lib.ModuleExecutor import ModuleExecutor
    from simoji.lib.SettingManager import SettingManager
    from simoji.lib.gui.MainWindow import MainWindow
    from simoji.lib.BasicFunctions import *

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
        setting_manager = SettingManager()
        global_settings, sample_list, success = setting_manager.read_setting(args.setting)

        if success:

            # get module
            module_loader = ModuleLoader()
            module_loader.get_available_modules()
            module_name = global_settings.module_path[-1].rstrip(".py")

            # check if it is Simulator
            module = module_loader.load_module(module_name)
            is_simulator_module = isinstance(module, Simulator)

            # get save path
            from simoji.lib.gui.SavePathDialog import SavePathDialog
            from simoji.lib.plotter.MainPlotWindow import MainPlotWindow

            # execute module
            plot_window = MainPlotWindow()
            plot_window.hide()
            module_executor = ModuleExecutor(plot_window, module_loader)

            def stop_execution():
                module_executor.timer.stop()
                module_executor.terminate_subprocesses(timeout=0.)
                module_executor.plot_window.close()
                app.exit()

            def save():

                save_path_dialog = SavePathDialog()

                if save_path_dialog.exec_():
                    save_path_dialog.root_save_path = "SimulationResults"
                    save_path_dialog.set_module_name(module_name)
                    save_path_dialog.set_execution_mode(global_settings.execution_mode)
                    save_path_dialog.show()
                    save_path = save_path_dialog.get_current_save_path()
                    save_file_format = save_path_dialog.get_file_format()

                    module_executor.save_results(global_settings=global_settings, sample_list=sample_list,
                                                 save_path=save_path,
                                                 save_file_format=save_file_format, app=app)

            import tempfile

            temp_dir = tempfile.TemporaryDirectory()   # use temporary directory as default save path (for custom save)
            module_executor.exec(is_simulator_module, global_settings, sample_list, save_path=temp_dir.name)
            module_executor.execution_stopped_sig.connect(save)
            module_executor.plot_window.closed_sig.connect(stop_execution)

            sys.exit(app.exec_())
        else:
            print("Warning: Couldn't read setting '" + args.setting + "'")