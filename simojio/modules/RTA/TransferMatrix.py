import numpy as np
from typing import List, Optional, Union

from simojio.modules.RTA.Polarization import Polarization


class TransferMatrix:
    """
    Calculate transfer matrix and resulting quantities (R, T, Psi, Delta) of layer stack with coherent and incoherent
    layers.

    The propagation directions can be defined in two different ways:
    (1) propagation angles in one layer
    (2) normalized in-plane wave-vector in one layer
    """

    def __init__(self, nk_list: List[List[Union[float, complex]]], thickness_list: List[float],
                 vacuum_wavelengths_list: List[float], is_coherent_list: Optional[List[bool]]=None):
        """
        Initialize simulation input.
        Note: units of d_list and wavelengths must be the same.

        :param nk_list: complex refractive index n+ik (layer, wavelength)
        :param thickness_list: thickness of each layer, first and last layer thickness is ignored
        :param vacuum_wavelengths_list: needs to fit to nk-list for each layer
        :param is_coherent_list: [bool] -> True for coherent layers, False for incoherent layers
        """

        self.polarization = None

        self.nk_list = nk_list
        self.thickness_list = thickness_list                    # layer thickness list (layer)
        self.vacuum_wavelengths_list = vacuum_wavelengths_list  # vacuum wavelengths (layer)
        self.is_coherent_list = is_coherent_list
        if is_coherent_list is None:
            self.is_coherent_list = [True] * len(self.thickness_list)

        # calculate k-length for each layer and n (k_length = 2 * pi * n / lambda)
        self.k_length_arr = np.array([2 * np.pi * np.array(nk) / self.vacuum_wavelengths_list for nk in self.nk_list])

        self.kzs_3d = None                  # out-of-plane wave-vector kz (layer, wavelength, angle)
        self.nks_3d = None                  # complex refractive index (layer, wavelength, angle)

        self.positions = None

        self.P_mat_save = None  # initialize lists for saving P and J in case of position-resolved calculations
        self.J_mat_save = None
        self.T_mat_save = None

        # results
        self.r = None
        self.R = None
        self.t = None
        self.T = None

        self.psi = None
        self.delta = None

    def set_polarization(self, polarization: Polarization):
        """
        Set polarization of incident light.
        :param polarization: Polarization.S or Polarization.P
        :return:
        """

        if polarization is Polarization.TOTAL:
            raise ValueError("Total polarization (unpolarized light) not implemented.")

        self.polarization = polarization

    def set_angles(self, angles: List[float], layer_idx: int):
        """
        Calculate out-of-plane wave-vectors (kz-values for each wavelength and propagation angle in each layer) from
        propagation angles in one layer. Additionally the nk-array is reshaped to 3d in order to allow multidimensional
        multiplication.

        Note:
        Angles are different in each layer! Calculate kappa (in-plane wave-vector) in the given layer which is
        constant for all layers. Together with the known k_length the kz follows for all layers.

        Given layer:
        kappa = sin(angle) * k_length[layer_idx]

        All layers:
        kz[idx] = np.sqrt(k_length[idx] ** 2 - kappa ** 2)

        :param angles: (deg)
        :param layer_idx
        """

        # reshape nk-array to given angle dimension
        self.nks_3d = np.tensordot(np.array(self.nk_list), np.ones(len(angles)), axes=0)

        angles_rad = np.array(angles) * np.pi / 180.
        kappa = np.tensordot(self.k_length_arr[layer_idx], np.sin(angles_rad), axes=0)
        k_length_arr_3d = np.tensordot(self.k_length_arr, np.ones(len(angles)), axes=0)

        self.kzs_3d = np.array([np.sqrt(k_length_arr_3d[idx] ** 2 - kappa **2)
                                for idx in range(len(self.k_length_arr))])

    def set_normalized_in_plane_wave_vectors(self, normalized_in_plane_wave_vectors: List[float], layer_idx: int):
        """
        Calculate out-of-plane wave-vectors (kz-values for each wavelength and propagation angle in each layer) from
        normalized in-plane wave-vectors (u = kappa / k_length) in one layer. Additionally the nk-array is reshaped to
        3d in order to allow multidimensional multiplication.

        Note:
        Angles are different in each layer! Calculate kappa (in-plane wave-vector) in the given layer which is
        constant for all layers. Together with the known k_length the kz follows for all layers.

        Given layer:
        kappa = u * k_length

        All layers:
        kz[idx] = np.sqrt(k_length[idx] ** 2 - kappa ** 2)

        :param normalized_in_plane_wave_vectors:
        :param layer_idx:
        :return:
        """

        u = np.array(normalized_in_plane_wave_vectors)

        # reshape nk-array to given in-plane wave-vactor dimension
        self.nks_3d = np.tensordot(np.array(self.nk_list), np.ones(len(u)), axes=0)

        kappa = np.tensordot(self.k_length_arr[layer_idx], u, axes=0)
        k_length_arr_3d = np.tensordot(self.k_length_arr, np.ones(len(u)), axes=0)

        self.kzs_3d = np.array([np.sqrt(k_length_arr_3d[idx] ** 2 - kappa ** 2)
                                for idx in range(len(self.k_length_arr))])

    def run_tm(self, do_position_resolved=False):
        """
        Evaluate the complete stack, starting from the top layer
        """

        if self.polarization is None:
            raise ValueError("No polarization defined. Set via set_polarization() method.")

        layer_indices = list(np.arange(len(self.thickness_list)))
        self.run_tm_sub_stack(layer_indices=layer_indices,
                              distance_to_first_interface=0.,
                              do_position_resolved=do_position_resolved)

    def run_tm_sub_stack(self, layer_indices: List[int], distance_to_first_interface=0., do_position_resolved=False):
        """
        Execute transfer matrix calculation.

        Go through the stack including the layers given in the index list.
        Note: The layer indices can also be reversed or shuffled if wanted.

        If multiple consecutive layers are coherent, they are joined to a coherent sub-stack with an effective R and T.
        Then, the coherent sub-stack acts just as an effective interface. In this way the stack is divided into
        sub-units which consist of incoherent layers with (effective) interfaces on top. The transfer matrix L[i] of a
        sub-unit i is calculated as

        L[i] = np.dot(array([[1/P[i],0],[0,P[i]]]),
                      array([[1,-R_rev[i]], [R[i], T_rev[i]*T[i] - R_rev[i]*R[i]]])) / T[i]

        where R _rev and T_rev are the reflected and transmitted wave powers for passing the (effective) interface
        reversely.

        For the very first sub-unit L[0] that describes the wave entering the stack from the first semi-infinite layer
        no propagation in the layer is given (propagation starts at interface). Hence, the matrix reads:

        L[0] = array([[1,-R_rev[0]], [R[0], T_rev[0]*T[0] - R_rev[0]*R[0]]])) / T[0]

        The total transfer matrix is then the product of all sub-matrices L[i]

        L_total = L[0] * L[1] * .. * L[N]

        where the products are matrix products (np.dot()).

        The total reflected and transmitted wave powers can then be extracted from L_total:

        T_total = 1 / L[0][0]
        R_total = L[1][0] / L[0][0]
        """

        if self.polarization is None:
            raise ValueError("No polarization defined. Set via set_polarization() method.")

        if self.kzs_3d is None:
            raise ValueError("Need to set angles or in-plane wavevectors first")

        is_coherent_sub_list = list(np.array(self.is_coherent_list)[layer_indices])

        if all(is_coherent_sub_list[1:-1]):
            self.r, self.t, self.R, self.T = self._calc_coherent_sub_stack(idx_list=layer_indices,
                                                                           distance_to_first_interface=distance_to_first_interface,
                                                                           do_position_resolved=do_position_resolved)
        else:
            # initialize transfer matrix as identity matrix
            L = np.array([[np.ones(self.kzs_3d[0].shape), np.zeros(self.kzs_3d[0].shape)],
                          [np.zeros(self.kzs_3d[0].shape), np.ones(self.kzs_3d[0].shape)]])
            L = np.transpose(L, (2, 3, 0, 1))

            # passing sub-units (propagation in incoherent layer + (effective) interface (can be coherent sub-stack))
            current_idx = layer_indices[0]
            while True:
                if current_idx == layer_indices[-1]:
                    break

                explicit_thickness = None
                if current_idx == layer_indices[0]:
                    explicit_thickness = distance_to_first_interface
                L_unit, current_idx = self._get_sub_unit_L(current_idx, layer_indices, explicit_thickness)
                L = np.matmul(L, L_unit)

            L = np.transpose(L, (2, 3, 0, 1))

            # Net complex transmission and reflection amplitudes
            L[0, 0] = np.ma.masked_where(L[0, 0] == 0, L[0, 0])  # avoid divide by zero error

            self.R = (L[1, 0] / L[0, 0]).real
            self.T = (1. / L[0, 0]).real

    def get_kz_arr(self, layer_idx: int):
        return self.kzs_3d[layer_idx]

    def calc_position_resolved_field_poynting_absorption(self, thetas_0, stepwidth=1.):
        """
        Calculate field amplitude, Poynting vector amplitude, and absorption for given layer stack position resolved.
        Given: transfer matrix T of complete stack (N-1 layers) and amplitude transmission coefficient t
        Assumptions: No incident light from bottom side (E_N- = 0), incident amplitude from top side one (E_0+ = 1)

        Known:
        1) transmission coefficient relates upwards propagating waves (E_N+ = t*E_0+ = t*1)
        2) transfer matrix T relates amplitude vectors (E_N = T*E_0, E_0 = T^{-1}*E_N)
        -> Calculation of incident amplitude vector: E_0 = T^{-1}*(t, 0)

        :param thetas_0: (rad)
        :param stepwidth: spacial increment between calculated positions along the stack normal
        :return:
        """

        # define position grid, where to calculate the amplitudes + initialize amplitude scalars/vectors
        self.positions = np.arange(0., np.sum(self.thickness_list[1:-1]), stepwidth)
        splitted_positions = self._split_positions_in_layers(self.positions)

        # initialize lists with shape given by angles and wavelengths grid
        E_of_z = [np.zeros((2, len(sp)) + self.kzs_3d[0].shape, dtype=complex) for sp in splitted_positions]
        Poynting_outofplane_of_z = [np.zeros((len(sp),) + self.kzs_3d[0].shape, dtype=complex) for sp in
                                    splitted_positions]
        Absorption_of_z = [np.zeros((len(sp),) + self.kzs_3d[0].shape, dtype=complex) for sp in splitted_positions]
        thetas_of_z = [np.zeros((len(sp),) + self.kzs_3d[0].shape, dtype=complex) for sp in splitted_positions]

        # start with known field amplitudes at bottom semi layer E_N = (t, 0)
        # Note: If you do the calculation top->bottom you have to invert all matrices which is probably slower
        E_N = np.array([np.ones(self.kzs_3d[0].shape, dtype=complex) * self.t,
                        np.zeros(self.kzs_3d[0].shape, dtype=complex)])
        current_E_after_interface = E_N

        for idx_coherent in range(len(splitted_positions))[::-1]:
            # go reversely through the coherent layers (neglect semi layers)
            idx_all = idx_coherent + 1

            # cross interface from previous layer (i+1 -> i)
            self._matrices_dot_vectors(self.J_mat_save[idx_all], current_E_after_interface,
                                       current_E_after_interface)

            # propagate (backwards) through current layer i
            self._matrices_dot_vectors(self.P_mat_save[idx_all], current_E_after_interface,
                                       current_E_after_interface)

            # calculate positions in current layer
            positions_current_layer = splitted_positions[idx_coherent] - splitted_positions[idx_coherent][0]

            # reshape (extend) positions array to wavelength-kz-grid
            pos_reshaped = np.transpose(
                positions_current_layer * np.ones(self.kzs_3d[0].shape + (len(positions_current_layer),)),
                (2, 0, 1))

            # calculate position resolved E-field amplitudes by propagating the field directly after the interface
            a, d = self._P_matrix_diagonal(self.kzs_3d[idx_all], pos_reshaped)

            E_of_z[idx_coherent][0] = current_E_after_interface[0] * d  # NOTE: switched a,d to get forward propagation
            E_of_z[idx_coherent][1] = current_E_after_interface[1] * a

            # -- calculate Poyting vector and absorption from the E-field amplitudes (polarization dependent) --
            thetas = np.arcsin(self.nks_3d[0] * np.sin(thetas_0) / self.nks_3d[idx_all])

            # expand thetas array to splitted positions:
            thetas_of_z[idx_coherent] = np.transpose(np.tensordot(thetas, np.ones(len(positions_current_layer)), axes=0),
                                            (2, 0, 1))
            Poynting_outofplane_of_z[idx_coherent] = self._poynting_from_Efield(E_of_z[idx_coherent],
                                                                                self.nks_3d[idx_all], thetas)
            Absorption_of_z[idx_coherent] = self._absorption_from_Efield(E_of_z[idx_coherent], self.nks_3d[idx_all],
                                                                         thetas, self.kzs_3d[idx_all])

        # -- concatenate the individual layers into one array which contains all positions --
        E = np.concatenate(E_of_z, axis=1)
        Poynting_outofplane = np.concatenate(Poynting_outofplane_of_z, axis=0)
        Absorption = np.concatenate(Absorption_of_z, axis=0)
        thetas_total = np.concatenate(thetas_of_z, axis=0)

        # -- add the up and down contribution of the E-field (total field) and square (intensity)
        if self.polarization == Polarization.S:
            Ex = 0
            Ey = E[0] + E[1]
            Ez = 0
        elif self.polarization == Polarization.P:
            Ex = (E[0] - E[1]) * np.cos(thetas_total)
            Ey = 0
            Ez = (-E[0] - E[1]) * np.sin(thetas_total)
        else:
            raise ValueError("Polarization must be 'Polarization.S' or 'Polarization.P'")

        E_total = np.sqrt(np.array(Ex) ** 2 + np.array(Ey) ** 2 + np.array(Ez) ** 2)
        E_intens = np.abs(E_total)

        return E_intens, Poynting_outofplane, Absorption

    # def calc_position_resolved_field_poynting_absorption(self, thetas_0, stepwidth=1.):
    #     """
    #     Calculate field amplitude, Poynting vector amplitude, and absorption for given layer stack position resolved.
    #     Given: transfer matrix T of complete stack (N-1 layers) and amplitude transmission coefficient t
    #     Assumptions: No incident light from top side (E_N- = 0), incident amplitude from bottom side one (E_0+ = 1)
    #     Known:
    #     1) transmission coefficient relates upwards propagating waves (E_N+ = t*E_0+ = t*1)
    #     2) transfer matrix relates amplitude vectors (E_N = T*E_0, E_0 = T^{-1}*E_N)
    #     -> Calculation of incident amplitude vector: E_0 = T^{-1}*(t, 0)
    #
    #     :param thetas_0:
    #     :param stepwidth: spacial increment between calculated positions along the stack normal
    #     :return:
    #     """
    #
    #     self.positions = np.arange(0., np.sum(self.thickness_list[1:-1]), stepwidth)
    #
    #     # -- define position grid, where to calculate the amplitudes + initialize amplitude scalars/vectors --
    #     splitted_positions = self._split_positions_in_layers(self.positions)
    #
    #     E_of_z = [np.zeros((2, len(sp)) + self.kzs_3d[0].shape, dtype=complex) for sp in splitted_positions]
    #     Poynting_outofplane_of_z = [np.zeros((len(sp),) + self.kzs_3d[0].shape, dtype=complex) for sp in
    #                                 splitted_positions]
    #     Absorption_of_z = [np.zeros((len(sp),) + self.kzs_3d[0].shape, dtype=complex) for sp in splitted_positions]
    #     thetas_of_z = [np.zeros((len(sp),) + self.kzs_3d[0].shape, dtype=complex) for sp in splitted_positions]
    #
    #     # -- start with known field in top semi layer E_N = (t, 0) --
    #     E_N = np.array([np.ones(self.kzs_3d[0].shape, dtype=complex) * self.t, np.zeros(self.kzs_3d[0].shape, dtype=complex)])
    #
    #     # -- calculate E-field amplitude after 1st interface --
    #     current_E_after_interface = E_N
    #
    #     # -- calculate the amplitudes in each layer directly after the interface and on position grid within layer --
    #     # NOTE: direction from top layer E_N=(t,0) to bottom layer E_0
    #
    #     for i in range((len(self.thickness_list) - 2), 0, -1):
    #         # -- interface i+1 -> i --
    #         self._matrices_dot_vectors(self.J_mat_save[i], current_E_after_interface, current_E_after_interface)
    #
    #         # -- backwards propagation in layer i --
    #         self._matrices_dot_vectors(self.P_mat_save[i - 1], current_E_after_interface, current_E_after_interface)
    #
    #         # -- calculate positions in current layer --
    #         positions_current_layer = splitted_positions[i - 1] - splitted_positions[i - 1][0]
    #
    #         # -- reshape (extend) positions array to wavelength-kz-grid --
    #         pos_reshaped = np.transpose(
    #             positions_current_layer * np.ones(self.kzs_3d[0].shape + (len(positions_current_layer),)), (2, 0, 1))
    #
    #         # -- calculate position resolved E-field amplitudes by propagating the field directly after the interface --
    #         a, d = self._P_matrix_diagonal(self.kzs_3d[i], pos_reshaped)
    #
    #         E_of_z[i - 1][0] = current_E_after_interface[0] * d  # NOTE: switched a,d to get forward propagation
    #         E_of_z[i - 1][1] = current_E_after_interface[1] * a
    #
    #         # -- calculate Poyting vector and absorption from the E-field amplitudes (polarization dependent) --
    #         thetas = np.arcsin(self.nks_3d[0] * np.sin(thetas_0) / self.nks_3d[i])
    #
    #         # expand thetas array to splitted positions:
    #         thetas_of_z[i - 1] = np.tensordot(thetas, np.ones(len(positions_current_layer)), axes=0).transpose(2, 0, 1)
    #         Poynting_outofplane_of_z[i - 1] = self._poynting_from_Efield(E_of_z[i - 1], self.nks_3d[i], thetas)
    #         Absorption_of_z[i - 1] = self._absorption_from_Efield(E_of_z[i - 1], self.nks_3d[i], thetas, self.kzs_3d[i])
    #
    #     # -- concatenate the individual layers into one array which contains all positions --
    #     E = np.concatenate(E_of_z, axis=1)
    #     Poynting_outofplane = np.concatenate(Poynting_outofplane_of_z, axis=0)
    #     Absorption = np.concatenate(Absorption_of_z, axis=0)
    #     thetas_total = np.concatenate(thetas_of_z, axis=0)
    #
    #     # -- add the up and down contribution of the E-field (total field) and square (intensity)
    #     if self.polarization == Polarization.S:
    #         Ex = 0
    #         Ey = E[0] + E[1]
    #         Ez = 0
    #     elif self.polarization == Polarization.P:
    #         Ex = (E[0] - E[1]) * np.cos(thetas_total)
    #         Ey = 0
    #         Ez = (-E[0] - E[1]) * np.sin(thetas_total)
    #     else:
    #         raise ValueError("Polarization must be 'Polarization.S' or 'Polarization.P'")
    #
    #     E_total = np.sqrt(Ex ** 2 + Ey ** 2 + Ez ** 2)
    #     E_intens = (E_total * np.conj(E_total)).real
    #
    #     return E_intens, Poynting_outofplane, Absorption

    def _get_sub_unit_L(self, start_idx: int, layer_indices: List[int], explicit_thickness=None) -> (np.array, int):
        """
        Calculate the transfer matrix of (multiple) subsequent coherent layers.

        Note: The layer_indices don't have to be subsequent, e.g. [1, 3, 4, 6] with start_idx=3

        :param explicit_thickness: explicitly given propagation distance in the first layer (layer thickness if None)
        """

        idx_list = [start_idx]

        if start_idx == layer_indices[-1]:
            raise ValueError("Start index is last layer index")

        try:
            idx_counter = layer_indices.index(start_idx)
        except:
            raise ValueError("Start index '" + str(start_idx) + "' not in index list " + str(layer_indices))

        while True:
            idx_counter += 1
            current_idx = layer_indices[idx_counter]
            idx_list.append(layer_indices[idx_counter])
            if current_idx == layer_indices[-1]:
                break
            if not self.is_coherent_list[current_idx]:
                break

        P = self._propagation_matrix_incoherent(start_idx, explicit_thickness)
        P = np.transpose(P, (2, 3, 0, 1))

        I = self._interface_matrix_incoherent(idx_list)
        I = np.transpose(I, (2, 3, 0, 1))

        L = np.matmul(P, I)

        return L, current_idx

    def _calc_coherent_sub_stack(self, idx_list: List[int], distance_to_first_interface=0.,
                                 do_position_resolved=False) -> (np.array, np.array, np.array, np.array):
        """
        Calculate the transfer matrix of a coherent sub-stack of the total stack which is defined by the layer indices.
        :param idx_list:
        :return: (r, t, R, T)
        """

        self.P_mat_save = []  # initialize lists for saving P and J in case of position-resolved calculations
        self.J_mat_save = []
        self.T_mat_save = []

        zero_mat = np.zeros(self.kzs_3d[idx_list[0]].shape)
        ones_mat = np.ones(self.kzs_3d[idx_list[0]].shape)

        # intialize transfer matrix as identity matrix
        T_mat = np.array([[ones_mat, zero_mat], [zero_mat, ones_mat]], dtype=complex)
        T_mat = np.transpose(T_mat, (2, 3, 0, 1))   # transpose to allow multidimensional multiplication

        for i in idx_list[0:-1]:

            # propagation in layer (for first layer the given distance to the interface is used)
            if i == idx_list[0]:
                layer_thickness = distance_to_first_interface
            else:
                layer_thickness = self.thickness_list[i]
            a, d = self._P_matrix_diagonal(self.kzs_3d[i], layer_thickness)
            P_mat = np.array([[a, zero_mat], [zero_mat, d]], dtype=complex)

            # interface to next layer (Note: it is not j=i+1 since sub-stack can be reverse/shuffled)
            j = idx_list[list(idx_list).index(i) + 1]  # index of next layer
            J_mat = self._J_matrix(self.kzs_3d[i], self.kzs_3d[j], self.nks_3d[i], self.nks_3d[j])

            if do_position_resolved:  # save the intermediate matrices if we want to do position-resolved calculations later
                self.P_mat_save.append(P_mat)
                self.J_mat_save.append(J_mat)

            # -- transpose matrices to allow direct matrix multiplication --
            P_mat = np.transpose(P_mat, (2, 3, 0, 1))
            J_mat = np.transpose(J_mat, (2, 3, 0, 1))

            # -- matrix multiplication for layer i (1st propagation P, 2nd interface J)
            T_mat = np.matmul(T_mat, P_mat)
            T_mat = np.matmul(T_mat, J_mat)

        # -- transpose matrix back --
        T_mat = np.transpose(T_mat, (2, 3, 0, 1))

        if do_position_resolved:  # save the T-matrix if we want to do position-resolved calculations later
            self.T_mat_save = T_mat

        # Net complex transmission and reflection amplitudes
        T_mat[0, 0] = np.ma.masked_where(T_mat[0, 0] == 0, T_mat[0, 0])  # avoid divide by zero error

        r = T_mat[1, 0] / T_mat[0, 0]
        t = 1. / T_mat[0, 0]

        # Net transmitted and reflected power, as a proportion of the incoming light power
        R = self._R_from_r(r)
        T = self._T_from_t(t, self.kzs_3d[idx_list[0]], self.kzs_3d[idx_list[-1]])

        return r, t, R, T

    def _J_matrix(self, kz_j, kz_i, n_j, n_i):
        """interface matrix for polarized light from layer j to layer i"""

        # avoid divide by zero error
        # todo: add mathematical solution for kz=0 values
        kz_j = np.ma.masked_where(kz_j == 0, kz_j)
        kz_j[np.isnan(kz_j)] = 1.e-21

        if self.polarization == Polarization.S:
            a = (kz_i + kz_j) / (2. * kz_j)
            b = (kz_j - kz_i) / (2. * kz_j)
        elif self.polarization == Polarization.P:
            a = (kz_j * n_i ** 2 + kz_i * n_j ** 2.) / (2. * kz_j * n_i * n_j)
            b = (kz_j * n_i ** 2 - kz_i * n_j ** 2.) / (2. * kz_j * n_i * n_j)
        else:
            raise ValueError("Polarization must be 'Polarization.S' or 'Polarization.p'")

        J_mat = np.array([[a, b], [b, a]], dtype=complex)
        return J_mat

    def _P_matrix_diagonal(self, kz_i, d_i):
        '''
        Return diagonal elements of propagation matrix of layer i at distance(s) d_i.
        d_i can be array-like or scalar.
        '''
        a = np.exp(-1.j * kz_i * d_i)
        d = np.exp(1.j * kz_i * d_i)
        return a, d

    def _interface_matrix_incoherent(self, layer_idx_list: List[int]) -> np.array:
        """Calculate interface matrix for transition from layer with index layer_idx to next layer"""

        r, t, R, T = self._calc_coherent_sub_stack(layer_idx_list)
        r_rev, t_rev, R_rev, T_rev = self._calc_coherent_sub_stack(layer_idx_list[::-1])

        T = np.ma.masked_where(T == 0, T)  # avoid divide by zero error

        # Interface matrix
        return np.array([[np.ones(R.shape), - R_rev], [R, T_rev * T - R_rev * R]]) / T

    def _propagation_matrix_incoherent(self, layer_idx: int, explicit_thickness=None) -> np.array:
        """
        We have kz = cos(theta) * k = cos(theta) * 2 * pi * n / lambda
        In coherent case P = np.exp(-1.j * kz * thickness)

        Byrnes:
        P = np.exp(-4 * np.pi * d_list[i] * (n_list[i] * cos(th_list[i])).imag / lam_vac)
        :return:
        """
        if explicit_thickness is None:
            thickness = self.thickness_list[layer_idx]
        else:
            thickness = explicit_thickness

        P = np.exp(-2. * thickness * self.kzs_3d[layer_idx].imag)
        P_mat = np.array([[1. / P, np.zeros(P.shape)], [np.zeros(P.shape), P]], dtype=complex)

        return P_mat

    def _R_from_r(self, r):
        """
        Calculate reflected power R, starting with reflection amplitude r.
        """
        return abs(r) ** 2

    def _T_from_t(self, t, kz_i, kz_f):
        '''[Furno, 2012] (A12), (A13)'''

        T = np.zeros(kz_i.shape)
        rows, cols = np.where(kz_i.real != 0.)  # for purely imaginary kz_i transmission is set to zero

        if self.polarization == Polarization.S:
            T[rows, cols] = abs(t[rows, cols] ** 2) * kz_f[rows, cols].real / kz_i[rows, cols].real
        elif self.polarization == Polarization.P:
            T[rows, cols] = abs(t[rows, cols] ** 2) * np.conj(kz_f[rows, cols]).real / np.conj(kz_i[rows, cols]).real
        else:
            raise ValueError("Polarization must be 'Polarization.S' or 'Polarization.P'")
        return T

    def _matrices_dot_vectors(self, matrices, vectors, output_array):
        """
        Calculate dot product of an array of 2x2-matrices and an array of 2-vectors,
        save the result in output_array.
        """
        output_array[0] = matrices[0, 0] * vectors[0] + matrices[0, 1] * vectors[1]
        output_array[1] = matrices[1, 0] * vectors[0] + matrices[1, 1] * vectors[1]

    def _split_positions_in_layers(self, positions):
        """
        Split the positions array into a list of arrays for each layer
        :param positions:
        :return: splitted_positions
        """
        splitted_positions = []
        first_index = 0
        current_d = 0

        for layer_thickness in self.thickness_list[1:-1]:
            # print('--')
            # print(positions)
            # print(layer_thickness)
            # print(current_d)
            last_index = np.where(positions < (layer_thickness + current_d))[0][-1]
            splitted_positions.append(positions[first_index:last_index + 1])
            first_index = last_index + 1
            current_d += layer_thickness
        return splitted_positions

    def _poynting_from_Efield(self, E_vec, n, theta):
        """
        Calculate the z-/normal-component of the Poynting vector from given E-field components
        [Multilayer optical calculations, Steven J. Byrnes (2018) https://arxiv.org/pdf/1603.02720.pdf] section 4.3
        NOTE: E_vec, n, and theta are 2D-arrays (wavelength-kz-grid)
        :param E_vec: electrical field amplitudes (E_up, E_down)
        :param n: refractive indices
        :param theta: angle versus normal
        :return: upward component of Poynting vector (vec{S}*vec{z})
        """

        if self.polarization == Polarization.S:
            Poynting = (n * np.cos(theta) * np.conj(E_vec[0] + E_vec[1]) * (E_vec[0] - E_vec[1])).real
        elif self.polarization == Polarization.P:
            Poynting = (n * np.conj(np.cos(theta)) * (E_vec[0] + E_vec[1]) * np.conj(E_vec[0] - E_vec[1])).real
        else:
            raise ValueError("Polarization must be 'Polarization.S' or 'Polarization.p'")

        return Poynting

    def _absorption_from_Efield(self, E_vec, n, theta, kz):
        """
        Calculate the z-dependent absorption from given E-field components
        [Multilayer optical calculations, Steven J. Byrnes (2018) https://arxiv.org/pdf/1603.02720.pdf] section 4.5
        NOTE: E_vec, n, and theta are 2D-arrays (wavelength-kz-grid)
        :param E_vec: electrical field amplitudes (E_up, E_down)
        :param n: refractive indices
        :param theta: angle versus normal
        :return: absorption profile a(z)
        """

        if self.polarization == 's':
            absorption = (abs(E_vec[0] + E_vec[1])) ** 2 * (n * np.cos(theta) * kz).imag
        elif self.polarization == 'p':
            absorption = (n * np.conj(np.cos(theta)) * (
                    kz * abs(E_vec[0] - E_vec[1]) ** 2 - np.conj(kz) * abs(E_vec[0] + E_vec[1]) ** 2)).imag
        else:
            raise ValueError("Polarization must be 'Polarization.S' or 'Polarization.p'")

        return absorption
