import numpy as np
import matplotlib.pyplot as plt
import multiprocessing as mp
from matplotlib.ticker import MaxNLocator
from typing import List, Optional
from anytree import RenderTree, render
from anytree.exporter import UniqueDotExporter
import os
import PySide2.QtWidgets as QtWidgets

from simoji.lib.module_executor.MyNode import MyNode
from simoji.lib.PlotContainer import PlotContainer
from simoji.lib.Sample import Sample
from simoji.lib.GlobalSettingsContainer import GlobalSettingsContainer
from simoji.lib.CallbackContainer import CallbackContainer


def show_callback(parent, callback: CallbackContainer):
    dlg = QtWidgets.QMessageBox(parent)
    dlg.setWindowTitle(callback.title)

    text = ""
    if callback.leave_path is not None:
        text += "<b>" + callback.leave_path + ":</b><br><br>"
    text += callback.message.replace("\n", "<br>")

    dlg.setText(text)
    dlg.exec_()


def plot_optimization_steps(optimization_values: List[float], optimization_value_name: str,
                            variable_values_list: List[List[float]], variable_names: List[str],
                            queue: mp.Queue, save: Optional[bool] = True,
                            is_variation_step_independent_plot: Optional[bool] = False,
                            title_prefix: Optional[str] = "optimization"):

    if len(variable_names) == 2:
        x = np.array(variable_values_list).T[0]
        y = np.array(variable_values_list).T[1]

        fig, ax = plt.subplots()

        im = ax.scatter(x, y, c=optimization_values, s=100)

        ax.set_xlabel(variable_names[0])
        ax.set_ylabel(variable_names[1])
        ax.set_title(title_prefix + " steps")

        cb = fig.colorbar(im, label=optimization_value_name, ax=ax, use_gridspec=True, cmap='viridis')

        plot_container = PlotContainer(fig=fig, title=title_prefix + " steps 2d", save=save,
                                       is_variation_step_independent_plot=is_variation_step_independent_plot)

        queue.put(plot_container)

    else:
        for idx, values in enumerate(np.array(variable_values_list).T):
            fig, ax = plt.subplots()

            im = ax.scatter(values, optimization_values, c=range(len(values)), cmap='cool',
                            label="optimization value")
            ax.set_xlabel(variable_names[idx])
            ax.set_ylabel(optimization_value_name)
            ax.set_title("optimization steps " + variable_names[idx])
            ax.legend()

            cb = fig.colorbar(im, label="optimization step", ax=ax, use_gridspec=True)
            cb.ax.yaxis.set_major_locator(MaxNLocator(integer=True))

            plot_container = PlotContainer(fig=fig, title="optimization steps " + variable_names[idx],
                                           save=save,
                                           is_variation_step_independent_plot=is_variation_step_independent_plot)
            queue.put(plot_container)


def get_optimization_settings(sample: Sample, global_settings: GlobalSettingsContainer):

    opt_value_name = sample.optimization_settings.name_of_value_to_be_optimized

    if global_settings.use_global_optimization_settings:
        method = global_settings.optimization_settings.current_solver
        maximize = global_settings.optimization_settings.maximize
        maximum_number_of_iterations = global_settings.optimization_settings.maximum_number_of_iterations
    else:
        method = sample.optimization_settings.current_solver
        maximize = sample.optimization_settings.maximize
        maximum_number_of_iterations = sample.optimization_settings.maximum_number_of_iterations

    return opt_value_name, method, maximize, maximum_number_of_iterations


def save_tree(tree: MyNode, save_path: str):
    try:
        UniqueDotExporter(tree, nodeattrfunc=lambda n: 'label="%s"' % n.name).to_picture(
            os.path.join(save_path, tree.name + "_tree.png"))
    except Exception as e:
        # save as txt
        with open(os.path.join(save_path, tree.name + "_tree.txt"), 'w') as f:
            for pre, _, node in RenderTree(tree, style=render.AsciiStyle()):
                f.write(str(pre) + str(node.name) + "\n")

