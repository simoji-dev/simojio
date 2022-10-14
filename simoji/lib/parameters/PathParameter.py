from simoji.lib.parameters.SingleParameter import SingleParameter
from simoji.lib.BasicFunctions import convert_path_str_to_list, convert_list_to_path_str

from typing import Optional, List
import os


class PathParameter(SingleParameter):
    """Contains a single path to a file (select_files=True) or to a path (select_files=False)."""

    def __init__(self, name: str, value: Optional[List[str]] = None, description: Optional[str] = None, bounds = None,
                 select_files: Optional[bool] = True):

        if value is None:
            value = convert_path_str_to_list(os.getcwd(), extract_relative_path_only=True)
        if description is None:
            description = "Choose path"

        super().__init__(name, value, description, bounds)

        self.name = name
        self.value = value
        self.description = description
        self.bounds = bounds
        self.select_files = select_files

    def get_path_str(self) -> str:
        return convert_list_to_path_str(self.value)

