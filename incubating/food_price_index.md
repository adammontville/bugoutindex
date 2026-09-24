# Food Price Index (FPI)

## Shadow series now on the site

The weekly publisher shows one FRED series as a shadow companion. It is labeled **not in the BugOut Index**, it has **no weight**, and it is not an input to `compute_index` or `CORE_METRICS`. A failed fetch does not abort the publish. When a previous block exists, that block is carried forward with its FRED observation date.

| Reading | FRED ID | BLS ID | What it is |
| --- | --- | --- | --- |
| Food CPI, year over year | `CPIUFDNS` | `CUUR0000SAF1` | CPI-U food, U.S. city average, **not seasonally adjusted**, 12-month percent change |

`CPIUFDNS` is the FRED id for the BLS not-seasonally-adjusted food index (1982–84=100). FRED does not publish `CUUR0000SAF1` or `CUSR0000SAF1` as series ids. The seasonally adjusted food index on FRED is `CPIUFDSL` (BLS `CUSR0000SAF1`). It is not used. BLS prints the 12-month food change from the not-seasonally-adjusted index; that is the household-facing number on the CPI news release. Seasonal adjustment is the 1-month convention, not this 12-month print.

The stored value is that 12-month percent change, rounded half-up to one decimal so it matches the BLS 12-month table. The date is the FRED observation date of the later index month. The index level itself is not charted.

`fetch_food_price_index` remains fail-closed (`NOT_WIRED`). The weekly job calls `fetch_food_shadow` and does not call the stub.

## Description
The Food Price Index (FPI) measures the cost of food relative to a baseline, providing insights into food affordability and accessibility. It is a critical indicator of economic stability, particularly for low-income populations, and can signal the risk of food insecurity during inflationary periods or supply chain disruptions.

## Data Source
- **Shipped companion**: BLS CPI-U food via FRED `CPIUFDNS` (BLS `CUUR0000SAF1`), 12-month percent change, not seasonally adjusted.
- **Not used**: FRED `CPIUFDSL` / BLS `CUSR0000SAF1` (seasonally adjusted index).
- **Alternative sources, not fetched**:
  - United Nations Food and Agriculture Organization (FAO) Food Price Index.
  - USDA Economic Research Service.

## Normalization
Draft only. This range is **not** applied, and it is **not** a contribution to the BugOut Index.

- **Range**: 0% (Stable food prices) to 10% (Significant food inflation).
- **Formula**:

Normalized Score = (1 - (Food Inflation Rate / 10)) * 100

## Purpose
The FPI is used to track affordability and accessibility of food, particularly in times of economic instability. Sharp increases in food prices often precede societal unrest and highlight the vulnerability of supply chains.

## Draft Status
The shadow series above is on the weekly site. Any future weight, including the 0–10% draft, is still incubating. Nothing in this note enters `compute_index` unless a later methodology version says so.

**Disclaimer**: Redistribution or use without explicit written permission is prohibited.
