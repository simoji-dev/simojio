import scipy.integrate as integrate

import matplotlib
import matplotlib.pyplot as plt

from simojio.lib.abstract_modules import Calculator
from simojio.lib.Layer import Layer
from simojio.lib.enums.LayerType import LayerType
from simojio.lib.parameters import *
from simojio.lib.BasicFunctions import *
from simojio.modules.RTA.MaterialFileReader import MaterialFileReader
from simojio.modules.RTA.TransferMatrix import TransferMatrix
from simojio.modules.RTA.Polarization import Polarization
from simojio.modules.OledOptics.PlotMode import PlotMode


class OledOptics(Calculator):
    """
    Calculate the power dissipation and derived quantities from a given OLED stack.
    """

    # -- define layer parameters --

    # all layers
    material_par = FileFromPathParameter(name="material",
                                         path=os.path.join("modules", "shared_resources", "optical_constants"),
                                         extension_list=[".fmf"], description="Material data file")
    # coherent + emission layers
    thickness_par = FloatParameter(name="thickness", value=50., bounds=(0., np.inf), description="layer thickness")

    # emission layers
    nb_dipoles_par = FixFloatParameter(name="number of dipoles", value=1, bounds=(0, 100),
                                       description="Number of active layers that represent the emission profile")
    aniso_par = FloatParameter(name="anisotropy coefficient", value=1. / 3., bounds=(0., 1.),
                               description="anisotropy coefficient")
    gamma_par = FloatParameter(name="gamma", value=1., bounds=(0., 1.),
                               description="electrical efficiency (or weighting of sub-device)")
    eta_rad_par = FloatParameter(name="eta_rad", value=1., bounds=(0., 1.),
                                 description="radiative efficiency")
    pl_spectrum_par = FileFromPathParameter(name="PL spectrum",
                                            path=os.path.join("modules", "shared_resources", "PLSpectra"),
                                            extension_list=[".txt"],
                                            description="Photoluminescent emission spectrum")

    available_layers = [
        Layer(layer_type=LayerType.SEMI, parameters=[material_par]),
        Layer(layer_type=LayerType.SUBSTRATE, parameters=[material_par, thickness_par]),
        Layer(layer_type=LayerType.COHERENT, parameters=[material_par, thickness_par]),
        Layer(layer_type=LayerType.EMISSION, parameters=[material_par, thickness_par, nb_dipoles_par, aniso_par,
              gamma_par, eta_rad_par, pl_spectrum_par])
    ]

    # -- define generic parameters --

    polarization_par = MultiStringParameter(name="polarization", value=Polarization.TOTAL.value,
                                            description="Polarisation of emitted light",
                                            bounds=[Polarization.TOTAL.value, Polarization.P.value,
                                                    Polarization.S.value])
    wavelengths_par = StartStopStepParameter(name="wavelengths", start=400, stop=800, step=1,
                                             description="wavelength range (nm)")
    angles_par = StartStopStepParameter(name="angles", start=0, stop=90, step=1,
                                        description='emission angles for SRI calculation (deg)')
    wavevectors_par = StartStopStepParameter(name="wave-vectors", start=0., stop=3.5, step=0.002,
                                             description="normalized in plane wave vector (u = k_parallel/k)")
    plot_mode_par = MultiStringParameter(name="plot mode power dissipation", value=PlotMode.U.value,
                                         description="Plot normalized (u) or absolute (kappa) in-plane wave vector",
                                         bounds=[PlotMode.U.value, PlotMode.KAPPA.value])
    calc_powdiss_flag_par = BoolParameter(name="calculate power dissipation spectra", value=True,
                                          description="Define whether to plot the power dissipation spectrum")
    calc_sri_flag_par = BoolParameter(name="calculate SRI", value=False,
                                      description="Define whether to calculate the spectral radiant intensity (SRI)")
    calc_eqe_flag_par = BoolParameter(name="calculate EQE", value=False,
                                      description="Calculate the external quantum efficiency")
    calc_loss_channels_flag_par = BoolParameter(name="calculate optical loss channels", value=False,
                                                description="Calculate the optical loss channels")

    generic_parameters = [polarization_par, wavelengths_par, wavevectors_par, angles_par,
                          plot_mode_par, calc_powdiss_flag_par, calc_sri_flag_par, calc_eqe_flag_par,
                          calc_loss_channels_flag_par]

    def __init__(self):
        super().__init__()

        # layer (property) lists
        self.layer_thickness_list = []  # thickness value of each layer
        self.optical_constants_arr = []  # complex refractive index (n+ik) for each layer and wavelength
        self.emission_layer_index_list = []  # list of indices of all emission layers in the stack
        self.coherent_layers_index_arr = np.array([])  # list of indices of all coherent layers in the stack
        self.is_coherent_list = []      # list of bools indicating coherent layers

        self.is_substrate_in_stack = False

        # module parameters
        self.module_parameter_dict = {}
        self.wavelength_arr = np.array([])
        self.polarization_list = []  # ['p', 's'] or ['p'] or ['s']
        self.u_arr = np.array([])  # u = normalized in-plane wave vector (k_parallel/k)
        self.u_2d_arr = np.array([])  # u_arr extended in wavelength dimension (allow multiplication in K calc)
        self.angles = np.array([])  # emission angles for SRI calculation (rad)
        self.angles_deg = np.array([])  # given emission angles (deg)
        self.pl_spectra_dict = dict()

        # results
        self.K_eml = None  # power dissipation spectrum in EML
        self.K_sub = None  # power dissipation spectrum in substrate
        self.K_out = None  # power dissipation spectrum in top semi layer (outcoupled)

        # optical loss channels
        self.loss_channels_labels = ['outcoupled', 'substrate', 'waveguide', 'evanescent', 'absorption',
                                     'non-radiative', 'electrical']
        self.loss_channels_list = [None] * len(self.loss_channels_labels)
        self.eqe = None  # external quantum efficiency
        self.sri = None  # normalized spectral radiant intensity (SRI)

        # execution flags
        self.calc_powdiss_flag = True
        self.calc_sri_flag = True
        self.calc_eqe_flag = True
        self.calc_loss_channels_flag = True

        # plot flags
        self.plot_sri_flag = True
        self.plot_angle_spectrum_flag = True
        self.plot_forward_spectrum_flag = True
        self.plot_optical_constants_flag = True

        self.plot_mode_powdiss = None

        self.numerical_results_precision = 5  # number of digits of numerical results
        self.str_formatter = '{:.' + str(int(self.numerical_results_precision)) + 'f}'

        # -> get flag for calculation of power dissipation in dependence of u-grid (not if only sri is calculated)
        self.calc_u_mode = any((self.calc_powdiss_flag, self.calc_eqe_flag, self.calc_loss_channels_flag))

    def update_generic_parameters(self):

        # get execution flags
        self.calc_powdiss_flag = self.get_generic_parameter_value(self.calc_powdiss_flag_par)
        self.calc_sri_flag = self.get_generic_parameter_value(self.calc_sri_flag_par)
        self.calc_eqe_flag = self.get_generic_parameter_value(self.calc_eqe_flag_par)
        self.calc_loss_channels_flag = self.get_generic_parameter_value(self.calc_loss_channels_flag_par)

        self.calc_u_mode = any((self.calc_powdiss_flag, self.calc_eqe_flag, self.calc_loss_channels_flag))
        self.plot_mode_powdiss = PlotMode(self.get_generic_parameter_value(self.plot_mode_par))

        # get list of polarization values which need to be calculated (convert 'total' to ['s', 'p'])
        polarization_str = self.get_generic_parameter_value(self.polarization_par)
        if polarization_str == Polarization.TOTAL.value:
            self.polarization_list = [Polarization.P, Polarization.S]
        else:
            self.polarization_list = [Polarization(polarization_str)]

        # -- wavelength, angle, wavevector grid --
        self.wavelength_arr = np.array(start_stop_step_to_list(self.get_generic_parameter_value(self.wavelengths_par)))

        # get normalized in-plane wave vector + replace value one (pole in calculation)
        u_real = start_stop_step_to_list(self.get_generic_parameter_value(self.wavevectors_par))
        try:
            idx_one = list(u_real).index(1.0)
            if idx_one >= 0:
                u_real[idx_one] = 1. - 1.e-9
        except:
            pass
        self.u_arr = np.array(u_real) * (1. + 0.j)

        # get angles for sri calculation (transform to rad)
        if self.calc_sri_flag:
            self.angles_deg = np.array(start_stop_step_to_list(self.get_generic_parameter_value(self.angles_par)))
            self.angles = self.angles_deg * np.pi / 180.

    def update_layer_parameters(self):

        # layer type dependent properties
        layer_type_list = [layer.layer_type for layer in self.layer_list]
        self.emission_layer_index_list = [idx for idx in range(len(layer_type_list))
                                          if (layer_type_list[idx] is LayerType.EMISSION)]
        self.coherent_layers_index_arr = np.array([idx for idx in range(len(layer_type_list))
                                                   if (layer_type_list[idx] in [LayerType.COHERENT,
                                                                                     LayerType.EMISSION])])
        self.is_coherent_list = [(layer_type_list[idx] in [LayerType.COHERENT, LayerType.EMISSION])
                                 for idx in range(len(layer_type_list))]

        if len(self.emission_layer_index_list) == 0:
            raise ValueError("No emission layer defined!")

        # layer parameter dependent properties
        self.get_layer_thickness_arr()
        self.get_optical_constants_arr()
        self.get_normalized_pl_spectra_dict()

        # check substrate position (only allowed at position 1)
        substrate_positions = [idx for idx in range(len(layer_type_list))
                               if layer_type_list[idx] is LayerType.SUBSTRATE]

        if len(substrate_positions) > 0:
            self.is_substrate_in_stack = True

            if substrate_positions != [1]:
                raise ValueError("Substrates at positions " + str(substrate_positions) + " (only allowed as 2nd layer)")

    def run(self):

        self.update_generic_parameters()
        self.update_layer_parameters()

        self.K_eml = None  # power dissipation spectrum in EML
        self.K_sub = None  # power dissipation spectrum in substrate
        self.K_out = None  # power dissipation spectrum in top semi layer (outcoupled)

        self.loss_channels_list = [None] * len(self.loss_channels_labels)
        self.eqe = None  # external quantum efficiency
        self.sri = None  # normalized spectral radiant intensity (SRI)

        # extend u_list to kz-shape to allow multidimensional multiplication in calculation of K
        self.u_2d_arr = np.tensordot(np.ones(len(self.wavelength_arr)), self.u_arr, axes=0)

        # -- calculate power dissipation for each sub-device (single emission layer) --
        for emission_layer_idx in self.emission_layer_index_list:

            # -- get normalized PL spectrum --
            K_eml, sri, eqe, loss_channels_list = self.calc_Ks_and_efficiencies(emission_layer_idx)

            if self.calc_powdiss_flag:
                if self.K_eml is None:
                    self.K_eml = K_eml
                else:
                    self.K_eml += K_eml

            if self.calc_sri_flag:
                if self.sri is None:
                    self.sri = sri
                else:
                    self.sri += sri

            if self.calc_eqe_flag:
                norm_factor = len(self.emission_layer_index_list)
                if self.eqe is None:
                    self.eqe = eqe / norm_factor
                else:
                    self.eqe += eqe / norm_factor

            # -- add loss channels of different emission layers --

            if self.calc_loss_channels_flag:
                norm_factor = len(self.emission_layer_index_list)
                if None in self.loss_channels_list:
                    self.loss_channels_list = [0. for i in range(len(self.loss_channels_list))]
                    self.loss_channels_list = loss_channels_list / norm_factor
                else:
                    self.loss_channels_list += loss_channels_list / norm_factor

        # -- plot K --
        if self.calc_powdiss_flag:
            self.plot_K_eml()

        # -- plot SRI --
        if self.calc_sri_flag:
            norm_angle_idx, norm_wavelength_idx = self.normalize_sri()
            self.plot_sri()
            self.plot_angle_spectrum(norm_wavelength_idx)
            self.plot_forward_spectrum(norm_angle_idx)

        self.plot_optical_constants()

    def get_layer_thickness_arr(self):
        self.layer_thickness_list = []
        for layer in self.layer_list:
            if layer.layer_type is LayerType.SEMI:
                thickness = None
            else:
                thickness = self.get_layer_parameter_value(self.thickness_par, layer)
            self.layer_thickness_list.append(thickness)

    def get_optical_constants_arr(self):
        mat_file_reader = MaterialFileReader()

        # optical_constants_list = []
        for idx, layer in enumerate(self.layer_list):
            material_par = self.get_layer_parameter(self.material_par, layer)

            # read optical constants from file
            material_file = os.path.join(self.material_par.path, self.get_layer_parameter_value(material_par,
                                                                                                layer))
            [wl_list, n_list, k_list] = mat_file_reader.read_optical_constants_from_fmf_file(material_file)

            # interpolate to given wavelength grid
            n_interpol = np.interp(x=self.wavelength_arr, xp=wl_list, fp=n_list)
            k_interpol = np.interp(x=self.wavelength_arr, xp=wl_list, fp=k_list)
            nk_complex = n_interpol + 1.j * k_interpol

            # store complex refractive index
            try:
                self.optical_constants_arr[idx] = np.array(nk_complex)
            except:
                self.optical_constants_arr.append(np.array(nk_complex))

    def get_normalized_pl_spectra_dict(self):
        """Normalize each spectrum to the sum of the integration value of all single spectra"""

        any_update = False

        # read each spectrum and normalize it to its global maximum value
        for emission_layer_idx in self.emission_layer_index_list:
            layer = self.layer_list[emission_layer_idx]
            pl_par = self.get_layer_parameter(self.pl_spectrum_par, layer)

            pl_spectrum_file = self.get_layer_parameter_value(pl_par, layer)
            pl_spectrum = self._get_single_pl_spectrum_from_file(pl_spectrum_file)
            self.pl_spectra_dict.update({emission_layer_idx: pl_spectrum})
            any_update = True

        # normalize spectra by sum of integration values of all spectra (recalculate if any spectrum changes)
        if any_update:
            integration_value = 0.
            for key in self.pl_spectra_dict:
                if len(self.wavelength_arr) == 1:
                    integration_value += self.pl_spectra_dict[key][0]
                else:
                    integration_value += integrate.trapz(y=self.pl_spectra_dict[key], x=self.wavelength_arr)

            for key in self.pl_spectra_dict:
                self.pl_spectra_dict[key] /= integration_value

    def _get_nk_without_eml_absorption(self, emission_layer_idx: int) -> np.array:
        """Set absorption of emission layer to zero (k=0)"""
        nk_list = []
        for idx, nk in enumerate(self.optical_constants_arr):
            if idx == emission_layer_idx:
                nk_list.append(nk.real)
            else:
                nk_list.append(nk)
        return np.array(nk_list)

    def calc_kz_array(self, idx_emission_layer: int, nk_arr_wo_eml_absorption: np.array) -> np.array:
        """
        Three dimensional array of out-of-plane wave vector kz with indices [layer, wavelength, angle].
        Depends on which layer is emission layer because the wave vector u is defined within the emission layer.

        Optionally, the kz-array for the sri is calculated from the given angles

        :param idx_emission_layer: index of emission layer in stack
        """

        # -- calculate total vector length for each layer --
        k_length_arr = []
        for i in range(len(nk_arr_wo_eml_absorption)):
            k_length_i = 2. * np.pi * nk_arr_wo_eml_absorption[i] / self.wavelength_arr
            k_length_arr.append(k_length_i)
        k_length_arr = np.array(k_length_arr)

        # -- calculate kappa --
        # Note: kappa is the same in every layer (continuous at boundaries) -> calculate in emission layer
        kappa_arr = np.tensordot(k_length_arr[idx_emission_layer], self.u_arr, axes=0)

        # -- calculate kz(layer, lambda, theta) --
        k_length_3d = np.tensordot(k_length_arr, np.ones(len(self.u_arr)), axes=0)
        kappa_3d = np.tensordot(np.ones(len(k_length_arr)), kappa_arr, axes=0)
        kz_arr = np.sqrt(k_length_3d ** 2 - kappa_3d ** 2)

        # -- calculate kz for sri
        kz_arr_sri = None
        if self.calc_sri_flag:
            n_div = nk_arr_wo_eml_absorption[0] / nk_arr_wo_eml_absorption[idx_emission_layer]
            u_2d = np.tensordot(n_div, abs(np.sin(self.angles)), axes=0)  # u is always positive

            # -- calculate kappa --
            # kappa is the same in every layer (continous at boundaries) -> calculate in active layer
            k_length_2d = np.tensordot(k_length_arr[idx_emission_layer], np.ones(len(self.angles)), axes=0)
            kappa_arr = k_length_2d * u_2d

            # -- calculate kz(layer, lambda, theta) --
            k_length_3d = np.tensordot(k_length_arr, np.ones(len(self.angles)), axes=0)
            kappa_3d = np.tensordot(np.ones(len(k_length_arr)), kappa_arr, axes=0)
            kz_arr_sri = np.sqrt(k_length_3d ** 2 - kappa_3d ** 2)

        return kz_arr, kz_arr_sri

    def calc_Ks_and_efficiencies(self, emission_layer_idx: int) -> (np.array, np.array, float, list):
        """
        Calculate power dissipation in emission layer for a monochromatic device (single EML)
        Note: we assume that all dipoles within one EML have the same 'electrical efficiency'. The real generation
        profile is given in the dipole weight array.

        All optical loss channels are calculated

        :param emission_layer_idx:
        :return: [K_eml_h, K_eml_v, K_eml_tot_pol]
        """

        pl_spectrum = self.pl_spectra_dict[emission_layer_idx]

        emission_layer = self.layer_list[emission_layer_idx]
        anisotropy_coefficient = self.get_layer_parameter_value(self.aniso_par, emission_layer)
        gamma = self.get_layer_parameter_value(self.gamma_par, emission_layer)
        eta_rad = self.get_layer_parameter_value(self.eta_rad_par, emission_layer)

        dipole_positions, dipole_weight_arr = self.get_dipole_distribution(emission_layer_idx)
        nb_dipoles = len(dipole_positions)

        nk_arr = np.array([np.array(nk_layer) for nk_layer in self.optical_constants_arr])

        # u grid
        up_dict, down_dict, all_coherent_dict, sub_out_dict = self._get_effective_reflection_dicts(emission_layer_idx,
                                                                                                   dipole_positions,
                                                                                                   use_angles=False)

        # sri grid
        if self.calc_sri_flag:
            up_dict_sri, down_dict_sri, all_coherent_dict_sri, sub_out_dict_sri \
                = self._get_effective_reflection_dicts(emission_layer_idx, dipole_positions, use_angles=True)
            u_2d_arr_sri = np.tensordot(nk_arr[0] / nk_arr[emission_layer_idx], np.sin(self.angles), axes=0)

        # -- extend PL-spectrum to shape of K (enable multiplication) --
        pl_spectrum_2d = np.array([pl_spectrum for i in range(len(self.u_arr))]).T

        # -- calculate upper integration limit for U calculation --
        u_crit_out = nk_arr[0] / nk_arr[emission_layer_idx]

        # get u_crit_out 2d
        u_crit_out_2d = np.zeros(self.u_2d_arr.shape)
        for i in range(len(self.wavelength_arr)):
            for j in range(len(self.u_2d_arr[0])):
                if self.u_2d_arr[i][j] <= u_crit_out[i]:
                    u_crit_out_2d[i][j] = 1.

        u_crit_sub = None
        if self.is_substrate_in_stack:
            u_crit_sub = nk_arr[1] / nk_arr[emission_layer_idx]

        # take smallest n value of organic layers
        u_crit_wg = []
        if self.is_substrate_in_stack:
            nk_org = nk_arr[2:-1].T
        else:
            nk_org = nk_arr[1:-1].T
        for i in range(len(self.wavelength_arr)):
            idx_min = np.argmin([nk.real for nk in nk_org[i]])
            u_crit_wg.append(nk_arr[idx_min][i] / nk_arr[emission_layer_idx][i])
        u_crit_wg = np.array(u_crit_wg)

        # --  calculate power dissipation spectrum in EML --
        K_eml_list = []
        sri_list = []
        eqe_list = []
        loss_channel_list = []

        for i in range(nb_dipoles):

            # -- calculate spectra from given in-plane wave-vector --
            # Needs to be also be done if only SRI is needed because eta_rad_eff needs to be calculated
            K_eml_i, K_sub_i, K_out_i = self._calc_Ks_for_single_dipole(self.u_2d_arr, up_dict, down_dict,
                                                                        all_coherent_dict, sub_out_dict,
                                                                        anisotropy_coefficient, i)

            # -- calculate 'weighted' power dissipation spectra (multiplied with PL-spectrum, gamma, eta_rad, ...) --
            # Note: this is important for adding them correctly (F different for different dipole positions)

            # calculate total dissipated power F (integrate over u from 0 to u_max)
            F = self.calc_F(K_eml_i)

            # calculate effective radiative efficiency (eta_rad_eff) for each wavelength
            eta_rad_eff = self._eta_rad_effective_formula(F, eta_rad)   # np.array

            # calculate weighted power dissipation spectrum
            K_eml_weighted_i = self._calc_weighted_K_eml(K_eml=K_eml_i,
                                                         dipole_weight=dipole_weight_arr[i],
                                                         gamma=gamma,
                                                         eta_rad_eff=eta_rad_eff,
                                                         pl_spectrum_2d=pl_spectrum_2d)

            K_eml_list.append(K_eml_weighted_i)

            # -- calculate sri --
            if self.calc_sri_flag:
                K_eml_sri_i, K_sub_sri_i, K_out_sri_i = self._calc_Ks_for_single_dipole(u_2d_arr_sri,
                                                                                        up_dict_sri,
                                                                                        down_dict_sri,
                                                                                        all_coherent_dict_sri,
                                                                                        sub_out_dict_sri,
                                                                                        anisotropy_coefficient, i)

                sri_i = self.sri_formula(K_out=K_out_sri_i, nk_out=nk_arr[0], nk_eml=nk_arr[emission_layer_idx],
                                         pl_spectrum=pl_spectrum, angles=self.angles)

                eta_rad_eff_2d_sri = np.tensordot(eta_rad_eff, np.ones(len(self.angles)), axes=0)
                sri_list.append(sri_i * dipole_weight_arr[i] * gamma * eta_rad_eff_2d_sri)

            # -- calculate EQE --
            if self.calc_eqe_flag:
                eqe = self._calc_eqe(K_out=K_out_i, u_crit_out=u_crit_out, F=F, eta_rad_eff=eta_rad_eff,
                                     dipole_weight=dipole_weight_arr[i], gamma=gamma, pl_spectrum=pl_spectrum)
                eqe_list.append(eqe)

            # -- calculate loss channels --
            if self.calc_loss_channels_flag:
                loss_channels_i = self._calc_loss_channels(K_eml=K_eml_i,
                                                           K_sub=K_sub_i,
                                                           K_out=K_out_i,
                                                           F=F,
                                                           u_crit_out=u_crit_out,
                                                           u_crit_sub=u_crit_sub,
                                                           u_crit_wg=u_crit_wg,
                                                           eta_rad_eff=eta_rad_eff,
                                                           dipole_weight=dipole_weight_arr[i],
                                                           gamma=gamma,
                                                           pl_spectrum=pl_spectrum)

                loss_channel_list.append(loss_channels_i)

        # -- sum up contributions of multiple active layers --
        K_eml = None
        if self.calc_powdiss_flag:
            K_eml = np.sum(K_eml_list, axis=0)

        sri = None
        if self.calc_sri_flag:
            sri = np.sum(sri_list, axis=0)

        eqe = None
        if self.calc_eqe_flag:
            eqe = np.sum(eqe_list) / nb_dipoles

        loss_channels = None
        if self.calc_loss_channels_flag:
            loss_channels = np.sum(loss_channel_list, axis=0) / nb_dipoles

        return K_eml, sri, eqe, loss_channels

    def _get_effective_reflection_dicts(self, emission_layer_idx: int, dipole_positions: np.array, use_angles=False):
        """
        Calculate reflection and transmission arrays for all polarizations. Initialize TransferMatrix instance with all
        layers of the stack and use the 'run_tm_sub_stack()' method to get the effective reflection/transmission of the
        sub-stacks (e.g. layers above and below the emitting dipole).
        """

        up_dict = {}            # {'polarization': [a_up, r_up, R_up, T_up]}
        down_dict = {}          # {'polarization': [a_down, r_down, R_down, T_down]}
        all_coherent_dict = {}  # {'polarization': [rc, Rc, Tc]}
        sub_out_dict = {}       # {'polarization': [rso, Rso, Tso]}

        nk_list = self._get_nk_without_eml_absorption(emission_layer_idx)

        tm_obj = TransferMatrix(nk_list=list(nk_list), thickness_list=self.layer_thickness_list,
                                vacuum_wavelengths_list=list(self.wavelength_arr),
                                is_coherent_list=self.is_coherent_list)

        # -- get sub-stack index lists --
        all_indices = np.arange(len(nk_list))

        # all coherent layers above the emission layer (reverse direction: as seen from the emission layer)
        if self.is_substrate_in_stack:
            up_indices = all_indices[1:emission_layer_idx + 1][::-1]
        else:
            up_indices = all_indices[:emission_layer_idx + 1][::-1]

        # all layers below the emission layer
        down_indices = all_indices[emission_layer_idx:]

        # set propagation directions (angles or in-plane wave-vectors)
        if use_angles:
            tm_obj.set_angles(list(self.angles_deg), layer_idx=0)  # emission angles in top-semi layer
        else:
            tm_obj.set_normalized_in_plane_wave_vectors(list(self.u_arr), layer_idx=emission_layer_idx)

        for polarization in self.polarization_list:
            tm_obj.set_polarization(polarization)

            a_up_list = []
            T_up_list = []
            a_down_list = []
            T_down_list = []

            # coherent layers above ('up') and below ('down') dipole
            for dipole_position in dipole_positions:

                # coherent layers above ('up') dipole
                tm_obj.run_tm_sub_stack(layer_indices=up_indices, distance_to_first_interface=dipole_position)
                a_up_list.append(tm_obj.r)
                T_up_list.append(tm_obj.T)

                # coherent layers below ('down') dipole
                distance_first_down_interface = self.layer_thickness_list[emission_layer_idx] - dipole_position
                tm_obj.run_tm_sub_stack(layer_indices=down_indices,
                                        distance_to_first_interface=distance_first_down_interface)
                a_down_list.append(tm_obj.r)
                T_down_list.append(tm_obj.T)

            # store calculated arrays in dictionaries
            up_dict.update({polarization: [a_up_list, T_up_list]})
            down_dict.update({polarization: [a_down_list, T_down_list]})

            # include additional reflections in incoherent substrate if present
            if self.is_substrate_in_stack:

                # all coherent layers below the glass substrate
                tm_obj.run_tm_sub_stack(layer_indices=all_indices[1:], distance_to_first_interface=0.)
                all_coherent_dict.update({polarization: [tm_obj.R, tm_obj.T]})

                # substrate - out interface (out = top semi)
                tm_obj.run_tm_sub_stack(layer_indices=[1, 0], distance_to_first_interface=0.)
                sub_out_dict.update({polarization: [tm_obj.R, tm_obj.T]})

        return up_dict, down_dict, all_coherent_dict, sub_out_dict

    def _calc_Ks_for_single_dipole(self, u_2d_arr: np.array, up_dict: dict, down_dict: dict,
                                   all_coherent_dict: dict, sub_out_dict: dict, anisotropy_coefficient: float,
                                   dipole_index: int) -> (np.array, np.array, np.array):
        """Calculate Ks for each given polarization and add them up"""

        angle_wavelength_shape = up_dict[self.polarization_list[0]][0][0].shape

        K_eml_i = np.zeros(angle_wavelength_shape) * (1. + 0.j)
        K_sub_i = np.zeros(angle_wavelength_shape) * (1. + 0.j)
        K_out_i = np.zeros(angle_wavelength_shape) * (1. + 0.j)

        for polarization in self.polarization_list:
            # calculate K_eml
            K_eml_h_i, K_eml_v_i = self.K_eml_formula(polarization=polarization,
                                                      a_up=up_dict[polarization][0][dipole_index],
                                                      a_down=down_dict[polarization][0][dipole_index],
                                                      u_2d_arr=u_2d_arr)
            K_eml_i += self._sum_horizontal_and_vertical_contributions(K_eml_h_i, K_eml_v_i, anisotropy_coefficient)

            # calculate K_sub
            K_sub_h_i, K_sub_v_i = self.K_sub_formula(polarization=polarization,
                                                      a_up=up_dict[polarization][0][dipole_index],
                                                      a_down=down_dict[polarization][0][dipole_index],
                                                      T_up=up_dict[polarization][1][dipole_index],
                                                      u_2d_arr=u_2d_arr)

            K_sub_i += self._sum_horizontal_and_vertical_contributions(K_sub_h_i, K_sub_v_i, anisotropy_coefficient)

            # calculate K_out
            if self.is_substrate_in_stack:
                K_out_h_i = self.K_out_formula(K_sub=K_sub_h_i,
                                               Tso=sub_out_dict[polarization][1],
                                               Rso=sub_out_dict[polarization][0],
                                               Rc=all_coherent_dict[polarization][0])

                K_out_v_i = self.K_out_formula(K_sub=K_sub_v_i,
                                               Tso=sub_out_dict[polarization][1],
                                               Rso=sub_out_dict[polarization][0],
                                               Rc=all_coherent_dict[polarization][0])

                K_out_i += self._sum_horizontal_and_vertical_contributions(K_out_h_i, K_out_v_i,
                                                                           anisotropy_coefficient)
            else:
                K_out_i = K_sub_i
                K_sub_i = np.zeros(angle_wavelength_shape) * (1. + 0.j)

        return K_eml_i, K_sub_i, K_out_i

    def _calc_weighted_K_eml(self, K_eml: np.array, dipole_weight: float, gamma: float, eta_rad_eff: np.array,
                             pl_spectrum_2d: np.array) -> np.array:

        # extend arrays to angle dimension (to fit shape of K and allow for multiplication)
        eta_rad_eff_2d = np.array([eta_rad_eff for i in range(len(self.u_arr))]).T

        # calculate weigthed power dissipation
        K_eml_weighted = K_eml * dipole_weight * gamma * eta_rad_eff_2d * pl_spectrum_2d

        return K_eml_weighted

    def _calc_eqe(self, K_out: np.array, u_crit_out: np.array, F: np.array, eta_rad_eff: np.array, dipole_weight: float,
                  gamma: float, pl_spectrum: np.array):
        """Calculate external quantum efficiency (EQE)"""

        U_out = self.calc_U(K_out, u_crit_out)
        integrand_out = dipole_weight * gamma * eta_rad_eff * pl_spectrum * U_out / F
        eqe = integrate.trapz(y=integrand_out, x=self.wavelength_arr)

        return eqe

    def _calc_loss_channels(self, K_eml: np.array, K_sub: np.array, K_out: np.array, F: np.array, u_crit_out: np.array,
                            u_crit_sub: np.array, u_crit_wg: np.array, eta_rad_eff: np.array, dipole_weight: float,
                            gamma: float, pl_spectrum: np.array) -> list:

        # -- calculate Us (angle integrated power dissipation spectra) --
        U_out = self.calc_U(K_out, u_crit_out)
        U_sub = None
        if self.is_substrate_in_stack:
            U_sub = self.calc_U(K_sub, u_crit_sub)
        U_wg = self.calc_U(K_eml, u_crit_wg)

        if self.is_substrate_in_stack:
            U_sub_wo_absorption = self.calc_U(K_eml, u_crit_sub)
        U_out_wo_absorption = self.calc_U(K_eml, u_crit_out)

        # -- calculate loss channel efficiencies --

        # outcoupled
        integrand_out = dipole_weight * gamma * eta_rad_eff * pl_spectrum * U_out / F

        # substrate
        if self.is_substrate_in_stack:
            integrand_sub_added = dipole_weight * gamma * eta_rad_eff * pl_spectrum * U_sub / F
        else:
            integrand_sub_added = np.zeros(integrand_out.shape)

        # waveguide
        integrand_wg_added = dipole_weight * gamma * eta_rad_eff * pl_spectrum * (
                    U_wg - (U_out_wo_absorption - U_out)) / F

        # evanescent
        integrand_evan_added = dipole_weight * gamma * eta_rad_eff * pl_spectrum

        # absorption
        if self.is_substrate_in_stack:
            integrand_absorption_added = dipole_weight * gamma * eta_rad_eff * pl_spectrum * U_sub_wo_absorption / F
        else:
            integrand_absorption_added = dipole_weight * gamma * eta_rad_eff * pl_spectrum * U_out_wo_absorption / F

        # non-radiative
        integrand_non_rad_added = dipole_weight * gamma * pl_spectrum

        # electrical
        integrand_electrical_added = dipole_weight * pl_spectrum

        # get single channel integrands from added integrands
        integrand_sub = integrand_sub_added - integrand_out
        integrand_wg = integrand_wg_added - integrand_sub_added
        integrand_evan = integrand_evan_added - (integrand_absorption_added - integrand_sub_added) - integrand_wg_added
        integrand_absorption = integrand_absorption_added - integrand_sub_added
        integrand_non_rad = integrand_non_rad_added - integrand_evan_added
        integrand_electrical = integrand_electrical_added - integrand_non_rad_added

        integrand_list = [integrand_out, integrand_sub, integrand_wg,
                          integrand_evan, integrand_absorption,
                          integrand_non_rad,
                          integrand_electrical]

        loss_channel_list = []
        for integrand in integrand_list:
            loss_channel_list.append(integrate.trapz(y=integrand * 100., x=self.wavelength_arr))

        return loss_channel_list

    def calc_a_arrays(self, kz_arr: np.array, r_up: np.array, r_down: np.array, dipole_position_arr: np.array,
                      emission_layer_idx: int) -> (np.array, np.array):
        """Calculate effective reflection for list of dipole positions"""

        a_up_arr = self.calc_a_formula(r_up, kz_arr[emission_layer_idx], dipole_position_arr)
        a_down_arr = self.calc_a_formula(r_down, kz_arr[emission_layer_idx], dipole_position_arr[::-1])

        return a_up_arr, a_down_arr

    def calc_U(self, K: np.array, u_crit: np.array) -> np.array:
        """calculate U(lambda): 2*integrate(K*u)du up to critical u_crit"""

        U = []
        integrand = np.array((2. * self.u_2d_arr * K).real)
        for idx in range(len(self.wavelength_arr)):
            idx_integration_limit, val = find_nearest(self.u_arr.real, u_crit[idx].real)
            U.append(integrate.trapz(y=integrand[idx][:(idx_integration_limit + 1)],
                                     x=self.u_arr.real[:(idx_integration_limit + 1)]))
        return np.array(U)

    def calc_F(self, K_eml: np.array) -> np.array:
        """calculate F(lambda): 2*integrate(K*u)du over whole given u_arr"""
        F = []
        integrand = np.array((2. * self.u_2d_arr * K_eml).real)
        for idx in range(len(self.wavelength_arr)):
            F.append(integrate.trapz(y=integrand[idx], x=self.u_arr.real))
        return np.array(F)

    def get_up_down_subdevice_indices(self, emission_layer_idx: int) -> (np.array, np.array):

        # get indices of up-substack (start from emission layer until first non-coherent layer)
        up_coh_idx_list = []
        idx = emission_layer_idx
        while True:
            up_coh_idx_list.append(idx)
            layer_type = self.layer_parameters_list[idx].layer_type

            if not layer_type in [LayerType.COHERENT, LayerType.EMISSION]:
                break
            idx -= 1

        # get indices of down-substack (start from emission layer until first non-coherent layer)
        down_coh_idx_list = []
        idx = emission_layer_idx
        while True:
            down_coh_idx_list.append(idx)
            layer_type = self.layer_parameters_list[idx].layer_type
            if not layer_type in [LayerType.COHERENT, LayerType.EMISSION]:
                break
            idx += 1

        return np.array(up_coh_idx_list), np.array(down_coh_idx_list)

    def calc_a_formula(self, r, kz, dz):
        """Calculate effective reflection at active layer positions given by dz (distance to first interface)."""
        a = []
        for i in range(len(dz)):
            a_i = r * np.exp(2. * kz * dz[i] * 1.j)
            a.append(a_i)
        return np.array(a)

    def get_dipole_distribution(self, emission_layer_idx) -> (np.array, np.array):
        """
        Get distance of each dipole with respect to the top interface of the layer and the weight of each dipole.
        :return dipole_positions, dipole_weights
        """

        layer_thickness = self.layer_thickness_list[emission_layer_idx]
        emission_layer = self.layer_list[emission_layer_idx]

        nb_dipoles = int(self.get_layer_parameter_value(self.nb_dipoles_par, emission_layer))

        if nb_dipoles == 1:
            dipole_position_arr = np.array([layer_thickness / 2.])
        else:
            dipole_position_arr = np.arange(nb_dipoles) * layer_thickness / (nb_dipoles - 1)

        # dipole weigths Todo: include emission profiles
        dipole_weights = np.array([1.] * nb_dipoles)

        return dipole_position_arr, dipole_weights

    def _get_single_pl_spectrum_from_file(self, pl_spectrum_file: str) -> np.array:
        """Read PL spectrum (.txt), normalize to maximum value, and interpolate to given wavelength grid"""
        pl_spectrum_data = np.loadtxt(os.path.join(self.pl_spectrum_par.path, pl_spectrum_file))
        pl_spectrum_fct = InterpolatedUnivariateSpline(pl_spectrum_data.T[0], pl_spectrum_data.T[1], k=1, ext=3)
        return pl_spectrum_fct(self.wavelength_arr)

    def K_eml_formula(self, polarization: str, a_up: np.array, a_down: np.array, u_2d_arr: np.array) \
            -> (np.array, np.array):
        """
        Radiated power density in EML for given 'u' (self driven dipole).
        [Furno]: A1, A2, A3
        [Diss. Fuchs]: additional /(self.k_length_e**2) but makes just constant offset

        :return K_eml_h, K_eml_v
        """
        if polarization == 'p':
            K_eml_h = 3. / 8. * (np.sqrt(1. - u_2d_arr ** 2)
                                 * (1. - a_up) * (1. - a_down) / (1. - a_up * a_down)).real  # (A2)
            K_eml_v = 3. / 4. * (u_2d_arr ** 2 / np.sqrt(1. - u_2d_arr ** 2)
                                 * (1. + a_up) * (1. + a_down) / (1. - a_up * a_down)).real  # (A1)
        elif polarization == 's':
            K_eml_h = 3. / 8. * (1. / np.sqrt(1. - u_2d_arr ** 2)
                                 * (1. + a_up) * (1. + a_down) / (1. - a_up * a_down)).real  # (A3)
            K_eml_v = np.zeros(np.array(K_eml_h).shape)  # no TE contribution from vertical dipoles -> set to zero
        else:
            raise ValueError('Error: wrong polarization type:', polarization, '. Use either s or p.')

        return K_eml_h, K_eml_v

    def K_sub_formula(self, polarization: str, a_up, a_down, T_up, u_2d_arr: np.array) -> (np.array, np.array):
        """Power dissipated into substrate [Furno, 2012] (A8), (A9), (A10)"""

        if polarization == 'p':
            K_sub_v = 3. / 8. * u_2d_arr ** 2 / np.sqrt(1. - u_2d_arr ** 2) \
                      * (abs(1. + a_down) / abs(1. - a_down * a_up)) ** 2 * T_up
            K_sub_h = 3. / 16. * np.sqrt(1. - u_2d_arr ** 2) * (abs(1. - a_down) / abs(1. - a_down * a_up)) ** 2 * T_up
        elif polarization == 's':
            K_sub_h = 3. / 16. / np.sqrt(1. - u_2d_arr ** 2) \
                      * (abs(1. + a_down) / abs(1. - a_down * a_up)) ** 2 * T_up
            K_sub_v = np.zeros(K_sub_h.shape)  # no TE contribution from vertical dipoles -> set to zero
        else:
            raise ValueError('Wrong polarization type:' + polarization + '. Use either s or p.')

        return K_sub_h, K_sub_v

    def K_out_formula(self, K_sub: np.array, Tso: np.array, Rso: np.array, Rc: np.array) -> np.array:
        return K_sub * Tso / (1. - Rso * Rc)

    def _sum_horizontal_and_vertical_contributions(self, K_horizontal: np.array, K_vertical: np.array,
                                                   anisotropy_coefficient: float) -> np.array:
        return anisotropy_coefficient * K_vertical + (1. - anisotropy_coefficient) * K_horizontal

    def _eta_rad_effective_formula(self, F: np.array, eta_rad: np.array):
        return (F * eta_rad) / (1 - eta_rad + F * eta_rad)

    def sri_formula(self, K_out: np.array, nk_out: np.array, nk_eml: np.array, pl_spectrum: np.array,
                    angles: np.array) -> np.array:
        """[Furno 2012, (A18)]"""
        n_div = (nk_out / nk_eml) ** 2
        costheta2d = np.tensordot(pl_spectrum * n_div, np.cos(angles), axes=0)
        P_out = K_out * costheta2d / np.pi
        return P_out.real

    def plot_K_eml(self):
        """
        Plot normalized power dissipation K*u in dependence of in-plane-wave vector (kappa) and energies (2d plot).
        As plot option, the in-plane-wavevector can be chosen to be normalized (u=kappa/k_length).

        Additionally, 1D lines are drawn that separate the regions where power is dissipated to (out, substrate,
        evanescent).
        """

        # -- calculate power dissipation K * u --
        Ku = (self.K_eml * self.u_2d_arr).real
        Ku = np.ma.masked_where(Ku <= 0, Ku)  # avoid error message for log(neg. values)

        # -- calculate energy array from wavelength array --
        # E[eV] = hc/(e*wl[nm]*1e-9)
        h = 6.62607004e-34
        c = 299792458.
        e = 1.602e-19
        pre_fact = h * c / (e * 1.e-9)
        energies = pre_fact / self.wavelength_arr
        energies_2d = np.array([energies] * len(self.u_arr)).T

        # -- get nk-values in order to calculate the 1D-lines and (optionally) kappa --

        # emission layer (eml)
        nk_eml = self.optical_constants_arr[self.emission_layer_index_list[0]].real
        if len(self.emission_layer_index_list) > 1:
            print('Note: For plotting, only the optical constants of the first emission layer ('
                  + self.layer_parameters_list[self.emission_layer_index_list[0]].name + ') are taken')

        # substrate (sub)
        nk_sub = None
        if self.is_substrate_in_stack:
            nk_sub = self.optical_constants_arr[1].real

        # top semi layer (out)
        nk_out = self.optical_constants_arr[0].real

        # -- get in-plane wave-vectors, plot-xaxis-label, and 1D-lines in dependence of plot mode --
        if self.plot_mode_powdiss == PlotMode.KAPPA:
            # Note: Here we need to provide the xy-grid in 2d since it is deformed
            x_label = "in-plane wave vector kappa (1/um)"
            energies_2d = np.array([energies] * len(self.u_arr)).T
            fact = 2. * np.pi * energies / 1.242
            kappa_2d = (self.u_2d_arr.real.T * fact * nk_eml).T
            wavevectors_2d = kappa_2d

            evan_line = nk_eml * fact
            out_line = nk_out * fact
            if self.is_substrate_in_stack:
                sub_line = nk_sub * fact
        else:
            x_label = 'normalized in-plane wave vector u'
            wavevectors_2d = self.u_2d_arr.real

            evan_line = np.ones(len(energies))
            out_line = nk_out / nk_eml
            if self.is_substrate_in_stack:
                sub_line = nk_sub / nk_eml

        # -- define plot labels --
        y_label = 'energy (eV)'
        cb_label = 'normalized power dissipation K*u'

        # -- do plotting --
        def get_heatmap_levels(z):
            # calculate levels for heatmap plot from 2d data minimum and maximum
            steps_per_decade = 10
            z[np.isnan(z)] = 0
            z[z <= 0] = 0
            if z.min() > 0.:
                lev_exp = np.arange(np.floor(np.log10(z.min()) - 1),
                                    np.ceil(np.log10(z.max()) + 1), (1. / steps_per_decade))
            else:
                lev_exp = np.arange(-8, np.ceil(np.log10(z.max()) + 1), (1. / steps_per_decade))
            levels = np.power(10, lev_exp)
            return levels

        # mask values < 0 for Ku
        Ku = np.ma.masked_where(Ku <= 0, Ku)

        fig, ax = plt.subplots()
        ax.set_xlabel(x_label)
        ax.set_ylabel(y_label)
        levels = get_heatmap_levels(Ku)
        im = ax.contourf(wavevectors_2d, energies_2d, Ku, levels, norm=matplotlib.colors.LogNorm(), cmap=plt.cm.jet)

        cb = fig.colorbar(im, ax=ax, format = "%.1e")
        cb.set_label(cb_label)

        # -- plot lines (separate outcoupled-, substrate- and evanescent part) --
        if self.is_substrate_in_stack:
            data_1d = [out_line, sub_line, evan_line]
            labels = ["out", "sub", "evan"]
            color_list = ["red", "blue", "black"]
        else:
            data_1d = [out_line, evan_line]
            labels = ["out", "evan"]
            color_list = ["red", "black"]

        for j in range(len(data_1d)):
            ax.plot(data_1d[j], energies, color=color_list[j], label=labels[j])
        ax.legend()

        self.plot_fig(fig, "power_dissipation")

        # save data (contourf cannot be saved automtically by simojio)
        file_path = os.path.join(self.get_save_dir(), "power_dissipation_plotdata.json")

        save_dict = {
            "title": "",
            "x-label": x_label,
            "y-label": y_label,
            "z-label": cb_label,
            "data-set-labels": "power_dissipation",
            "plot-data": [wavevectors_2d.tolist(), energies_2d.tolist(), Ku.tolist()]
        }

        json_file = open(file_path, 'w', encoding='utf-8')
        json.dump(save_dict, json_file, sort_keys=True, indent=4)
        json_file.close()

    def normalize_sri(self) -> (int, int):
        """
        Normalize 2d angle-resolved emission spectrum to maximum intensity of spectrum closest to forward emission.
        :return angle_index, wavelength_index used for normalization
        """
        spectrum, angle_index = self.get_forward_spectrum_and_index()
        wavelength_index = int(np.argmax(spectrum))
        self.sri = self.sri / spectrum[wavelength_index]
        return angle_index, wavelength_index

    def get_forward_spectrum_and_index(self) -> (np.array, int):
        """Get emission spectrum at angle closest to zero degree."""
        idx, value = find_nearest(list(self.angles), 0.)
        return self.sri.T[idx], idx

    def plot_sri(self):

        if self.plot_sri_flag:
            fig, ax = plt.subplots()
            im = ax.imshow(self.sri[::-1], extent=xy_to_extent(list(self.angles * 180. / np.pi),
                                                               list(self.wavelength_arr)), aspect='auto')
            ax.set_xlabel("angle (deg)")
            ax.set_ylabel("wavelength (nm)")

            cb = fig.colorbar(im, label="spectral radiant intensity (SRI)", ax=ax, use_gridspec=True)
            self.plot_fig(fig, "simulated SRI")

    def plot_angle_spectrum(self, idx_max_wl: int):

        if self.plot_angle_spectrum_flag:
            fig, ax = plt.subplots()
            # idx_max_wl = np.argmax(self.get_forward_spectrum())
            angle_spectrum = self.sri[idx_max_wl]
            ax.plot(self.angles * 180. / np.pi, angle_spectrum,
                    label="intensity at " + str(self.wavelength_arr[idx_max_wl]) + "nm")
            ax.legend()
            ax.set_xlabel("angle (deg)")
            ax.set_ylabel("intensity (arb. units)")

            self.plot_fig(fig, "angle-resolved emission at maximum wavelength")

    def plot_forward_spectrum(self, forward_angle_index: int):

        if self.plot_angle_spectrum_flag:
            fig, ax = plt.subplots()
            forward_spectrum = self.sri.T[forward_angle_index]
            ax.plot(self.wavelength_arr, forward_spectrum,
                    label="intensity at " + str(self.angles[forward_angle_index] * 180 / np.pi) + "deg")
            ax.legend()
            ax.set_xlabel("wavelength (nm)")
            ax.set_ylabel("intensity (arb. units)")

            self.plot_fig(fig, "forward emission spectrum")

    def plot_optical_constants(self):
        if self.plot_optical_constants_flag:
            fig, (ax1, ax2) = plt.subplots(nrows=2, sharex='col')

            plotted_materials = []
            material_names = [self.get_layer_parameter_value(self.material_par, layer) for layer in self.layer_list]

            for idx, name in enumerate(material_names):
                if name not in plotted_materials:
                    plotted_materials.append(name)

                    complex_nk = self.optical_constants_arr[idx]
                    ax1.plot(self.wavelength_arr, complex_nk.real, '.-', label=name)
                    ax2.plot(self.wavelength_arr, complex_nk.imag, '.-')

            ax1.set_ylabel("refractive index n")
            ax1.legend()
            ax2.set_xlabel("wavelength (nm)")
            ax2.set_ylabel("extinction coefficient k")

            self.plot_fig(fig, title="optical constants")

    def get_results_dict(self) -> dict:
        """Return the calculated numerical values as dict"""

        results_dict = {}

        if self.calc_eqe_flag:
            eqe = self.eqe
            if not self.eqe is None:
                eqe *= 100.
                results_dict.update({"EQE [%]": eqe})
            else:
                results_dict.update({"EQE [%]": eqe})

        if self.calc_loss_channels_flag:
            for idx, label in enumerate(self.loss_channels_labels):
                loss_channel_value = self.loss_channels_list[idx]
                if self.loss_channels_list[idx] is not None:
                    results_dict.update({self.loss_channels_labels[idx] + ' [%]': loss_channel_value})
                else:
                    results_dict.update({self.loss_channels_labels[idx] + ' [%]': loss_channel_value})

        return results_dict
