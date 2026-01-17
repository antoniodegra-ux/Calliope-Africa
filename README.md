### Energy Planning for the Eastern Africa Power Pool (EAPP): Geographically Explicit Modelling of Renewable Integration

This repository contains code for performing Calliope-based optimization of energy distribution across the Eastern Africa Power Pool (EAPP). It focuses on the geographically explicit modeling of renewable energy integration within the region.

This work is part of the Master’s thesis project by Antonio De Grazia and Ilaria Cigala at Politecnico di Milano.

The folder *pre_processing* contains information about the individualization and classification of the Wind and Solar **MSRs (Model Supply Regions)**
The folder *model* contains the input files to be used in Calliope pipeline. 
The folder *post_processing* contains the code to generate the final plots of the results and additional analysis.  
To run the model for each reference scenario, navigate to the model directory and select the year to be simulated along with the macro-scenario type (Existing Transmission, Transmission Expansion, or Autarky).
From there, run the Run_in_Spyder.py file, which sequentially launches the six sub-scenarios.