import os
import pandas as pd
import numpy as np
import re
import logging

DATA_PATH = os.getenv('DATA_PATH')
if DATA_PATH is None:
    raise ValueError("DATA_PATH needs to be set")


def changeTrade(eba, rightba, wrongba, start=None, end=None, tol=1):
    logger = logging.getLogger("clean")
    ind = [True]*len(eba.df.index)
    if start is not None:
        ind &= eba.df.index > start
    if end is not None:
        ind &= eba.df.index < end
    ind_diff = ((
        (eba.df.loc[:, eba.KEY["ID"] % (rightba, wrongba)] + eba.df.loc[
            :, eba.KEY["ID"] % (wrongba, rightba)]).abs() > tol)
        | eba.df.loc[:, eba.KEY["ID"] % (wrongba, rightba)].isna())
    ind_diff &= ind
    eba.df.loc[ind_diff, eba.KEY["ID"] % (wrongba, rightba)] = (
        -eba.df.loc[ind_diff, eba.KEY["ID"] % (rightba, wrongba)])
    nchange = sum(ind_diff)
    if nchange > 0:
        logger.debug("Picking %s over %s for %d pts" % (
                rightba, wrongba, nchange))

    return eba


def fillNAs(eba, col, pad_limit=2, limit=3):
    logger = logging.getLogger("clean")
    ind_na = eba.df.loc[:, col].isna()
    nchange = ind_na.sum()
    if nchange > 0:
        logger.debug("%s: %d NA values to deal with" % (
                col, nchange))

    # first try pad for 2 hours
    eba.df.loc[:, col] = eba.df.loc[:, col].fillna(
        method='pad', limit=pad_limit)

    ind_na = eba.df.loc[:, col].isna()
    nchange = ind_na.sum()
    if nchange > 0:
        logger.debug("%s: replacing %d NA values with next/prev week" % (
                col, nchange))
        if nchange > 50:
            logger.warning("%s: replacing %d NA values with next/prev week" % (
                    col, nchange))
        for ts in eba.df.index[ind_na]:
            try:
                eba.df.loc[ts, col] = eba.df.loc[
                    ts-pd.Timedelta("%dH" % (7*24)), col]
            except KeyError:
                eba.df.loc[ts, col] = eba.df.loc[
                    ts+pd.Timedelta("%dH" % (7*24)), col]
            # If we didn't manage to get the right value, look forward
            cnt = 0
            while np.isnan(eba.df.loc[ts, col]):
                cnt += 1
                if cnt > limit:
                    logger.error("Tried to look %d times ahead for %s" %
                                 (limit, str(ts)))
                    raise ValueError("Can't fill this NaN")
                eba.df.loc[ts, col] = eba.df.loc[
                        ts+pd.Timedelta("%dH" % (cnt*7*24)), col]

    return eba


def removeOutliers(eba, col, start=None, end=None, thresh_u=None,
                   thresh_l=None, remove=True, limit=4):
    logger = logging.getLogger("clean")
    if start is None:
        start = pd.to_datetime("2016-01-01")
    if end is None:
        end = pd.to_datetime("2017-01-02")

    if (thresh_u is None) and (thresh_l is None):
        mu = eba.df.loc[start:end, col].mean()
        sigma = eba.df.loc[start:end, col].std()
        ind_out = np.abs(eba.df.loc[:, col]-mu) > (3*sigma)
    else:
        if thresh_l is None:
            thresh_l = -np.inf
        if thresh_u is None:
            thresh_u = +np.inf
        ind_out = (eba.df.loc[:, col] < thresh_l)
        ind_out |= (eba.df.loc[:, col] > thresh_u)

    ind_out &= (eba.df.index > start) & (eba.df.index < end)

    nchange = sum(ind_out)

    logger.debug("%s: %d outliers out of [%.2g, %.2g]" % (
            col, nchange, thresh_l, thresh_u))
    if nchange > 10:
        logger.warning("%s: %d outliers out of [%.2g, %.2g]" % (
            col, nchange, thresh_l, thresh_u))
    if remove:
        eba.df.loc[ind_out, col] = np.nan

    return eba


def applyFixes3(eba, log_level=logging.INFO):
    logger = logging.getLogger("clean")
    log_level_old = logger.level
    logger.setLevel(log_level)
    # special changes
    logger.debug("\tSpecial changes")

    eba = removeOutliers(eba, "EBA.NSB-FPC.ID.H", thresh_u=-5,
                         start=pd.to_datetime("2016-02-12"),
                         end=pd.to_datetime("2016-02-14"))
    eba = removeOutliers(eba, "EBA.NSB-FPC.ID.H", thresh_u=-5,
                         start=pd.to_datetime("2016-08-01"),
                         end=pd.to_datetime("2016-08-15"))
    eba = removeOutliers(eba, "EBA.NSB-FPL.ID.H", thresh_u=-5.,
                         start=pd.to_datetime("2016-08-01"),
                         end=pd.to_datetime("2016-08-15"))
    eba = removeOutliers(eba, "EBA.NSB-FPC.ID.H", thresh_u=-5,
                         start=pd.to_datetime("2016-10-07"),
                         end=pd.to_datetime("2016-10-08 03:00"))
    eba = removeOutliers(eba, "EBA.NSB-FPL.ID.H", thresh_u=-5.,
                         start=pd.to_datetime("2016-10-07"),
                         end=pd.to_datetime("2016-10-08 03:00"))
    for ba, ba2 in [("IID", "CISO"), ("PJM", "CPLW"), ("PJM", "DUK"),
                    ("PJM", "TVA"),
                    ("FPL", "SOCO"), ("SC", "SOCO"), ("SEPA", "SOCO"),
                    ("CPLW", "TVA"), ("DUK", "TVA"),
                    ("FMPP", "FPL"), ("FPC", "FPL"), ("JEA", "FPL"),
                    ("SEC", "FPL"),
                    ("CPLW", "DUK"), ("YAD", "DUK"), ("SEPA", "DUK"),
                    ("DOPD", "BPAT"), ("LDWP", "BPAT"),
                    ("FMPP", "FPC"), ("SEC", "FPC"),
                    ("LDWP", "PACE"),
                    ("LDWP", "NEVP"),
                    ("SEPA", "SC"),
                    ("FMPP", "TEC"),
                    ("SEC", "JEA"),
                    ("NSB", "FPC"), ("NSB", "FPL")]:

        eba = fillNAs(eba, eba.KEY["ID"] % (ba, ba2))
        eba = changeTrade(eba, ba, ba2, tol=0.)

    for field in ["D", "NG"]:
        eba = removeOutliers(eba, eba.get_cols(
            r="FPC", field=field)[0], thresh_l=200.)
        eba = removeOutliers(eba, eba.get_cols(
            r="TVA", field=field)[0], thresh_l=3000.)
        eba = removeOutliers(eba, eba.get_cols(r="PSCO", field=field)[
                             0], thresh_l=2000., thresh_u=10000.)
        eba = removeOutliers(eba, eba.get_cols(
            r="PACE", field=field)[0], thresh_u=10000.)
        eba = removeOutliers(
            eba, eba.get_cols(r="SRP", field=field)[0], thresh_l=1000.,
            thresh_u=5000., start=pd.to_datetime("2016-12-01"),
            end=pd.to_datetime("2016-12-31"))
        eba = removeOutliers(
            eba, eba.get_cols(r="SRP", field=field)[0], thresh_u=4900.,
            start=pd.to_datetime("2016-01-01"),
            end=pd.to_datetime("2016-05-01"))
        eba = removeOutliers(eba, eba.get_cols(
            r="LDWP", field=field)[0], thresh_l=100.)
        eba = removeOutliers(
            eba, eba.get_cols(r="IPCO", field=field)[0], thresh_l=800.,
            start=pd.to_datetime("2016-08-01"),
            end=pd.to_datetime("2016-08-05"))
        eba = removeOutliers(eba, eba.get_cols(
            r="EPE", field=field)[0], thresh_l=100.)
        eba = removeOutliers(eba, eba.get_cols(r="GVL", field=field)[
                             0], thresh_l=50., thresh_u=500.)

    eba = removeOutliers(
        eba, eba.get_cols(r="SCL", field="D")[0], thresh_l=500.,
        start=pd.to_datetime("2016-12-01"), end=pd.to_datetime("2016-12-31"))
    # WACM outliers
    eba = removeOutliers(eba, eba.get_cols(
        r="WACM", field="NG")[0], thresh_l=2500.)
    eba = removeOutliers(eba, eba.get_cols(
        r="WACM", field="D")[0], thresh_l=2000.)
    eba = removeOutliers(
        eba, eba.get_cols(r="WACM", field="D")[0], thresh_u=3000.,
        start=pd.to_datetime("2016-05-01"), end=pd.to_datetime("2016-05-31"))
    eba = removeOutliers(
        eba, eba.get_cols(r="WACM", field="NG")[0], thresh_l=3500.,
        start=pd.to_datetime("2016-01-01"), end=pd.to_datetime("2016-01-31"))
    eba = removeOutliers(
        eba, eba.get_cols(r="WACM", field="D")[0], thresh_u=4000.,
        start=pd.to_datetime("2016-01-01"), end=pd.to_datetime("2016-01-31"))

    for field in ["D", "NG", "TI"]:
        eba = fillNAs(eba, eba.get_cols(r="WACM", field=field)[0])

    # WALC outliers
    for field in ["D", "NG"]:
        eba = removeOutliers(
            eba, eba.get_cols(r="WALC", field=field)[0], thresh_u=2000.,
            start=pd.to_datetime("2016-01-01"),
            end=pd.to_datetime("2016-03-15"))
    eba = removeOutliers(eba, "EBA.WALC-LDWP.ID.H", thresh_l=100.)
    eba = fillNAs(eba, eba.KEY["ID"] % ("WALC", "LDWP"))
    eba = changeTrade(eba, "WALC", "LDWP", tol=0.)
    eba = removeOutliers(
        eba, eba.get_cols(r="WALC", field="D")[0], thresh_l=700.,
        start=pd.to_datetime("2016-02-17"), end=pd.to_datetime("2016-02-19"))
    eba = removeOutliers(
        eba, eba.get_cols(r="WALC", field="D")[0], thresh_l=200.,
        start=pd.to_datetime("2016-01-01"), end=pd.to_datetime("2016-05-01"))
    eba = removeOutliers(
        eba, eba.get_cols(r="WALC", field="D")[0], thresh_l=700.,
        start=pd.to_datetime("2016-03-01"), end=pd.to_datetime("2016-03-08"))

    eba = removeOutliers(
        eba, eba.get_cols(r="TPWR", field="D")[0], thresh_l=300.,
        start=pd.to_datetime("2016-10-15"), end=pd.to_datetime("2016-10-17"))
    eba = removeOutliers(eba, eba.get_cols(r="SEC", field="D")[
                         0], thresh_l=40., thresh_u=300.)

    # TIDC outliers
    for field in ["D", "NG"]:
        eba = removeOutliers(
            eba, eba.get_cols(r="TIDC", field=field)[0], thresh_l=50.,
            start=pd.to_datetime("2016-10-01"))
    eba = removeOutliers(
        eba, eba.get_cols(r="TIDC", field="D")[0], thresh_l=200., thresh_u=500,
        start=pd.to_datetime("2016-10-31"), end=pd.to_datetime("2016-11-01"))

    # WAUW outliers
    eba = removeOutliers(
        eba, "EBA.WAUW-SWPP.ID.H", thresh_l=5.,
        start=pd.to_datetime("2016-04-22"), end=pd.to_datetime("2016-05-08"))
    eba = fillNAs(eba, eba.KEY["ID"] % ("WAUW", "SWPP"))
    eba = changeTrade(eba, "WAUW", "SWPP", tol=0.)

    eba.df.loc[pd.to_datetime('2016-06-11 12:00:00'),
               eba.get_cols(r="WAUW", field="D")[0]] = 85.
    eba = removeOutliers(eba, eba.get_cols(r="WAUW", field="D")[
                         0], thresh_l=50., thresh_u=150.)

    # SEPA - when filling NaNs I now have some negative total trade - redo the
    # following from step 2:
    # Negative net trade - change SOCO so that negative net trade is zeroed out
    partners = eba.get_trade_partners("SEPA")
    ind_neg = eba.df.loc[
        :, [eba.KEY["ID"] % ("SEPA", ba2) for ba2 in partners]].sum(axis=1) < 0
    ind_na = eba.df.loc[:, eba.KEY["ID"] % ("SEPA", "SOCO")].isna()

    eba.df.loc[ind_neg & ind_na, eba.KEY["ID"] % ("SEPA", "SOCO")] = 0.
    eba.df.loc[ind_neg, eba.KEY["ID"] % ("SEPA", "SOCO")] -= eba.df.loc[
        ind_neg, [eba.KEY["ID"] % ("SEPA", ba2) for ba2 in partners]].sum(
            axis=1)
    eba = changeTrade(eba, "SEPA", "SOCO", tol=0.)

    # DEAA-SRP connection - there are very small zeros - set to 0.
    # GRIF-WALC connection - same
    for connection in ["EBA.GRIF-WALC.ID.H", "EBA.DEAA-SRP.ID.H"]:
        cnt_very_neg = (eba.df.loc[:, connection] < -10.).sum()
        if cnt_very_neg > 0:
            logger.error("%s: %d negative values" % (connection, cnt_very_neg))
        ind_neg = eba.df.loc[:, connection] < 0.
        eba.df.loc[ind_neg, connection] = 0.

    logger.debug("\t\tDone with special changes\n")

    logger.setLevel(log_level_old)
    return eba


def standardFixes(eba):
    ''' Fill NaNs, ID antisymmetric, TI = sum(ID)
    '''
    logger = logging.getLogger("clean")
    logger.info("\t\tEBA standard adjustments")
    # Same for all - added BAs here one at a time to check what is happening
    sorted_regions = [
        re.split(r"\.|-", el)[1] for el in
        eba.df.loc[:, eba.get_cols(r=eba.regions, field="D")]
        .sum().sort_values(ascending=False).index]

    for ba in sorted_regions:

        logger.debug("\tStandard changes for %s" % ba)
        partners = eba.get_trade_partners(ba)
        for ba2 in partners:
            eba = changeTrade(eba, ba2, ba, tol=0.)
        for field in ["D", "NG"]:
            eba = fillNAs(eba, eba.get_cols(r=ba, field=field)[0])
        eba.df.loc[:, eba.KEY["TI"] % ba] = eba.df.loc[
            :, [eba.KEY["ID"] % (ba, ba2) for ba2 in partners]].sum(axis=1)

    return eba


def egrid_adjust(eba):
    from load import EGRID
    logger = logging.getLogger("clean")
    logger.info("\t\tEBA adjusting to match eGRID")
    egrid_ba = EGRID(sheet_name='BA16')
    cols = [col for col in egrid_ba.df.columns if col not in ["BANAME", "BACODE"]]
    egrid_ba.df.loc[egrid_ba.df.BACODE == 'BPAT', cols] += egrid_ba.df.loc[
        egrid_ba.df.BACODE == 'CSTO', cols].values
    egrid_ba.df = egrid_ba.df.drop(egrid_ba.df.index[egrid_ba.df.BACODE == 'CSTO'])

    ba = egrid_ba.df.loc[:, ['BACODE', 'BANGENAN']]
    ba.set_index('BACODE', inplace=True)
    ba.sort_index(inplace=True)
    ba.columns = [col.replace('BA', '').replace('AN', '') for col in ba.columns]
    ba.fillna(0., inplace=True)
    # Drop extra columns
    ba = ba.drop([np.nan, 'AMPL', 'CEA', 'GRIS', 'HECO'])
    ba.head()

    elec = eba.df.loc[:, eba.get_cols(eba.regions, "NG")]
    elec.columns = [col.split(".")[1].split("-")[0] for col in elec.columns]
    elec = pd.DataFrame(elec.sum())
    elec.columns = ["NGEN"]

    diff = ba - elec
    exclude = ["CPLW", "HST", "NSB", "AZPS", "SRP",
               "DEAA", "GWA", "HGMA", "NBSO", "SEPA",
               "WWA", "SEC"]
    for bacode in diff.index:
        if bacode not in exclude:
            eba.df.loc[:, eba.get_cols(bacode, "NG")] += diff.loc[
                bacode, "NGEN"] / 8784
            
    return eba


def final_adjust(eba):
    '''
    Fix energy balance and make sure there are no negative values left.
    This is the very last step.
    '''
    logger = logging.getLogger("clean")
    logger.info("\t\tEBA final adjustments")
    # List of BAs for which we adjust demand - for all others adjust generation
    adjust_D = ["TEPC", "CPLW", "HST", "NSB"]
    adjust_NG = ["DEAA", "GWA", "HGMA", "NBSO", "SEPA", "WWA",
                 "PSEI", "GCPD", "SEC"]

    # Same for all - added BAs here one at a time to check what is happening
    sorted_regions = [
        re.split(r"\.|-", el)[1] for el in
        eba.df.loc[:, eba.get_cols(r=eba.regions, field="D")]
        .sum().sort_values(ascending=False).index]

    for ba in sorted_regions:

        if ba in adjust_NG:
            eba.df.loc[:, eba.get_cols(r=ba, field="NG")[0]] = (
                        eba.df.loc[:, eba.get_cols(r=ba, field="D")[0]]
                        + eba.df.loc[:, eba.get_cols(r=ba, field="TI")[0]])
        else:
            eba.df.loc[:, eba.get_cols(r=ba, field="D")[0]] = (
                eba.df.loc[:, eba.get_cols(r=ba, field="NG")[0]]
                - eba.df.loc[:, eba.get_cols(r=ba, field="TI")[0]])

    # Some of the BAs now have negative generation or demand for a few hours
    for ba in ["CHPD", "DOPD", "DUK", "EEI", "GRIF", "SPA", "YAD"]:
        ind_neg = eba.df.loc[:, eba.get_cols(r=ba, field="D")[0]] < 0
        eba.df.loc[ind_neg, eba.get_cols(r=ba, field="NG")[0]] += (
            1. - eba.df.loc[ind_neg, eba.get_cols(r=ba, field="D")[0]])
        eba.df.loc[ind_neg, eba.get_cols(r=ba, field="D")[0]] = 1.
    for ba in ["PGE", "SCL"]:
        ind_neg = eba.df.loc[:, eba.get_cols(r=ba, field="NG")[0]] < 0
        eba.df.loc[ind_neg, eba.get_cols(r=ba, field="D")[0]] += (
            1. - eba.df.loc[ind_neg, eba.get_cols(r=ba, field="NG")[0]])
        eba.df.loc[ind_neg, eba.get_cols(r=ba, field="NG")[0]] = 1.

    return eba


# def checkBA(eba, ba, tol=1e-2, log_level=logging.INFO):
#     '''
#     Sanity check function
#     '''
#     logger = logging.getLogger("clean")
#     log_level_old = logger.level
#     logger.setLevel(log_level)
#     logger.debug("Checking %s" % ba)
#     partners = eba.get_trade_partners(ba)
# 
#     # NaNs
#     for field in ["D", "NG", "TI"]:
#         ind_na = eba.df.loc[:, eba.get_cols(r=ba, field=field)[0]].isna()
#         cnt_na = ind_na.sum()
#         if cnt_na != 0:
#             logger.error("There are still %d nans for %s field %s" %
#                          (cnt_na, ba, field))
# 
#     for ba2 in partners:
#         cnt_na = eba.df.loc[:, eba.KEY["ID"] % (ba, ba2)].isna().sum()
#         if cnt_na != 0:
#             logger.error("There are still %d nans for %s-%s" %
#                          (cnt_na, ba, ba2))
# 
#     # TI+D == NG
#     res1 = eba.df.loc[:, eba.get_cols(r=ba, field="NG")[0]] - (
#             eba.df.loc[:, eba.get_cols(r=ba, field="D")[0]]
#             + eba.df.loc[:, eba.get_cols(r=ba, field="TI")[0]])
#     if (res1.abs() > tol).sum() != 0:
#         logger.error("%s: TI+D == NG violated" % ba)
# 
#     # TI == ID.sum()
#     res2 = (
#         eba.df.loc[:, eba.get_cols(r=ba, field="TI")[0]]
#         - eba.df.loc[:, [eba.KEY["ID"] % (ba, ba2) for ba2 in partners]].sum(
#             axis=1))
#     if (res2.abs() > tol).sum() != 0:
#         logger.error("%s: TI == ID.sum()violated" % ba)
# 
#     # ID[i,j] == -ID[j,i]
#     for ba2 in partners:
#         res3 = eba.df.loc[:, eba.KEY["ID"] %
#                           (ba, ba2)]+eba.df.loc[:, eba.KEY["ID"] % (ba2, ba)]
#         if (res3.abs() > tol).sum() != 0:
#             logger.error("%s-%s: ID[i,j] == -ID[j,i] violated" % (ba, ba2))
# 
#     # D and NG negative
#     for field in ["D", "NG"]:
#         ind_neg = eba.df.loc[:, eba.get_cols(r=ba, field=field)[0]] < 0
#         cnt_neg = ind_neg.sum()
#         if cnt_neg != 0:
#             logger.error("%s: there are %d <0 values for field %s" %
#                          (ba, cnt_neg, field))
#     logger.setLevel(log_level_old)


def EBA_3():
    '''
    What big changes can I make by hand?
    '''
    from load import BA_DATA
    logger = logging.getLogger('clean')
    logger.info("Starting EBA_3")

    eba = BA_DATA(step=2)

    eba = applyFixes3(eba)
    eba = standardFixes(eba)
    eba = egrid_adjust(eba)
    eba = final_adjust(eba)

    for ba in eba.regions:
        eba.checkBA(ba)

    logger.info("Saving EBA_3 data")
    fileNm = os.path.join(DATA_PATH, "analysis/EBA_3.csv")
    eba.df.to_csv(fileNm)
