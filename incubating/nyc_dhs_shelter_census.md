# NYC DHS Daily Shelter Census — companion only

The weekly publisher shows one NYC Open Data series as a shadow companion. It is labeled **New York City only** and **not in the BugOut Index**. It has **no weight**, and it is not an input to `compute_index` or `CORE_METRICS`. A failed fetch does not abort the publish. When a previous block exists, that block is carried forward with its census date.

This note is the issue [#81](https://github.com/adammontville/bugoutindex/issues/81) companion for homelessness frequency. It does not change the live score.

## What stays in the score

HUD AHAR Part 1 remains the annual national homelessness anchor. The published input is still **0.23**, HUD reference date **2024-01-01**, read from `runtime/data/annual_inputs.csv`. Methodology version stays **1.0.0**.

## What this companion is

| | |
| --- | --- |
| Publisher | NYC Department of Homeless Services, via NYC Open Data |
| Dataset | [DHS Daily Report](https://data.cityofnewyork.us/Social-Services/DHS-Daily-Report/k46n-sa2m) (`k46n-sa2m`) |
| Field | `total_individuals_in_shelter` |
| Definition | Single adults, people in adult families, and adults and children in families with children in the DHS shelter system on the census date |
| Cadence | Daily |
| Geography | New York City only. Not a U.S. total |
| Stored as | A headcount, not a percent of population |

The families-with-children column (`total_individuals_in_families_with_children_in_shelter_`) is a subset. The companion uses the shelter-system total.

## How it differs from HUD AHAR

HUD AHAR is a national point-in-time rate, sheltered and unsheltered, about once a year. This series is a New York City shelter headcount, updated most days, and it does not include people who are unsheltered. Same topic, different place, different definition, different cadence. That is why it sits beside the index instead of replacing the annual checklist.

## Recommendation

**Add as a shadow/companion. Keep the annual HUD checklist for the score.** A later methodology version would be required before this, or any other local series, could enter `compute_index`.

Ramsey County, Toronto, and San Francisco sit in the same companion panel. The sources that were checked and skipped are in [shelter_census_companions.md](shelter_census_companions.md).
