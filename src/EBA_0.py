import os
import pandas as pd
import xlrd
import json
import re
import logging
import time
from load import EGRID

DATA_PATH = os.getenv('DATA_PATH')
if DATA_PATH is None:
    raise ValueError("DATA_PATH needs to be set")


def EBA_0():
    '''
    Parse EBA data. This was downloaded from:
        https://www.eia.gov/opendata/bulkfiles.php
    A user guide can be found here:
        https://www.eia.gov/realtime_grid/docs/userguide-knownissues.pdf
    The raw data is structured as json dictionaries, one per line. There are
    two types of dictionaries, with descriptor and time series information. We
    split the two types of data in two lists and extract BA level data only.
    '''
    logger = logging.getLogger('parse')
    logger.info("Starting EBA_0")
    with open(os.path.join(DATA_PATH, "raw", "EBA.txt")) as fr:
        lines = fr.readlines()

    # convert json - each line is a dictionary
    data = []
    for l in lines:
        data += [json.loads(l)]

    # separate id data from ts data
    ts_data = [d for d in data if len(d.keys()) == 10]
    # id_list = [d for d in data if len(d.keys()) == 5]

    # TS data frame
    df = pd.DataFrame(ts_data)

    # Get list of BAs in eGrid data set
    egrid = EGRID(sheet_name='BA16')
    egrid_ba_codes = egrid.df.BACODE

    info = "Missing in EBA dataset:\n"
    for ba in egrid_ba_codes:
        if not (
            ba in df.apply(lambda el: re.split(r"\.|-", el.series_id)[1],
                           axis=1).unique()):
            if not isinstance(ba, str):
                info += "%s\n" % ba
            else:
                info += "%s : %s\n" % (
                    ba, egrid.df[egrid.df.BACODE == ba].BANAME.iloc[0])
    logger.info(info)

    logger.debug(info)
    # Get series_id in EBA data set for the correct BAs
    # For the Interchange series, make sure both elements are a BA

    def choose(el, ba_list):
        if '.ID.H' in el.series_id:
            return ((re.split(r"\.|-", el.series_id)[1] in ba_list)
                    and (re.split(r"\.|-", el.series_id)[2] in ba_list))
        else:
            return (re.split(r"\.|-", el.series_id)[1] in ba_list)
    df = df[df.apply(lambda el: choose(el, egrid_ba_codes.values), axis=1)]

    df_list = []
    for lab in df.series_id:
        if len(df[df.series_id == lab]) != 1:
            logger.warn("label %s is not unique!" % lab)
        sel = df.series_id == lab

        ts = pd.DataFrame.from_dict(dict(df.loc[sel, 'data'].values[0]),
                                    orient="index")
        ts.columns = [lab]
        ts.index = pd.to_datetime(ts.index)
        ts.sort_index(inplace=True)
        df_list += [ts]
    df_extract = pd.concat(df_list, axis=1)

    logger.info("Saving EBA_0 data")
    df_extract.to_csv(os.path.join(DATA_PATH, "analysis/EBA_0.csv"))
