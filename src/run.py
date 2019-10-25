'''
File to run different data processing steps.
'''
import os
import logging.config
import argparse
from EBA_0 import EBA_0
from EBA_1 import EBA_1
from EBA_2 import EBA_2
from EBA_3 import EBA_3
from AMPD_0 import AMPD_0
from AMPD_1 import AMPD_1
from AMPD_2 import AMPD_2
from SEED import SEED

DATA_PATH = os.getenv('DATA_PATH')
if DATA_PATH is None:
    raise ValueError("DATA_PATH needs to be set")

if __name__ == '__main__':
    # Parse args
    argparser = argparse.ArgumentParser()
    argparser.add_argument('--fLog', default=False)
    argparser.add_argument('--cLog', default=True)
    argparser.add_argument('--dLog', default=False)
    argparser.add_argument('--run', default=None)
    args = argparser.parse_args()

    # Setup logging
    logging.config.fileConfig('logging.conf')
    logger = logging.getLogger(__name__)
    logger.info("Configured logging")

    # Run
    if args.run is not None:
        exec(args.run + '()')
