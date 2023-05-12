from enum import Enum


class SaveDataFileFormats(str, Enum):
    """File formats for auto saving of plot data."""

    JSON = ".json"
    CSV = ".csv"
    TXT = ".txt"
