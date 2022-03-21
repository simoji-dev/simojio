from enum import Enum


class ExecutionMode(str, Enum):
    SINGLE = "single"
    VARIATION = "variation"
    OPTIMIZATION = "optimization"
    COUPLED_OPTIMIZATION = "coupled optimization"
