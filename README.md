# Tracking emissions in the US electricity system
This repository contains the code to reproduce the results in the paper: [ADD REF]

# Setup
This has only been tested on Linux/OSX. Adjustments may be needed to run on Windows.
* The code was developped using python 3.5, and may not work with prior versions.
* Clone or download this repository to your machine.
* Set the following environment variables (for example by editing your `.bashrc` file):
    * `CODE_PATH`: the path to the folder where you downloaded this repository.
    * `DATA_PATH`: the path where you will save data.
    * `FIGURE_PATH`: the path where you will create figures.
* Data download:
    * AMPD: we provide a script in the `src` folder to do this
    * IEA EBA data: available here. [Add link]
    * eGRID data: available here. [Add link]

# Usage
## Generating the dataset
* We provide a Makefile in the `src` folder to regenerate the dataset.

## Generating the figures
* We provide a Makefile in the `reports/tracking_emissions` folder to regenerate the figures.
* This Makefile expects your system to have a python virtual environment (created with `conda`) - this is convenient but not necessary, as figures can be generated one by one from the notebooks.
