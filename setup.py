from setuptools import setup

setup(
    name='simoji',
    version='2.0.0_master',
    packages=['simoji', 'simoji.modules'],
    install_requires=['PySide2==5.15.2.1', 'numpy==1.19.5', 'scipy==1.5.4', 'matplotlib==3.2.2', 'anytree==2.8.0',
                      'psutil==5.9.0'],
    url='https://github.com/simoji-dev/simoji',
    license='LGPLv3',
    author='elmogit',
    description='Framework for running python modules with multidimensional parameter sets'
)

