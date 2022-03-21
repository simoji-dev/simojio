import PySide2.QtWidgets as QtWidgets

from simoji.lib.parameters import *

from simoji.lib.gui.parameter_widgets.BoolParWidget import BoolParWidget
from simoji.lib.gui.parameter_widgets.MultiStringParWidget import MultiStringParWidget
from simoji.lib.gui.parameter_widgets.FixFloatParWidget import FixFloatParWidget
from simoji.lib.gui.parameter_widgets.AnyStringParWidget import AnyStringParWidget
from simoji.lib.gui.parameter_widgets.ChoosePathWidget import ChoosePathWidget


def parameter2widget(parameter: SingleParameter, is_sub_parameter=False) -> QtWidgets.QWidget:

    if isinstance(parameter, FixFloatParameter):
        widget = FixFloatParWidget(parameter, is_sub_parameter)
    elif isinstance(parameter, BoolParameter):
        widget = BoolParWidget(parameter, is_sub_parameter)
    elif isinstance(parameter, MultiStringParameter):
        widget = MultiStringParWidget(parameter, is_sub_parameter)
    elif isinstance(parameter, AnyStringParameter):
        widget = AnyStringParWidget(parameter, is_sub_parameter)
    elif isinstance(parameter, PathParameter):
        widget = ChoosePathWidget(parameter, is_sub_parameter)
    else:
        raise ValueError("Single parameter of unknown type: " + str(parameter))

    return widget

