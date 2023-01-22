from setuptools import setup

setup(
    name='simoji',
    packages=['simoji', 'simoji.modules'],
    install_requires=['PySide2', 'numpy', 'scipy', 'matplotlib', 'anytree', 'psutil'],
    url='https://github.com/simoji-dev/simoji',
    license='LGPLv3',
    author='elmogit',
    description='Framework for running python modules with multidimensional parameter sets'
)

