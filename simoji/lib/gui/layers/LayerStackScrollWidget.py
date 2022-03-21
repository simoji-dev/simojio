import PySide2.QtWidgets as QtWidgets

from simoji.lib.gui.layers.LayerStackWidget import LayerStackWidget


class LayerStackScrollWidget(QtWidgets.QScrollArea):

    def __init__(self):

        super().__init__()

        self.layer_stack_widget = LayerStackWidget()
        self.setWidget(self.layer_stack_widget)
        self.setWidgetResizable(True)

    def set_layer_list(self, layer_list: list):
        self.layer_stack_widget.set_layer_list(layer_list)

    def get_layer_list(self) -> list:
        return self.layer_stack_widget.get_layer_list()

    def set_module(self, module):
        self.layer_stack_widget.set_module(module)