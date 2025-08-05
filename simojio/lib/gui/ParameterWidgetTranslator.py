import PySide6.QtWidgets as QtWidgets

from simojio.lib.parameters import *

from simojio.lib.gui.parameter_widgets.BoolParWidget import BoolParWidget
from simojio.lib.gui.parameter_widgets.MultiStringParWidget import MultiStringParWidget
from simojio.lib.gui.parameter_widgets.FixFloatParWidget import FixFloatParWidget
from simojio.lib.gui.parameter_widgets.AnyStringParWidget import AnyStringParWidget
from simojio.lib.gui.parameter_widgets.ChoosePathWidget import ChoosePathWidget


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

