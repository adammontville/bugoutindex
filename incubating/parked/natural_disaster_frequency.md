# Natural Disaster Frequency

**Status: PARKED** (Adam Montville, 2026-09-23). Off the active incubating list. Not near-term work. Not in the BugOut Index. `fetch_natural_disaster_frequency` is fail-closed (`NOT_WIRED`) and the weekly publisher does not call it.

The note below is the original stub. Disaster counts are regional and episodic. They do not provide a directional weekly reading of national conditions, which is what the index is for.

## Description
This metric tracks the frequency and severity of natural disasters, including hurricanes, earthquakes, and wildfires, as a measure of environmental and societal stability.

## Data Source
- **Primary Source**: NOAA National Centers for Environmental Information ([https://www.ncdc.noaa.gov/](https://www.ncdc.noaa.gov/))
- **Alternative Sources**: USGS Earthquake Data, FEMA Disaster Declarations.

## Normalization
- **Range**: 0 (High frequency) to 100 (Low frequency)
- **Formula**:
