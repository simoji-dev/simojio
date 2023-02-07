from abc import ABC
import matplotlib.pyplot as plt

# imports for simoji interface
from simoji.lib.abstract_modules import Plotter
from simoji.lib.parameters import *

# imports of SriReader module
from simoji.modules.SriPlotter.AngleSpectrumReader import AngleSpectrumReader
from simoji.modules.SriPlotter.FitType import FitType
from simoji.lib.BasicFunctions import *


class SriPlotter(Plotter, ABC):
    """Plotter of angle-resolved luminescence spectra measured with SweepMe."""

    # -- generic parameters --
    angles_par = StartStopStepParameter(name="angles", start=-89, stop=89, step=1, description="emission angles")
    wavelengths_par = StartStopStepParameter(name="wavelengths", start=400, stop=800, step=1, description="wavelengths")
    boxcar_par = FloatParameter(name="boxcar", value=0, description="boxcar value")
    reference_angle_par = FloatParameter(name="reference angle", value=0,
                                         description="Reference angle at which intermediate measurements are don")
    intensity_drift_fit_type_par = MultiStringParameter(name="intensity drift correction", value=FitType.NO.value,
                                                        description="Fit type for intensity drift correction",
                                                        bounds=[FitType.NO.value, FitType.LINEAR.value,
                                                                FitType.EXPONENTIAL.value, FitType.INTERPOLATE.value])
    exclude_angles_par = AnyStringParameter(name="exclude angles", value="",
                                            description="Angles to be excluded from angle grid. Give as list of tuples, e.g. '(-5,5), (10,20)'")
    cycle_par = FixFloatParameter(name="angle cycle", value=0,
                                  description="Number of angle cycle for multiple measurements cycles (e.g. -90 -> 90 -> -90")

    normalize_sri_par = BoolParameter(name="normalize SRI", value=True,
                                      description="Normalize SRI to maximum of spectrum at angle closest to zero deg.")
    angle_offset_par = FloatParameter(name="angle offset", value=0., description="angle offset")

    enable_grid_par = BoolParameter(name="enable angle-wavelength grid", value=True,
                                    description="select whether to project the data onto the angle-wavelength grid")

    generic_parameters = [angles_par, wavelengths_par, boxcar_par, reference_angle_par,
                                              intensity_drift_fit_type_par, exclude_angles_par, cycle_par,
                                              normalize_sri_par,
                                              angle_offset_par, enable_grid_par]

    # -- evaluation set parameters --
    path_par = PathParameter(name="SRI data", value=["exp_data"], description="Path to folder containing SRI data",
                             select_files=False)

    evaluation_set_parameters = [path_par]

    def __init__(self):
        super().__init__()

        self.angle_spectrum_reader = AngleSpectrumReader()

        self.intensities = None
        self.wavelengths = None
        self.angles = None

        self.reference_angle = 0.
        self.angle_offset = 0.

        self.boxcar = 0
        self.cycle = 0
        self.drift_fit_type = FitType.NO

        self.project_onto_grid_bool = False
        self.wavelength_grid = None
        self.angle_grid = None

        self.spectrometer_match_str = None  # sweepme files contain user defined name of spectrometer device
        self.motor_match_str = None  # sweepme files contain user defined name of rotation motor device

        self.normalize_bool = False

        self.plot_flag = True
        self.hide_flag = False

        self.sri_data_path = None

        self.new_data = False

    def update_generic_parameters(self):
        """
        This method is called for each execution step of the module. E.g. in optimization mode, the module instance
        is created first and then for each optimization step, the configure methods and the run method are called.
        The dictionary only contains parameters that have been changed with respect to the previous run.
        """

        # optionally, project sri data onto angle-wavelength grid (+ exclude angles)
        self.project_onto_grid_bool = self.get_generic_parameter_value(self.enable_grid_par)

        if self.project_onto_grid_bool:
            self.wavelength_grid = start_stop_step_to_list(self.get_generic_parameter_value(self.wavelengths_par))
            angle_grid_total = start_stop_step_to_list(self.get_generic_parameter_value(self.angles_par))

            # remove 'exclude angles' from angle grid
            exclude_angles_str_list = self.get_generic_parameter_value(self.exclude_angles_par)
            exclude_angles_tuple_list = eval_exclude_tuple(exclude_angles_str_list)

            self.angle_grid = remove_exclude_values_from_list(total_value_list=angle_grid_total,
                                                              exclude_tuple_list=exclude_angles_tuple_list)

        self.angle_offset = self.get_generic_parameter_value(self.angle_offset_par)
        self.normalize_bool = self.get_generic_parameter_value(self.normalize_sri_par)
        self.boxcar = int(self.get_generic_parameter_value(self.boxcar_par))
        self.cycle = int(self.get_generic_parameter_value(self.cycle_par))
        self.reference_angle = self.get_generic_parameter_value(self.reference_angle_par)
        self.drift_fit_type = FitType(self.get_generic_parameter_value(self.intensity_drift_fit_type_par))

    def update_evaluation_set_parameters(self):

        self.new_data = True    # todo: Add check, if data have been updated to avoid repeated data loading
        self.sri_data_path = convert_list_to_path_str(self.get_evaluation_parameter_value(self.path_par))

    def run(self):

        self.update_generic_parameters()
        self.update_evaluation_set_parameters()

        if self.new_data:
            data_dict = self.angle_spectrum_reader.read_angle_spectrum_from_path(path=self.sri_data_path,
                                                                                 angles=self.angle_grid,
                                                                                 wavelengths=self.wavelength_grid,
                                                                                 reference_angle=self.reference_angle,
                                                                                 angle_offset=self.angle_offset,
                                                                                 boxcar=self.boxcar,
                                                                                 cycle=self.cycle,
                                                                                 drift_fit_type=self.drift_fit_type,
                                                                                 normalize=self.normalize_bool)

            # plot angle-spectra
            self.angles = data_dict[self.angle_spectrum_reader.angles_label]
            self.wavelengths = data_dict[self.angle_spectrum_reader.wavelengths_label]
            self.intensities = data_dict[self.angle_spectrum_reader.intensities_label]

            self.plot_adf(self.angles, self.wavelengths, self.intensities)
            self.plot_sri(self.angles, self.wavelengths, self.intensities)

            # plot intensity drift correction
            data_max = data_dict[self.angle_spectrum_reader.maxima_label]
            data_fit = data_dict[self.angle_spectrum_reader.fit_label]
            data_corr = data_dict[self.angle_spectrum_reader.corrected_label]

            self.plot_intensity_drift_corr(data_max, data_fit, data_corr)

    def plot_adf(self, angles: np.array, wavelengths: np.array, intensities: np.array):
        """
        Plot angular distribution function (angular emission spectrum) at wavelength at which the intensity is
        highest in forward direction (at angle closest to zero deg).
        """

        if self.plot_flag:
            # get angle closest to zero degree + spectrum at that angle
            idx, value = find_nearest(angles, 0.)
            spectrum = intensities[idx]

            # get index of maximum intensity of the spectrum
            idx_max = list(spectrum).index(max(spectrum))
            wl_max = wavelengths[idx_max]
            print("Maximum wavelength: ", wl_max)

            # get angular emission spectrum
            angular_spectrum = intensities.T[idx_max]

            # plot
            fig, ax = plt.subplots()
            ax.plot(angles, angular_spectrum, '.-', label="emission at " + str(wl_max) + "nm")
            ax.set_xlabel("angle (deg)")
            ax.set_ylabel("intensity (arb. units)")
            ax.legend()

            self.plot_fig(fig, "angular emission")

    def plot_sri(self, angles: np.array, wavelengths: np.array, intensities: np.array):

        is_2d = False
        if (len(wavelengths) > 1) and (len(angles) > 1):
            is_2d = True
        else:
            print("SRI not plotted: Data grid not 2-dimensional.")

        if self.plot_flag and is_2d:
            fig, ax = plt.subplots()
            im = ax.imshow(intensities.T[::-1], extent=xy_to_extent(list(angles), list(wavelengths)),
                           interpolation='nearest')
            ax.set_xlabel("angle (deg)")
            ax.set_ylabel("wavelength (nm)")

            if self.normalize_bool:
                format = "%.1f"
            else:
                format = "%.1e"
            cb = fig.colorbar(im, label="spectral radiant intensity (SRI)", ax=ax, use_gridspec=True,
                              format=format)

            self.plot_fig(fig, "experimental SRI")

    def plot_intensity_drift_corr(self, data_maxima, data_fit, data_corr):

        fig, ax = plt.subplots()
        ax.plot(*data_maxima, 'o', label="maxima")
        ax.plot(*data_fit, '.-', label="fit")
        ax.plot(*data_corr, '.-', label="correction")
        ax.set_xlabel("measurement step")
        ax.set_ylabel("intensity (arb. units)")

        self.plot_fig(fig, "intensity drift")