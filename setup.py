from setuptools import setup

setup(
    name='simoji',
    version='2.0.0_master',
    packages=['simoji', 'simoji.modules'],
    install_requires=['PySide2', 'numpy>=1.10.0', 'scipy>=0.19', 'matplotlib==3.2.2', 'pydicom', 'sympy>=0.7',
                      'emcee>=3.0.1', 'anytree', 'packaging', 'psutil'],
    url='https://github.com/simoji-dev/simoji',
    license='LGPLv3',
    author='Christian Haenisch',
    author_email='christian.haenisch@tu-dresden.de',
    description='Framework for running python modules with different parameter sets'
)
