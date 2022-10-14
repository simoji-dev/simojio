from simoji.lib.parameters import *


class StartStopStepParameter(NestedParameter):

    def __init__(self, name: str, start: float, stop: float, step: float, description: str):

        start_par = FixFloatParameter(name="start", value=start, description="start value")
        stop_par = FixFloatParameter(name="stop", value=stop, description="stop value")
        step_par = FixFloatParameter(name="step", value=step, description="step value")

        super().__init__(name=name, parameters=[start_par, stop_par, step_par], description=description)
