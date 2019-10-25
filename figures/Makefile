# Makefile to make figures for "Hourly production and consumption emissions factors for the US electricity system"
# This project should be run using a python 3.5 executable with the necessary packages installed (see conda and pip requirements files)

$(info [MKINFO] DATA_PATH is $(DATA_PATH))
$(info [MKINFO] FIGURE_PATH is $(FIGURE_PATH))
$(info [MKINFO] python is $(shell which python))

MYDIR=$(DATA_PATH)/analysis

DATA_FILES = $(MYDIR)/SEED_CO2_Y.csv $(MYDIR)/SEED_CO2_M.csv $(MYDIR)/SEED_CO2_H.csv $(MYDIR)/SEED_E_Y.csv $(MYDIR)/SEED_E_M.csv $(MYDIR)/SEED_E_H.csv $(MYDIR)/SEED_SO2_Y.csv $(MYDIR)/SEED_NOX_Y.csv

# The following rule also creates data files for the SI SO2 and NOx maps
$(FIGURE_PATH)/main/d3map/data/graph_E_CO2i.json: fig1_map.ipynb $(DATA_FILES)
	jupyter nbconvert --execute fig1_map.ipynb
	rm fig1_map.html 

$(FIGURE_PATH)/main/fig2.pdf: fig2_variability.ipynb $(DATA_FILES)
	jupyter nbconvert --execute fig2_variability.ipynb
	rm fig2_variability.html 

$(FIGURE_PATH)/main/fig3.pdf: fig3_profiles.ipynb $(DATA_FILES)
	jupyter nbconvert --execute fig3_profiles.ipynb
	rm fig3_profiles.html 

$(FIGURE_PATH)/main/fig4.pdf: fig4_trade.ipynb $(DATA_FILES)
	jupyter nbconvert --execute fig4_trade.ipynb
	rm fig4_trade.html 

$(FIGURE_PATH)/si/monthly_sums.pdf: SI_monthly_plots.ipynb $(DATA_FILES)
	jupyter nbconvert --execute SI_monthly_plots.ipynb
	rm SI_monthly_plots.html 

$(FIGURE_PATH)/si/daily_profiles/daily_profiles.pdf: SI_daily_profiles.ipynb $(DATA_FILES)
	jupyter nbconvert --execute SI_daily_profiles.ipynb
	rm SI_daily_profiles.html 

$(FIGURE_PATH)/si/AMPD_report.html: SI_AMPD_report.ipynb $(DATA_FILES)
	jupyter nbconvert --ExecutePreprocessor.timeout=100 --execute SI_AMPD_report.ipynb
	mv SI_AMPD_report.html $(FIGURE_PATH)/si/AMPD_report.html

$(FIGURE_PATH)/si/sanity.html: SI_sanity.ipynb $(DATA_FILES)
	jupyter nbconvert --ExecutePreprocessor.timeout=100 --execute SI_sanity.ipynb
	mv SI_sanity.html $(FIGURE_PATH)/si/sanity.html

$(FIGURE_PATH)/si/sankey/data_CO2.json: SI_sankey.ipynb $(DATA_FILES)
	jupyter nbconvert --execute SI_sankey.ipynb
	rm SI_sankey.html 

# This notebook creates a dummy file when it is done as a convenience for make
$(FIGURE_PATH)/si/annualPlot/dummy: SI_annualPlot.ipynb $(DATA_FILES)
	jupyter nbconvert --ExecutePreprocessor.timeout=100 --execute SI_annualPlot.ipynb
	rm SI_annualPlot.html

$(FIGURE_PATH)/si/back_forth.pdf: SI_back_forth.ipynb $(DATA_FILES)
	jupyter nbconvert --execute SI_back_forth.ipynb
	rm SI_back_forth.html 

FILENMS = fig2.pdf fig3.pdf fig4.pdf d3map/data/graph_E_CO2i.json
MAIN_FIGS = $(FILENMS:%=$(FIGURE_PATH)/main/%)
SI_FILENMS = daily_profiles/daily_profiles.pdf monthly_sums.pdf AMPD_report.html annualPlot/dummy sankey/data_small.json back_forth.pdf
SI_FIGS = $(SI_FILENMS:%=$(FIGURE_PATH)/si/%)

.PHONY: all
all: $(MAIN_FIGS) $(SI_FIGS)
