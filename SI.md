# SI.md
The repository for the paper is available on Github, at https://github.com/jdechalendar/tracking_emissions. The latest version of this document (SI.md) will be in that repository.
## Repository structure
* Core functionality is implemented in the `src/` folder. See README.md at repository root for how to run the code.
   * `load.py` provides classes to load data from different sources - these classes provide accessor functions and checks - no data transformations here.
   * `EBA_n.py` contains cleaning of the EBA data for stage n, `AMPD_n.py` contains cleaning of the AMPD data for stage n, and `SEED.py` generates the consumption emissions dataset.
* We store data at different stages (raw, after different cleaning stages, cleaned). The loader classes should be able to load the datasets at each stage (after the extraction stage).
* The `figures` folder contains jupyter notebooks to recreate figures for the paper.

## Dataset reference
* eGRID data refers to eGRID 2016 data (various geographic levels, annual data)
* EBA data refers to data from the IEA's EBA.txt bulk download file (BA or region level, hourly data)
* AMPD or EPA data refers to data downloaded from the AMPD ftp (PLNT-level, hourly data)
* SEED data refers to the dataset produced by the code in this repository - this data reports hourly generation, trade and co2 emissions at the BA level, using data from the eGRID, AMPD and EBA datasets.

## Some general notes on data cleaning
We only consider 2016. For each data cleaning step, we provide commands to reproduce to generate results. See `src/Makefile` and run `make all` to regenerate data.

## AMPD: emissions data
The AMPD data set was scraped from the EPA's ftp server. This contains hourly-level emissions data for fossil-fuel plants in the US.

### Notes for data extraction - `src/AMPD_0.py`
* Extract raw AMPD data
* Create datetime column, keeping timestamp as is (no timezone change)
* Group data by facility (drops unit-level information)
* Convert all units to metric
* Drop unused columns

### Notes for data cleaning - `src/AMPD_1.py`: PLNT-level cleaning
* Restrict egrid data to con-us
* Drop 110 AMPD plants out of 1460 that have less than 8600 timestamps
    * cf notebook `figures/SI_AMPD_report.ipynb` on these 110 plants
* Drop the 11 plants in AMPD that are not in EGRID
* Only consider EGRID plants that are in AMPD in this step
* Compare annual totals for EGRID unadjusted and AMPD data. 220 plants have a difference that is more than 10 tons, 125 have a difference that is more than 1000 tons.
* Ensure that AMPD annual totals matches unadjusted EGRID facility-level data, spread the difference equally across all timesteps
* EGRID adjusts the emissions of CHP and biomass plants - Use the adjusted and unadjusted EGRID numbers to calculate adjustment ratios for CHP and additive adjustments for biomass. First adjust CHP only plants, and then all biomass plants (those that are both biomass and chp are treated as biomass).
* A couple plants seem to still have differences between adjusted and unadjusted data. Use additive adjustements here.

### Notes for data cleaning - `src/AMPD_2.py`: BA-level cleaning
* Group data by BACODE
* Absorb CSTO's 1 plant into BPAT
* Timezoning - using the `ba_to_tz.xlsx` file. Note that data is provided as local standard time according to the AMPD website. We understand that to mean there are no daylight savings in the data and that moving to UTC requires an hour shift that is the same all hours of the year.
* Reconcile AMPD data with eGRID unadjusted data
* Calculate plant-by-plant adjustments at an annual level using eGRID unadjusted and adjusted data
* Apply plant-by-plant adjustments at an hourly level to the AMPD data


## EBA: electricity data
* We use the EBA data as our main data source for electricity data. The user guide can be found [here](https://www.eia.gov/realtime_grid/docs/userguide-knownissues.pdf).
* This data is cross-checked against the EGRID dataset which provides annual values.
* Our main concerns when cleaning the EBA data are:
    * Demand and generation are within realistic ranges,
    * Trade matrix is antisymmetric,
    * Total trade vector is consistent with trade matrix,
    * Demand, generation and total trade are consistent (energy balance).

### Outline of data cleaning procedure
At each step, intermediate data sets are saved to disk and results are summarized.
* `EBA_0.py` extracts the raw data to our format
* `EBA_1.py` deals with demand and generation data
* `EBA_2.py` deals with pairwise trade data
* `EBA_3.py` deals with consistency: pairwise trade to total trade and total trade to demand and generation

### Notes for data extraction - `src/EBA_0.py`
Data is downloaded from <https://www.eia.gov/opendata/bulkfiles.php>. The extraction code parses the EBA data set in its newline-delimited JSON format and saves BA-level data as a dataframe. Raw data appears to be provided as UTC, so we store the timestamp as is. In the following, we will assume the timezone is UTC.

#### Sanity checks
* Check list of balancing areas in the EGRID data against list of those in the EBA dataset.
* 7 lines in EGRID do not appear in the EBA data set:
  * AMPL, CEA, HECO are in Alaska and Hawaii (nameplate capacities 595, 1048, 2427 MW)
  * NBSO is in Canada (nameplate capacity 244 MW)
  * CSTO changed its name in 2014 - will incorporate emissions data in BPAT (nameplate capacity 689 MW)
  * GRIS (nameplate capacity 324 MW) - 2 plants, that will not be considered in the analysis
  * There is a "No Balancing Area" line
* Out of these 7, only NBSO will be added to the EBA dataset (see step 1).
Important note: after this step, data will always be read through the load.EBA() interface.

### Notes for data cleaning - `src/EBA_1.py`
1. Restrict data to 2016. Timestamp is assumed to be UTC.
2. Drop demand forecast columns.
3. Add missing trade columns: WACM-SRP and PNM-SRP.
4. Add missing columns for NBSO.
5. Add missing demand columns for the 9 producer-only BAs (set to zero).
6. Check ranges for demand, generation and interchange data. We reject both negative and unrealistically high data (using eGRID reports of nameplate capacities and assumptions). For negative data for demand and generation, values below -100 MW are set to NaN and values between -100 and 0 are set to 0.

### Notes for EBA cleaning - `src/EBA_2.py`: cleaning pairwise trade.
* Many of these decisions were made subjectively, by visually inspecting plots showing pairwise trade as reported by the two entities and deciding which one was correct when there was a difference.
* Errors included:
  * Timestamp shifts,
  * Missing data,
  * Inconsistent reports from the two BAs involved in the pairwise trade,
  * Unphysical outliers,
  * Inconsistency between the sum of pairwise trades and total reported trade for a given BA.

### Notes for EBA cleaning - `src/EBA_3.py`: energy balances
In this step we make sure  that total trade, generation and demand are balanced so that no energy is lost
* There is some overlap between steps 2 and 3 for the EBA data, but in general step 2 is more focused on cleaning pairwise trades, and step 3 is more focused on making sure that the energy balances for each balancing area are consistent.
* Most of the demand and generation cleaning also happens here.
* The data is also adjusted so that annual totals match what is in eGRID (with some exceptions).
* The very last step is to make sure that energy balances are correct.
* At the end of this step, a sanity check is run for each BA (using function `check_BA()`).

## EGRID dataset
The eGRID data set reference for 2016 can be found [here](https://www.epa.gov/sites/production/files/2018-02/documents/egrid2016_technicalsupportdocument_0.pdf). The time resolution of eGRID data is annual. Our goal in this work is to provide and analyze estimates for hourly data of some of the key eGRID indicators. The eGRID dataset is used at different steps to validate the more granular data that is obtained from the AMPD and EBA datasets.

## Calculating consumption emissions - `src/SEED.py`
* The cleaned generation and emissions data (now both hourly and BA-level) are joined in one large dataframe
* We solve a linear system at each timestep to obtain an hourly consumption emissions vector
* We directly calculate an hourly production emissions vector by dividing the relevant columns
* This is done at the annual level for CO2, NOX and SO2, and at the monthly and hourly levels for CO2 (sub-annual data for NOX and SO2 is not trusted).
