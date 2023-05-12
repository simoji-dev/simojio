from simojio.lib.parameters.SingleParameter import SingleParameter


class BoolParameter(SingleParameter):

    def __init__(self, name: str, value: bool, description: str):

        super().__init__(name=name, value=value, description=description)

    def _check_value(self, value: bool) -> bool:
        """Check if value is of right type."""

        if not isinstance(value, bool):
            return False
        else:
            return True
