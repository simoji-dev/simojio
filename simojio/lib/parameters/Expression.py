from simojio.lib.parameters.AnyStringParameter import AnyStringParameter


class Expression(AnyStringParameter):
    """Mathematical expression that can contain several Variables and results in a single float value."""

    prefix = "EXPR_"

    def __init__(self, name: str, value: str):

        super().__init__(name=name, value=value,
                         description="Mathematical expression that can contain several Variables and results in a "
                         "single float value.")

