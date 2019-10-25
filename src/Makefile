# Makefile for the consumption emissions project
# This project should be run using a python 3.5 executable with the necessary packages installed (see conda and pip requirements files)

$(info [MKINFO] DATA_PATH is $(DATA_PATH))
$(info [MKINFO] python is $(shell which python))

MYDIR=$(DATA_PATH)/analysis

# Data extraction
$(MYDIR)/EBA_0.csv : EBA_0.py
	python run.py --run=EBA_0
$(MYDIR)/AMPD_0.csv : AMPD_0.py
	python run.py --run=AMPD_0

# EBA data cleaning
$(MYDIR)/EBA_1.csv : $(MYDIR)/EBA_0.csv EBA_1.py load.py
	python run.py --run=EBA_1
$(MYDIR)/EBA_2.csv : $(MYDIR)/EBA_1.csv EBA_2.py load.py
	python run.py --run=EBA_2
$(MYDIR)/EBA_3.csv : $(MYDIR)/EBA_2.csv EBA_3.py load.py
	python run.py --run=EBA_3

# AMPD data cleaning
$(MYDIR)/AMPD_1.csv : $(MYDIR)/AMPD_0.csv AMPD_1.py load.py
	python run.py --run=AMPD_1
$(MYDIR)/AMPD_2.csv : $(MYDIR)/AMPD_1.csv AMPD_2.py load.py
	python run.py --run=AMPD_2

# SEED dataset
$(MYDIR)/SEED_CO2_H.csv : $(MYDIR)/AMPD_2.csv $(MYDIR)/EBA_3.csv SEED.py load.py
	python run.py --run=SEED

FILENMS = EBA_0.csv AMPD_0.csv EBA_1.csv AMPD_1.csv AMPD_2.csv EBA_2.csv EBA_3.csv SEED_CO2_H.csv
DATASETS = $(FILENMS:%=$(MYDIR)/%)

.PHONY: all
all: $(DATASETS)
