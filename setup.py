from setuptools import setup

setup(
    name='simoji',
    version='0.1.0_master',
    packages=['simoji', 'simoji.modules'],
    install_requires=['numpy>=1.10.0', 'scipy>=0.19', 'matplotlib==3.2.2', 'lmfit>=0.9.12', 'pydicom', 'sympy>=0.7',
                      'numdifftools>=0.9', 'PySide2', 'emcee>=3.0.1', 'anytree', 'Cython', 'packaging', 'psutil',
                      'tmm'],
    url='https://github.com/elmogit/simoji',
    license='LGPLv3',
    author='Christian Haenisch',
    author_email='christian.haenisch@tu-dresden.de',
    description='Framework for running python modules with different parameter sets'
)
