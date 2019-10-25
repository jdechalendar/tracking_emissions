import os
import pandas as pd
import numpy as np
import logging
from load import BA_DATA

DATA_PATH = os.getenv('DATA_PATH')
if DATA_PATH is None:
    raise ValueError("DATA_PATH needs to be set")


def changeTrade(eba, rightba, wrongba, start=None, end=None, tol=1):
    '''
    Helper function to reconcile two trades that do not agree.
    '''
    logger = logging.getLogger('clean')
    ind = [True]*len(eba.df.index)
    if start is not None:
        ind &= eba.df.index > start
    if end is not None:
        ind &= eba.df.index < end
    ind_diff = (
        ((eba.df.loc[:, eba.KEY["ID"] % (rightba, wrongba)] + eba.df.loc[
            :, eba.KEY["ID"] % (wrongba, rightba)]).abs() > tol)
        | eba.df.loc[:, eba.KEY["ID"] % (wrongba, rightba)].isna())
    ind_diff &= ind
    eba.df.loc[ind_diff, eba.KEY["ID"] % (wrongba, rightba)] = (
        -eba.df.loc[ind_diff, eba.KEY["ID"] % (rightba, wrongba)])

    logger.debug("Picking %s over %s for %d pts" %
                 (rightba, wrongba, sum(ind_diff)))

    return eba


def removeTradeOutliers(eba, ba, ba2, start=None, end=None, thresh_u=None,
                        thresh_l=None, remove=True, limit=4):
    '''
    Helper function to remove outliers from trade data.
    '''
    logger = logging.getLogger('clean')
    if start is None:
        start = pd.to_datetime("2016-01-01")
    if end is None:
        end = pd.to_datetime("2017-01-02")

    if (thresh_u is None) and (thresh_l is None):
        mu = eba.df.loc[start:end, eba.KEY["ID"] % (ba, ba2)].mean()
        sigma = eba.df.loc[start:end, eba.KEY["ID"] % (ba, ba2)].std()
        ind_out = np.abs(eba.df.loc[:, eba.KEY["ID"] %
                                    (ba, ba2)]-mu) > (3*sigma)
    else:
        if thresh_l is None:
            thresh_l = -np.inf
        if thresh_u is None:
            thresh_u = +np.inf
        ind_out = eba.df.loc[:, eba.KEY["ID"] % (ba, ba2)] < thresh_u
        ind_out &= eba.df.loc[:, eba.KEY["ID"] % (ba, ba2)] > thresh_l

    ind_out &= (eba.df.index > start) & (eba.df.index < end)

    logger.debug("%s->%s: %d outliers" % (ba, ba2, sum(ind_out)))
    if remove:
        eba.df.loc[ind_out, eba.KEY["ID"] % (ba, ba2)] = np.nan
        newstart = start-pd.Timedelta('1h')
        eba.df.loc[newstart:end, eba.KEY["ID"] % (ba, ba2)] = eba.df.loc[
            newstart:end, eba.KEY["ID"] % (ba, ba2)].fillna(method='pad',
                                                            limit=limit)
        eba = changeTrade(eba, ba, ba2, start=start, end=end)

    return eba


def applyFixes(eba):
    '''
    A first round of fixes. The general strategy was to go after the most
    obvious errors first.
    '''
    logger = logging.getLogger('clean')
    
    logger.debug("TEPC fixes")
    # 7h time shift for TEPC
    ba = "TEPC"
    ind = eba.df.index > pd.to_datetime("2016-05-15")
    for ba2 in eba.get_trade_partners(ba):
        eba.df.loc[ind, eba.KEY["ID"] % (ba, ba2)] = eba.df.loc[
            ind, eba.KEY["ID"] % (ba, ba2)].shift(-7).values
    eba.df.loc[ind, eba.KEY["TI"] % "TEPC"] = eba.df.loc[
        ind, eba.KEY["TI"] % "TEPC"].shift(-7).values
    eba.df.loc[ind, eba.KEY["D"] % "TEPC"] = eba.df.loc[
        ind, eba.KEY["D"] % "TEPC"].shift(-7).values
    eba.df.loc[ind, eba.KEY["NG"] % "TEPC"] = eba.df.loc[
        ind, eba.KEY["NG"] % "TEPC"].shift(-7).values

    # Take PNM values after May 1st
    eba = changeTrade(eba, "PNM", "TEPC", pd.to_datetime("2016-05-01"))
    eba = changeTrade(eba, "WALC", "TEPC", pd.to_datetime("2016-07-22"))
    eba = changeTrade(eba, "TEPC", "AZPS", pd.to_datetime("2016-07-22"))

    # Clean TEPC NaNs
    for ba2 in eba.get_trade_partners(ba):
        ind = eba.df.loc[:, eba.KEY["ID"] % (ba, ba2)].isna()

        logger.debug(("Replacing %d NaNs from %s with %s") %
                     (ind.sum(), ba, ba2))
        eba.df.loc[ind, eba.KEY["ID"] % (ba, ba2)] = - eba.df.loc[
            ind, eba.KEY["ID"] % (ba2, ba)]

    eba = changeTrade(eba, "WALC", "TEPC", pd.to_datetime("2016-01-01"))
    eba = changeTrade(eba, "SRP", "TEPC", pd.to_datetime("2016-01-01"))
    eba = changeTrade(eba, "AZPS", "TEPC", pd.to_datetime("2016-05-09"),
                      pd.to_datetime("2016-05-17"))
    eba = changeTrade(eba, "EPE", "TEPC", pd.to_datetime("2016-05-09"),
                      pd.to_datetime("2016-05-17"))
    eba = changeTrade(eba, "AZPS", "TEPC", pd.to_datetime("2016-01-01"),
                      pd.to_datetime("2016-02-01"))
    eba = changeTrade(eba, "EPE", "TEPC", pd.to_datetime("2016-01-01"),
                      pd.to_datetime("2016-02-01"))
    eba = changeTrade(eba, "PNM", "TEPC", pd.to_datetime("2016-01-17"),
                      pd.to_datetime("2016-01-25"))
    eba = changeTrade(eba, "PNM", "TEPC", pd.to_datetime("2016-02-05"),
                      pd.to_datetime("2016-02-09"))
    eba = changeTrade(eba, "EPE", "TEPC", pd.to_datetime("2016-02-05"),
                      pd.to_datetime("2016-02-09"))
    eba = changeTrade(eba, "AZPS", "TEPC", pd.to_datetime("2016-02-05"),
                      pd.to_datetime("2016-02-09"))
    eba = changeTrade(eba, "TEPC", "AZPS", pd.to_datetime("2016-02-25"),
                      pd.to_datetime("2016-02-26"))

    # Change TI to be more like ID
    eba.df.loc[:, eba.get_cols(r=ba, field="TI")[0]] = eba.df.loc[
                :, [eba.KEY["ID"] % (ba, ba2) for ba2 in
                    eba.get_trade_partners(ba)]].sum(axis=1)

    logger.debug("TVA fixes")
    ba = "TVA"
    partners = eba.get_trade_partners(ba)
    for ba2 in ["LGEE", "MISO", "PJM"]:
        eba.df.loc[:, eba.KEY["ID"] % (ba, ba2)] = - eba.df.loc[
            :, eba.KEY["ID"] % (ba2, ba)]
    eba = changeTrade(eba, "TVA", "SOCO", pd.to_datetime("2016-01-22"),
                      pd.to_datetime("2016-01-23"))
    eba = changeTrade(eba, "TVA", "SOCO", pd.to_datetime("2016-03-04"),
                      pd.to_datetime("2016-03-05"))
    eba = changeTrade(eba, "TVA", "SOCO", pd.to_datetime("2016-04-30"),
                      pd.to_datetime("2016-05-01"))
    eba = changeTrade(eba, "TVA", "SOCO", pd.to_datetime("2016-11-28"))

    logger.debug("CISO fixes")
    # 1. CISO-IID
    # If I look at the difference between ID.sum() and TI after September
    # (when there is no shift in time),
    # the following operation makes the difference noticeably smaller
    eba.df.loc[:, eba.KEY["ID"] % ("CISO", "IID")] = -eba.df.loc[
        :, eba.KEY["ID"] % ("IID", "CISO")]
    # 1. CISO-AZPS
    # CISO data is incorrect between June 25th and July 8th
    ind = (eba.df.index > pd.to_datetime("2016-06-25")) & (
        eba.df.index < pd.to_datetime("2016-07-08"))
    eba.df.loc[ind, eba.KEY["ID"] % ("CISO", "AZPS")] = - eba.df.loc[
        ind, eba.KEY["ID"] % ("AZPS", "CISO")]
    # ... but correct in the following windows:
    # For all data before 2019-09-13, it looks like TI data for CISO is
    # shifted forward 1H
    # Assume the same needs to be done for D and NG
    ind = eba.df.index < pd.to_datetime("2016-09-13")
    eba.df.loc[ind, eba.KEY["TI"] % "CISO"] = eba.df.loc[
        ind, eba.KEY["TI"] % "CISO"].shift(-1).values
    eba.df.loc[ind, eba.KEY["D"] % "CISO"] = eba.df.loc[
        ind, eba.KEY["D"] % "CISO"].shift(-1).values
    eba.df.loc[ind, eba.KEY["NG"] % "CISO"] = eba.df.loc[
        ind, eba.KEY["NG"] % "CISO"].shift(-1).values

    logger.debug("AZPS fixes")
    ba = "AZPS"
    for ba2 in ["CISO", "WALC", "GRMA", "SRP", "PACE", "PNM", "WACM",
                "IID", "LDWP", "TEPC"]:
        eba = changeTrade(eba, ba2, ba, pd.to_datetime("2016-01-01"),
                          pd.to_datetime("2016-01-17"))
    for ba2 in ["CISO", "WALC", "GRMA", "SRP", "WACM", "PACE", "PNM"]:
        eba = changeTrade(eba, ba2, ba, pd.to_datetime("2016-07-21"),
                          pd.to_datetime("2016-07-23"))
    for ba2 in ["CISO", "WALC", "GRMA", "SRP", "WACM", "PACE", "PNM",
                "IID"]:
        eba = changeTrade(eba, ba2, ba, pd.to_datetime("2016-08-18"),
                          pd.to_datetime("2016-08-19"))
    for ba2 in ["CISO", "WALC", "GRMA", "SRP", "WACM", "PACE", "PNM",
                "IID"]:
        eba = changeTrade(eba, ba2, ba, pd.to_datetime("2016-10-20"),
                          pd.to_datetime("2016-10-22"))
    for ba2 in ["CISO", "SRP", "WACM", "PACE", "WALC", "GRMA", "PNM",
                "IID"]:
        eba = changeTrade(eba, ba2, ba, pd.to_datetime("2016-02-25"),
                          pd.to_datetime("2016-02-26"))
    for ba2 in ["CISO", "SRP", "WACM", "PACE", "WALC", "GRMA", "PNM",
                "IID"]:
        eba = changeTrade(eba, ba2, ba, pd.to_datetime("2016-09-16"),
                          pd.to_datetime("2016-09-17"))
    eba = changeTrade(eba, "PACE", ba, pd.to_datetime("2016-02-22"),
                      pd.to_datetime("2016-02-25"))
    eba = changeTrade(eba, "AZPS", "WALC", pd.to_datetime("2016-02-18"),
                      pd.to_datetime("2016-02-19"))
    eba = changeTrade(eba, "AZPS", "SRP", pd.to_datetime("2016-07-30"),
                      pd.to_datetime("2016-07-31"))
    eba = changeTrade(eba, "PACE", "AZPS", pd.to_datetime("2016-06-30"),
                      pd.to_datetime("2016-07-01"))
    eba = changeTrade(eba, "AZPS", "WACM", pd.to_datetime("2016-05-17"),
                      pd.to_datetime("2016-05-18"))

    # Missing points for the AZPS-LDWP connection
    eba.df.loc[[pd.to_datetime("2016-07-22 15:00"),
                pd.to_datetime("2016-07-22 16:00")],
               eba.KEY["ID"] % ("AZPS", "LDWP")] = eba.df.loc[
        [pd.to_datetime("2016-07-22 14:00")],
        eba.KEY["ID"] % ("AZPS", "LDWP")].values[0]
    eba.df.loc[[pd.to_datetime("2016-08-18 22:00")],
               eba.KEY["ID"] % ("AZPS", "LDWP")] = eba.df.loc[
        [pd.to_datetime("2016-08-18 21:00")],
        eba.KEY["ID"] % ("AZPS", "LDWP")].values[0]
    eba.df.loc[[pd.to_datetime("2016-10-21 00:00")],
               eba.KEY["ID"] % ("AZPS", "LDWP")] = eba.df.loc[
        [pd.to_datetime("2016-10-20 23:00")],
        eba.KEY["ID"] % ("AZPS", "LDWP")].values[0]

    logger.debug("BANC fixes")
    eba.df.loc[:, eba.KEY["ID"] % ("BANC", "CISO")] = -eba.df.loc[
        :, eba.KEY["ID"] % ("CISO", "BANC")]

    eba = changeTrade(eba, "BANC", "TIDC", pd.to_datetime("2016-01-25"),
                      pd.to_datetime("2016-01-27"))
    eba = changeTrade(eba, "BANC", "TIDC", pd.to_datetime("2016-07-18"),
                      pd.to_datetime("2016-07-19"))
    # Need to adjust TI as a consequence
    ba = "BANC"
    partners = eba.get_trade_partners(ba)
    eba.df.loc[:, eba.get_cols(r=ba, field="TI")[0]] = eba.df.loc[
        :, [eba.KEY["ID"] % (ba, ba2) for ba2 in partners]].sum(axis=1)
    # Assume this changes NG
    eba.df.loc[:, eba.get_cols(r=ba, field="NG")[0]] = (
        eba.df.loc[:, eba.get_cols(r=ba, field="D")[0]]
        + eba.df.loc[:, eba.get_cols(r=ba, field="TI")[0]])

    logger.debug("OVEC fixes")
    ba = "OVEC"

    partners = eba.get_trade_partners(ba)
    eba.df.loc[:, eba.KEY["ID"] % ("OVEC","LGEE")] = - eba.df.loc[
                :, eba.KEY["ID"] % ("LGEE","OVEC")]

    ba2 = "PJM"
    ind = eba.df.loc[:, eba.KEY["ID"] % (ba,ba2)].isna()
    eba.df.loc[ind, eba.KEY["ID"] % (ba,ba2)] = - eba.df.loc[ind, eba.KEY["ID"] % (ba2,ba)]
    changeTrade(eba, "OVEC", "PJM", start=pd.to_datetime("2016-05-27"))

    set_to_nan = eba.df.loc[:, eba.KEY["ID"] % (ba,ba2)].abs() < 10
    ind_time = (eba.df.index<pd.to_datetime("2016-10-01"))
    ind = set_to_nan & ind_time
    eba.df.loc[ind, eba.KEY["ID"] % (ba,ba2)] = np.nan
    eba.df.loc[ind_time, eba.KEY["ID"] % (ba,ba2)] = eba.df.loc[ind_time, eba.KEY["ID"] % (ba,ba2)].fillna(method='pad', limit=14)

    ind = (eba.df.index > pd.to_datetime("2016-03-13")) & (eba.df.index < pd.to_datetime("2016-03-17"))
    eba.df.loc[ind, eba.KEY["ID"] % ("PJM","OVEC")] = 0.
    changeTrade(eba, "OVEC", "PJM", start=pd.to_datetime("2016-03-13"), end=pd.to_datetime("2016-03-17"))

    changeTrade(eba, "OVEC", "PJM", start=pd.to_datetime("2016-05-17"), end=pd.to_datetime("2016-05-19"))
    changeTrade(eba, "OVEC", "PJM", start=pd.to_datetime("2016-03-01"), end=pd.to_datetime("2016-07-01"))

    # Dealing with the data after 20161028 - we use the median carbon intensity for the rest of the year and carbon data
    fileNm = os.path.join(DATA_PATH, "analysis/AMPD_2.csv")
    co2_ovec = pd.read_csv(fileNm, index_col=0, parse_dates=['DATE_TIME_UTC'],
                           infer_datetime_format=True, usecols=['DATE_TIME_UTC', "CO2_OVEC"])
    ind = eba.df.index > pd.to_datetime("20161028")
    eba.df.loc[ind, eba.get_cols(r=ba, field="NG")[0]] = (
        1.017 * co2_ovec[co2_ovec.index > pd.to_datetime("20161028")]["CO2_OVEC"])
    eba.df.loc[ind, eba.KEY["ID"] % ("OVEC", "PJM")] = (
        -eba.df.loc[ind, eba.KEY["ID"] % ("OVEC", "LGEE")]
        + eba.df.loc[ind, eba.get_cols(r=ba, field="NG")[0]])

    changeTrade(eba, "OVEC", "PJM", tol=0.)

    # 3. Make TI equal ID.sum()
    eba.df.loc[:, eba.get_cols(r=ba, field="TI")[0]] = eba.df.loc[
        :, [eba.KEY["ID"] % (ba,ba2) for ba2 in eba.get_trade_partners(ba)]].sum(axis=1)
    # # 4. For the missing demand and generation values: use median demand, and then use TI+D == NG
    ind = eba.df.loc[:, eba.get_cols(r=ba, field="D")[0]].isna()
    eba.df.loc[ind, eba.get_cols(r=ba, field="D")[0]] = eba.df.loc[
        ~ind, eba.get_cols(r=ba, field="D")[0]].median()
    eba.df.loc[:, eba.get_cols(r=ba, field="NG")[0]] = (
        eba.df.loc[:, eba.get_cols(r=ba, field="D")[0]]
        + eba.df.loc[:, eba.get_cols(r=ba, field="TI")[0]])

    logger.debug("BPAT fixes")
    eba = changeTrade(eba, "PGE", "BPAT")
    eba = changeTrade(eba, "AVA", "BPAT")
    eba = changeTrade(eba, "BPAT", "DOPD", pd.to_datetime("2016-04-24"),
                      pd.to_datetime("2016-04-25"))
    eba = changeTrade(eba, "BPAT", "DOPD", pd.to_datetime("2016-11-06"),
                      pd.to_datetime("2016-11-08"))
    eba = changeTrade(eba, "BPAT", "CHPD", pd.to_datetime("2016-11-06"),
                      pd.to_datetime("2016-11-08"))
    eba = changeTrade(eba, "BPAT", "GCPD", pd.to_datetime("2016-11-06"),
                      pd.to_datetime("2016-11-08"))
    eba = changeTrade(eba, "BPAT", "NWMT", pd.to_datetime("2016-11-29"),
                      pd.to_datetime("2016-12-03"))
    eba = changeTrade(eba, "BPAT", "GCPD", pd.to_datetime("2016-11-29"),
                      pd.to_datetime("2016-12-06"))
    eba = changeTrade(eba, "BPAT", "SCL", pd.to_datetime("2016-12-13"),
                      pd.to_datetime("2016-12-25"))
    eba = changeTrade(eba, "BPAT", "IPCO")
    eba = changeTrade(eba, "BPAT", "GCPD")

    logger.debug("WALC fixes")
    eba = changeTrade(
        eba, "WACM", "WALC", start=pd.to_datetime("2016-02-18"),
        end=pd.to_datetime("2016-02-19"))
    eba = changeTrade(
        eba, "CISO", "WALC", start=pd.to_datetime("2016-02-18"),
        end=pd.to_datetime("2016-02-19"))
    eba = changeTrade(
        eba, "SRP", "WALC", start=pd.to_datetime("2016-02-18"),
        end=pd.to_datetime("2016-02-19"))
    eba = changeTrade(
        eba, "WALC", "WACM", start=pd.to_datetime("2016-05-17"),
        end=pd.to_datetime("2016-05-18"))

    logger.debug("SWPP fixes")
    eba = changeTrade(eba, "AECI", "SWPP", pd.to_datetime("2016-11-17"),
                      pd.to_datetime("2016-11-21"))
    eba = changeTrade(eba, "SPA", "SWPP", pd.to_datetime("2016-11-17"),
                      pd.to_datetime("2016-11-21"))
    eba = changeTrade(eba, "SWPP", "WAUW", pd.to_datetime("2016-07-27"),
                      pd.to_datetime("2016-07-29"))
    eba = changeTrade(eba, "SWPP", "WAUW", pd.to_datetime("2016-12-25"),
                      pd.to_datetime("2016-12-27"))
    eba = changeTrade(eba, "SWPP", "WACM", pd.to_datetime("2016-03-13"),
                      pd.to_datetime("2016-03-14"))
    eba = changeTrade(eba, "SWPP", "WACM", pd.to_datetime("2016-05-17"),
                      pd.to_datetime("2016-05-18"))
    eba = changeTrade(eba, "MISO", "SWPP")

    logger.debug("MISO fixes")
    eba = changeTrade(eba, "PJM", "MISO")
    eba = changeTrade(eba, "MISO", "SOCO")
    eba = changeTrade(eba, "AECI", "MISO", pd.to_datetime("2016-03-22"),
                      pd.to_datetime("2016-03-23"))
    eba = changeTrade(eba, "AECI", "MISO", pd.to_datetime("2016-05-11"),
                      pd.to_datetime("2016-05-12"))
    eba = changeTrade(eba, "AECI", "MISO", pd.to_datetime("2016-08-30"),
                      pd.to_datetime("2016-09-02"))
    eba = changeTrade(eba, "AECI", "MISO", pd.to_datetime("2016-11-15"),
                      pd.to_datetime("2016-11-30"))
    eba = changeTrade(eba, "MISO", "SPA", pd.to_datetime("2016-12-25"))
    eba = changeTrade(eba, "MISO", "LGEE", pd.to_datetime("2016-12-10"),
                      pd.to_datetime("2016-12-14"))
    eba = changeTrade(eba, "MISO", "SPA", pd.to_datetime("2016-02-03"),
                      pd.to_datetime("2016-02-04"))
    eba = changeTrade(eba, "AECI", "MISO")

    logger.debug("PJM fixes")
    eba = changeTrade(eba, "PJM", "DUK", pd.to_datetime("2016-07-31"),
                      pd.to_datetime("2016-08-01"))
    for ba2 in ["CPLE", "NYIS", "LGEE"]:
        eba = changeTrade(eba, ba2, "PJM", pd.to_datetime("2016-03-13"),
                          pd.to_datetime("2016-03-15"))
    eba = changeTrade(eba, "NYIS", "PJM", pd.to_datetime("2016-05-17"),
                      pd.to_datetime("2016-05-29"))
    eba = changeTrade(eba, "NYIS", "PJM", pd.to_datetime("2016-11-01"),
                      pd.to_datetime("2016-11-08"))
    eba = changeTrade(eba, "PJM", "CPLE")
    eba = changeTrade(eba, "NYIS", "PJM")
    eba = changeTrade(eba, "LGEE", "PJM")
    eba = changeTrade(eba, "DUK", "PJM")

    logger.debug("SEPA fixes")
    ba = "SEPA"
    partners = eba.get_trade_partners("SEPA")
    # Try to infer missing data from partners
    for ba2 in partners:
        ind = eba.df.loc[:, eba.KEY["ID"] % (ba, ba2)].isna()
        eba.df.loc[ind, eba.KEY["ID"] % (ba, ba2)] = - eba.df.loc[
            ind, eba.KEY["ID"] % (ba2, ba)]
    ind = eba.df.loc[:, eba.KEY["ID"] % ("SOCO", "SEPA")].isna()
    eba.df.loc[ind, eba.KEY["ID"] % ("SOCO", "SEPA")] = - eba.df.loc[
        ind, eba.KEY["ID"] % ("SEPA", "SOCO")]

    eba = changeTrade(eba, "SEPA", "SC")
    eba = changeTrade(eba, "SEPA", "DUK")
    eba = changeTrade(eba, "SEPA", "SCEG")
    # Negative net trade - change SOCO so that negative net trade is zeroed
    # out
    ind_neg = eba.df.loc[:, [eba.KEY["ID"] % ("SEPA", ba2) for ba2 in
                             partners]].sum(axis=1) < 0.
    ind_na = eba.df.loc[:, eba.KEY["ID"] % ("SEPA", "SOCO")].isna()

    eba.df.loc[ind_neg & ind_na, eba.KEY["ID"] % ("SEPA", "SOCO")] = 0.
    eba.df.loc[ind_neg, eba.KEY["ID"] % ("SEPA", "SOCO")] -= eba.df.loc[
        ind_neg, [eba.KEY["ID"] % ("SEPA", ba2) for ba2 in partners]].sum(
        axis=1)
    eba = changeTrade(eba, "SEPA", "SOCO")

    # TI is ID.sum()
    eba.df.loc[:, eba.get_cols(r=ba, field="TI")[0]] = eba.df.loc[
        :, [eba.KEY["ID"] % (ba, ba2) for ba2 in partners]].sum(axis=1)
    # Assume this changes NG
    eba.df.loc[:, eba.get_cols(r=ba, field="NG")[0]] = (
        eba.df.loc[:, eba.get_cols(r=ba, field="D")[0]]
        + eba.df.loc[:, eba.get_cols(r=ba, field="TI")[0]])

    ba = "GRMA"
    logger.debug("GRMA fixes")
    eba.df.loc[:, eba.get_cols(r=ba, field="TI")[0]] = eba.df.loc[
        :, eba.get_cols(r=ba, field="NG")[0]]
    eba.df.loc[:, eba.KEY["ID"] % ("GRMA", "AZPS")] = eba.df.loc[
        :, eba.get_cols(r=ba, field="TI")[0]]
    eba = changeTrade(eba, "GRMA", "AZPS", tol=0.)

    ba = "GWA"
    logger.debug("GWA fixes")
    eba = changeTrade(eba, "NWMT", "GWA", tol=0.)
    eba.df.loc[:, eba.KEY["ID"] % ("GWA", "NWMT")] = eba.df.loc[
        :, eba.KEY["ID"] % ("GWA", "NWMT")].apply(lambda x: max(x, 0))
    eba = changeTrade(eba, "GWA", "NWMT", tol=0.)
    eba.df.loc[:, eba.get_cols(r=ba, field="TI")[0]] = eba.df.loc[
        :, eba.KEY["ID"] % ("GWA", "NWMT")]
    eba.df.loc[:, eba.get_cols(r=ba, field="NG")[0]] = eba.df.loc[
        :, eba.get_cols(r=ba, field="TI")[0]]

    ba = "WWA"
    logger.debug("GWA fixes")
    eba = changeTrade(eba, "NWMT", "WWA", tol=0.)
    eba.df.loc[:, eba.KEY["ID"] % ("WWA", "NWMT")] = eba.df.loc[
        :, eba.KEY["ID"] % ("WWA", "NWMT")].apply(lambda x: max(x, 0))
    eba = changeTrade(eba, "WWA", "NWMT", tol=0.)
    eba.df.loc[:, eba.get_cols(r=ba, field="TI")[0]] = eba.df.loc[
        :, eba.KEY["ID"] % ("WWA", "NWMT")]
    eba.df.loc[:, eba.get_cols(r=ba, field="NG")[0]] = eba.df.loc[
        :, eba.get_cols(r=ba, field="TI")[0]]

    ba = "HGMA"
    logger.debug("HGMA fixes")
    eba.df.loc[:, eba.get_cols(r=ba, field="TI")[0]] = eba.df.loc[
        :, eba.get_cols(r=ba, field="NG")[0]]
    eba.df.loc[:, eba.KEY["ID"] % ("HGMA", "SRP")] = eba.df.loc[
        :, eba.get_cols(r=ba, field="TI")[0]]
    eba = changeTrade(eba, "HGMA", "SRP", tol=0.)

    logger.debug("YAD fixes")
    ba = "YAD"
    partners = eba.get_trade_partners(ba)
    # Try to infer missing data from partners
    for ba2 in partners:
        ind = eba.df.loc[:, eba.KEY["ID"] % (ba, ba2)].isna()
        eba.df.loc[ind, eba.KEY["ID"] % (ba, ba2)] = - eba.df.loc[
            ind, eba.KEY["ID"] % (ba2, ba)]
    eba = changeTrade(eba, "DUK", "YAD", tol=0.)
    eba = changeTrade(eba, "CPLE", "YAD", tol=0.)

    # Negative net trade - change DUK so that negative net trade is zeroed
    # out
    ind_neg = eba.df.loc[:, [eba.KEY["ID"] % (ba, ba2) for ba2 in
                             partners]].sum(axis=1) < 0.
    ind_na = eba.df.loc[:, eba.KEY["ID"] % (ba, "DUK")].isna()

    eba.df.loc[ind_neg & ind_na, eba.KEY["ID"] % (ba, "DUK")] = 0.
    eba.df.loc[ind_neg, eba.KEY["ID"] % (ba, "DUK")] -= eba.df.loc[
        ind_neg, [eba.KEY["ID"] % (ba, ba2) for ba2 in partners]].sum(
        axis=1)
    eba = changeTrade(eba, ba, "DUK", tol=0.)

    # TI is ID.sum()
    eba.df.loc[:, eba.get_cols(r=ba, field="TI")[0]] = eba.df.loc[
        :, [eba.KEY["ID"] % (ba, ba2) for ba2 in partners]].sum(axis=1)
    # Assume this changes NG
    eba.df.loc[:, eba.get_cols(r=ba, field="NG")[0]] = (
        eba.df.loc[:, eba.get_cols(r=ba, field="D")[0]]
        + eba.df.loc[:, eba.get_cols(r=ba, field="TI")[0]])

    logger.debug("DUK fixes")
    ba = "DUK"
    eba = changeTrade(eba, "SOCO", "DUK", pd.to_datetime("2016-11-10"))

    ind_time = (eba.df.index > pd.to_datetime("2016-11-28")) & (
        eba.df.index < pd.to_datetime("2016-12-03"))
    ind_na = eba.df.loc[:, eba.KEY["ID"] % ("SOCO", "DUK")].abs() < 10.

    ind_na &= ind_time

    eba.df.loc[ind_na, eba.KEY["ID"] % ("SOCO", "DUK")] = np.nan
    eba.df.loc[ind_time, eba.KEY["ID"] % ("SOCO", "DUK")] = eba.df.loc[
        ind_time, eba.KEY["ID"] % ("SOCO", "DUK")].fillna(
        method="pad", limit=30)
    eba = changeTrade(eba, "SOCO", "DUK", pd.to_datetime("2016-11-10"))

    for ba2 in ["SCEG", "CPLW", "SC"]:
        eba = changeTrade(eba, ba2, "DUK", pd.to_datetime("2016-12-07"),
                          pd.to_datetime("2016-12-09"))

    eba = changeTrade(eba, "SCEG", "DUK", pd.to_datetime("2015-07-11"),
                      pd.to_datetime("2016-07-12"))
    eba = changeTrade(eba, "DUK", "SC", pd.to_datetime("2016-10-09"),
                      pd.to_datetime("2016-10-21"))
    eba = changeTrade(eba, "DUK", "SOCO")
    eba = changeTrade(eba, "DUK", "CPLE", pd.to_datetime("2015-12-31"),
                      pd.to_datetime("2016-01-02"))
    eba = changeTrade(eba, "DUK", "SC", pd.to_datetime("2015-12-31"),
                      pd.to_datetime("2016-01-02"))
    eba = changeTrade(eba, "DUK", "SCEG", pd.to_datetime("2015-12-31"),
                      pd.to_datetime("2016-01-02"))
    eba = changeTrade(eba, "DUK", "TVA", pd.to_datetime("2015-12-31"),
                      pd.to_datetime("2016-01-02"))
    eba = changeTrade(eba, "DUK", "CPLE")
    eba = changeTrade(eba, "DUK", "TVA")

    logger.debug("TVA fixes")
    ba = "TVA"
    eba = changeTrade(eba, "TVA", "SOCO")
    eba = changeTrade(eba, "AECI", "TVA")

    ba2 = "AECI"
    set_to_nan = eba.df.loc[:, eba.KEY["ID"] % (ba, ba2)].abs() < 10
    ind_time = (eba.df.index > pd.to_datetime("2016-06-13")) & (
        eba.df.index < pd.to_datetime("2016-06-17"))
    ind = set_to_nan & ind_time
    eba.df.loc[ind, eba.KEY["ID"] % (ba, ba2)] = np.nan
    eba.df.loc[ind_time, eba.KEY["ID"] % (ba, ba2)] = eba.df.loc[
        ind_time, eba.KEY["ID"] % (ba, ba2)].fillna(method='pad', limit=80)
    eba = changeTrade(eba, "TVA", "AECI")

    logger.debug("small fixes")
    eba = changeTrade(eba, "PGE", "BPAT")
    eba = changeTrade(eba, "NEVP", "WALC", pd.to_datetime("2016-02-18"),
                      pd.to_datetime("2016-02-19"))
    eba = changeTrade(eba, "PACW", "PACE", pd.to_datetime("2016-12-30"))
    eba = changeTrade(eba, "PGE", "PACW", pd.to_datetime("2016-03-25"),
                      pd.to_datetime("2016-03-26"))
    eba = changeTrade(eba, "PACE", "PACW", pd.to_datetime("2016-02-26"),
                      pd.to_datetime("2016-02-28"))
    eba = removeTradeOutliers(
        eba, "PACW", "PACE", pd.to_datetime("2016-07-21"),
        pd.to_datetime("2016-07-25"))
    eba = changeTrade(eba, "SWPP", "ERCO")

    eba = changeTrade(eba, "EEI", "MISO")
    eba = changeTrade(eba, "EEI", "TVA")

    logger.debug("Cleaning leftover NaNs")
    for ba in eba.regions:
        partners = eba.get_trade_partners(ba)

        cnt1 = 0
        for ba2 in partners:
            cnt1 += eba.df.loc[:, eba.KEY["ID"] % (ba, ba2)].isna().sum()

        for ba2 in partners:
            ind = eba.df.loc[:, eba.KEY["ID"] % (ba, ba2)].isna()
            eba.df.loc[ind, eba.KEY["ID"] % (ba, ba2)] = - eba.df.loc[
                ind, eba.KEY["ID"] % (ba2, ba)]

        cnt2 = 0
        for ba2 in partners:
            cnt2 += eba.df.loc[:, eba.KEY["ID"] % (ba, ba2)].isna().sum()

        if (cnt1 > 0):
            logger.debug("%s - NaN count: %d to % d across %d partners" % (
                    ba, cnt1, cnt2, len(partners)))

    return eba


def applyFixes2(eba):
    '''
    A second round of fixes.
    '''
    ba = "WAUW"
    eba = changeTrade(eba, "NWMT", ba, pd.to_datetime("2016-12-25"))
    eba = changeTrade(eba, "WACM", ba, pd.to_datetime("2016-12-25"))
    eba = changeTrade(eba, ba, "NWMT", pd.to_datetime("2016-11-29"),
                      pd.to_datetime("2016-12-03"))
    eba = changeTrade(eba, ba, "WACM", pd.to_datetime("2016-05-17"),
                      pd.to_datetime("2016-05-18"))
    eba = changeTrade(eba, ba, "WACM", pd.to_datetime("2016-06-10"),
                      pd.to_datetime("2016-06-13"))
    eba = changeTrade(eba, ba, "WACM", tol=0.)
    eba = changeTrade(eba, "NWMT", ba, tol=0.)
    eba = changeTrade(eba, "SWPP", ba, tol=0.)

    ba = "WACM"
    eba = changeTrade(eba, "PACE", ba)
    eba = changeTrade(eba, "PSCO", ba)
    eba = changeTrade(eba, "PNM", ba)
    eba = changeTrade(eba, ba, "AZPS")
    eba = changeTrade(eba, ba, "SWPP")

    ba = "TEC"
    eba = changeTrade(eba, ba, "SEC", start=pd.to_datetime("2016-06-12"),
                      end=pd.to_datetime("2016-06-13"))
    eba = changeTrade(eba, ba, "FPC", end=pd.to_datetime("2016-01-03"))
    eba = changeTrade(eba, ba, "SEC", start=pd.to_datetime("2016-11-05"))
    eba = changeTrade(eba, ba, "SEC", tol=0.)
    eba = changeTrade(eba, ba, "FPL", tol=0.)
    eba = changeTrade(eba, ba, "FMPP", tol=0.)
    eba = changeTrade(eba, ba, "FPC", tol=0.)

    ba = "TAL"
    eba = changeTrade(eba, "SOCO", "TAL", pd.to_datetime("2016-11-25"),
                      pd.to_datetime("2016-12-31"))
    ba2 = "SOCO"
    set_to_nan = eba.df.loc[:, eba.KEY["ID"] % (ba, ba2)].abs() < 10
    ind_time = (eba.df.index > pd.to_datetime("2016-12-01"))
    ind = set_to_nan & ind_time
    eba.df.loc[ind, eba.KEY["ID"] % (ba, ba2)] = np.nan
    eba.df.loc[ind_time, eba.KEY["ID"] % (ba, ba2)] = eba.df.loc[
        ind_time, eba.KEY["ID"] % (ba, ba2)].fillna(method='pad', limit=14)
    eba = changeTrade(eba, ba, ba2, start=pd.to_datetime("2016-12-01"))
    eba = changeTrade(eba, ba, "FPC", tol=0.)
    eba = changeTrade(eba, ba, "SOCO", tol=0.)

    ba = "SOCO"
    eba = changeTrade(eba, "AEC", ba)
    eba = changeTrade(eba, "SOCO", "SC", pd.to_datetime("2016-10-08"),
                      pd.to_datetime("2016-10-21"))
    eba = changeTrade(eba, "SC", "SOCO", pd.to_datetime("2016-09-30"),
                      pd.to_datetime("2016-10-01"))
    eba = changeTrade(eba, "SC", "SOCO", pd.to_datetime("2016-05-05"),
                      pd.to_datetime("2016-05-21"))
    eba = changeTrade(eba, "FPL", "SOCO", pd.to_datetime("2016-05-17"),
                      pd.to_datetime("2016-05-18"))
    eba = changeTrade(eba, "SOCO", "SCEG", pd.to_datetime("2016-01-23"),
                      pd.to_datetime("2016-01-24"))
    for ba2 in ["FPL", "SC", "SCEG", "FPC"]:
        eba = changeTrade(eba, ba2, "SOCO", pd.to_datetime("2016-11-26"))
    eba = changeTrade(eba, "SC", "SOCO", pd.to_datetime("2015-12-31"),
                      pd.to_datetime("2016-01-02"))

    for ba2 in ["FPL", "FPC", "SCEG", "SC"]:
        eba = changeTrade(eba, ba2, ba)

    ba = "SEC"
    for ba2 in ["FPC", "JEA", "FPL"]:
        eba = changeTrade(eba, ba2, "SEC", tol=0.)

    eba = changeTrade(eba, "PSEI", "SCL", pd.to_datetime("2016-12-10"))

    ba = "SCEG"
    eba = changeTrade(eba, "SCEG", "SC")
    eba = changeTrade(eba, "SCEG", "CPLE", pd.to_datetime("2016-02-09"),
                      pd.to_datetime("2016-02-13"))
    eba = changeTrade(eba, "CPLE", "SCEG", pd.to_datetime("2016-03-13"),
                      pd.to_datetime("2016-03-24"))
    eba = changeTrade(eba, "CPLE", "SCEG")

    eba = changeTrade(eba, "CPLE", "SC")

    eba = changeTrade(eba, "PSCO", "PNM", pd.to_datetime("2016-07-23"),
                      pd.to_datetime("2016-07-25"))
    eba = changeTrade(eba, "PSCO", "SWPP")

    eba = changeTrade(eba, "PNM", "AZPS")

    eba = changeTrade(eba, "CISO", "PACW")
    for ba2 in ["PACE", "BPAT", "PGE"]:
        eba = changeTrade(eba, "PACW", ba2, tol=0.)

    ba = "PACE"
    eba = changeTrade(eba, "PACE", "NWMT", pd.to_datetime("2016-11-10"))
    for ba2 in ["NWMT", "IPCO", "NEVP", "AZPS"]:
        eba = changeTrade(eba, ba2, "PACE", tol=0.)

    eba = changeTrade(eba, "NYIS", "ISNE",  tol=0.)
    eba = changeTrade(eba, "NWMT", "AVA", tol=0.)
    eba = changeTrade(eba, "NWMT", "IPCO", tol=0.)

    eba = changeTrade(eba, "NSB", "FPC", tol=0.)
    eba = changeTrade(eba, "NSB", "FPL", tol=0.)

    # CHPD exports to PSEI according to Wikipedia
    eba = changeTrade(eba, "CHPD", "PSEI")
    eba = changeTrade(eba, "CHPD", "DOPD")
    eba = changeTrade(eba, "CHPD", "BPAT", tol=0.)

    eba = changeTrade(eba, "FPL", "FMPP", pd.to_datetime("2016-01-01"),
                      pd.to_datetime("2016-03-13"))
    eba = changeTrade(eba, "FPL", "FMPP", pd.to_datetime("2016-04-09"),
                      pd.to_datetime("2016-04-17"))
    eba = changeTrade(eba, "FPL", "FMPP")
    eba = changeTrade(eba, "FMPP", "FPC", pd.to_datetime("2015-12-31"),
                      pd.to_datetime("2016-01-02"))
    eba = changeTrade(eba, "FMPP", "FPC")
    eba = changeTrade(eba, "JEA", "FMPP")

    eba = changeTrade(eba, "FPL", "FPC", pd.to_datetime("2015-12-31"),
                      pd.to_datetime("2016-01-02"))
    eba = changeTrade(eba, "GVL", "FPC", pd.to_datetime("2015-12-31"),
                      pd.to_datetime("2016-01-02"))
    eba = changeTrade(eba, "GVL", "FPC")
    eba = changeTrade(eba, "GVL", "FPL")

    eba = changeTrade(eba, "FPL", "HST")
    eba = removeTradeOutliers(eba, "HST", "FPL", thresh_l=0)

    eba = changeTrade(eba, "JEA", "FPL")
    eba = changeTrade(eba, "PSEI", "GCPD", tol=0.)

    return eba


def EBA_2():
    '''
    Putting it all together.
    '''
    logger = logging.getLogger('clean')
    logger.info("Starting EBA_2")

    eba = BA_DATA(step=1)

    eba = applyFixes(eba)
    eba = applyFixes2(eba)

    logger.info("Saving EBA_2 data")
    fileNm = os.path.join(DATA_PATH, "analysis/EBA_2.csv")
    eba.df.to_csv(fileNm)
