import PySide2.QtWidgets as QtWidgets


class RotatedButton(QtWidgets.QPushButton):

    def __init__(self, text, parent, orientation = "west"):
        super(RotatedButton,self).__init__(text, parent)
        self.orientation = orientation

    def paintEvent(self, event):
        painter = QtWidgets.QStylePainter(self)
        if self.orientation == "east":
            painter.rotate(270)
            painter.translate(-1 * self.height(), 0)
        if self.orientation == "west":
            painter.rotate(90)
            painter.translate(0, -1 * self.width())
        painter.drawControl(QtWidgets.QStyle.CE_PushButton, self.getSyleOptions())  # QtWidgets.QStyle.CE_PushButton

    def minimumSizeHint(self):
        size = super(RotatedButton, self).minimumSizeHint()
        size.transpose()
        return size

    def sizeHint(self):
        size = super(RotatedButton, self).sizeHint()
        size.transpose()
        return size

    def getSyleOptions(self):
        options = QtWidgets.QStyleOptionButton()
        options.initFrom(self)
        size = options.rect.size()
        size.transpose()
        options.rect.setSize(size)
        options.features = QtWidgets.QStyleOptionButton.None_
        if self.isFlat():
            options.features |= QtWidgets.QStyleOptionButton.Flat
        if self.menu():
            options.features |= QtWidgets.QStyleOptionButton.HasMenu
        if self.autoDefault() or self.isDefault():
            options.features |= QtWidgets.QStyleOptionButton.AutoDefaultButton
        if self.isDefault():
            options.features |= QtWidgets.QStyleOptionButton.DefaultButton
        if self.isDown() or (self.menu() and self.menu().isVisible()):
            options.state |= QtWidgets.QStyle.State_Sunken
        if self.isChecked():
            options.state |= QtWidgets.QStyle.State_On
        if not self.isFlat() and not self.isDown():
            options.state |= QtWidgets.QStyle.State_Raised

        options.text = self.text()
        options.icon = self.icon()
        options.iconSize = self.iconSize()
        return options