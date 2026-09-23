# Air Quality Index (AQI)

**Status: PARKED** (Adam Montville, 2026-09-23). Off the active incubating list. Not near-term work. Not in the BugOut Index. `fetch_air_quality_index` is fail-closed (`NOT_WIRED`) and the weekly publisher does not call it.

The note below is the original stub. It is kept so the idea is findable. It is not a commitment to build a series. A national air-quality average is a health and environment reading, not a directional weekly measure of the societal conditions the index tracks.

## Description
The Air Quality Index (AQI) measures air pollution levels and their impact on human health. Higher values indicate poorer air quality and greater health risks.

## Data Source
- **Primary Source**: EPA’s AirNow API ([https://www.airnow.gov/](https://www.airnow.gov/))
- **Alternative Sources**: OpenWeatherMap API or local environmental agencies.

## Normalization
- **Range**: 0 (Good) to 500 (Hazardous)
- **Formula**:
