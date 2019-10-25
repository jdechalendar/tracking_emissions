'''
AMPD step 2
'''

import os
import pandas as pd
import numpy as np
import logging
from load import AMPD, EGRID


DATA_PATH = os.getenv('DATA_PATH')
if DATA_PATH is None:
    raise ValueError("DATA_PATH needs to be set")


def AMPD_2():
    '''
    BA-level cleaning.
    Adjust AMPD data so that annual BA-level totals matches eGRID data. In this
    version, we use BA-level data only from eGRID to make the adjustment, and
    split the adjustment equally over all timesteps.
    '''
    logger = logging.getLogger('clean')
    logger.info("Starting AMPD_2")

    # Load AMPD data
    ampd = AMPD(step=1)

    # Load EGRID data
    egrid_ba = EGRID(sheet_name='BA16')
    egrid_plnt = EGRID(sheet_name='PLNT16')

    # Add BACODE field to ampd.df
    ampd.df.loc[:, "BACODE"] = ampd.df.ORISPL_CODE.map(
        dict(zip(egrid_plnt.df.ORISPL.values, egrid_plnt.df.BACODE.values)))

    # Absorb CSTO (1 plant) in BPAT
    ampd.df.loc[ampd.df.BACODE == 'CSTO', 'BACODE'] = 'BPAT'
    egrid_plnt.df.loc[egrid_plnt.df.BACODE == 'CSTO', 'BACODE'] = 'BPAT'
    cols = [col for col in egrid_ba.df.columns if col not in
            ["BANAME", "BACODE"]]
    egrid_ba.df.loc[egrid_ba.df.BACODE == 'BPAT', cols] += egrid_ba.df.loc[
        egrid_ba.df.BACODE == 'CSTO', cols].values
    egrid_ba.df = egrid_ba.df.drop(
        egrid_ba.df.index[egrid_ba.df.BACODE == 'CSTO'])

    cols = ["BACODE", "OP_DATE_TIME", "CO2", "SO2", "NOX"]
    ampd_ba = ampd.df.loc[:, cols].groupby(["BACODE", "OP_DATE_TIME"]).sum()
    ampd_ba.reset_index(inplace=True)

    # Change timestamps to UTC
    BA_to_tz = getTimezoneInfo()
    ampd_ba.loc[:, 'DATE_TIME_UTC'] = ampd_ba.OP_DATE_TIME
    for bacode in ampd_ba.BACODE.unique():
        ampd_ba.loc[ampd_ba.BACODE == bacode,
                    "DATE_TIME_UTC"] -= pd.DateOffset(hours=BA_to_tz[bacode])
    ampd_ba.drop(columns=['OP_DATE_TIME'], inplace=True)

    # Compute annual totals
    ampd_ba_ann = ampd_ba.groupby('BACODE').sum()

    ba = egrid_ba.df.loc[:, ['BACODE', 'BACO2AN', 'BASO2AN', 'BANOXAN']]
    ba.set_index('BACODE', inplace=True)
    ba.sort_index(inplace=True)
    ba.columns = [col.replace('BA', '').replace('AN', '')
                  for col in ba.columns]
    ba.fillna(0., inplace=True)
    ba.head()

    logger.info("Extra BA rows in the EGRID BA-level data:\n")
    logger.info(ba.index.difference(ampd_ba_ann.index))
    ba = ba.loc[ampd_ba_ann.index, :]
    logger.debug(ba.index.difference(ampd_ba_ann.index))

    timesteps = ampd_ba.loc[:, ['BACODE', 'DATE_TIME_UTC']].groupby(
        'BACODE').count()
    logger.debug((~(timesteps == 8784)).sum())

    # try to reconcile ampd with egrid unadjusted
    # note: could also do this with monthly data if available?
    print(ba.index.difference(ampd_ba_ann.index))
    diff = ba - ampd_ba_ann

    for bacode in diff.index.values:
        for col in ["CO2", "SO2", "NOX"]:
            ampd_ba.loc[ampd_ba.BACODE == bacode, col] += diff.loc[
                bacode, col] / 8784

    # Check that this happened as expected
    ampd_ba_ann = ampd_ba.groupby('BACODE').sum()

    ba = egrid_ba.df.loc[:, ['BACODE', 'BACO2AN', 'BASO2AN', 'BANOXAN']]
    ba.set_index('BACODE', inplace=True)
    ba.sort_index(inplace=True)
    ba.columns = [col.replace('BA', '').replace('AN', '')
                  for col in ba.columns]
    ba.fillna(0., inplace=True)
    ba.head()

    logger.debug("Extra BA rows in the EGRID BA-level data:\n")
    logger.debug(ba.index.difference(ampd_ba_ann.index))
    ba = ba.loc[ampd_ba_ann.index, :]
    logger.debug(ba.index.difference(ampd_ba_ann.index))

    diff = ampd_ba_ann - ba
    logger.debug(diff.describe())

    # Pivot dataframe before adding missing BAs
    ampd_ba_p = ampd_ba.pivot(index='DATE_TIME_UTC', columns='BACODE')

    # add missing BAs
    ba = egrid_ba.df.loc[:, ['BACODE', 'BACO2AN', 'BASO2AN', 'BANOXAN']]
    ba.set_index('BACODE', inplace=True)
    ba.sort_index(inplace=True)
    ba.columns = [col.replace('BA', '').replace('AN', '')
                  for col in ba.columns]
    ba.fillna(0., inplace=True)
    ba.head()

    missing_bas = ba.index.difference(ampd_ba_ann.index)
    logger.debug("Extra BA rows in the EGRID BA-level data:\n")
    logger.debug(missing_bas)
    for poll in ["CO2", "SO2", "NOX"]:
        for bacode in missing_bas:
            if bacode is not np.nan:
                ampd_ba_p[poll, bacode] = ba.loc[bacode, poll] / len(ampd_ba_p)

    # Final sanity check
    # Stack the columns back for the sanity check
    ampd_ba_sanity = ampd_ba_p.stack().reset_index()

    # Recalculate AMPD annual sums
    ampd_ba_ann = ampd_ba_sanity.groupby('BACODE').sum()
    logger.debug(ba.index.difference(ampd_ba_ann.index))

    # Don't take the NaN row for the diff
    diff = ba.loc[ampd_ba_ann.index, :] - ampd_ba_ann
    logger.debug("EGRID BA level vs AMPD adjusted")
    logger.debug("Diff:")
    logger.debug(diff.describe())
    logger.debug("NA row in egrid BA-level")
    logger.debug(ba.loc[[np.nan], ])

    # Rename columns
    ampd_ba_p.columns = ['_'.join(col).strip() for col in
                         ampd_ba_p.columns.values]

    # Save data
    logger.info("AMPD_2 - saving data")
    fileNm_out = os.path.join(DATA_PATH, 'analysis', 'AMPD_2.csv')
    ampd_ba_p.to_csv(fileNm_out)


def getTimezoneInfo():
    fileNm = os.path.join(DATA_PATH, "raw", "ba_tz.xlsx")
    BA_to_tz = pd.read_excel(fileNm)

    def get_offset(tz):
        if tz == "Pacific":
            return -8
        elif tz == "Central":
            return -6
        elif tz == "Arizona":
            return -7
        elif tz == "Eastern":
            return -5
        elif tz == "Mountain":
            return -7
        else:
            return 0
    BA_to_tz["offset"] = BA_to_tz.Timezone.apply(get_offset)
    BA_to_tz = dict(zip(BA_to_tz.BACODE, BA_to_tz.offset))
    return BA_to_tz
