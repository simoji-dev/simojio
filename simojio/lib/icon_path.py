import os, sys


def icon_path(relative_path):
    try:
        base_path = sys._MEIPASS
        return os.path.join(base_path, 'simojio', 'lib', 'gui', 'icon', relative_path)
    except Exception:
        return os.path.join('lib', 'gui', 'icon', relative_path)
