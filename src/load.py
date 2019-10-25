'''
This file contains code to load EBA, eGrid and AMPD datasets. The file provides
one class for each data set. Data can either be raw (of the type that is output
from the parse.py script) or cleaned (outputs from clean.py).

The data handler classes provide methods to access the data in different ways
and perform some checks.
'''
import os
import pandas as pd
import logging
import re


DATA_PATH = os.getenv('DATA_PATH')
if DATA_PATH is None:
    raise ValueError("DATA_PATH needs to be set")


class BA_DATA(object):
    '''Class to handle BA-level data. The EBA class provides generation,
    consumption, the trade matrix and total interchange either at the BA or at
    the regional (IEA-defined) level. User guide:
        https://www.eia.gov/realtime_grid/docs/userguide-knownissues.pdf

    Timestamps are in UTC.

    EBA data columns
    ----------------
    D: Demand
    NG: Net Generation
    TI: Total Interchange - (positive if exports)
    ID: Interchange with directly connected balancing authorities - (positive
        if exports)

    Consistency requirements
    ------------------------
    - Interchange data is antisymmetric: ID[i,j] == -ID[j,i]
    - Total trade with interchange data: TI == sum(ID[i,:])
    - Balance equation for total trade, demand, generation: TI + D == NG

    Methods
    -------
    get_cols(self, r) : generate column names for regions r for a given field.

    Attributes
    ----------
    regions : are in alphabetical order
    df : raw dataframe
    '''
    # Convenience dictionary to refer to keys
    # call KEY['D']%ri to get demand for region ri
    KEYS = {"E": {'D': 'EBA.%s-ALL.D.H', 'NG': 'EBA.%s-ALL.NG.H',
                  'TI': 'EBA.%s-ALL.TI.H', 'ID': 'EBA.%s-%s.ID.H'},
            "CO2": {'D': "CO2_%s_D", 'NG': "CO2_%s_NG",
                    "TI": "CO2_%s_TI", "ID": "CO2_%s-%s_ID"},
            "SO2": {'D': "SO2_%s_D", 'NG': "SO2_%s_NG",
                    "TI": "SO2_%s_TI", "ID": "SO2_%s-%s_ID"},
            "NOX": {'D': "NOX_%s_D", 'NG': "NOX_%s_NG",
                    "TI": "NOX_%s_TI", "ID": "NOX_%s-%s_ID"},
            "CO2i": {'D': "CO2i_%s_D", 'NG': "CO2i_%s_NG"},
            "SO2i": {'D': "SO2i_%s_D", 'NG': "SO2i_%s_NG"},
            "NOXi": {'D': "NOXi_%s_D", 'NG': "NOXi_%s_NG"}}

    def __init__(self, step=None, fileNm=None, df=None, variable="E",
                 dataset="EBA"):
        self.logger = logging.getLogger('load')

        if df is not None:
            self.df = df
        else:
            if step is not None:
                fileNm = os.path.join(
                    DATA_PATH, 'analysis', '%s_%d.csv' % (dataset, step))
            if fileNm is None:
                fileNm = os.path.join(DATA_PATH, "analysis", "EBA_0.csv")
            self.df = pd.read_csv(fileNm, index_col=0, parse_dates=True)

        self.variable = variable
        self.regions = self._parse_data_cols()
        self.fileNm = fileNm
        self.KEY = self.KEYS[variable]

    def get_cols(self, r=None, field="D"):
        if r is None:
            r = self.regions
        if isinstance(r, str):
            r = [r]
        return [self.KEY[field] % ir for ir in r]

    def get_trade_partners(self, ba):
        partners = []
        for ba2 in self.regions:
            if ((self.KEY["ID"] % (ba, ba2) in self.df.columns)
                    and (self.KEY["ID"] % (ba2, ba) in self.df.columns)):
                partners += [ba2]
        return partners

    def _parse_data_cols(self):
        '''
        Checks:
        - Consistent number of regions for demand / generation / total
            interchange / trade matrix
        Returns the list of regions
        '''
        regions = set([re.split(r"\.|-|_", el)[1] for el in self.df.columns])
        D_cols = [re.split(r"\.|-|_", el)[1] for el in self.df.columns if 'D'
                  in re.split(r"\.|-|_", el)]
        NG_cols = [re.split(r"\.|-|_", el)[1] for el in self.df.columns if 'NG'
                   in re.split(r"\.|-|_", el)]
        TI_cols = [re.split(r"\.|-|_", el)[1] for el in self.df.columns if 'TI'
                   in re.split(r"\.|-|_", el)]
        ID_cols = [re.split(r"\.|-|_", el)[1] for el in self.df.columns if 'ID'
                   in re.split(r"\.|-|_", el)]
        ID_cols2 = [re.split(r"\.|-|_", el)[2] for el in self.df.columns if
                    'ID' in re.split(r"\.|-|_", el)]

        if len(NG_cols) != len(D_cols):
            self.logger.warn(
                'Inconsistent columns: len(NG_cols) != len(D_cols)')
        if set(NG_cols) != regions:
            self.logger.warn(
                'Inconsistent columns: set(NG_cols) != regions')

        if not ("i" in self.variable):
            if len(NG_cols) != len(TI_cols):
                self.logger.warn(
                    'Inconsistent columns: len(NG_cols) != len(TI_cols)')
            if set(NG_cols) != set(ID_cols):
                self.logger.warn(
                    'Inconsistent columns: set(NG_cols) != set(ID_cols)')
            if set(NG_cols) != set(ID_cols2):
                self.logger.warn(
                    'Inconsistent columns: set(NG_cols) != set(ID_cols2)')

        return sorted(list(regions))

    def get_trade_out(self, r=None):
        if r is None:
            r = self.regions
        if isinstance(r, str):
            r = [r]
        cols = []
        for ir2 in self.regions:
            cols += [self.KEY['ID'] % (ir, ir2) for ir in r]
        return [c for c in cols if c in self.df.columns]


    def checkBA(self, ba, tol=1e-2, log_level=logging.INFO):
        '''
        Sanity check function
        '''
        logger = self.logger
        log_level_old = logger.level
        logger.setLevel(log_level)
        logger.debug("Checking %s" % ba)
        partners = self.get_trade_partners(ba)
    
        # NaNs
        for field in ["D", "NG", "TI"]:
            ind_na = self.df.loc[:, self.get_cols(r=ba, field=field)[0]].isna()
            cnt_na = ind_na.sum()
            if cnt_na != 0:
                logger.error("There are still %d nans for %s field %s" %
                             (cnt_na, ba, field))
    
        for ba2 in partners:
            cnt_na = self.df.loc[:, self.KEY["ID"] % (ba, ba2)].isna().sum()
            if cnt_na != 0:
                logger.error("There are still %d nans for %s-%s" %
                             (cnt_na, ba, ba2))
    
        # TI+D == NG
        res1 = self.df.loc[:, self.get_cols(r=ba, field="NG")[0]] - (
                self.df.loc[:, self.get_cols(r=ba, field="D")[0]]
                + self.df.loc[:, self.get_cols(r=ba, field="TI")[0]])
        if (res1.abs() > tol).sum() != 0:
            logger.error("%s: TI+D == NG violated" % ba)
    
        # TI == ID.sum()
        res2 = (
            self.df.loc[:, self.get_cols(r=ba, field="TI")[0]]
            - self.df.loc[:, [self.KEY["ID"] % (ba, ba2) for ba2 in partners]]\
                .sum(axis=1))
        if (res2.abs() > tol).sum() != 0:
            logger.error("%s: TI == ID.sum()violated" % ba)
    
        # ID[i,j] == -ID[j,i]
        for ba2 in partners:
            res3 = (self.df.loc[:, self.KEY["ID"] % (ba, ba2)] 
                    + self.df.loc[:, self.KEY["ID"] % (ba2, ba)])
            if (res3.abs() > tol).sum() != 0:
                logger.error("%s-%s: ID[i,j] == -ID[j,i] violated" % (ba, ba2))
    
        # D and NG negative
        for field in ["D", "NG"]:
            ind_neg = self.df.loc[:, self.get_cols(r=ba, field=field)[0]] < 0
            cnt_neg = ind_neg.sum()
            if cnt_neg != 0:
                logger.error("%s: there are %d <0 values for field %s" %
                             (ba, cnt_neg, field))
        logger.setLevel(log_level_old)


class AMPD(object):
    '''
    Class to handle the AMPD data.
    '''

    def __init__(self, step=None, fileNm=None):
        self.logger = logging.getLogger('load')

        if step is not None:
            fileNm = os.path.join(DATA_PATH, 'analysis', 'AMPD_%d.csv' % step)
        if fileNm is None:
            fileNm = os.path.join(DATA_PATH, 'analysis', 'AMPD_0.csv')

        self.fileNm = fileNm
        if step < 2:
            self.df = pd.read_csv(fileNm, parse_dates=['OP_DATE_TIME'],
                                  infer_datetime_format=True)
        elif step == 2:
            self.df = pd.read_csv(fileNm, index_col=0, parse_dates=True)

        self.logger.info('Loading AMPD from %s' % self.fileNm)


class EGRID(object):
    '''
    Simple class to handle EGRID data.
    The eGrid dataset contains a list of plants in the US including:
    - ORISPL code
    - Plant name
    - Operator name
    - Balancing authority
    - State
    - Geographical coordinates
    - Nominal capacity
    '''

    def __init__(self, fileNm=None, sheet_name='BA16'):
        self.logger = logging.getLogger('load')

        if fileNm is None:
            fileNm = os.path.join(
                DATA_PATH,
                "raw/EGRID/egrid2016_all_files/egrid2016_data_metric.xlsx")

        self.df = pd.read_excel(fileNm, sheet_name=sheet_name, header=1)
        self.fileNm = fileNm
        self.sheet_name = sheet_name
        self.logger.info('Loading EGRID sheet %s' % self.sheet_name)

    def get_groups(self, grp_type='BACODE'):
        '''
        Method get_groups returns a dictionary of the form:
        {grp_type: {state:[plant_codes]}}
        This can then be used to aggregate AMPD data according to grp_type.
        Options for parameter grp_type are: BA_CODE, NERC, SUBRGN.
        '''
        if self.sheet_name != "PLNT16":
            raise ValueError("Cannot call this function with sheet %s!"
                             % self.sheet_name)

        return self.df.groupby([grp_type])['PSTATABB', 'ORISPL']\
            .apply(lambda df: df.groupby(["PSTATABB"])['ORISPL']
                   .apply(list).to_dict()).to_dict()
