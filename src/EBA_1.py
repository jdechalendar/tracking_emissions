import os
import pandas as pd
import numpy as np
import logging
import pickle
from load import BA_DATA, EGRID

DATA_PATH = os.getenv('DATA_PATH')
if DATA_PATH is None:
    raise ValueError("DATA_PATH needs to be set")


def EBA_1(clip=False):
    '''
    Basic data cleaning.
    1. Restrict data to 2016.
    2. Drop demand forecast columns.
    3. Add missing trade columns: WACM-SRP and PNM-SRP.
    4. Add missing columns for NBSO.
    5. Add missing demand columns for the 9 producer-only BAs (set to zero).
    6. Check ranges for demand, generation and interchange data. We reject both
    negative and unrealistically high data (using eGRID reports of nameplate
    capacities and assumptions).
    '''
    logger = logging.getLogger('clean')
    logger.info("Starting EBA_1")

    # Load EBA data
    eba = BA_DATA(step=0)

    # 1. Restrict to 2016 data in UTC
    eba.df = eba.df.loc[pd.to_datetime("20160101"):pd.to_datetime(
        "2016-12-31 23:00:00")]

    # 2. Drop demand forecast columns
    eba.df.drop(columns=[col for col in eba.df.columns if 'DF.H' in col],
                inplace=True)

    # 3. Add missing trade columns for SRP
    eba.df['EBA.WACM-SRP.ID.H'] = -eba.df['EBA.SRP-WACM.ID.H']
    eba.df['EBA.PNM-SRP.ID.H'] = -eba.df['EBA.SRP-PNM.ID.H']

    # 4. Add missing columns for NBSO
    eba.df.loc[:, 'EBA.NBSO-ISNE.ID.H'] = - eba.df.loc[:, 'EBA.ISNE-NBSO.ID.H']
    eba.df.loc[:, 'EBA.NBSO-ALL.D.H'] = eba.df.loc[:, 'EBA.NBSO-ISNE.ID.H']\
        .apply(lambda x: -min(x, 0))
    eba.df.loc[:, 'EBA.NBSO-ALL.NG.H'] = eba.df.loc[:, 'EBA.NBSO-ISNE.ID.H']\
        .apply(lambda x: max(x, 0))
    eba.df.loc[:, 'EBA.NBSO-ALL.TI.H'] = eba.df.loc[:, 'EBA.NBSO-ISNE.ID.H']

    # 5. Add missing demand columns for the 9 producer-only BAs
    for col in eba.get_cols(field="D"):
        if col not in eba.df.columns:
            eba.df.loc[:, col] = 1.

    # 6. Ranges
    # 6.1 Lower bound 0 for generation and demand
    # Values below -100 set to nan, and between -100 and 0 to 0
    for field in ["NG", "D"]:
        logger.info("%d negative %s values" % (
            np.sum(np.sum(eba.df.loc[:, eba.get_cols(field=field)] < 0)),
            field))
        logger.info("%d values below -100 for %s" % (
            np.sum(np.sum(eba.df.loc[:, eba.get_cols(field=field)] < -100)),
            field))

        cnt1 = eba.df.loc[:, eba.get_cols(field=field)].isna().sum().sum()
        eba.df.loc[:, eba.get_cols(field=field)] = eba.df.loc[
            :, eba.get_cols(field=field)].mask(
                    lambda x: x < -100., other=np.nan)
        eba.df.loc[:, eba.get_cols(field=field)] = eba.df.loc[
            :, eba.get_cols(field=field)].mask(
                    lambda x: x < 0., other=0.)
        cnt2 = eba.df.loc[:, eba.get_cols(field=field)].isna().sum().sum()
        logger.debug("NAs bfr/aftr/diff: %d %d %d" % (cnt1, cnt2, cnt2-cnt1))

    # 6.2 Upper bound for NG, D, TI
    # Load EGRID data
    egrid = EGRID(sheet_name='BA16')
    # Upper bounds - based on nameplate capacities and assumptions
    NAMEP_NG = dict(zip(egrid.df.BACODE.values, egrid.df.NAMEPCAP.values))
    NAMEP_NG['PSEI'] = 3500.
    NAMEP_NG['CPLW'] = 1000.
    NAMEP_NG['BANC'] = 3500.
    NAMEP_NG['PGE'] = 3000.

    NAMEP_D = dict(zip(egrid.df.BACODE.values, egrid.df.NAMEPCAP.values))
    NAMEP_D['PSEI'] = 6000.
    NAMEP_D['CPLW'] = 1500.
    NAMEP_D['TPWR'] = 1000.
    NAMEP_D['HST'] = 150.
    NAMEP_D['BANC'] = 5000.
    NAMEP_D['NSB'] = 150.
    NAMEP_D['PGE'] = 4500.

    NAMEP_ID = dict(zip(egrid.df.BACODE.values, egrid.df.NAMEPCAP.values))
    NAMEP_ID['CPLW'] = 1000.
    NAMEP_ID['HST'] = 150.
    NAMEP_ID['PSEI'] = 4000.
    NAMEP_ID['PGE'] = 3000.
    NAMEP_ID['NSB'] = 75.

    NAMEP_TI = dict(zip(egrid.df.BACODE.values, egrid.df.NAMEPCAP.values))
    NAMEP_TI['CPLW'] = 600.
    NAMEP_TI['HST'] = 150.
    NAMEP_TI['NSB'] = 150.
    NAMEP_TI['PGE'] = 4500.
    NAMEP_TI['PSEI'] = 6000.

    rules = {"NG": NAMEP_NG, "D": NAMEP_D, "TI": NAMEP_TI, "ID": NAMEP_ID}

    for field in ["D", "NG", "TI"]:
        cnt = 0
        for ba in eba.regions:
            curr_col = eba.get_cols(ba, field=field)[0]
            mask = eba.df.loc[:, curr_col].abs() > rules[field][ba]
            cnt += np.sum(mask)
            eba.df.loc[mask, curr_col] = np.nan
        logger.info("%s: %d values were too high" % (field, cnt))

    cnt = 0
    for ba in eba.regions:
        for pair in eba.get_trade_out(ba):
            mask = eba.df.loc[:, pair].abs() > NAMEP_ID[ba]
            if np.sum(mask) > 0:
                eba.df.loc[mask, pair] = 0.
                cnt += np.sum(mask)
    logger.info(
        "%d interchange (ID) values were rejected because they were too high"
        % cnt)

    logger.info("Saving EBA_1 data")
    fileNm = os.path.join(DATA_PATH, "analysis/EBA_1.csv")
    eba.df.to_csv(fileNm)

    # pickle the clipping ranges to be able to reuse them in step 3
    pickle.dump(rules, open(os.path.join(
        DATA_PATH, "analysis/EBA_1_clippers.p"), "wb"))
