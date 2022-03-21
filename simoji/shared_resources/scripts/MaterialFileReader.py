import numpy as np


class MaterialFileReader:

    def __init__(self):
        pass

    def read_fmf_file(self, file_path: str) -> dict:
        """Read given fmf"""

        file_in = open(file_path, 'r')
        fmf_dict = {}
        data_def = []
        data = []
        category_key = None

        for line in file_in:
            if len(line) > 1:
                line_stripped = line.lstrip().rstrip()  # remove spaces at beginning and end of line
                if line_stripped[0] == '[' and line_stripped[-1] == ']':
                    if line_stripped[1] == '*':
                        category_key = line_stripped[2:-1]
                    else:
                        category_key = line_stripped[1:-1]
                    fmf_dict.update({category_key: {}})
                elif category_key == 'data':
                    data_list_str = self.my_split(line_stripped)
                    data_list_float = list(map(float, data_list_str))
                    data.append(data_list_float)
                elif category_key == 'data definitions':
                    line_split = line.split(':')
                    data_def.append([line_split[0].lstrip().rstrip(), ''.join(line_split[1:]).lstrip().rstrip()])
                elif category_key != None:  # skip first line (encoding stuff)
                    line_split = line.split(':')
                    fmf_dict[category_key].update(
                        {line_split[0].lstrip().rstrip(): ''.join(line_split[1:]).lstrip().rstrip()})

        file_in.close()

        fmf_dict.update({'data definitions': data_def})
        fmf_dict.update({'data': np.array(data).T})

        return fmf_dict

    @staticmethod
    def my_split(str):
        seps = [' ', '\t']
        res = [str]
        for sep in seps:
            str, res = res, []
            for seq in str:
                res += seq.split(sep)
        return res

    def read_optical_constants_from_fmf_file(self, file_path: str) -> list:
        """
        Read optical constants from .fmf file and return wavelengths, n-values, and k-values.
        :param file_path: path to optical constants file
        :return [[wl_list], [n_list], [k_list]] with wl=wavelength
        """

        # -- read file --
        file_dict = self.read_fmf_file(file_path)

        data_definitions = file_dict['data definitions']
        data = file_dict['data']

        # -- get data definitions and wavelength list --

        name_values_dict = {}   # {name: array([values])}
        for idx, item in enumerate(data_definitions):   # item = ['name', 'unit']
            name_values_dict.update({item[0]: data[idx]})

        # if len(name_values_dict) > 3:
        #     raise ValueError("More than 3 data columns given in file " + file_path + ". Reading anisotropic optical"
        #                                                                              "constants not yet implemented.")

        if 'wavelength' in name_values_dict:
            wavelength_list = name_values_dict['wavelength']
        else:
            raise ValueError("'wavelength' not given in data definitions of file: " + file_path)

        # -- convert to complex refractive index --

        if ('n' in name_values_dict) and ('k' in name_values_dict):
            n_list = name_values_dict['n']
            k_list = name_values_dict['k']
        elif ('eps1' in name_values_dict) and ('eps2' in name_values_dict):
            eps1_values = name_values_dict['eps1']
            eps2_values = name_values_dict['eps2']
            eps_complex = eps1_values + 1.j * eps2_values
            nk_complex = np.sqrt(eps_complex)
            n_list = nk_complex.real
            k_list = nk_complex.imag
        else:
            raise ValueError("Unknown data definitions in file " + file_path + ". Use ('n','k') or ('eps1', 'eps2').")

        return [wavelength_list, n_list, k_list]


