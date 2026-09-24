# Food Price Index (FPI)

**Status:** Next companion candidate (Adam Montville, 2026-09-23). Not in the BugOut Index. No weight. The real fetcher is a follow-up, not this note. `fetch_food_price_index` is fail-closed (`NOT_WIRED`) until that follow-up lands a cited FRED or BLS series. The weekly publisher does not call it.

Food is the next incubating idea worth a real companion series: a published food CPI (or a clearly named food component), shown beside the score with a source and an observation date. The normalization range below is a draft. It is not v1.0.0 math.

## Description
The Food Price Index (FPI) measures the cost of food relative to a baseline, providing insights into food affordability and accessibility. It is a critical indicator of economic stability, particularly for low-income populations, and can signal the risk of food insecurity during inflationary periods or supply chain disruptions.

## Data Source
- **Primary Source**: The U.S. Bureau of Labor Statistics (BLS) Consumer Price Index (CPI) food component.
- **Alternative Sources**:
  - United Nations Food and Agriculture Organization (FAO) Food Price Index.
  - USDA Economic Research Service.

## Normalization
- **Range**: 0% (Stable food prices) to 10% (Significant food inflation).
- **Formula**:

Normalized Score = (1 - (Food Inflation Rate / 10)) * 100

## Purpose
The FPI is used to track affordability and accessibility of food, particularly in times of economic instability. Sharp increases in food prices often precede societal unrest and highlight the vulnerability of supply chains.

## Draft Status
Next companion candidate only. Not under construction in the weekly job, and not a promise that the 0–10% draft range will ship. A follow-up may add a real fetcher. That fetcher still does not enter `compute_index` unless a later methodology version says so.

**Disclaimer**: Redistribution or use without explicit written permission is prohibited.