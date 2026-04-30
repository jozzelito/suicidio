# SUICIDE MORTALITY RATE
**Homicide and Unemployment Database for Mexico (1990-2024)**
This repository contains two data files for the analysis of violence and socioeconomic factors in Mexico. The objective is to identify risk groups to design prevention campaigns for the health sector.

# Content
data.xlsx - Homicides by federal entity, sex, and rates per 100,000 inhabitants (1990-2024)
unemployment.csv - National total unemployment rate (1991-2025)

# Data Sources
Homicides: Provided as data.xlsx. Source is not specified. Contains data from 1990 to 2024 for 32 federal entities plus Nacional, Extranjero, and Not specified.
Unemployment: World Bank / International Labour Organization. Indicator SL.UEM.TOTL.ZS. Coverage 1991-2025. The 2025 value is preliminary.

# Structure
The homicide file includes the following columns: ANO (year), CVE_ENT (entity code), ENTIDAD (entity name), HOMBRES (male victims), MUJERES (female victims), DESCONOCIDO (unknown sex), TOTAL (total victims), POBLACION_HOMBRES (male population), POBLACION_MUJERES (female population), POBLACION_TOTAL (total population), TASA_HOMBRES (male rate), TASA_MUJERES (female rate), TASA_TOTAL (total rate). Rates are calculated per 100,000 inhabitants.

# The unemployment file contains columns: date, value (unemployment percentage), and additional metadata from the World Bank API.
Application for the Health Sector
This database allows identification of high-risk groups through the following analyses:
Temporal trends in homicides by sex and entity to detect sustained increases
Correlation between violence and unemployment as a social determinant of health
Identification of entities with rates above the national average to target interventions
Comparison of sex-based gaps to design differentiated campaigns

# Limitations
The homicide data prior to 2015 may have underreporting. The "Not specified" category (code 99) represents victims without an assigned entity. The foreign population (code 33) has no population data for rate calculation. Unemployment data is only available at the national level and cannot be disaggregated by entity.

# Suggested Use
To identify risk groups, calculate percentiles by entity and year, analyze homicide rates by sex, and construct time series for each state. Combining homicide data with unemployment allows assessment of the relationship between economic conditions and violence at the national level.

# License
Public and academic use. Users should cite the original sources of each dataset if known.

# Contributions
Contributions that add unemployment data by entity, mental health indicators, or health service availability by state are welcome to enrich prevention analysis.
