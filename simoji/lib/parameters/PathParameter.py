from simoji.lib.parameters.SingleParameter import SingleParameter
from simoji.lib.enums.ParameterCategory import ParameterCategory
# from simoji.lib.BasicFunctions import convert_path_str_to_list

from typing import Optional, List
import os
from pathlib import Path


class PathParameter(SingleParameter):
    """Contains a single path to a file (select_files=True) or to a path (select_files=False)."""

    def __init__(self, name: str, value: Optional[List[str]] = None, description: Optional[str] = None, bounds = None,
                 select_files: Optional[bool] = True):

        if value is None:
            value = self.convert_path_str_to_list(os.getcwd(), extract_relative_path_only=True)
        if description is None:
            description = "Choose path"

        super().__init__(name, value, description, bounds)

        self.name = name
        self.value = value
        self.description = description
        self.bounds = bounds
        self.select_files = select_files

    def convert_path_str_to_list(self, path_str: str, extract_relative_path_only=True) -> list:
        """
        Convert an OS dependent path str to a list of path elements
        :param path_str: 'dir1/dir2/filename' (Linux) or 'dir1\dir2\filename' (Windows)
        :return: ['dir1', 'dir2', 'filename']
        """

        if extract_relative_path_only:
            # get relative path to current working directory to assure portability
            # https://stackoverflow.com/a/57153766
            parent = Path(os.path.abspath(os.curdir))
            son = Path(path_str)
            if parent in son.parents or parent == son:
                path_str = son.relative_to(parent)
        path_parts = Path(path_str).parts

        return list(path_parts)