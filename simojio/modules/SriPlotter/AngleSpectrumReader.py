from typing import List, Optional
import os
from pathlib import Path
from packaging import version
import numpy as np
from simojio.modules.SriPlotter.FitType import FitType
import datetime
from simojio.lib.BasicFunctions import find_nearest, savgol_smooth, interpol, project_2d_array_onto_grid
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit


class AngleSpectrumReader:
    """
    Reads angle-resolved emission spectrum from SweepMe data. For each angle-step there are two files, one containing
    the one-dimensional measurement data (e.g. time, voltage) and a second, containing the intensity spectrum.

    The measurement might contain additionally inserted reference measurements at a fix angle (reference-angle). From
    the evolution of the maximum of these measurements the overall intensity change (e.g. due to degradation) can be
    estimated and corrected.
    """

    def __init__(self):

        self.file_extension = ".txt"

        self.angles_label = "angles"
        self.wavelengths_label = "wavelengths"
        self.intensities_label = "intensities"
        self.times_label = "times"
        self.maxima_label = "maxima"
        self.fit_label = "fit"
        self.corrected_label = "corrected"

    def read_angle_spectrum_from_path(self, path: Path, angles: Optional[List[float]] = None,
                                      wavelengths: Optional[List[float]] = None,
                                      reference_angle: Optional[float] = None, angle_offset: Optional[float] = 0.,
                                      boxcar: Optional[int] = 0, cycle: Optional[int] = 0,
                                      drift_fit_type: Optional[FitType] = FitType.NO,
                                      normalize: Optional[bool] = True) -> dict:
        """
        Read and process angle-resolved emission spectrum from experimental data (SweepMe).
        :param path:
        :param angles:
        :param wavelengths:
        :param reference_angle:
        :param angle_offset:
        :param boxcar:
        :param cycle:
        :param drift_fit_type:
        :param normalize:
        :return: angles, wavelengths, intensities
        """

        version_str = self._get_sweepme_version(path)
        created = self._get_creation_date(path)

        exp_times, exp_angles, exp_wavelengths, exp_intensities = self._eval_sweepme_files(path)

        data_dict = self._process_sri(exp_times=np.array(exp_times),
                                      exp_angles=np.array(exp_angles),
                                      exp_wavelengths=np.array(exp_wavelengths),
                                      exp_intensities=np.array(exp_intensities),
                                      angles_grid=angles,
                                      wavelengths_grid=wavelengths,
                                      reference_angle=reference_angle,
                                      angle_offset=angle_offset,
                                      boxcar=boxcar,
                                      cycle=cycle,
                                      intensity_drift_fit_type=drift_fit_type,
                                      normalize=normalize)
        return data_dict

    @staticmethod
    def _get_sweepme_version(path: Path) -> str:
        """
        Read setting file (.set) and extract version number from first line
        :param path:
        :return: version as string, e.g. "1.5.5.38"
        """

        # find/read SweepMe setting file
        setting_file_list = [f for f in os.listdir(path) if f.endswith(".set")]
        if len(setting_file_list) == 0:
            raise ValueError("No SweepMe setting file found in given path: " + str(path))
        elif len(setting_file_list) > 1:
            raise ValueError("Multiple SweepMe setting files found in given path: " + str(path))
        else:
            setting_file = setting_file_list[0]

        # get SweepMe version (should be in first line as "#SweepMe!v1.5.5.38")
        f = open(os.path.join(path, setting_file), "r")
        lines = []
        for line in f:
            lines.append(line)

        version_str = lines[0].lstrip("#SweepMe!v").rstrip()

        return version_str

    def _eval_sweepme_files(self, path: Path) -> (np.array, np.array, np.array, np.array):
        """
        Each measurement step (angle) has an ID and is saved in two files:
            (1) "motor file": single value data (time, voltage etc)
            (2) "spectrometer file": spectrum (2 columns with wavelengths, intensities)

        The ID has two parts, separated by "-" (e.g. ID1-13) means branch "1" step "13".

        Here, we sort the files by there ID and identify a pair of files for each ID [motor_file, spectrometer_file].
        We differentiate between the 2 files by the length of their file name (the spectrometer_file always contains
        some additional label and, hence, is longer).

        :param path: Path to SweepMe results dir
        :param version_str: e.g. "1.5.5.38"
        :return: times, angles, wavelengths, intensities
        """

        def read_spectrometer_file(file_path: str) -> (np.array, np.array):
            """Two columns [wavelengths, intensities]. First 3 lines are header."""
            data = np.loadtxt(file_path, skiprows=3).transpose()
            return data[0], data[1]

        def read_motor_file(file_path: str) -> (float, float):
            """
            Read elapsed time and motor position (angle) from file. Last line are the numerical data. First line is
            header.
            """
            lines = [line.rstrip().split("\t") for line in open(file_path, 'r')]

            time_tags = ["time elapsed", "time"]    # This is auto generated by SweepMe so it shouldn't change to often
            position_tag = "position"               # combined with name of motor device, but this can be anything

            time_idx = None
            position_idx = None

            header = [str(item).lower() for item in lines[0]]
            for time_tag in time_tags:
                if time_tag in header:
                    time_idx = header.index(time_tag)
                    break

            for position_idx, label in enumerate(lines[0]):
                if position_tag in label.lower():
                    break

            if (time_idx is None) or (position_idx is None):
                raise ValueError("Couldn't find time and/or position column in lines[0]" + "\t".join(lines[0]))

            time_str = lines[-1][time_idx]
            position_str = lines[-1][position_idx]

            return float(time_str), float(position_str)

        all_file_names = [f for f in os.listdir(path) if f.endswith(self.file_extension)]

        id_list = []
        id_tag = "ID"

        # get all ID strings that are present in the file names
        for file_name in all_file_names:
            if id_tag in file_name:
                id_tag_containing_components = [component for component in file_name.split("_") if
                                                component.startswith(id_tag)]
                if len(id_tag_containing_components) != 1:
                    raise ValueError("There are multiple or zero ID-tag components in file name: " + file_name)
                id_str = id_tag_containing_components[0]
                if id_str not in id_list:
                    id_list.append(id_str)

        # get the file name pairs for each ID string [motor file, spectrum file]
        motor_spectrum_file_list = []
        for id_str in sorted(id_list):
            files_with_that_id = [f for f in all_file_names if id_str in f]

            # sort by length of file-name str -> NOTE: This is the trick to differentiate between the 2 files!!
            motor_spectrum_file_list.append(sorted(files_with_that_id, key=len))

        # evaluate data from file pairs
        angles = []
        times = []
        wavelengths = []
        intensities = []
        for motor_file, spec_file in motor_spectrum_file_list:
            time_elapsed, angle = read_motor_file(os.path.join(path, motor_file))
            angles.append(angle)
            times.append(time_elapsed)
            wavelengths, spectrum = read_spectrometer_file(os.path.join(path, spec_file))
            intensities.append(spectrum)

        return times, angles, wavelengths, intensities

    @staticmethod
    def _get_creation_date(path: Path) -> str:
        """
        Try to find a setting file (.set extension) in the given path and try to read the creation date from there.
        :param path: path in which the files should be evaluated
        :return:
        """

        created = "NaN"

        for file_path in [Path(os.path.join(path, f)) for f in os.listdir(path)]:
            if file_path.suffix == ".set":
                try:
                    created = str(datetime.datetime.fromtimestamp(path.stat().st_mtime))
                except Exception as e:
                    print(e)

        return created

    def _process_sri(self, exp_times: np.array, exp_angles: np.array, exp_wavelengths: np.array,
                     exp_intensities: np.array, angles_grid: Optional[List[float]] = None,
                     wavelengths_grid: Optional[List[float]] = None,
                     reference_angle: Optional[float] = None, angle_offset: Optional[float] = 0.,
                     boxcar: Optional[int] = 0, cycle: Optional[int] = 0,
                     intensity_drift_fit_type: Optional[FitType] = FitType.NO, normalize: Optional[bool] = True) -> dict:
        """
        Process the raw experimental data:
        (1) smooth the experimental spectra
        (2) correct for overall intensity decrease by fitting additional intermediate measurements at reference angle
        (3) Project the data onto a given wavelength and angle grid (optional)
        (4) Optionally: Normalize SRI to angle closest to zero deg
        :param exp_angles: array with all angles at which a measurement was done
        :param exp_wavelengths: array with experimental wavelength list
        :param exp_intensities: array with measured intensities
        :return: angles, wavelengths, intensities
        """

        project_onto_grid = not ((angles_grid is None) and (wavelengths_grid is None))

        # (1) smooth the experimental spectra
        intensities = np.array(savgol_smooth(exp_intensities, boxcar, polyorder=2))

        # (2) correct for overall intensity decrease by fitting additional intermediate measurements at reference angle
        intensities, data_maxima, data_fit, data_corr = self._correct_intensity_drift(exp_times=exp_times,
                                                    exp_angles=exp_angles,
                                                    exp_wavelengths=exp_wavelengths,
                                                    exp_intensities=intensities,
                                                    wavelengths_grid=wavelengths_grid,
                                                    project_onto_grid=project_onto_grid,
                                                    reference_angle=reference_angle,
                                                    intensity_drift_fit_type=intensity_drift_fit_type)

        angles, wavelengths, intensities = self._get_spectra_of_cycle_without_reference_spectra(exp_angles,
                                                                                                exp_wavelengths,
                                                                                                intensities,
                                                                                                reference_angle, cycle)

        # (3) project the data onto a given wavelength and angle grid (optional)

        if project_onto_grid:
            angles, wavelengths, intensities = self._project_sri_onto_grid(angles, wavelengths, intensities,
                                                                           angles_grid, wavelengths_grid, angle_offset)

        # (4) Optionally: Normalize SRI to angle closest to zero deg
        if normalize:
            angles, wavelengths, intensities = self._normalize_sri(angles, wavelengths, intensities)

        return {
            self.angles_label: angles,
            self.wavelengths_label: wavelengths,
            self.intensities_label: intensities,
            self.maxima_label: data_maxima,
            self.fit_label: data_fit,
            self.corrected_label: data_corr
        }

    def _correct_intensity_drift(self, exp_times: np.array, exp_angles: np.array, exp_wavelengths: np.array,
                                 exp_intensities: np.array, wavelengths_grid: Optional[List[float]] = None,
                                 project_onto_grid=False, reference_angle: Optional[float] = None,
                                 intensity_drift_fit_type: Optional[FitType] = FitType.NO
                                 ) -> (np.array, list, list, list):
        """
        Get all spectra taken at the reference angle and extract the maximum intensity (in the given wavelength range
        if option is selected). Fit the dependency of those maximum values with respect to the step number they are
        recorded (measurement ID) and multiply the inverse of the resulting function to the initial intensities.
        :param angles:
        :param intensities:
        :return:
        """

        if intensity_drift_fit_type is FitType.NO:
            intensities = exp_intensities
            data_maxima = []
            data_fit = []
            data_corr = []
        else:
            # get spectra at reference angle
            idx_list = np.where(exp_angles == reference_angle)[0]
            spectra_list = [exp_intensities[i] for i in idx_list]

            # get wavelength range (min/max index) in which to find the maximum intensity
            # Note: if projection onto angle-wavelength grid is disabled, the whole wavelength range is used
            min_idx = 0
            max_idx = len(exp_wavelengths) - 1
            if project_onto_grid:
                min_idx, min_value = find_nearest(exp_wavelengths, min(wavelengths_grid))
                max_idx, max_value = find_nearest(exp_wavelengths, max(wavelengths_grid))

            # get maxima of reference spectra (normalize to first value)
            maxima_list = [max(spectrum[min_idx: (max_idx + 1)]) for spectrum in spectra_list]
            normalized_maxima = np.array(maxima_list) / maxima_list[0]

            times_for_maxima = [exp_times[idx] for idx in idx_list]

            fit_values = self._fit_maxima_of_reference_spectra(times_for_maxima, normalized_maxima,
                                                               intensity_drift_fit_type, exp_times)
            correction_array = 1. / fit_values

            data_maxima = [times_for_maxima, normalized_maxima]
            data_fit = [exp_times, fit_values]
            data_corr = [exp_times, correction_array]

            # correct intensities
            intensities = np.array([exp_intensities[i] * correction_array[i] for i in range(len(exp_angles))])

        return intensities, data_maxima, data_fit, data_corr

    def _fit_maxima_of_reference_spectra(self, maxima_steps: list, maxima: list, fit_type: FitType,
                                         all_steps: np.array):
        """
        Linear, exponential, or interpolation fit of the maximum values of the reference spectra.
        :param steps:
        :param maxima:
        :param fit_type:
        :return: fit values for each measurement step
        """

        if fit_type is FitType.LINEAR:
            init_para = [(-0.001, 1.0), (-5e-4, 1.0), (-1e-3, 1.0), (-1e-4, 1.0)]
            popt, fit_valid = self._execute_fit(init_para, maxima_steps, maxima, self._linear_function)
            return self._linear_function(all_steps, *popt)
        elif fit_type is FitType.EXPONENTIAL:
            init_para = [(0.1, -0.01, 0.9), (-1e-4, 0.06, 1.00), (-1e-5, 0.1, 1.00), (-1e-6, 0.01, 1.01),
                         (3e-3, -1e-2, 1.00), (-3e-1, 0.015, 1.30), (0.5, -1e-2, 0.5)]
            try:
                popt, fit_valid = self._execute_fit(init_para, maxima_steps, maxima, self._exp_function)
                return self._exp_function(all_steps, *popt)
            except:
                return np.ones(len(all_steps))
        elif fit_type is FitType.INTERPOLATE:
            func = interpol(maxima_steps, maxima)
            return func(all_steps)

    def _execute_fit(self, init_para, steps, maxima, fit_function):
        xdata = np.array(steps)
        ydata = np.array(maxima)
        y_err = 1.0
        pcov = 'inf'
        popt = None
        fit_valid = False

        for i in np.arange(len(init_para)):
            if not fit_valid:
                try:
                    popt, pcov = curve_fit(fit_function, xdata, ydata, p0=init_para[i])
                except:
                    pcov = 'inf'
                    popt = [0]
                fit_valid = self._check_fit_par(popt, pcov)
            else:
                break
        return popt, fit_valid

    def _check_fit_par(self, popt, pcov):
        test_flag = False
        if str(pcov) != 'inf':
            try:
                perr = np.sqrt(np.diag(pcov))
                for i in np.arange(len(perr)):
                    if abs(perr[i] / popt[i]) < 1:  # error < parameter: fit valid
                        test_flag = True
            except:
                pass
        return test_flag

    def _linear_function(self, x, a, b):
        return a * x + b

    def _exp_function(self, x, a, b, c):
        return a * np.exp(b * x) + c

    def _get_spectra_of_cycle_without_reference_spectra(self, angles: np.array, wavelengths: np.array,
                                                        intensities: np.array, reference_angle, cycle=0) -> (
            np.array, np.array, np.array):
        """
        Remove all additional measurements taken at the reference angle from the sri.
        :param angles:
        :param wavelengths:
        :param intensities:
        :return:
        """

        def get_slope_idx(value, left_value=None, right_value=None):
            if (left_value is None) and (right_value is None):
                return 0
            elif left_value is None:
                if right_value > value:
                    return 1
                elif right_value < value:
                    return -1
                else:
                    return 0
            elif right_value is None:
                if left_value > value:
                    return -1
                elif left_value < value:
                    return 1
                else:
                    return 0
            else:
                if (left_value < value) and (right_value > value):
                    return 1
                elif (left_value > value) and (right_value < value):
                    return -1
                else:
                    return 0

        def get_slope_idx_of_previous_undefined(idx_to_check):

            if (angles[idx_to_check] == reference_angle) and (slope_idx_list[idx_to_check] == 0):
                return 0
            else:
                # go to left/right until not reference angle found -> get slope from those values
                left_value = None
                right_value = None

                total_idx_range = range(len(angles))

                # go to left
                current_idx = idx_to_check - 1
                while current_idx in total_idx_range:
                    if (angles[current_idx] == reference_angle) and (slope_idx_list[current_idx] == 0):
                        pass
                    else:
                        left_value = angles[current_idx]
                        break
                    current_idx -= 1

                # go to right
                current_idx = idx_to_check + 1
                while current_idx in total_idx_range:
                    if (angles[current_idx] == reference_angle) and (slope_idx_list[current_idx] == 0):
                        pass
                    else:
                        right_value = angles[current_idx]
                        break
                    current_idx += 1

                return get_slope_idx(angles[idx_to_check], left_value, right_value)

        def split_cycles():
            # return list of index lists, one for each cycle (they still include the reference points)
            # a new cycle is identified by a changing slope of the angles (e.g., in slope_idx_list 1 -> -1)

            all_indices = list(np.arange(len(angles)))
            cycle_start_indices = []
            current_slope = None

            for i in range(len(slope_idx_list)):
                if slope_idx_list[i] != 0:
                    if current_slope is None:
                        current_slope = slope_idx_list[i]
                    if slope_idx_list[i] != current_slope:
                        cycle_start_indices.append(i)
                        current_slope = slope_idx_list[i]

            cycle_idx_lists = []
            last_start_idx = 0
            for i in range(len(cycle_start_indices)):
                cycle_idx_lists.append(all_indices[last_start_idx:cycle_start_indices[i]])
                last_start_idx = cycle_start_indices[i]

            cycle_idx_lists.append(all_indices[last_start_idx:])  # append last cycle

            return cycle_idx_lists

        # -- identify angle cycles by rising/ falling angle values, difficulty: reference angles in between --
        # Note: need to keep the measurements that are in the row, e.g. keep reference angle 10 in row 8,9,10,11,12 but
        # kick it out in row 1,2,3,10,4,5,6

        # 1) check for decreasing/increasing values of direct neighbours
        slope_idx_list = []  # list of slope-indices indicating a positive (1), undefined (0), or negative (-1) slope
        for idx, angle in enumerate(angles):
            if (idx == 0) or (idx == len(angles) - 1):  # first and last point are undefined
                slope_idx_list.append(0)
            else:
                slope_idx_list.append(get_slope_idx(angle, angles[idx - 1], angles[idx + 1]))

        # 2) double check undefined values, if neighbour is reference angle, check next neighbour
        for idx, slope_idx in enumerate(slope_idx_list):
            if slope_idx_list[idx] == 0:
                slope_idx_list[idx] = get_slope_idx_of_previous_undefined(idx)

        # 3) get spectra of given cycle without reference spectra
        cycle_idx_lists = split_cycles()
        if cycle > len(cycle_idx_lists) - 1:
            cycle_idx_list = cycle_idx_lists[0]
        else:
            cycle_idx_list = cycle_idx_lists[cycle]

        intensities_new = []
        angles_new = []
        for idx in cycle_idx_list:
            if slope_idx_list[idx] != 0:
                angles_new.append(angles[idx])
                intensities_new.append(intensities[idx])

        return np.array(angles_new), wavelengths, np.array(intensities_new)

    def _project_sri_onto_grid(self, angles: np.array, wavelengths: np.array, intensities: np.array,
                               angles_grid: np.array, wavelengths_grid: np.array, angle_offset: float) -> (
            np.array, np.array, np.array):
        """
        Project the experimental sri onto the given angle-wavelength grid. Use 2d-interpolation of experimental sri to
        get values between the experimental measured grid.
        :param angles:
        :param wavelengths:
        :param intensities:
        :return:
        """

        x_grid = np.array(angles_grid) + angle_offset

        intensities_new = project_2d_array_onto_grid(x_init=angles, y_init=wavelengths, data2d_init=intensities.T,
                                                     x_grid=x_grid, y_grid=wavelengths_grid)

        return angles_grid, wavelengths_grid, intensities_new.T

    def _normalize_sri(self, angles: np.array, wavelengths: np.array, intensities: np.array) -> (np.array, np.array,
                                                                                                 np.array):

        idx, value = find_nearest(angles, 0.)
        spectrum = intensities[idx]
        norm_value = max(spectrum)
        if norm_value == 0.:
            norm_value = 1.
        intensities = intensities / norm_value
        # self.plot_spectra([[wavelengths, spectrum]])

        return angles, wavelengths, intensities


if __name__ == "__main__":
    pass
