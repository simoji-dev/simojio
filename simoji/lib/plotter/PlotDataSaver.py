import matplotlib.pyplot as plt
import numpy as np
import os
import json
import csv
from typing import *

from simoji.lib.plotter.SaveDataFileFormats import SaveDataFileFormats
from simoji.lib.BasicFunctions import *


class PlotDataSaver:

    def __init__(self, file_format=SaveDataFileFormats.CSV):
        self.file_format = file_format

        # save dict keys
        self.title_key = "title"
        self.x_label_key = "x-label"
        self.y_label_key = "y-label"
        self.z_label_key = "z-label"
        self.data_set_labels_key = "data-set-labels"
        self.plot_data_key = "plot-data"

    def save_figure_data(self, figure: plt.Figure, figure_save_path: str):

        for idx, ax in enumerate(figure.get_axes()):
            # An ax might include different plot-artists (e.g. an image with lines on top)
            # -> save in separate files

            plot_data_lines = []
            data_set_labels_lines = []

            plot_data_images = []
            data_set_labels_images = []

            plot_data_collections = []
            data_set_labels_collections = []

            nb_of_different_artists = 0

            # 1D-plot
            if len(ax.lines) > 0:
                nb_of_different_artists += 1
                plot_data_lines = [np.array(line.get_xydata()).T.tolist() for line in ax.lines]
                data_set_labels_lines = [line.get_label() for line in ax.lines]

            # 2D-imshow
            if len(ax.images) > 0:
                nb_of_different_artists += 1

                for image in ax.images:
                    data2d = np.array(image.get_array())[::-1]  # origin is on top left corner
                    x_data, y_data = self._extent_to_xy(image.get_extent(), data2d.shape)
                    plot_data_images.append([x_data, y_data, data2d.tolist()])
                    data_set_labels_images.append(image.get_label())

            # 2D-scatter
            if len(ax.collections) > 0:
                nb_of_different_artists += 1

                for collection in ax.collections:
                    if collection.get_offsets().T.tolist() == [[0.], [0.]]:
                        # Note: Special case are colorbars
                        # They yield [[0.0], [0.0]] for get_offset() -> check for this result and ignore the data in case
                        pass
                    else:
                        xy_data = np.array(collection.get_offsets()).T.tolist()
                        z_data = np.array(collection.get_array()).tolist()
                        xyz_data = xy_data + [z_data]

                        plot_data_collections.append(xyz_data)
                        data_set_labels_collections.append(collection.get_label())

            # todo: error message if data cannot be saved (e.g. contourf)

            if len(plot_data_lines) > 0:
                save_dict_lines = {
                    self.title_key: ax.get_title(),
                    self.x_label_key: ax.get_xlabel(),
                    self.y_label_key: ax.get_ylabel(),
                    self.data_set_labels_key: data_set_labels_lines,
                    self.plot_data_key: plot_data_lines
                }

                if nb_of_different_artists > 1:
                    suffix = "lines"
                else:
                    suffix = None

                self._save_to_file(save_dict=save_dict_lines, ax_idx=idx, figure_save_path=figure_save_path,
                                   suffix=suffix)

            if len(plot_data_images) > 0:

                # try to get the color bar label (if there is no color bar for this ax, the z-label is set to None
                z_label = None
                for image in ax.images:
                    try:
                        z_label = image.colorbar._label  # if a colorbar is found, it is (usually) the only one
                        break
                    except:
                        pass

                save_dict_images = {
                    self.title_key: ax.get_title(),
                    self.x_label_key: ax.get_xlabel(),
                    self.y_label_key: ax.get_ylabel(),
                    self.z_label_key: z_label,
                    self.data_set_labels_key: data_set_labels_images,
                    self.plot_data_key: plot_data_images
                }

                if nb_of_different_artists > 1:
                    suffix = "images"
                else:
                    suffix = None

                self._save_to_file(save_dict=save_dict_images, ax_idx=idx, figure_save_path=figure_save_path,
                                   suffix=suffix)

            if len(plot_data_collections) > 0:

                # try to get the color bar label (if there is no color bar for this ax, the z-label is set to None
                z_label = None
                for collection in ax.collections:
                    try:
                        z_label = collection.colorbar._label  # if a colorbar is found, it is (usually) the only one
                        break
                    except:
                        pass

                save_dict_collections = {
                    self.title_key: ax.get_title(),
                    self.x_label_key: ax.get_xlabel(),
                    self.y_label_key: ax.get_ylabel(),
                    self.z_label_key: z_label,
                    self.data_set_labels_key: data_set_labels_collections,
                    self.plot_data_key: plot_data_collections
                }

                if nb_of_different_artists > 1:
                    suffix = "collections"
                else:
                    suffix = None

                self._save_to_file(save_dict=save_dict_collections, ax_idx=idx, figure_save_path=figure_save_path,
                                   suffix=suffix)

    def _extent_to_xy(self, extent: list, shape_2d) -> (list, list):

        left, right, bottom, top = extent

        horizontal_offset = (right - left) / (2. * shape_2d[1])   # half the length of a pixel
        x_data = np.linspace(left + horizontal_offset, right - horizontal_offset, shape_2d[1]).tolist()

        vertical_offset = (top - bottom) / (2. * shape_2d[0])  # half the length of a pixel
        y_data = np.linspace(bottom + vertical_offset, top - vertical_offset, shape_2d[0]).tolist()

        return x_data, y_data

    def _save_to_file(self, save_dict: dict, ax_idx: int, figure_save_path: str, suffix: Optional[str] = None):

        file_paths = self._get_file_paths(data_set_labels=save_dict[self.data_set_labels_key],
                                          ax_idx=ax_idx, figure_save_path=figure_save_path, suffix=suffix)

        if self.file_format is SaveDataFileFormats.JSON:
            self._save_as_json(file_paths[0], save_dict)
        elif self.file_format is SaveDataFileFormats.CSV:
            self._save_as_csv(file_paths, save_dict)
        elif self.file_format is SaveDataFileFormats.TXT:
            self._save_as_txt(file_paths, save_dict)
        else:
            raise NotImplementedError("File format '" + str(self.file_format) + "' not implemented.")

    def _get_file_paths(self, data_set_labels: List[str], ax_idx: int, figure_save_path: str,
                       suffix: Optional[str] = None):
        """
        Add suffix and index of axis to the save path.
        :param ax_idx:
        :param figure_save_path:
        :param suffix:
        :return:
        """

        base_path, filename = os.path.split(figure_save_path)
        filename += "_plotdata"
        if ax_idx > 0:
            filename += "ax" + str(ax_idx)

        if suffix is None:
            suffix = ""
        else:
            suffix = "_" + suffix

        file_name_list = []
        if self.file_format is SaveDataFileFormats.JSON:
            file_name_list = [filename + suffix]
        elif self.file_format in [SaveDataFileFormats.CSV, SaveDataFileFormats.TXT]:
            if len(data_set_labels) > 1:
                for label in data_set_labels:
                    file_name_list.append(filename + "_" + label + suffix)
            else:
                file_name_list.append(filename + suffix)
        else:
            raise NotImplementedError("File format '" + str(self.file_format) + "' not implemented for saving.")

        return [os.path.join(base_path, filename + self.file_format.value) for filename in file_name_list]

    def _save_as_json(self, file_path: str, save_dict: dict):
        """Save as .json file with multiple data sets in one file."""

        print("json saving")

        json_file = open(file_path, 'w', encoding='utf-8')
        json.dump(save_dict, json_file, sort_keys=True, indent=4)
        json_file.close()

    def _save_as_csv(self, file_paths: List[str], save_dict: dict):
        """
        Save as (multiple) .csv file(s) with one data set per file.

        Problem: 2D data -> convert to column style
        """

        print('csv saving')

        label_keys = [self.x_label_key, self.y_label_key, self.z_label_key]
        labels = []

        for label_key in label_keys:
            if label_key in save_dict:
                labels.append(save_dict[label_key])

        for idx, file_path in enumerate(file_paths):
            with open(file_path, 'w', newline='') as outcsv:
                writer = csv.writer(outcsv)
                data = self._convert_to_column_style(save_dict[self.plot_data_key][idx])

                # write header
                writer.writerow(["plot-title", save_dict[self.title_key]])
                writer.writerow([labels[idx] for idx in range(len(data[0]))])

                # write data
                writer.writerows(data)

    def _save_as_txt(self, file_paths: List[str], save_dict: dict):
        """
        Save as (multiple) .csv file(s) with one data set per file.

        Problem: 2D data -> convert to column style
        """

        print('txt saving')

        label_keys = [self.x_label_key, self.y_label_key, self.z_label_key]
        labels = []

        for label_key in label_keys:
            if label_key in save_dict:
                labels.append(save_dict[label_key])

        for idx, file_path in enumerate(file_paths):
            with open(file_path, 'w') as outtxt:
                data = self._convert_to_column_style(save_dict[self.plot_data_key][idx])

                # write header
                outtxt.writelines(["# plot-title: " + save_dict[self.title_key] + "\n"])
                outtxt.writelines("# " + ",".join([labels[idx] for idx in range(len(data[0]))]) + "\n")

                # write data
                outtxt.writelines([",".join([str(val) for val in row]) + "\n" for row in data])

    def _convert_to_column_style(self, data: list) -> np.array:
        """
        Data can be present as lists with same shape (as meshgrid style in numpy), e.g.

        x = [[0.8, .0.7, 0.5], [1.1, 1.2, 1.3]]
        y = [[0.8, .0.7, 0.5], [1.1, 1.2, 1.3]]
        data = [[0.8, .0.7, 0.5], [1.1, 1.2, 1.3]]

        or with 1D-ND-shape meaning that the axis values are given in 1D lists and the actual data are given as
        multi-dimensional list, e.g.

        x = [1,2,3]
        y = [1,2]
        data = [[0.8, .0.7, 0.5], [1.1, 1.2, 1.3]]

        For both cases, they are converted to column style, e.g.

        column_data = [[1, 1, 0.8],
                       [1, 2, 0.7],
                       [2, 1, 0.5],
                       [2, 2, 1.1],
                       [3, 1, 1.2],
                       [3, 2, 1.3]]

        :param data:
        :return: column_data
        """

        is_1d_list = [len(np.array(item).shape) == 1 for item in data]

        if all(is_1d_list[:-1]) and (not is_1d_list[-1]):
            # extend axis lists to meshgrid shape of last item
            data = [item for item in np.meshgrid(*data[:-1])] + [data[-1]]

        column_data = np.array(np.vstack(list((map(np.ravel, data))))).T

        return column_data

