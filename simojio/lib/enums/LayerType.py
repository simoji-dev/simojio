from enum import Enum


class LayerType(str, Enum):

    STANDARD = "standard"
    COHERENT = "coherent"
    SEMI = "semi"
    SUBSTRATE = "substrate"
    ELECTRODE = "electrode"
    INTERFACE = "interface"
    TRANSPORT = "transport"
    EMISSION = "emission"
