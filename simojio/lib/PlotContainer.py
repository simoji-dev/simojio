import matplotlib.pyplot as plt


class PlotContainer:

    def __init__(self, fig: plt.figure, title: str, save=True,
                 is_variation_step_independent_plot=False):

        self.fig = fig
        self.title = title
        self.save = save
        self.is_variation_step_independent_plot = is_variation_step_independent_plot

        self.sample_idx = None
        self.evaluation_set_idx = None

    def set_sample_evaluation_set_idx(self, sample_idx: int, evaluation_set_idx: int):
        self.sample_idx = sample_idx
        self.evaluation_set_idx = evaluation_set_idx