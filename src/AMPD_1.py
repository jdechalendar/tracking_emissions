'''
AMPD step 1

'''
import os
import numpy as np
import logging
from load import AMPD, EGRID


DATA_PATH = os.getenv('DATA_PATH')
if DATA_PATH is None:
    raise ValueError("DATA_PATH needs to be set")


def AMPD_1():
    '''
    PLNT-level cleaning.
    '''
    logger = logging.getLogger('clean')
    logger.info("Starting AMPD_1")

    # Load result from step 0
    ampd = AMPD(step=0)

    # Load egrid data
    egrid_plnt = EGRID(sheet_name='PLNT16')

    # Restrict to states in Con-US
    egrid_plnt.df = egrid_plnt.df[~egrid_plnt.df.PSTATABB.isin(['AK', 'HI'])]

    # Drop the AMPD plants that do not have enough timestamps
    x = ampd.df.loc[:, ["ORISPL_CODE", "OP_DATE_TIME"]].groupby(
        'ORISPL_CODE').count()
    to_drop = x.mask(x > 8600).dropna()
    print("Dropping %d plants out of %d that do not have enough timestamps" % (
            len(to_drop), len(x)))
    ampd.df = ampd.df[~ampd.df.ORISPL_CODE.isin(to_drop.index.values)]

    egrid_orispl = set(egrid_plnt.df.ORISPL.values)
    ampd_orispl = set(ampd.df.ORISPL_CODE.values)
    egrid_only = egrid_orispl - ampd_orispl
    ampd_only = ampd_orispl - egrid_orispl
    print("%d are in egrid but not in ampd" % len(egrid_only))
    print("%d are in ampd but not in egrid" % len(ampd_only))

    # Drop the 11 AMPD plants that are not in EGRID
    ampd.df = ampd.df[~ampd.df.ORISPL_CODE.isin(ampd_only)]

    # For this step, also drop the EGRID plants that are not in AMPD
    egrid_plnt.df = egrid_plnt.df[~egrid_plnt.df.ORISPL.isin(egrid_only)]

    # Calculate AMPD annual totals
    ampd_ann = ampd.df.loc[:, ['ORISPL_CODE', 'CO2', 'SO2', 'NOX']].groupby(
        'ORISPL_CODE').sum()

    # Prepare EGRID unadjusted data
    egrid_un_ann = egrid_plnt.df.loc[:, ['ORISPL', 'UNCO2', 'UNSO2', 'UNNOX']]
    egrid_un_ann.columns = ['ORISPL_CODE', 'CO2', 'SO2', 'NOX']
    egrid_un_ann.set_index('ORISPL_CODE', inplace=True)
    egrid_un_ann.fillna(0, inplace=True)
    egrid_un_ann.sort_index(inplace=True)

    # Prepare EGRID adjusted data
    egrid_ann = egrid_plnt.df.loc[:, [
        'ORISPL', 'PLCO2AN', 'PLSO2AN', 'PLNOXAN']]
    egrid_ann.columns = ['ORISPL_CODE', 'CO2', 'SO2', 'NOX']
    egrid_ann.set_index('ORISPL_CODE', inplace=True)
    egrid_ann.sort_index(inplace=True)
    egrid_ann.fillna(0, inplace=True)

    # Check that we now have the same plants in both
    logger.debug(ampd_ann.index.equals(egrid_un_ann.index))
    logger.info("Checking %d plants from AMPD against EGRID unadj."
                % len(egrid_un_ann.index))

    # Check EGRID unadjusted data against AMPD annual totals
    logger.info("Checking EGRID unadjusted data against AMPD annual totals")
    diff = egrid_un_ann - ampd_ann
    tol = 10  # metric tonne
    diff = diff[(diff.CO2.abs() > tol) | (diff.SO2.abs() > tol)
                | (diff.NOX.abs() > tol)]
    logger.debug(diff.describe())

    # Check that all of the plants have 8,784 timesteps
    timesteps = ampd.df.loc[:, ['ORISPL_CODE', 'OP_DATE_TIME']].groupby(
        'ORISPL_CODE').count()
    logger.debug(np.sum(~(timesteps == 8784)))

    # try to reconcile ampd with egrid unadjusted
    for code in diff.index.values:
        for col in ["CO2", "SO2", "NOX"]:
            ampd.df.loc[ampd.df.ORISPL_CODE == code, col] += diff.loc[
                code, col] / 8784

    # Check results
    ampd_ann2 = ampd.df.loc[:, ['ORISPL_CODE', 'CO2', 'SO2', 'NOX']].groupby(
        'ORISPL_CODE').sum()
    diff2 = egrid_un_ann - ampd_ann2
    tol = 10  # metric tonne
    logger.debug(diff2.describe())
    if len(diff2[(diff2.CO2.abs() > tol) | (diff2.SO2.abs() > tol)
                 | (diff2.NOX.abs() > tol)]) > 0:
        logger.warn("Cleaning did not go as expected")

    # Now reconcile ampd with egrid adjusted - using first multiplication for
    # CHP and then substraction for biomass. Note that this is not perfect for
    # those plants that have both CHP and biomass flags

    logger.info("Dealing with CHP plants (excluding biomass)")
    df_tmp = egrid_plnt.df[(egrid_plnt.df.CHPFLAG == "Yes") & ~(
        egrid_plnt.df.RMBMFLAG == "Yes")]
    logger.debug(len(df_tmp))

    egrid_ann = df_tmp.loc[:, ['ORISPL', 'PLCO2AN', 'PLSO2AN', 'PLNOXAN']]
    egrid_ann.columns = ['ORISPL_CODE', 'CO2', 'SO2', 'NOX']
    egrid_ann.set_index('ORISPL_CODE', inplace=True)
    egrid_ann.sort_index(inplace=True)
    egrid_ann.fillna(0, inplace=True)

    egrid_un_ann = df_tmp.loc[:, ['ORISPL', 'UNCO2', 'UNSO2', 'UNNOX']]
    egrid_un_ann.columns = ['ORISPL_CODE', 'CO2', 'SO2', 'NOX']
    egrid_un_ann.set_index('ORISPL_CODE', inplace=True)
    egrid_un_ann.fillna(0, inplace=True)
    egrid_un_ann.sort_index(inplace=True)

    logger.debug(egrid_un_ann.sum())
    logger.debug(egrid_ann.sum())

    ratios = egrid_ann / egrid_un_ann
    tol = .01  # metric tonne
    logger.debug(len(ratios))

    ratios.fillna(0, inplace=True)

    logger.debug(ratios.describe())

    # try to reconcile ampd with egrid adjusted for CHP
    for code in ratios.index.values:
        for col in ["CO2", "SO2", "NOX"]:
            ampd.df.loc[ampd.df.ORISPL_CODE == code, col] *= ratios.loc[
                code, col]

    logger.info("Dealing with biomass plants (including CHP)")
    df_tmp = egrid_plnt.df[(egrid_plnt.df.RMBMFLAG == "Yes")]
    print(len(df_tmp))

    egrid_ann = df_tmp.loc[:, ['ORISPL', 'PLCO2AN', 'PLSO2AN', 'PLNOXAN']]
    egrid_ann.columns = ['ORISPL_CODE', 'CO2', 'SO2', 'NOX']
    egrid_ann.set_index('ORISPL_CODE', inplace=True)
    egrid_ann.sort_index(inplace=True)
    egrid_ann.fillna(0, inplace=True)

    egrid_un_ann = df_tmp.loc[:, ['ORISPL', 'UNCO2', 'UNSO2', 'UNNOX']]
    egrid_un_ann.columns = ['ORISPL_CODE', 'CO2', 'SO2', 'NOX']
    egrid_un_ann.set_index('ORISPL_CODE', inplace=True)
    egrid_un_ann.fillna(0, inplace=True)
    egrid_un_ann.sort_index(inplace=True)

    logger.debug(egrid_un_ann.sum())
    logger.debug(egrid_ann.sum())

    diff = egrid_ann - egrid_un_ann
    tol = 1  # metric tonne
    logger.debug(len(diff))

    logger.debug(diff.describe())

    # try to reconcile ampd with egrid adjusted for biomass
    for code in diff.index.values:
        for col in ["CO2", "SO2", "NOX"]:
            ampd.df.loc[ampd.df.ORISPL_CODE == code, col] += diff.loc[
                code, col] / 8784

    # Recalculate AMPD annual totals
    logger.info("Final round of adjustments")
    ampd_ann2 = ampd.df.loc[:, ['ORISPL_CODE', 'CO2', 'SO2', 'NOX']].groupby(
        'ORISPL_CODE').sum()

    egrid_ann = egrid_plnt.df.loc[:, [
        'ORISPL', 'PLCO2AN', 'PLSO2AN', 'PLNOXAN']]
    egrid_ann.columns = ['ORISPL_CODE', 'CO2', 'SO2', 'NOX']
    egrid_ann.set_index('ORISPL_CODE', inplace=True)
    egrid_ann.sort_index(inplace=True)
    egrid_ann.fillna(0, inplace=True)

    # Check EGRID unadjusted data against AMPD annual totals
    diff2 = egrid_ann - ampd_ann2
    tol = 1  # metric tonne
    logger.debug(len(diff2))
    diff2 = diff2[(diff2.CO2.abs() > tol) | (diff2.SO2.abs() > tol)
                  | (diff2.NOX.abs() > tol)]

    logger.debug(diff2.describe())

    logger.debug(len(diff2))

    # try to reconcile ampd with egrid adjusted for the final plants
    for code in diff2.index.values:
        for col in ["CO2", "SO2", "NOX"]:
            ampd.df.loc[ampd.df.ORISPL_CODE == code, col] += diff2.loc[
                code, col] / 8784

    # final check
    ampd_ann3 = ampd.df.loc[:, ['ORISPL_CODE', 'CO2', 'SO2', 'NOX']].groupby(
        'ORISPL_CODE').sum()
    egrid_ann = egrid_plnt.df.loc[:, [
        'ORISPL', 'PLCO2AN', 'PLSO2AN', 'PLNOXAN']]
    egrid_ann.columns = ['ORISPL_CODE', 'CO2', 'SO2', 'NOX']
    egrid_ann.set_index('ORISPL_CODE', inplace=True)
    egrid_ann.sort_index(inplace=True)
    egrid_ann.fillna(0, inplace=True)

    diff = egrid_ann - ampd_ann3
    tol = 1  # metric tonne
    logger.debug(len(diff))

    logger.debug(diff.describe())

    # Save data
    logger.info("AMPD 1 - Saving data")
    fileNm_out = os.path.join(DATA_PATH, 'analysis', 'AMPD_1.csv')
    ampd.df.to_csv(fileNm_out)
