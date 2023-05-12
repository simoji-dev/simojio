from simojio.lib.abstract_modules import Calculator
from simojio.lib.parameters import *
from simojio.lib.BasicFunctions import *
from simojio.lib.enums.LayerType import LayerType
from simojio.lib.Layer import Layer
from simojio.modules.RTA.TransferMatrix import TransferMatrix
from simojio.modules.RTA.Polarization import Polarization
from simojio.modules.RTA.MaterialFileReader import MaterialFileReader

import numpy as np
import matplotlib.pyplot as plt
from typing import List


class RTA(Calculator):
    """
    Example module for performing simulations.
    """

    # -- Define generic parameters --
    polarization_par = MultiStringParameter(name="polarization", value=Polarization.TOTAL.value,
                                            description="Polarisation of emitted light",
                                            bounds=[Polarization.TOTAL.value, Polarization.P.value,
                                                    Polarization.S.value])
    wavelengths_par = StartStopStepParameter(name="wavelengths", start=400, stop=800, step=1,
                                             description="wavelength range (nm)")
    design_wavelength_par = FixFloatParameter(name="design wavelength", value=600,
                                              description="Wavelength for which the numerical values are calculated.")
    angles_par = StartStopStepParameter(name="2D angles", start=0, stop=90, step=1,
                                        description='emission angles for SRI calculation (deg)')

    enable_2D_par = BoolParameter(name="2D calculation", value=True, description="Plot 2D spectra.")

    top_illumination = "top illumination"
    bottom_illumination = "bottom illumination"
    illumination_direction_par = MultiStringParameter(name="illumination direction", value=top_illumination,
                                                      description="Direction from where the light enters",
                                                      bounds=[top_illumination, bottom_illumination])

    generic_parameters = [illumination_direction_par, polarization_par, wavelengths_par, design_wavelength_par,
                          enable_2D_par, angles_par]

    # -- define layer parameters --
    material_par = FileFromPathParameter(name="material", path=os.path.join("modules", "shared_resources",
                                                                            "optical_constants"),
                                         extension_list=[".fmf"], description="Material data file")
    thickness_par = FloatParameter(name="thickness", value=50., bounds=(0., np.inf), description="layer thickness")

    available_layers = [
        Layer(LayerType.COHERENT, parameters=[material_par, thickness_par]),
        Layer(LayerType.SUBSTRATE, parameters=[material_par, thickness_par]),
        Layer(LayerType.SEMI, parameters=[material_par])
    ]

    def __init__(self):
        super().__init__()

        self.wavelengths = []           # wavelengths (nm)
        self.design_wavelength = 600    # wavelength (nm)
        self.polarization = None        # Polarization.P, Polarization.S, or Polarization.TOTAL
        self.angles = []                # emission angles for SRI calculation (deg)

        self.material_file_reader = MaterialFileReader()

        self.plot_flag = True
        self.enable_2D = True

        self.illumination_direction = self.top_illumination

        self.R_0deg = np.array([])
        self.T_0deg = np.array([])
        self.A_0deg = np.array([])

        self.R_design = None
        self.T_design = None
        self.A_design = None

        self.R_2d = np.array([])
        self.T_2d = np.array([])
        self.A_2d = np.array([])

    def update_generic_parameters(self):

        self.polarization = Polarization(self.get_generic_parameter_value(self.polarization_par))
        self.wavelengths = start_stop_step_to_list(self.get_generic_parameter_value(self.wavelengths_par))
        self.design_wavelength = self.get_generic_parameter_value(self.design_wavelength_par)
        if self.design_wavelength < min(self.wavelengths) or self.design_wavelength > max(self.wavelengths):
            self.callback(title="Design wavelength out of range",
                          message="The given design wavelength is out of the given wavelength range.")
        self.angles = start_stop_step_to_list(self.get_generic_parameter_value(self.angles_par))
        self.enable_2D = self.get_generic_parameter_value(self.enable_2D_par)
        self.illumination_direction = self.get_generic_parameter_value(self.illumination_direction_par)

    def run(self):
        self.update_generic_parameters()

        if self.illumination_direction == self.bottom_illumination:
            self.layer_list = self.layer_list[::-1]

        nk_list = self._get_nk_list_from_layers()
        thickness_list = self._get_thickness_list_from_layers()
        is_coherent_list = self._get_is_coherent_list_from_layers()

        title_list = ["reflection " + self.polarization.value + "-pol",
                      "transmission " + self.polarization.value + "-pol",
                      "absorption " + self.polarization.value + "-pol"]

        tm = TransferMatrix(nk_list=nk_list,
                            thickness_list=thickness_list,
                            vacuum_wavelengths_list=self.wavelengths,
                            is_coherent_list=is_coherent_list)

        # RTA at 0deg
        R, T, A = self._get_RTA(tm=tm, angles=[0.], polarization=self.polarization)
        self.R_0deg, self.T_0deg, self.A_0deg = R.T[0], T.T[0], A.T[0]
        self.plot_1d(self.wavelengths, [self.R_0deg, self.T_0deg, self.A_0deg], title_list)

        # RTA at design wavelength and 0deg
        self.R_design, self.T_design, self.A_design = [np.interp(self.design_wavelength, self.wavelengths, data) for
                                                       data in [self.R_0deg, self.T_0deg, self.A_0deg]]

        # RTA 2d
        if self.enable_2D:
            self.R_2d, self.T_2d, self.A_2d = self._get_RTA(tm=tm, angles=self.angles, polarization=self.polarization)
            self.plot_2d(self.angles, list(self.wavelengths), [self.R_2d, self.T_2d, self.A_2d], title_list)

    def get_results_dict(self) -> dict:
        return {
            "R design": self.R_design,
            "T design": self.T_design,
            "A design": self.A_design,
        }

    def _get_RTA_at_design_wavelength(self) -> (float, float, float):
        """Extract RTA at 0deg and design wavelength. Interpolate RTA values."""
        return [np.interp(self.design_wavelength, self.wavelengths, data) for data in [self.R_0deg, self.T_0deg,
                                                                                       self.A_0deg]]

    def _get_thickness_list_from_layers(self) -> List[float]:
        """Get the layer thicknesses"""

        thickness_list = []
        for layer in self.layer_list:
            if layer.layer_type is LayerType.SEMI:
                thickness_list.append(np.inf)
            else:
                thickness_list.append(self.get_layer_parameter_value(self.thickness_par, layer=layer))
        return thickness_list

    def _get_is_coherent_list_from_layers(self) -> List[bool]:
        """Check which layers are coherent"""

        return [layer.layer_type == LayerType.COHERENT for layer in self.layer_list]

    def _get_nk_list_from_layers(self) -> List[List[float]]:
        """Read material files and interpolate nk-values to given wavelengths grid"""

        nk_list = []
        for layer in self.layer_list:
            material_file = self.get_layer_parameter_value(self.material_par, layer)
            material_path = os.path.join(self.material_par.path, material_file)

            [wl_list, n_list, k_list] = self.material_file_reader.read_optical_constants_from_fmf_file(material_path)

            # interpolate to given wavelength grid
            n_interpol = np.interp(x=self.wavelengths, xp=wl_list, fp=n_list)
            k_interpol = np.interp(x=self.wavelengths, xp=wl_list, fp=k_list)
            nk_complex = n_interpol + 1.j * k_interpol

            nk_list.append(nk_complex)

        return nk_list

    def _get_RTA(self, tm: TransferMatrix, angles: List[float], polarization: Polarization) -> (np.array, np.array,
                                                                                                np.array):

        def RTA_single(tm: TransferMatrix, polarization: Polarization):
            tm.set_polarization(polarization)
            tm.run_tm()
            R, T = np.array(tm.R), np.array(tm.T)
            A = np.ones(R.shape) - R - T
            return R, T, A

        tm.set_angles(angles=angles, layer_idx=0)  # top to bottom

        if polarization is Polarization.TOTAL:
            Rs, Ts, As = RTA_single(tm, Polarization.S)
            Rp, Tp, Ap = RTA_single(tm, Polarization.P)
            R = (Rs + Rp) / 2.
            T = (Ts + Tp) / 2.
            A = (As + Ap) / 2.
        else:
            R, T, A = RTA_single(tm, polarization)

        return R, T, A

    def plot_1d(self, wavelengths: List[float], intensity_list: List[np.array], title_list: List[str]):

        fig, ax = plt.subplots()
        ax.set_xlabel("wavelength (nm)")
        ax.set_ylabel("intensity (arb. units)")

        for idx, intensities in enumerate(intensity_list):
            ax.plot(wavelengths, intensities, label=title_list[idx])

        ax.legend()
        self.plot_fig(fig, "1D spectra (0 deg)")

    def plot_2d(self, x: list, y: list, data_2d_list: List[np.array], title_list: List[str]):

        for idx, data_2d in enumerate(data_2d_list):
            fig, ax = plt.subplots()

            # Note: pyplot imshow has its origin on the upper left side by default -> put origin='lower'
            im = ax.imshow(data_2d, extent=(min(x), max(x), min(y), max(y)), origin='lower', aspect='auto')
            ax.set_title(title_list[idx])
            ax.set_xlabel("angle of incidence (deg)")
            ax.set_ylabel("wavelength (nm)")
            cb = fig.colorbar(im, label=title_list[idx], ax=ax, use_gridspec=True)
            self.plot_fig(fig, title_list[idx])
