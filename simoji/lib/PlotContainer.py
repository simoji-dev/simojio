import matplotlib.pyplot as plt


class PlotContainer:
    """Contains a pyplot figure and parameters that define how, where, and if the figure will be saved."""

    def __init__(self, fig: plt.figure, title: str, save=True,
                 is_variation_step_independent_plot=False):

        self.fig = fig
        self.title = title
        self.save = save
        self.is_variation_step_independent_plot = is_variation_step_independent_plot

        self.sample_idx = None
        self.dataset_idx = None

    def set_sample_dataset_idx(self, sample_idx: int, dataset_idx: int):
        self.sample_idx = sample_idx
        self.dataset_idx = dataset_idx