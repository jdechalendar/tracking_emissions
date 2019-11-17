#Tracking emissions in the US electricity system
This repository contains the code to reproduce the results in the paper: [ADD REF on publication].

# Setup
Note: this setup has only been tested on Linux/OSX. Adjustments may be needed to run on Windows.
* The code was developped using python 3.5, and may not work with prior versions.
* Dependencies include numpy (1.17.1), pandas (0.25), xlrd.
* Clone or download this repository to your machine.
* Set the following environment variables by sourcing the provided `.env` file (run `source .env` from the command line at the repository root). Alternatively, you can define the following environement variables (for example by editing your `.bashrc` file):
    * `CODE_PATH`: the path to the folder where you downloaded this repository.
    * `DATA_PATH`: the path where you will save data.
    * `FIGURE_PATH`: the path where you will create figures.
* Data download: these should go to the folder pointed by the `DATA_PATH` environment variable. There are three datasets:
    * AMPD: We download from the EPA ftp server. We provide a script in the `src` folder to do this (run `./scrapeAMPD.sh` from the command line from the `src` folder). This should go to `data/raw/AMPD`. Note that the download from AMPD can take some time, depending on the speed of your connection.
    * IEA EBA data: [available here](https://www.eia.gov/opendata/bulkfiles.php). The `EBA.txt` file should go to `data/raw/`.
    * eGRID data: [available here](https://www.epa.gov/energy/emissions-generation-resource-integrated-database-egrid). The EGRID folder should go to `data/raw/`.

# Usage
## Set environment variables
* `source .env` from the folder this file is in.

## Generating the dataset
* We provide files for the final dataset in the `data/analysis` folder. Figures in the paper (and most of the SI Appendix figures) can be regenerated with these files.
* Alternatively, we also provide a Makefile in the `src` folder to regenerate the dataset, as well as intermediate steps. Type `make all` from the `src` folder to regenerate the dataset.

## Generating the figures
* We provide a Makefile in the `reports/tracking_emissions` folder to regenerate the figures in the paper and SI Appendix. The following commands can be used:
    * `make main`: figures for the main paper.
    * `make si_basic`: figures for the SI Appendix that do not require building the intermediate data steps.
    * `make si`: all figures for the SI Appendix.
    * `make all`: all figures.

* Figures can be also generated one by one from the notebooks.
