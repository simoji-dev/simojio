from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.pyplot as plt

from simoji.lib.plotter.PlotDataSaver import PlotDataSaver
from simoji.lib.plotter.SaveDataFileFormats import SaveDataFileFormats

plt.rcParams.update({'figure.max_open_warning': 0})     # mute warning "More than 20 figures have been opened"


class PlotCanvas(FigureCanvas):

    def __init__(self, parent):

        self.figure = plt.figure()

        super().__init__(self.figure)
        self.setParent(parent)

        self.is_initialized = False
        self.fig_size = None

        self.plot_data_saver = PlotDataSaver()

    def update_plot(self, fig):

        if not self.is_initialized:
            self.is_initialized = True
            self.fig_size = fig.get_size_inches()

        self.figure = fig
        self.draw()
        self.flush_events()

    def save_figure(self, figure_save_path: str, save_file_format: SaveDataFileFormats):
        """Save .png of figure and extract plot data"""

        if not self.is_initialized:
            raise ValueError("Cannot save figure, is not initialized.")

        # store current figure geometry
        current_size = self.figure.get_size_inches()

        # change figure geometry to initial values (as defined in the module) and save to .png
        self.figure.set_size_inches(*self.fig_size)
        self.figure.tight_layout()
        self.figure.savefig(figure_save_path + ".png")

        # change figure geometry back to current size (to fit it into the window again)
        self.figure.set_size_inches(*current_size)
        self.update_plot(self.figure)

        self.plot_data_saver.file_format = save_file_format
        self.plot_data_saver.save_figure_data(self.figure, figure_save_path)







