from simojio.lib.abstract_modules import Calculator
from simojio.modules.OledOptics.OledOptics import OledOptics
from simojio.lib.parameters import *
from simojio.lib.BasicFunctions import *

import numpy as np
import importlib
import matplotlib.pyplot as plt


class SriSimulator(Calculator):
    """
    Calculates the spectral radiant intensity (SRI). Use result from OledOpticsSimulator + advanced plotting options.
    Optional: Include the alterations of the SRI due to the additional lenses in the PL-Goniometer setup.
    """

    # use OledOptics module
    oled_optics_simulator = OledOptics()
    oled_optics_simulator.plot_sri_flag = False

    # -- define layer parameters --
    available_layers = oled_optics_simulator.available_layers

    # -- define generic parameters --

    # general sri calculation
    generic_parameters = [
        oled_optics_simulator.polarization_par,
        oled_optics_simulator.wavelengths_par,
        oled_optics_simulator.angles_par
    ]

    # sri correction
    do_sri_correction_switch_par = BoolParameter(name="do SRI correction", value=False,
                                                 description="Calculate correction of SRI due to spot offset etc")

    Ex_par = FloatParameter(name="Ex", value=0., description="lateral offset emission point [mm]")
    Ez_par = FloatParameter(name="Ez", value=0., description="axial offset emission point [mm]")
    Mx_par = FloatParameter(name="Mx", value=0., description="lateral offset cylinder [mm]")
    Mz_par = FloatParameter(name="Mz", value=0., description="axial offset cylinder [mm]")
    substrate_thickness_par = FloatParameter(name="substrate thickness", value=1.1,
                                             description="Substrate thickness [mm]")
    lens2_shift_z_par = FloatParameter(name="shift z lens 2", value=139.,
                                       description="axial offset of lens 2 vs overlapping focus with lens1")
    detector_shift_z_par = FloatParameter(name="shift z detector", value=0.2,
                                          description="axial offset of detector vs sitting in focus of lens2")

    generic_parameters += [do_sri_correction_switch_par, Ex_par, Ez_par, Mx_par, Mz_par,
                           substrate_thickness_par, lens2_shift_z_par, detector_shift_z_par]

    def __init__(self):
        super().__init__()

        self.angles = None
        self.angles_deg = None
        self.wavelengths = None
        self.sri = None

        self.do_sri_correction = False  # self.do_sri_correction_switch_par.value
        self.Ex = self.Ex_par.value
        self.Ez = self.Ez_par.value
        self.Mx = self.Mx_par.value
        self.Mz = self.Mz_par.value

        self.d_sub = self.substrate_thickness_par.value

        self.shift_lens2 = self.lens2_shift_z_par.value
        self.shift_detector = self.detector_shift_z_par.value

        self.layer_parameters_list = list()
        self.layer_type_list = list()

        self.sri_corrector = None
        self.any_sri_correction_parameter = False

        self.plot_flag = True

    def configure_generic_parameters(self, generic_parameters: dict):
        self.any_sri_correction_parameter = False
        self.generic_parameters = generic_parameters

        if self.do_sri_correction_switch_par.name in generic_parameters:
            self.do_sri_correction = generic_parameters[self.do_sri_correction_switch_par.name]
        if self.Ez_par.name in generic_parameters:
            self.any_sri_correction_parameter = True
            self.Ex = generic_parameters[self.Ex_par.name]
        if self.Ez_par.name in generic_parameters:
            self.any_sri_correction_parameter = True
            self.Ez = generic_parameters[self.Ez_par.name]
        if self.Mx_par.name in generic_parameters:
            self.any_sri_correction_parameter = True
            self.Mx = generic_parameters[self.Mx_par.name]
        if self.Mz_par.name in generic_parameters:
            self.any_sri_correction_parameter = True
            self.Mz = generic_parameters[self.Mz_par.name]

        if self.substrate_thickness_par.name in generic_parameters:
            self.any_sri_correction_parameter = True
            self.d_sub = generic_parameters[self.substrate_thickness_par.name]

        if self.lens2_shift_z_par.name in generic_parameters:
            self.any_sri_correction_parameter = True
            self.shift_lens2 = generic_parameters[self.lens2_shift_z_par.name]
        if self.detector_shift_z_par.name in generic_parameters:
            self.any_sri_correction_parameter = True
            self.shift_detector = generic_parameters[self.detector_shift_z_par.name]

        generic_parameters.update({self.oled_optics_simulator.wavevectors_par.name: [0., 3.5, 0.002]})
        self.oled_optics_simulator.configure_generic_parameters(generic_parameters)

    def run(self):

        self.configure_oled_optics_simulator()
        self.oled_optics_simulator.run()

        self.angles = self.oled_optics_simulator.angles
        self.angles_deg = np.array([round(angle * 180. / np.pi, 7) for angle in self.angles])  # avoid strange rounding
        self.wavelengths = self.oled_optics_simulator.wavelength_arr
        self.sri = self.oled_optics_simulator.sri

        # do sri correction
        if self.do_sri_correction:
            # reload module
            module = importlib.import_module('simojio.modules.SriSimulator.SriCorrection')
            module = importlib.reload(module)
            module_cls = getattr(module, 'SriCorrection')

            # initialize SriCorrection module with given geometrical values
            self.sri_corrector = module_cls()
            self.sri_corrector.set_emission_point(x=self.Ex, z=self.Ez)
            self.sri_corrector.set_substrate(thickness=self.d_sub, n=1.5)
            self.sri_corrector.set_cylinder(x=self.Mx, z=self.Mz, radius=20., n=1.5)
            self.sri_corrector.add_lens(x=0., z=0., f=50., overlap_focus_with_last_lens_focus=True, shift_z=0.)
            self.sri_corrector.add_lens(x=0., z=0., f=11., overlap_focus_with_last_lens_focus=True,
                                        shift_z=self.shift_lens2)
            self.sri_corrector.set_detector(x=0., z=0., width=0.4, NA=0.1, tilt_angle=0.,
                                            place_in_last_lens_focus=True, shift_z=self.shift_detector)

            self.angles_deg, self.wavelengths, self.sri = self.sri_corrector.calculate_sri_correction(self.angles_deg,
                                                                                                      self.wavelengths,
                                                                                                      self.sri)
        if self.plot_flag:
            self.plot_sri()
            self.plot_adf(self.angles_deg, self.wavelengths, self.sri)

    def get_results_dict(self) -> dict:
        return {}

    def configure_oled_optics_simulator(self):

        self.oled_optics_simulator.layer_list = self.layer_list

        oled_optics_generic_parameters_names = [par.name for par in self.oled_optics_simulator.generic_parameters]

        for parameter in self.generic_parameters:
            if parameter.name in oled_optics_generic_parameters_names:
                par_idx = oled_optics_generic_parameters_names.index(parameter.name)
                self.oled_optics_simulator.generic_parameters[par_idx] = parameter

        self.oled_optics_simulator.calc_powdiss_flag_par.value = False
        self.oled_optics_simulator.calc_eqe_flag_par.value = False
        self.oled_optics_simulator.calc_sri_flag_par.value = True
        self.oled_optics_simulator.calc_loss_channels_flag_par.value = False

        self.oled_optics_simulator.plot_sri_flag = False
        self.oled_optics_simulator.plot_angle_spectrum_flag = False
        self.oled_optics_simulator.plot_forward_spectrum_flag = False
        self.oled_optics_simulator.plot_optical_constants_flag = False

    def plot_sri(self):

        if len(self.wavelengths) > 1:
            fig, ax = plt.subplots()
            im = ax.imshow(self.sri, extent=xy_to_extent(list(self.angles * 180. / np.pi), list(self.wavelengths)),
                           origin='lower')
            ax.set_xlabel("angle (deg)")
            ax.set_ylabel("wavelength (nm)")

            fig.colorbar(im, label="spectral radiant intensity (SRI)", ax=ax, use_gridspec=True)

            self.plot_fig(fig, "simulated SRI")

    def plot_adf(self, angles: np.array, wavelengths: np.array, intensities: np.array):
        """
        Plot angular distribution function (angular emission spectrum) at wavelength at which the intensity is
        highest in forward direction (at angle closest to zero deg).
        """

        # get angle closest to zero degree + spectrum at that angle
        idx, value = find_nearest(angles, 0.)

        spectrum = intensities.T[idx]

        # get index of maximum intensity of the spectrum
        idx_max = list(spectrum).index(max(spectrum))

        # get angular emission spectrum
        angular_spectrum = intensities[idx_max]

        fig, ax = plt.subplots()
        ax.plot(angles, angular_spectrum, '.-', label="angular emission")
        ax.set_xlabel("angle (deg)")
        ax.set_ylabel("intensity (arb. units)")
        ax.legend()

        self.plot_fig(fig=fig, title="angular emission")
