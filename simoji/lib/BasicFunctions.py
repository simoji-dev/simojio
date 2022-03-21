from pathlib import Path
import os
import importlib
import sys
import inspect
import numpy as np
import platform
import warnings
import collections.abc
import argparse
import json
import datetime
from configparser import ConfigParser

from typing import List
from scipy.interpolate import interp2d, interp1d  # for projection onto angle-wavelength grid
from scipy.signal import savgol_filter
from scipy.interpolate import InterpolatedUnivariateSpline  # TODO: replace with numpy interpolation
from io import StringIO

from simoji.lib.enums.ExecutionMode import ExecutionMode
from simoji.lib.abstract_modules import *
from typing import Union, Optional


def icon_path(relative_path):
    try:
        base_path = sys._MEIPASS
        return os.path.join(base_path, 'simoji', 'lib', 'gui', 'icon', relative_path)
    except Exception:
        return os.path.join('lib', 'gui', 'icon', relative_path)


def find_nearest(array: list, value: float) -> (int, float):
    idx = (np.abs(np.array(array) - value)).argmin()
    return idx, array[idx]


def flatten(l: Union[list, tuple]):
    out = []
    for item in l:
        if isinstance(item, (list, tuple)):
            out.extend(flatten(item))
        else:
            out.append(item)
    return out


def convert_list_to_path_str(list_of_path_elements: list) -> str:
    """
    Convert a path with its elements given in a list to a OS dependent str
    :param list_of_path_elements = ['dir1', 'dir2', 'filename']
    :return 'dir1/dir2/filename' (Linux) or 'dir1\dir2\filename' (Windows)
    """
    path = Path(*list_of_path_elements)
    if not path.exists():
        raise ValueError("Given path '" + str(path) + "' doesn't exist.")
    return str(path)


def convert_path_str_to_list(path_str: str, extract_relative_path_only=True) -> list:
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
        if parent in son.parents or parent==son:
            path_str = son.relative_to(parent)
    path_parts = Path(path_str).parts

    return list(path_parts)


def convert_module_path_to_import_str(module_path: str, module_root_path=None) -> str:
    if module_root_path is None:
        module_root_path = "modules"
    path = os.path.normpath(module_path)
    splitted_path = path.split(os.sep)
    import_str = "simoji." + ".".join(splitted_path[splitted_path.index(module_root_path):]).rstrip('.py')
    # import_str = ".".join(splitted_path[splitted_path.index(module_root_path):]).rstrip('.py')
    return import_str


def reload_module(import_str: str, class_name=None):
    module = importlib.import_module(import_str)
    module = importlib.reload(module)

    if class_name is None:
        clsmembers = inspect.getmembers(sys.modules[__name__], inspect.isclass)
        class_name = clsmembers[0]

    module_cls = getattr(module, class_name)

    return module_cls


def get_module_class_from_path_given_as_list(path: list):
    module_path_str = convert_list_to_path_str(path)
    module_import_str = convert_module_path_to_import_str(module_path_str)
    module_cls = reload_module(module_import_str, path[-1].rstrip(".py"))
    module_cls.module_path = path
    return module_cls


def check_expression(expr_str: str, par_dict: dict, return_used_parameters=False) -> (bool, str):
    global_dict = {'sqrt': np.sqrt, 'exp': np.exp, 'sin': np.sin, 'cos': np.cos,
                   'np.sqrt': np.sqrt, 'np.exp': np.exp, 'np.sin': np.sin, 'np.cos': np.cos,
                   '__builtins__': None}    # the latter makes sure that the user input doesn't execute dangerous stuff

    try:
        eval_str = eval(expr_str.replace('\n', ''), global_dict, par_dict)
        success = True
    except:
        eval_str = expr_str
        success = False

    used_parameters = None
    if success and return_used_parameters:
        used_parameters = []
        for par in sorted(par_dict)[::-1]:  # invert: replace "VAR_10" first since it includes "VAR_1"
            if par in expr_str:
                used_parameters.append(par)
                expr_str.replace(par, "0")  # replace with something that is probably not in the par_dict (work around)

    return success, eval_str, used_parameters


def start_stop_step_to_list(start_stop_step_list: List[float]) -> list:
    """Convert parameter form (start, stop, step) to list."""

    [start, stop, step] = list(map(float, start_stop_step_list))

    if start == stop:
        value_list = [start]
    else:
        arr = np.arange(start, stop, step)
        # -- include stop element to np.array() if it fits --
        # example 1: par=[0,2,1]   -> arr = [0,1,2]
        # example 2: par=[0,2,1.1] -> arr = [0,1.1] -> not: np.arange(start, stop+step, step)=[0,1.1,2.2]
        if (arr[-1] + step) == stop:
            arr = np.append(arr, [stop])

        value_list = list(arr)

    return value_list


def eval_exclude_tuple(par_list: list) -> list:
    """
    Evaluate the str containing exclude tuples, e.g. "(1,2) (1, 2)(2,3),  (3,4)", given as list (str space separate)
    :param par_list: ['(1,2)', '(1.', '2)(2,3)', '(3,4)'] (from str above)
    :return: tuple list [(1, 2), (1, 2), (2, 3), (3, 4)]
    """
    par_str = "".join(par_list)
    par_list_new = []
    tuple_collector = ''
    tuple_bool = False
    for letter in par_str:
        if letter == "(":
            tuple_bool = True
        if tuple_bool:
            if letter != " ":
                tuple_collector += letter
            if letter == ")":
                par_list_new.append(eval(tuple_collector))
                tuple_bool = False
                tuple_collector = ""
    return par_list_new


def remove_exclude_values_from_list(total_value_list: list, exclude_tuple_list: list) -> list:
    """
    From a given total_value_list, remove all values that are within the bounds given in the exclude_tuple_list, e.g.:
    total_value_list = [1,2,3,4,5,6,7,8,9,10]
    exclude_tuple_list = [(0,3), (7,8)]
    -> remaining_values_list = [4,5,6,9,10]

    :param total_value_list:
    :param exclude_tuple_list:
    :return: remaining_values_list
    """

    def is_in_exclude_tuples(check_value: float) -> bool:
        is_in_tuple_bool = False
        for bound_tuple in exclude_tuple_list:
            if (check_value >= min(bound_tuple)) and (check_value <= max(bound_tuple)):
                is_in_tuple_bool = True
                break
        return is_in_tuple_bool

    remaining_values_list = []
    for value in total_value_list:
        if not is_in_exclude_tuples(value):
            remaining_values_list.append(value)

    return remaining_values_list


def project_2d_array_onto_grid(x_init: np.array, y_init: np.array, data2d_init: np.array, x_grid: np.array,
                               y_grid: np.array) -> np.array:
    """
    Project a 2d-array (data2d_init) defined on the initial grid (x_init, y_init) onto a new grid (x_grid, y_grid).
    Use 2d- or 1d-interpolation of the initial data depending on the dimensionality of data2d_init. If data2d_init is
    only a single value, return a constant array of this value.
    :param x_init:
    :param y_init:
    :param data2d_init:
    :param x_grid:
    :param y_grid:
    :return: data2d_grid: np.array
    """

    if data2d_init.shape == (1, 1):
        # single point given, return constant array
        data2d_grid = data2d_init[0, 0] * np.ones((len(x_grid), len(y_grid)))
    elif data2d_init.shape[0] == 1:
        # 1d on x-axis
        data_func = interp1d(x_init, data2d_init[0])
        data2d_grid = np.array([data_func(x_grid)]).T
        print(data2d_grid)
    elif data2d_init.shape[1] == 1:
        # 1d on y-axis
        data_func = interp1d(y_init, data2d_init[:, 0])
        data_1d = data_func(y_grid)
        data2d_grid = np.array([[data_1d[i]] for i in range(len(data_1d))])
    else:
        # 2d interpolation
        data_func = interp2d(x_init, y_init, data2d_init)
        data2d_grid = data_func(x_grid, y_grid)

        if len(x_grid) == 1:
            data2d_grid = np.array([data2d_grid]).T
        elif len(y_grid) == 1:
            data2d_grid = np.array([data2d_grid])

    return data2d_grid


def savgol_smooth(data: np.array, boxcar: int, polyorder: int) -> np.array:
    """Apply a Savitzky-Golay filter to an array (to smooth the data)."""

    if boxcar == 0:
        smoothed = data
    else:
        smoothed = []
        for i in np.arange(len(data)):
            window_length = boxcar
            if not is_odd(window_length):
                window_length = boxcar - 1
            with warnings.catch_warnings():
                # ignore warning: "FutureWarning: Using a non-tuple sequence for multidimensional indexing is deprecated
                # use `arr[tuple(seq)]` instead of `arr[seq]`. In the future this will be interpreted as an array index,
                # `arr[np.array(seq)]`, which will result either in an error or a different result. b = a[a_slice]"
                # -> should be solved in scipy1.2.0 (https://github.com/scipy/scipy/issues/9086)
                warnings.simplefilter("ignore")
                y = savgol_filter(data[i], window_length, polyorder, deriv=0, delta=1.0, axis=-1, mode='interp',
                                  cval=0.0)
            smoothed.append(y)

    return np.array(smoothed)


def is_odd(num):
    """Check whether given number is odd."""
    return num % 2 != 0


def interpol(x, y, order=None):
    """ Interpolate y values and return function
    :param x: arguments
    :param y: values
    :return: function y(x)
    """
    if order == None:
        if len(x) > 3:
            order = 3  # cubic interpolation (works for more than 3 entries)
        elif len(x) > 2:
            order = 2  # quadratic interpolation (works for more than 2 entries)
        else:
            order = 1  # linear interpolation

    extrapolation_mode = 3  # ext=3 return boundary value for extrapolation

    # sort xy list for increasing x to avoid interpolation error (not critical because function obj returned)
    xy = np.array(sorted(np.array([x, y]).transpose(), key=lambda l: l[0])).transpose()
    x = xy[0]
    y = xy[1]

    # remove duplicates
    check_list = []
    x_new = []
    y_new = []
    for i in range(len(x)):
        if x[i] in check_list:
            pass
            # print(x[i], y[i], y[check_list.index(x[i])])
        else:
            x_new.append(x[i])
            y_new.append(y[i])
        check_list.append(x[i])

    try:
        func = InterpolatedUnivariateSpline(x_new, y_new, k=order,
                                            ext=extrapolation_mode)  # TODO: replace with numpy interpolation
    except:
        raise ValueError
    return func


def xy_to_extent(x_list: list, y_list: list) -> list:
    """
    Convert x-list and y-list to extent=[left, right, bottom, top] that can be passed to pyplots imshow.
    Assumes increasing, equally spaced values for x- and y-list and at least two values for each list

    :return [left, right, bottom, top]
    """
    horizontal_grid_offset = (x_list[1] - x_list[0]) / 2.
    left = x_list[0] - horizontal_grid_offset
    right = x_list[-1] + horizontal_grid_offset

    vertical_grid_offset = (y_list[1] - y_list[0]) / 2.
    bottom = y_list[0] - vertical_grid_offset
    top = y_list[-1] + vertical_grid_offset

    return [left, right, bottom, top]


def is_jsonable(x):
    try:
        json.dumps(x)
        return True
    except:
        return False


def update_nested_dict(initial_dict, new_dict):
    """
    Update of nested dictionaries. Input dictionary is updated.
    [https://stackoverflow.com/questions/3232943/update-value-of-a-nested-dictionary-of-varying-depth]
    :param initial_dict: dictionary that should be updated
    :param new_dict: dictionary that should be merged into the initial dict
    """
    for k, v in new_dict.items():
        if isinstance(v, collections.abc.Mapping):
            initial_dict[k] = update_nested_dict(new_dict.get(k, {}), v)
        else:
            initial_dict[k] = v
    return initial_dict


def get_save_path(root_save_path: str, is_simulator_module: bool, is_coupled_evaluation: bool, sample_name: str,
                  dataset_name: Optional[str] = None):

    # if isinstance(module, DataSetReader) or isinstance(module, Fitter):
    #     is_simulator_module = False
    # else:
    #     is_simulator_module = True

    if is_simulator_module:
        save_path = os.path.join(root_save_path, sample_name)
    else:
        if dataset_name is None:
            raise ValueError("No dataset name defined")
        if is_coupled_evaluation:
            save_path = os.path.join(root_save_path, dataset_name, sample_name)
        else:
            save_path = os.path.join(root_save_path, sample_name, dataset_name)

    if not os.path.exists(save_path):
        os.makedirs(save_path)

    return save_path


def write_to_ini(file_path: str, section_name: str, values_dict: dict):
    config = ConfigParser()
    config.optionxform = str    # preserve capital letters

    base_path = os.path.split(file_path)[0]
    if not os.path.exists(base_path):
        os.makedirs(base_path)

    if os.path.exists(file_path):
        config.read(file_path)

    with open(file_path, 'w') as configfile:
        config.add_section(section_name)

        for value_name in values_dict:
            config.set(section_name, str(value_name), str(values_dict[value_name]))
        config.write(configfile)


def chunks(lst, n):
    """Yield successive n-sized chunks from lst.
    Taken from https://stackoverflow.com/questions/312443/how-do-you-split-a-list-into-evenly-sized-chunks"""
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


def get_time_stamp() -> str:
    # -- create time stemp string in order to use it as suffix for the coupled directory --
    time_stamp_wo_ms = str(datetime.datetime.now()).split('.')[0]  # date and time separated by space
    time_stamp_joined = time_stamp_wo_ms.replace(" ", "_")  # h:min:sec -> avoid ':'
    time_stamp = time_stamp_joined.replace(":", "-")

    return time_stamp