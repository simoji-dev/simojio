from PySide2.QtWidgets import QFrame
from PySide2.QtGui import QPalette, QColor


class QHLine(QFrame):
    def __init__(self):
        super(QHLine, self).__init__()
        self.setFrameShape(QFrame.HLine)
        self.setFrameShadow(QFrame.Sunken)

    def set_color(self, color: QColor):
        self.setFrameShadow(QFrame.Plain)
        pal = self.palette()
        pal.setColor(QPalette.WindowText, color)
        self.setPalette(pal)
