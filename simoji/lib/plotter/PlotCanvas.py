import PySide2.QtWidgets as QtWidgets

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.pyplot as plt

from simoji.lib.plotter.PlotDataSaver import PlotDataSaver
from simoji.lib.plotter.SaveDataFileFormats import SaveDataFileFormats

plt.rcParams.update({'figure.max_open_warning': 0})     # mute warning "More than 20 figures have been opened"


class PlotCanvas(FigureCanvas):

    def __init__(self, parent):

        self.figure = plt.figure()
        # self.figure.subplots_adjust(bottom=0.2)

        super().__init__(self.figure)
        self.setParent(parent)

        # self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        # self.updateGeometry()
        self.is_initialized = False
        self.figsize = None

        self.plot_data_saver = PlotDataSaver()

    def update_plot(self, fig):

        if not self.is_initialized:
            self.is_initialized = True
            self.figsize = fig.get_size_inches()

        self.figure = fig
        self.draw()
        self.flush_events()

    def save_figure(self, figure_save_path: str, save_file_format: SaveDataFileFormats):
        """
        Save .png of figure and extract plot data.

        There might be multiple axes in the figure that might contain multiple artists (lines, images, collections).
        For each axis the data are stored in a separate file (add index to file name).

        The data of one axis are stored in a .json file. A dictionary to be stored looks like:

        {
        "title": ax.get_title(),
        "x-label": ax.get_xlabel(),
        "y-label": ax.get_ylabel(),
        "plot-data": []
        }

        Plot data may look different for different plot-dimensions:
        1D: [[x-list1, y-list1], [x-list2, y-list2], ...]
        2D: [[x-list1, y-list1, 2D-list1], [x-list2, y-list2, z-2D-list2], ...]
        3D: [[x-list1, y-list1, z-list1, 3D-list1], [x-list2, y-list2, z-list2, 3D-list2], ...]

        :param figure_save_path:
        :return:
        """

        if not self.is_initialized:
            raise ValueError("Cannot save figure, is not initialized.")

        # store current figure geometry
        current_size = self.figure.get_size_inches()

        # change figure geometry to initial values (as defined in the module) and save to .png
        self.figure.set_size_inches(*self.figsize)
        self.figure.tight_layout()
        self.figure.savefig(figure_save_path + ".png")

        # change figure geometry back to current size (to fit it into the window again)
        self.figure.set_size_inches(*current_size)
        self.update_plot(self.figure)

        self.plot_data_saver.file_format = save_file_format
        self.plot_data_saver.save_figure_data(self.figure, figure_save_path)







