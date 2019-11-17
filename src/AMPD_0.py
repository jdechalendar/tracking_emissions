import os
import pandas as pd
import logging
from joblib import Parallel, delayed
import time

DATA_PATH = os.getenv('DATA_PATH')
if DATA_PATH is None:
    raise ValueError("DATA_PATH needs to be set")


def AMPD_0(year=2016):
    """
    Use the parseEPAFile function to parse the different zip files downloaded
    from the AMPD ftp server, and save one file for all of 2016.
    """
    logger = logging.getLogger('parse')
    logger.info("Starting AMPD_0")

    start_time = time.time()
    base_path = os.path.join(DATA_PATH, 'raw', 'AMPD')

    logger.info('Starting %d' % year)
    df_list = []
    path = os.path.join(base_path, str(year))
    fnames = os.listdir(path)

    df_list = Parallel(n_jobs=-1)(delayed(parseEPAFile)(
       os.path.join(path, name)) for name in fnames)

    # Do this sequentially - kept here for debugging.
    # df_list = [parseEPAFile(
    #     os.path.join(path, name), ORISPL_to_tz) for name in fnames]

    logger.info('Combining data')
    df = pd.concat(df_list)
    logger.info('Saving file')
    path_out = os.path.join(DATA_PATH, 'analysis', 'AMPD_0.csv')

    df.to_csv(path_out, index=False)
    logger.info('%.2fmin so far' % ((time.time() - start_time)/60.0))


def parseEPAFile(pathNm, cols=None):
    """
    Parse one file downloaded from the EPA AMPD ftp server
        ftp://newftp.epa.gov/DMDnLoad/emissions/hourly/monthly/

    1. Create a datetime column.
    2. Aggregate data by ORISPL code and timestamp (this bundles the different
    units in a plant).
    3. Change units to metric
    4. Select only columns we need
    """
    col_name_map = {'CO2_MASS': 'CO2_MASS (tons)',
                    'CO2_RATE': 'CO2_RATE (tons/mmBtu)',
                    'GLOAD': 'GLOAD (MW)',
                    'HEAT_INPUT': 'HEAT_INPUT (mmBtu)',
                    'NOX_MASS': 'NOX_MASS (lbs)',
                    'NOX_RATE': 'NOX_RATE (lbs/mmBtu)',
                    'SLOAD': 'SLOAD (1000lb/hr)',
                    'SLOAD (1000 lbs)': 'SLOAD (1000lb/hr)',
                    'SO2_MASS': 'SO2_MASS (lbs)',
                    'SO2_RATE': 'SO2_RATE (lbs/mmBtu)'
                    }
    sh_to_metr_tons = 0.9071847
    lbs_to_metr_tons = 0.000453592

    # Read data
    df_tmp = pd.read_csv(pathNm, low_memory=False)

    # Rename columns
    df_tmp.rename(col_name_map, axis='columns', inplace=True)

    # 1. Parse timestamp (local time)
    df_tmp.loc[:, 'OP_DATE_TIME'] = pd.to_datetime(
        df_tmp['OP_DATE'] + '-' + df_tmp['OP_HOUR'].astype(str),
        format='%m-%d-%Y-%H')
    df_tmp.loc[:, 'YEAR'] = df_tmp.loc[:, 'OP_DATE_TIME'].dt.year.astype(int)
    df_tmp.loc[:, 'MONTH'] = df_tmp.loc[:, 'OP_DATE_TIME'].dt.month.astype(int)

    # 2. Group by ORISPL and timestamp (drop UNIT level)
    df_tmp = df_tmp.groupby(
        ['STATE', 'ORISPL_CODE', 'YEAR', 'MONTH', 'OP_DATE_TIME']).sum()
    df_tmp.reset_index(inplace=True)

    # 3. Change units to metric
    df_tmp.loc[:, 'CO2'] = df_tmp.loc[:, 'CO2_MASS (tons)'] * sh_to_metr_tons
    df_tmp.loc[:, 'SO2'] = df_tmp.loc[:, 'SO2_MASS (lbs)'] * lbs_to_metr_tons
    df_tmp.loc[:, 'NOX'] = df_tmp.loc[:, 'NOX_MASS (lbs)'] * lbs_to_metr_tons

    # 4. Keep as little info as possible to save space
    keep_cols = [
        'STATE', 'ORISPL_CODE', 'OP_DATE_TIME', 'OP_TIME', 'GLOAD (MW)',
        'SO2', 'NOX', 'CO2', 'HEAT_INPUT (mmBtu)', 'FAC_ID']

    if cols != 'all':
        return df_tmp.loc[:, keep_cols]
    else:
        return df_tmp
