from simoji.lib.parameters.MultiStringParameter import MultiStringParameter

import os


class FileFromPathParameter(MultiStringParameter):
    """ComboBox with all files in given path"""

    def __init__(self, name: str, path: str, extension_list: list, description: str):

        self.name = name
        self.path = path
        self.extension_list = extension_list

        self.description = description

        files = self.get_files()

        super().__init__(name, value=files[0], description=self.description, bounds=files)

    def get_files(self):
        all_files = [f for f in os.listdir(self.path) if os.path.isfile(os.path.join(self.path, f))]

        right_extension_files = []
        for f in all_files:
            for extension in self.extension_list:
                if extension in f:
                    right_extension_files.append(f)
                    break

        super().__init__(self.name, value=right_extension_files[0], description=self.description,
                         bounds=right_extension_files)

        return right_extension_files

    def _check_value(self, value: str) -> bool:
        """Check if path exists."""

        if os.path.exists(os.path.join(self.path, value)):
            return True
        else:
            return False

