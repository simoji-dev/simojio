from enum import Enum


class FitType(Enum):
    """Fit types for intensity change correction of AngleSpectrumReader."""

    NO = 'no'
    LINEAR = 'linear'
    EXPONENTIAL = 'exponential'
    INTERPOLATE = 'interpolate'
