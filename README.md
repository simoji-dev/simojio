# <span style="color:blue; opacity: 0.7">simoji</span>

Framework for automated execution of python modules with different input parameter values and/or input data sets.

Simoji provides:
* a powerful GUI for...
  * editing multiple input parameter values
  * organizing 1-dimensional layer structures 
  * displaying numerical and graphical results
  * saving results in an organized, recursive folder structure
* automated, multidimensional, and parallelized loops through value ranges of many parameters
* optimization routines that minimize/maximize target values defined in your module

If you already have or plan to write a calculation or data evaluation script that depends on multiple input parameters
(general or organized in 1-dimensional layer structures) simoji can easily extend the capability of this script to
(multidimensional) parameter variations or optimizations.

## Getting Started

Thank you very much for considering to use and/or contribute to simoji. You can either use the program by running 
existing modules or extend it by writing your own modules. Of course, you are also warmly invited to contribute to the 
core program!

These instructions will get you a copy of the project up and running on your local machine for usage and/or development. 
It is also possible to build an executable file of the program - see deployment notes for details.

### Prerequisites

You need a python3 installation on your machine. Simoji is tested with Windows10 and Linux Mint. For other distros and 
OS there is no guarantee that it will work.

### Installing

It is highly recommended running the program in a virtual environment (venv) which can be equipped with all the 
necessary site packages without effecting the system installation. Such a venv can be created via

```
python3 -m venv [venv-name]
```

Logging into this venv is done via 

* Linux: `source [venv-name]/bin/activate`
* Windows: `source [venv-name]\Scripts\activate`

To install all required python packages one can rely on the setup.py file on the top level of the repository. It 
includes a list of requirements which will be installed by running

```
pip install -e .
```

The `-e` flag makes sure that program is installed in an editable state, and all the edits made to the .py files will be 
automatically included in the installed package.

Finally, we can run simoji by navigating to the `simoji` folder and execute 

```
python main.py
```

Modern IDEs such as [PyCharm](https://www.jetbrains.com/pycharm/) can include/automate the above described steps.

## Deployment

One can build an executable file by using pyinstaller and the respective specification file
`simoji_builder.spec` (update path to top level folder: 'pathex') in the top level folder:

`pyinstaller simoji_builder.spec`

This will create an executable file in the `dist` folder which can then be copied and run on other systems with the same 
OS. 

NOTE: An executable works only on the OS is was build. So if you want to use the executable on a Windows system, you 
have to build it on a Windows system.

## Contributing

Please read [CONTRIBUTING.md](CONTRIBUTING.md) for details on our code of conduct, and the process for submitting pull requests to us.

## Versioning

We use [SemVer](http://semver.org/) for versioning. For the versions available, see the [tags on this repository](https://github.com/your/project/tags). 

## Authors

* **Christian Hänisch** - *Initial work* - [elmogit](https://github.com/elmogit)

See also the list of [contributors](https://github.com/your/project/contributors) who participated in this project.

## License

This project is licensed under the LGPL license - see the [LICENSE.md](LICENSE.md) file for details

## Acknowledgments

* Hat tip to anyone whose code was used
* Inspiration
* etc

