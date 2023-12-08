from setuptools import setup

setup(
    name='simojio',
    packages=['simojio', 'simojio.modules'],
    install_requires=['PySide2', 'numpy', 'scipy', 'matplotlib', 'anytree', 'psutil', 'packaging'],
    url='https://github.com/simoji-dev/simoji',
    license='LGPLv3',
    author='elmogit',
    description='Framework for running python modules with multidimensional parameter sets'
)

