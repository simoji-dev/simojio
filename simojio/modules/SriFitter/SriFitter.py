from simojio.lib.abstract_modules import Fitter
from simojio.modules.SriPlotter.SriPlotter import SriPlotter
from simojio.modules.SriSimulator.SriSimulator import SriSimulator
from simojio.lib.BasicFunctions import *

import numpy as np
import matplotlib.pyplot as plt


class SriFitter(Fitter):

    sri_plotter = SriPlotter()
    sri_simulator = SriSimulator()
    sri_simulator.plot_flag = True

    generic_parameters = []
    for par in sri_plotter.generic_parameters:
        if par.name not in [sri_plotter.enable_grid_par.name,
                            sri_plotter.normalize_sri_par.name]:
            generic_parameters.append(par)

    for par in sri_simulator.generic_parameters:
        if par.name not in [sri_simulator.oled_optics_simulator.wavelengths_par.name,
                            sri_simulator.oled_optics_simulator.angles_par.name]:
            generic_parameters.append(par)

    evaluation_set_parameters = sri_plotter.evaluation_set_parameters

    available_layers = sri_simulator.available_layers

    def __init__(self):
        super().__init__()

        self.idx_normalization_angle = None
        self.adf_plot_data_container = None

        self.normalized_sri = None
        self.sri_difference = None

    def configure_generic_parameters(self):

        self.sri_simulator.queue = self.queue
        sri_simulator_par_names = [par.name for par in self.sri_simulator.generic_parameters]
        for par in self.generic_parameters:
            if par.name in sri_simulator_par_names:
                par_idx = sri_simulator_par_names.index(par.name)
                self.sri_simulator.generic_parameters[par_idx] = par

        self.sri_plotter.plot_flag = False
        self.sri_plotter.hide_flag = True
        self.sri_plotter.project_onto_grid_bool = True
        self.sri_plotter.normalize_bool = True
        self.sri_plotter.queue = self.queue

        sri_plotter_par_names = [par.name for par in self.sri_plotter.generic_parameters]
        for par in self.generic_parameters:
            if par.name in sri_plotter_par_names:
                par_idx = sri_plotter_par_names.index(par.name)
                self.sri_plotter.generic_parameters[par_idx] = par

    def configure_layers(self):
        self.sri_simulator.layer_list = self.layer_list

    def configure_evaluation_set_parameters(self):
        self.sri_plotter.evaluation_set_parameters = self.evaluation_set_parameters

    def run(self):

        self.configure_generic_parameters()
        self.configure_evaluation_set_parameters()
        self.configure_layers()

        self.sri_plotter.plot_flag = False
        self.sri_plotter.hide_flag = True
        self.sri_plotter.project_onto_grid_bool = True
        self.sri_plotter.normalize_bool = True
        self.sri_plotter.run()

        self.sri_simulator.plot_flag = False
        self.sri_simulator.run()

        self.calc_optimization_value()

    def get_results_dict(self) -> dict:
        return {"SRI difference": self.sri_difference}

    def get_fit_name_and_value(self) -> (str, float):
        return "SRI difference", self.sri_difference

    def calc_optimization_value(self):

        # -- get simulated data --
        # OledOpticsSimulator has no exclude angles function. Remove angles after calculation
        # -> get indices of angles that are not in the experimental data (excluded angles)

        excluded_angle_values = set(self.sri_simulator.angles_deg) - set(self.sri_plotter.angles)
        excluded_angles_indices = [list(self.sri_simulator.angles_deg).index(angle) for angle in excluded_angle_values]

        restricted_sri = []
        for idx, spectrum in enumerate(self.sri_simulator.sri.T):
            if idx not in excluded_angles_indices:
                restricted_sri.append(spectrum)

        sim_data = np.array(restricted_sri).T

        # normalize simulated spectra to (new) smallest angle (it is calculated without exclude angles before)
        idx, value = find_nearest(list(self.sri_plotter.angles), 0.)
        spectrum = sim_data.T[idx]
        sim_data = sim_data / max(spectrum)

        # re-normalize simulated data (previous normalization angle might have been removed)
        self.normalized_sri = self.normalize_sri(np.array(self.sri_plotter.angles), sim_data).T

        # plot results
        plot_sri = len(self.sri_plotter.intensities) > 1
        if plot_sri:
            sri_difference = self.sri_plotter.intensities - self.normalized_sri
            self.plot_sri(np.array(self.sri_simulator.angles_deg), self.sri_simulator.wavelengths, sri_difference,
                          name='SRI difference')

        plot_adf = True
        if plot_adf:
            self.plot_adf(np.array(self.sri_plotter.angles), self.sri_simulator.wavelengths,
                          [self.sri_plotter.intensities, self.normalized_sri], ['experimental', 'simulated'])

        self.sri_difference = np.linalg.norm(self.sri_plotter.intensities - self.normalized_sri)

    def normalize_sri(self, angles: np.array, intensities: np.array) -> np.array:
        idx, value = find_nearest(angles, 0.)
        spectrum = intensities.T[idx]
        return intensities / max(spectrum)

    def plot_sri(self, angles, wavelengths, sri_difference, name=None):

        is_2d = False
        if (len(wavelengths) > 1) and (len(angles) > 1):
            is_2d = True
        else:
            print("SRI not plotted: Data grid not 2-dimensional.")

        if is_2d:
            fig, ax = plt.subplots()
            im = ax.imshow(sri_difference.T[::-1], extent=xy_to_extent(list(angles), list(wavelengths)))
            ax.set_xlabel("angle (deg)")
            ax.set_ylabel("wavelength (nm)")

            cb = fig.colorbar(im, label="deviation of normalized SRI", ax=ax, use_gridspec=True)

            self.plot_fig(fig, "SRI difference")

    def plot_adf(self, angles: np.array, wavelengths: np.array, intensities_list: list, labels_list: list):
        """
        Plot angular distribution function (angular emission spectrum) at wavelength at which the intensity is
        highest in forward direction (at angle closest to zero deg).
        """

        # get angle closest to zero degree + spectrum at that angle
        idx, value = find_nearest(angles, 0.)

        plot_data = []
        for intensities in intensities_list:
            spectrum = intensities[idx]

            # get index of maximum intensity of the spectrum
            idx_max = list(spectrum).index(max(spectrum))

            # get angular emission spectrum
            angular_spectrum = intensities.T[idx_max]

            # get plot data
            plot_data.append([angles, angular_spectrum])

        fig, ax = plt.subplots()
        for idx in range(len(plot_data)):
            ax.plot(plot_data[idx][0], plot_data[idx][1], '.-', label=labels_list[idx])
        ax.set_xlabel("angle (deg)")
        ax.set_ylabel("intensity (arb. units)")
        ax.legend()

        self.plot_fig(fig=fig, title="angular emission")
