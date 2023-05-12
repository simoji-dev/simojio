import PySide2.QtWidgets as QtWidgets
import PySide2.QtCore as QtCore

import matplotlib
import matplotlib.pyplot as plt
import os
import numpy as np

from simojio.lib.plotter.SinglePlotWidget import SinglePlotWidget
import simojio.lib.OptimizationResultsContainer
from simojio.lib.plotter.OptimizationResultsWidget import OptimizationResultsWidget
from simojio.lib.plotter.VariationResultsWidget import VariationResultsWidget
from simojio.lib.VariationResultsContainer import VariationResultsContainer
from simojio.lib.plotter.SaveDataFileFormats import SaveDataFileFormats

matplotlib.use("Qt5Agg")


class TabPlotWindow(QtWidgets.QMainWindow):
    """
    Window that fills one tab of the plot window. It includes either the overview plots/results (for variations or
    optimizations) or all the results that are emitted by a module for a single configuration.

    In case of the overview plots the plots are updated from step to step. In order to identify them, their titles are
    stored in a list.
    """

    def __init__(self, plot_every_steps=1):
        super().__init__()

        self.plot_every_steps = plot_every_steps

        self.figure_list = list()       # [DockWidget, title, save_bool]

        self.plot_counter = 0
        self.maximum_number_of_shown_plots = 10

        self.variation_results_widget = None
        self.variation_results_plot = None
        self.variation_result_values = []
        self.variation_result_labels = []

    def plot(self, fig, title: str, save=True):

        all_titles = []
        if len(self.figure_list) > 0:
            all_titles = list(zip(*self.figure_list))[1]    # transpose list with zip, titles are in column 1

        if title in all_titles:
            # figure already exists and is updated here
            dock_widget = self.figure_list[all_titles.index(title)][0]
            dock_widget.widget().update_plot(fig)
        else:
            # figure does not yet exist and needs to be created
            plot_widget = SinglePlotWidget(self.plot_every_steps)
            plot_widget.update_plot(fig)
            self.new_dock_widget(plot_widget, title, save)

    def add_optimization_results(self,
                                 opt_results: simojio.lib.OptimizationResultsContainer.OptimizationResultsContainer):
        widget = OptimizationResultsWidget(opt_results)
        self.new_dock_widget(widget, "optimization results", save=True)
        self.save_fig_list.append(True)

    def update_variation_results(self, variation_results: VariationResultsContainer):
        if self.variation_results_widget is None:
            self.variation_results_widget = VariationResultsWidget(variation_results)
            self.new_dock_widget(self.variation_results_widget, "numerical results", True)

            if variation_results.plot_flag:
                if len(variation_results.result_names) > 0:
                    self.variation_results_plot = SinglePlotWidget(self.plot_every_steps)
                    self.new_dock_widget(self.variation_results_plot, "numerical results plot", True)

                    self.variation_result_labels = variation_results.result_names
                    self.variation_result_values = [[None] * len(self.variation_result_labels)] * len(
                        variation_results.variation_results_list)

        self.variation_results_widget.update_variation_results_widget(variation_results)

        # update plot
        if variation_results.plot_flag:
            self.variation_result_values[variation_results.update_idx] = variation_results.variation_results_list[
                variation_results.update_idx]
            result_values = np.array(self.variation_result_values).T

            if len(result_values) > 0:
                fig, ax = plt.subplots()
                for idx, label in enumerate(self.variation_result_labels):
                    steps = np.arange(len(variation_results.variation_results_list))
                    values = result_values[idx]
                    ax.plot(steps, values, 'o-', label=label)

                ax.set_xticks(steps)
                rotation = 0
                if len(steps) > 5:
                    rotation = 90
                ax.set_xticklabels(variation_results.row_names, rotation=rotation)
                ax.legend()
                # ax.set_xlabel("variation set")
                ax.set_ylabel("result value")
                fig.tight_layout()
                self.variation_results_plot.update_plot(fig)

    def new_dock_widget(self, widget: QtWidgets.QWidget, title: str, save: bool):

        dock_widget = QtWidgets.QDockWidget(self)
        dock_widget.setWidget(widget)
        dock_widget.setWindowTitle(title)

        self.figure_list.append([dock_widget, title, save])
        self.plot_counter += 1

        if (self.plot_counter % 2) == 0:
            self.addDockWidget(QtCore.Qt.RightDockWidgetArea, dock_widget)
        else:
            self.addDockWidget(QtCore.Qt.LeftDockWidgetArea, dock_widget)

    def save(self, save_path: str, save_file_format: SaveDataFileFormats):
        """Save data of all plots and text widgets."""

        for idx, [dock_widget, title, save] in enumerate(self.figure_list):
            if save:
                widget = dock_widget.widget()
                widget_save_path = os.path.join(save_path, dock_widget.windowTitle())

                if isinstance(widget, OptimizationResultsWidget):
                    widget.save_data(widget_save_path)
                elif isinstance(widget, VariationResultsWidget):
                    widget.save_data(widget_save_path)
                else:
                    widget.save_figure(widget_save_path, save_file_format)
