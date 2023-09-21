import simojio.lib.BasicFunctions as basic

import numpy as np
from scipy.interpolate import InterpolatedUnivariateSpline
import scipy.integrate as integrate
import scipy.optimize as scopt


class SriCorrection:

    def __init__(self, angle_stepwidth=0.01):

        # angle grid for calculation of sri correction (deg)
        self.angle_stepwidth = angle_stepwidth
        self.angles = np.array(basic.start_stop_step_to_list([-90., 90., angle_stepwidth]))

        # emission point properties
        self.emission_point = None

        # substrate properties
        self.substrate = None

        # cylinder properties
        self.cylinder = None

        # optical lenses
        self.lens_list = []     # list of lens objects along z-axis (from rotation center to detector)

        # detector properties (coordinates with respect to rotation center) --
        self.detector = None

        # execution flags
        self.include_lenses_flag = True
        self.plot_boundary_angles_flag = False

    def set_emission_point(self, x: float, z: float, width=0., shape="box"):
        self.emission_point = EmissionPoint(x=x, z=z, width=width, shape=shape)

    def set_substrate(self, thickness: float, n: float):
        self.substrate = Substrate(thickness=thickness, n=n)

    def set_cylinder(self, x: float, z: float, radius: float, n: float):
        self.cylinder = Cylinder(x=x, z=z, radius=radius, n=n)

    def add_lens(self, x: float, z: float, f: float, overlap_focus_with_last_lens_focus=True, shift_z=0.):
        """
        Add lens object to lens_list. If place_in_last_lens_focus=True, absolute z-position is ignored and instead
        calculated from the focus position of the last lens and the shift relative to this position (shift_z). If the
        first lens is added, the focus of the cylinder is used.
        :param x: lateral shift with respect to optical axis [mm]
        :param z: axial position with respect to rotation center (origin) [mm]
        :param f: focal length [mm]
        :param overlap_focus_with_last_lens_focus: bool that defines if the lens is placed in the focus of the last lens
        :param shift_z: axial shift with respect to the focus of the last lens
        :return:
        """

        if self.detector is not None:
            raise Warning("Detector already set. Check, if position (relative to last lens) needs to be updated.")

        if overlap_focus_with_last_lens_focus:
            z = self.get_last_lens_focus_position() + f + shift_z

        self.lens_list.append(Lens(x=x, z=z, f=f))

    def set_detector(self, x=0., z=0., width=0., NA=0.2, tilt_angle=0., place_in_last_lens_focus=True, shift_z=0.):
        """
        Define detector properties and position.
        :param x: lateral shift with respect to optical axis [mm]
        :param z: axial position with respect to rotation center (origin) [mm]
        :param width: phyiscal width of the opening [mm] of the detector aperture
        :param NA: numerical aperture
        :param tilt_angle: tilt angle of the detector [deg] with respect to perfectly facing the optical axis (z-axis)
        :param place_in_last_lens_focus: bool that defines if the lens is placed in the focus of the last lens
        :param shift_z: axial shift with respect to the focus of the last lens
        :return:
        """

        if place_in_last_lens_focus:
            z = self.get_last_lens_focus_position() + shift_z

        self.detector = Detector(x=x, z=z, width=width, NA=NA, tilt_angle=tilt_angle)

    def get_last_lens_focus_position(self) -> float:

        if len(self.lens_list) == 0:
            if self.cylinder is None:
                raise ValueError("Cylinder not yet defined. Cannot get focus position.")
            else:
                focus_position_z = self.cylinder.get_focus_position_z()
        else:
            last_lens = self.lens_list[-1]
            if isinstance(last_lens, Lens):
                focus_position_z = last_lens.get_focus_position_z()
            else:
                raise ValueError("Last object in lens_list is not a Lens object.")

        return focus_position_z

    def calculate_sri_correction(self, angles: np.array, wavelengths: np.array,
                                 intensities: np.array) -> (np.array, np.array, np.array):

        # -- check if main components are defined --
        if self.emission_point is None:
            raise ValueError("Emission point not defined. Need to run set_emission_point() before SRI calculation.")

        if self.substrate is None:
            raise ValueError("Substrate not defined. Need to run set_substrate() before SRI calculation.")

        if self.cylinder is None:
            raise ValueError("Cylinder not defined. Need to run set_cylinder() before SRI calculation.")

        if self.detector is None:
            raise ValueError("Detector not defined. Need to run set_detector() before SRI calculation.")

        # -- check shapes of input --
        # intensities should have shape (wavelengths, angles)
        if angles.shape[0] != intensities.shape[1]:
            raise ValueError("Shape of angles and intensities doesn't fit: " + str(angles.shape[0]) + " vs. "
                             + str(intensities.shape[1]))
        if wavelengths.shape[0] != intensities.shape[0]:
            raise ValueError("Shape of wavelengths and intensities doesn't fit: " + str(wavelengths.shape[0]) + " vs. "
                             + str(intensities.shape[0]))

        # -- interpolate intensities to simulation angle grid (use trapz integration afterwards) --
        intensities_interpolated = []
        for idx, wavelength in enumerate(wavelengths):
            intensities_wl = InterpolatedUnivariateSpline(angles, intensities[idx], k=1)
            intensities_interpolated.append(intensities_wl(self.angles))
        intensities_interpolated = np.array(intensities_interpolated)

        # -- calculate altered intensity for each detector angle (step by step) --
        intensities_corrected = []
        boundary_angles = []
        for detector_angle in angles:

            [min_angle, max_angle] = self.calculate_boundary_angles(detector_angle)
            if self.plot_boundary_angles_flag:
                boundary_angles.append([min_angle, max_angle])

            idx_min_angle, value = basic.find_nearest(list(self.angles), min_angle)
            idx_max_angle, value = basic.find_nearest(list(self.angles), max_angle)

            if idx_min_angle == idx_max_angle:
                intensities_at_angle = intensities_interpolated.T[idx_min_angle]
            else:
                intensities_at_angle = []
                for idx, wavelength in enumerate(wavelengths):
                    integrated_intensity = integrate.trapz(intensities_interpolated[idx][idx_min_angle:idx_max_angle],
                                                           dx=self.angle_stepwidth)
                    intensities_at_angle.append(integrated_intensity)

            intensities_corrected.append(intensities_at_angle)

        if self.plot_boundary_angles_flag:
            bounds_1 = np.array(boundary_angles).T[0]
            bounds_2 = np.array(boundary_angles).T[1]
            self.plot_boundary_angles(angles, bounds_1 - angles, bounds_2 - angles)

        intensities_normalized = self.normalize_sri(angles, np.array(intensities_corrected).T)

        return angles, wavelengths, intensities_normalized

    def calculate_boundary_angles(self, detector_angle_deg: float) -> list:
        """
        For a given detector angle, calculate the emission angles that correspond to the two rays that hit the edges of
        the detector. Later, integrating the sri over the range given by those two angles results in the corrected sri.

        :param detector_angle_deg: angular position of the detector with respect to the rotation coordinate system
        :return (minimum_boundary_angle, maximum_boundary_angle)
        """

        detector_angle_rad = detector_angle_deg * np.pi / 180.

        # (1) Get positions of emission point + detector in rotated coordinate system
        E_delta_vec_R, M_delta_vec_R, E_delta_vec_M = self.get_positions_in_rotated_system(detector_angle_rad)

        # (2) Calculate the emission angle that corresponds to the ray hitting the detector edge
        # Start with an emission angle close to zero deg (parallel optical axis in rotated system)
        # Minimize detector edge - ray distance by varying the emission angle
        #
        # Note:
        # The emission angle of the SriSimulator is the angle in the half cylinder
        # If n_cylinder = n_substrate, this is the same angle as in the substrate

        min_emission_angle = -5. * np.pi / 180.
        max_emission_angle = 5. * np.pi / 180.

        boundary_angles = []
        for x_value_detector_edge in self.detector.get_edge_positions():
            angle_rotated = scopt.brentq(self.calculate_ray_detector_distance, min_emission_angle, max_emission_angle,
                                         rtol=1e-15, args=(x_value_detector_edge, detector_angle_rad, E_delta_vec_R,
                                                           M_delta_vec_R, E_delta_vec_M))
            boundary_angles.append((angle_rotated + detector_angle_rad) * 180. / np.pi)

        return sorted(boundary_angles)

    def get_positions_in_rotated_system(self, detector_angle_rad: float) -> (np.array, np.array, np.array):
        """
        For the ray transfer analysis the coordinate system is rotated in such a way that the detector is located on the
        optical axis meaning rotated the 'detector angle'. In case of a displaced emission spot (E) and/or cylinder
        midpoint (M) their coordinates will change during the rotation yielding new coordinates E_delta and M_delta.
        Additionally, the rotated emission point is given relative to the rotated cylinder midpoint: E_delta_M

        :param: detector_angle_deg: detector angle [deg]
        :return: E_delta_vec_R: rotated emission point coordinates (z,x) relative to rotation axis R
        :return: M_delta_vec_R: rotated cylinder midpoint coordinates (z,x) relative to rotation axis R
        :return: E_delta_vec_M: rotated emission point coordinates (z,x) relative to rotated cylinder midpoint
        """

        # -- create emission point (E) and cylinder midpoint (M) coordinate vectors --
        E0_vec_M = np.array([self.emission_point.z, self.emission_point.x])  # relative to M, NOTE: z-coordinate first
        M0_vec_R = np.array([self.cylinder.z, self.cylinder.x])

        # -- translate emission point coordinates in rotation-coordinate system --
        E0_vec_R = E0_vec_M + M0_vec_R

        # -- define rotation matrix (for given detector angle delta) --
        # NOTE: rotation of coordinate system -> actually the inverse rotation matrix
        rot_mat = np.array([[np.cos(detector_angle_rad), np.sin(detector_angle_rad)],
                            [-np.sin(detector_angle_rad), np.cos(detector_angle_rad)]])

        # -- rotate emission point and cylinder midpoint coordinates --
        E_delta_vec_R = np.dot(rot_mat, E0_vec_R)
        M_delta_vec_R = np.dot(rot_mat, M0_vec_R)

        # -- translate rotated emission point coordinates back to cylinder midpoint coordinate system --
        E_delta_vec_M = E_delta_vec_R - M_delta_vec_R

        return E_delta_vec_R, M_delta_vec_R, E_delta_vec_M

    def calculate_ray_detector_distance(self, emission_angle_at_emission_point_rad: float, detector_edge_x: float,
                                        detector_angle_rad: float, E_delta_vec_R: np.array, M_delta_vec_R: np.array,
                                        E_delta_vec_M: np.array) -> float:
        """
        Calculate distance between detector edge and ray at z-position of detector. Use ray transfer analysis method.
        Notation vectors: X=(x, theta), P=(z, x)
        Notation indices: hc=half-cylinder, M=cylinder coordinate system, R=rotation coordinate_system

        :param emission_angle_at_emission_point: with respect to optical axis (angle in the rotated coordinate system)
        :param detector_edge_x:
        :return: distance
        """

        # define initial ray vector (in cylinder-midpoint coordinate system)
        # Note1: E_vec is given as (Ez, Ex) -> for ray transfer we need X=(x, theta)
        # Note2: Calculate propagation in substrate + cylinder in cylinder-midpoint coordinate system

        # initial vector in the substrate (at emission point)
        X_vec_initial_M = np.array([E_delta_vec_M[1], emission_angle_at_emission_point_rad])            # (x, theta)

        # propagation in substrate
        P_sub_hc_M = self.propagation_in_substrate(X_vec_initial_M, E_delta_vec_M, detector_angle_rad)  # (z,x)
        X_sub_hc_in = np.array([P_sub_hc_M[1], X_vec_initial_M[1]])                                       # (x, theta)

        # refraction at substrate-half-cylinder-interface
        X_hc_initial = self.refraction_at_tilted_planar_interface(X_in=X_sub_hc_in, tilt_angle_rad=detector_angle_rad,
                                                                  n1=self.substrate.n, n2=self.cylinder.n)

        # propagation in half-cylinder
        tan_theta = np.tan(X_hc_initial[1])
        x = X_hc_initial[0]
        z = P_sub_hc_M[0]
        R = self.cylinder.radius
        alpha = 1 + tan_theta ** 2
        beta = x - tan_theta * z
        z_P = 1. / alpha * (-tan_theta * beta + np.sqrt((tan_theta * beta) ** 2 - (beta ** 2 - R ** 2) * alpha))

        X_hc_air_in = np.dot(self.P_matrix(z_P - z), X_hc_initial)
        P_hc_air_M = np.array([z_P, X_hc_air_in[0]])

        # refraction at half-cylinder-air interface (Note: R<0 -> interface orientation)
        M_hc = self.spherical_interface(n1=self.cylinder.n, n2=1.0, R=-self.cylinder.radius)
        X_hc_air_out = np.dot(M_hc, X_hc_air_in)

        # transformation to rotation coordinate system
        # NOTE: M=(z,x), X_M = (x, theta) -> theta-coordinate unchanged
        X_hc_air_R = np.array([(X_hc_air_out[0] + M_delta_vec_R[1]), X_hc_air_out[1]])
        P_hc_air_R = P_hc_air_M + M_delta_vec_R     # todo: check, correct??

        current_P_vector = P_hc_air_R   # (z,x)
        current_X_vector = X_hc_air_R   # (x, theta)

        # optionally: propagation through lenses
        if self.include_lenses_flag:
            for lens_obj in self.lens_list:
                # propagation to lens
                propagation_matrix = self.P_matrix(dz=(lens_obj.z-current_P_vector[0]))
                current_X_vector = np.dot(propagation_matrix, current_X_vector)
                current_P_vector = np.array([lens_obj.z, current_X_vector[0]])

                # refraction at lens
                refraction_matrix = self.thin_lens(lens_obj.f)
                current_X_vector = np.dot(refraction_matrix, current_X_vector)

        # propagation to detector
        propagation_matrix = self.P_matrix(dz=(self.detector.z - current_P_vector[0]))
        X_detector = np.dot(propagation_matrix, current_X_vector)
        P_detector = np.array([self.detector.z, X_detector[0]])

        # calculate distance to detector edge
        ray_detector_distance = detector_edge_x - X_detector[0]

        return ray_detector_distance

    def propagation_in_substrate(self, X_vec_initial_M: np.array, E_delta_vec_M: np.array,
                                 detector_angle_rad: float) -> np.array:
        """Calculate coordinates of the ray at the substrate-cylinder interface"""

        emission_angle_rad = X_vec_initial_M[1]

        # -- calculate coordinates of the sub-hc refraction point in the rotated system (detector on z-axis, M origin)
        x_tilde = self.substrate.thickness / np.cos(emission_angle_rad - detector_angle_rad)
        P_sub_hc = np.array([np.cos(emission_angle_rad), np.sin(emission_angle_rad)]) * x_tilde + E_delta_vec_M

        return P_sub_hc

    def refraction_at_tilted_planar_interface(self, X_in: np.array, tilt_angle_rad: float,
                                              n1: float, n2: float) -> np.array:
        """
        Calculate effective incidence angle (rotation to coordinate system with planar interface),
        apply planar interface matrix, rotate back.
        :param X_in: (x, theta)
        :param tilt_angle_rad: delta
        :param n1: refractive index of first material
        :param n2: refractive index of second material
        :return:
        """

        theta_out = n1 / n2 * (X_in[1] - tilt_angle_rad) + tilt_angle_rad
        X_out = np.array([X_in[0], theta_out])

        return X_out

    def planar_interface_matrix(self, n1, n2):
        """
        Calculate ray transfer matrix of a planar interface separating two media with refractive indices n1, n2.
        [N. Hodgson and H. Weber, Laser resonators and beam propagation (Springer Science and Business Media,
        Inc., 2005).] -> page 12
        :param n1: refractive index incidence medium
        param n2: refractive index transmission medium
        :return: M: transfer matrix
        """
        return np.array([[1., 0.], [0, n1 / n2]])

    def thin_lens(self, f):
        """
        Calculate transfer matrix of thin lens with focal length f. [N. Hodgson and H. Weber, Laser resonators and beam
        propagation (Springer Science and Business Media, Inc., 2005).] -> page 14
        :param f: Focal length of lens
        :return: transfer matrix
        """
        return np.array([[1., 0.], [-1./f, 1]])

    def spherical_interface(self, n1, n2, R):
        """
        Calculate ray transfer matrix for a spherical interface with radius R that separates two media with refractive
        indices n1 and n2. [N. Hodgson and H. Weber, Laser resonators and beam propagation (Springer Science and
        Business Media, Inc., 2005).] -> page 12
        :param n1: refractive index incidence medium
        :param n2: refractive index transmission medium
        :param R: radius of spherical interface (positive = midpoint in medium 2, negative = midpoint in medium 1)
        :return: transfer matrix
        """
        return np.array([[1., 0.], [(n1 - n2) / (n2 * R), n1 / n2]])

    def P_matrix(self, dz):
        """
        Calculate ray transfer matrix of free propagation in homogeneous medium.
        [N. Hodgson and H. Weber, Laser resonators and beam propagation (Springer Science and Business Media,
        Inc., 2005).] -> page 10
        :param dz: propagation length along the optical axis (z)
        :return: M: transfer matrix
        """
        P = np.array([[1., dz], [0., 1.]])
        return P

    def normalize_sri(self, angles: np.array, intensities: np.array) -> np.array:
        """Normalize SRI to maximum of spectrum at angle closest to zero deg."""
        idx, value = basic.find_nearest(list(angles), 0.)
        spectrum = intensities.T[idx]
        return intensities / max(spectrum)

    def plot_boundary_angles(self, detector_angles: np.array, boundary_angles_1: np.array, boundary_angles_2: np.array):

        plot_data = [[detector_angles, boundary_angles_1],
                     [detector_angles, boundary_angles_2]]

        # -- define labels and execute the plot --
        name = 'boundary angles'
        data_set_labels = ['bounds1', 'bounds2']
        axes_labels = [['detector angle [deg]', 'boundary angle [deg']] * 2
        data_ls = ['.-', '.-']
        suffix = 'boundary_angles'

        # self.adf_plot_data_container = PlotDataContainer(plot_name=name, plot_type=PlotType.ONE_DIMENSIONAL,
        #                                                  plot_data=plot_data, axes_labels=axes_labels, data_ls=data_ls,
        #                                                  multi_data_sets=True,
        #                                                  data_set_labels=data_set_labels, suffix=suffix, save=True)
        # self.connector.send((ConnectorDataType.PLOT, self.adf_plot_data_container))
        print('todo add boundary plot')


class EmissionPoint:
    """Emission point located inside the cylinder"""

    def __init__(self, x: float, z: float, width=0., shape="box"):

        self.x = x          # lateral position with respect to cylinder midpoint [mm]
        self.z = z          # axial position with respect to cylinder midpoint [mm]

        self.width = width  # width [mm]
        self.shape = shape  # shape of emission pattern, "box" means equal emission from the whole area


class Substrate:
    """Substrate which is first passed by the emitted ray."""

    def __init__(self, thickness: float, n: float):

        self.thickness = thickness      # [mm]
        self.n = n                      # refractive index


class Cylinder:
    """(Half) cylinder in which the emission point is located"""

    def __init__(self, x: float, z: float, radius: float, n: float):

        # positions with respect to origin (rotation center) of zx-coordinate system (z-axis = optical axis)
        self.x = x  # displacement from optical axis [mm]
        self.z = z  # position along optical axis [mm]

        self.radius = radius    # [mm]
        self.n = n              # refractive index (use constant real value only)

    def get_focal_length(self) -> float:
        return self.radius / (self.n - 1.)

    def get_focus_position_z(self, absolute_position=False) -> float:
        """Focus position of cylinder in z-direction with respect to cylinder midpoint or (optional) absolute"""

        focus_position_z = self.radius + self.get_focal_length()

        if absolute_position:
            focus_position_z += self.z

        return focus_position_z


class Lens:
    """Thin optical lens used in the setup for angular resolved photoluminescence"""

    def __init__(self, x: float, z: float, f: float):

        # positions with respect to origin (rotation center) of zx-coordinate system (z-axis = optical axis)
        self.x = x     # displacement from optical axis [mm]
        self.z = z     # position along optical axis [mm]

        # focal length
        self.f = f     # focal length [mm]

    def get_focus_position_z(self) -> float:
        return self.z + self.f


class Detector:
    """Detector with finite extension (opening) and acceptance angle (numerical aperture)"""

    def __init__(self, x: float, z: float, width: float, NA: float, tilt_angle: float):

        # positions with respect to origin (rotation center) of zx-coordinate system (z-axis = optical axis)
        self.x = x          # displacement from optical axis [mm]
        self.z = z          # position along optical axis [mm]

        # opening (width) and numerical aperture
        self.width = width  # width [mm]
        self.NA = NA        # numerical aperture of detector

        # tilting angle
        self.tilt_angle = tilt_angle    # angle describing how much the angle is tilted from idealy facing z-axis [deg]

    def get_edge_positions(self) -> (float, float):
        """x-positions of detector edges with respect to optical axis (z-axis)"""

        edge_1 = self.x - self.width / 2.
        edge_2 = self.x + self.width / 2.

        return edge_1, edge_2