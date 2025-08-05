import PySide6.QtWidgets as QtWidgets

from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from simojio.lib.plotter.PlotCanvas import PlotCanvas
from simojio.lib.plotter.SaveDataFileFormats import SaveDataFileFormats


class SinglePlotWidget(QtWidgets.QScrollArea):

    def __init__(self, plot_every_steps: int):
        super().__init__()

        self.setWidgetResizable(True)

        self.layout = QtWidgets.QVBoxLayout()
        self.setLayout(self.layout)

        self.canvas = None
        self.toolbar = None

        self.update_counter = 0
        self.plot_every_steps = plot_every_steps

        self.current_fig = None

    def update_plot(self, fig):

        self.current_fig = fig
        if (self.update_counter % self.plot_every_steps) == 0:
            self._renew_canvas()
            self.canvas.update_plot(fig)
        self.update_counter += 1

    def _renew_canvas(self):

        if self.toolbar is not None:
            self.layout.removeWidget(self.toolbar)
            self.toolbar.deleteLater()
        if self.canvas is not None:
            self.layout.removeWidget(self.canvas)
            self.canvas.deleteLater()

        self.canvas = PlotCanvas(self)
        self.toolbar = NavigationToolbar(self.canvas, self)
        self.layout.addWidget(self.toolbar)
        self.layout.addWidget(self.canvas)

    def save_figure(self, figure_save_path: str, save_file_format: SaveDataFileFormats):
        self.canvas.save_figure(figure_save_path, save_file_format)
        self.canvas.update_plot(self.current_fig)

    def get_url(self):
        return self.canvas.figure.get_url()
