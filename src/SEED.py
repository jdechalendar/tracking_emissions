import os
import sys
import pandas as pd
import numpy as np
import logging
import time

DATA_PATH = os.getenv('DATA_PATH')
if DATA_PATH is None:
    raise ValueError("DATA_PATH needs to be set")


def consumption_emissions(F, P, ID):
    '''
    Create linear system to calculate consumption emissions
    - Create import matrix
    - Create linear system and solve:
    f_i^c*(d_i+sum_j t_{ji}) - sum_j t_{ij}*f_j^c = F_i^p
    where:
        f_i^c: consumption emissions at node i
        d_i: demand at node i
        t: trade matrix - t_{ij} is from node i to j
        F_i^p: emissions produced at node i
    Note: np version must be high enough, otherwise np.linalg.cond fails
    on a matrix with only zeros.
    '''
    from distutils.version import LooseVersion
    assert LooseVersion(np.__version__) >= LooseVersion('1.15.1')

    # Create and solve linear system
    Imp = (-ID).clip(min=0)  # trade matrix reports exports - we want imports
    I_tot = Imp.sum(axis=1)  # sum over columns
    A = np.diag(P + I_tot) - Imp
    b = F

    perturbed = []
    if np.linalg.cond(A) > (1./sys.float_info.epsilon):
        # matrix is ill-conditioned
        for i in range(len(A)):
            if ((np.abs(A[:, i]).sum() == 0.)
                    & (np.abs(A[i, :]).sum() == 0.)):
                A[i, i] = 1.  # slightly perturb that element
                perturbed += [i]
                # force this to be zero so the linear system makes sense
                b[i] = 0.

    X = np.linalg.solve(A, b)

    for j in perturbed:
        if (X[j] != 0.):
            print(b[j])
            print(np.abs(A[j, :]).sum())
            print(np.abs(A[:, j]).sum())
            raise ValueError("X[%d] is %.2f instead of 0" % (j, X[j]))

    return X, len(perturbed)


def makeSEED(poll="CO2", time_lev="H"):
    '''
    Combine AMPD and EBA data to create the SEED data set.
    Calculates consumption-based emissions.
    '''
    from load import BA_DATA
    logger = logging.getLogger('clean')
    logger.info("Starting SEED - %s - %s" % (poll, time_lev))

    # Load AMPD data
    fileNm = os.path.join(DATA_PATH, "analysis/AMPD_2.csv")
    ampd_ba_p = pd.read_csv(fileNm, index_col=0, parse_dates=['DATE_TIME_UTC'],
                            infer_datetime_format=True)

    # Load EBA data
    eba = BA_DATA(step=3)
    
    # Select the pollutant
    cols = [col for col in ampd_ba_p.columns if poll in col]
    df_poll = ampd_ba_p.loc[:, cols].copy(deep=True)
    df_poll.columns = [col+"_NG" for col in df_poll.columns]
    # Merge dataframes
    df_j = df_poll.join(eba.df, how='inner')


    # Drop the extra BAs
    df_j = df_j.drop(["%s_%s_NG" % (poll, ba) for ba in
                      ['AMPL', 'HECO', 'GRIS', 'CEA']], axis=1)
    
    # Fill NAs and zeros
    for col in df_j.columns:
        if "CO2" in col:
            df_j[col] = df_j[col].fillna(1./100)
            df_j.loc[(df_j[col] == 0.), col] = 1./100
        elif "SO2" in col:
            df_j[col] = df_j[col].fillna(1./100/1000)
            df_j.loc[(df_j[col] == 0.), col] = 1./100/1000
        elif "NOX" in col:
            df_j[col] = df_j[col].fillna(1./100/1000)
            df_j.loc[(df_j[col] == 0.), col] = 1./100/1000
        elif "-ALL.D.H" in col:
            df_j[col] = df_j[col].fillna(1.)
            df_j.loc[df_j[col] == 0., col] = 1.
        elif "-ALL.NG.H" in col:
            df_j[col] = df_j[col].fillna(1.)
            df_j.loc[df_j[col] == 0., col] = 1.
        elif "-ALL.TI.H" in col:
            df_j[col] = df_j[col].fillna(0.)
        elif "ID.H" in col:
            df_j[col] = df_j[col].fillna(0.)
        else:
            logger.warn("Unexpected column %s" % col)
         
    # allocate space for the consumption emissions (speeds up what's next)
    newcols = (df_j.columns.tolist()
               + ["%si_%s_D" % (poll, ba) for ba in eba.regions])
    df_j = df_j.reindex(columns=newcols)
    
    # Aggregate to month, year, or do nothing to stay at hour
    if time_lev == "M":
        df_j = df_j.groupby(df_j.index.month).sum()
    elif time_lev == "Y":
        df_j = df_j.groupby(df_j.index.year).sum()

    def apply_consumption_calc(row, poll):
        '''
        Extract data for a row in the dataframe with EBA and AMPD data and call
        the consumption emissions function
        '''
        P = row[[eba.KEY['NG'] % r for r in eba.regions]].values
        ID = np.zeros((len(eba.regions), len(eba.regions)))
        for i, ri in enumerate(eba.regions):
            for j, rj in enumerate(eba.regions):
                if eba.KEY['ID'] % (ri, rj) in eba.df.columns:
                    ID[i][j] = row[eba.KEY['ID'] % (ri, rj)]

        F = row[[("%s_%s_NG") % (poll, ba) for ba in eba.regions]].values
        X = [np.nan for ba in eba.regions]
        try:
            X, pert = consumption_emissions(F, P, ID)
        except np.linalg.LinAlgError:
            pass
        except ValueError:
            raise
        row[[("%si_%s_D") % (poll, ba) for ba in eba.regions]] = X
        return row

    logger.debug("Calculating consumption emissions...")
    start_time = time.time()
    df_j = df_j.apply(lambda x: apply_consumption_calc(x, poll), axis=1)
    end_time = time.time()
    logger.debug("Elapsed time was %g seconds" % (end_time - start_time))

    # Create columns for consumption
    for ba in eba.regions:
        df_j.loc[:, "%s_%s_D" % (poll, ba)] = df_j.loc[:, "%si_%s_D" % (poll, ba)] * df_j.loc[
            :, eba.get_cols(r=ba, field="D")[0]]

    # Create columns for pairwise trade
    for ba in eba.regions:
        for ba2 in eba.get_trade_partners(ba):
            imp = df_j.loc[:, eba.KEY["ID"] % (ba,ba2)].apply(lambda x: min(x, 0))
            exp = df_j.loc[:, eba.KEY["ID"] % (ba,ba2)].apply(lambda x: max(x, 0))
            df_j.loc[:, "%s_%s-%s_ID" % (poll, ba, ba2)] = (
                imp * df_j.loc[:, "%si_%s_D" % (poll, ba2)]
                + exp * df_j.loc[:, "%si_%s_D" % (poll, ba)])

    # Create columns for total trade
    for ba in eba.regions:
        df_j.loc[:, "%s_%s_TI" % (poll, ba)] = df_j.loc[:, [
                "%s_%s-%s_ID" % (poll, ba, ba2) for ba2 in
                eba.get_trade_partners(ba)]].sum(axis=1)

    # Create EBA object for CO2
    poll_data = BA_DATA(df=df_j.loc[:, [col for col in df_j.columns if "%s_" % poll in col]],
              variable=poll)
    # Create EBA object for ELEC
    elec = BA_DATA(df=df_j.loc[:, [col for col in df_j.columns if "EBA." in col]],
              variable="E")

    # Save results
    fileNm = os.path.join(DATA_PATH, "analysis/SEED_%s_%s.csv" % (poll, time_lev))
    poll_data.df.to_csv(fileNm)
    
    fileNm = os.path.join(DATA_PATH, "analysis/SEED_E_%s.csv" % time_lev)
    elec.df.to_csv(fileNm)
    
    # Also save emissions factors
    # Add columns for production-based EFs
    for ba in eba.regions:
        df_j.loc[:, "%si_%s_NG" % (poll, ba)] = (
            poll_data.df.loc[:, poll_data.get_cols(r=ba, field="NG")].values.flatten()
            / elec.df.loc[:, elec.get_cols(r=ba, field="NG")].values.flatten())

    # Extract production- and consumption-based EFs
    efs = 1000 * df_j.loc[:, [col for col in df_j.columns if "%si_" % poll in col]]
    fileNm = os.path.join(DATA_PATH, "analysis/SEED_EFs_%s_%s.csv" % (poll, time_lev))
    efs.to_csv(fileNm)
    
def SEED():
    for poll in ["CO2", "SO2", "NOX"]:
        makeSEED(poll, time_lev="Y")
    for time_lev in ["M", "H"]:
        makeSEED("CO2", time_lev)
