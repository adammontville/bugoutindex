# Crime input refresh replay

Research only. This note scores the **unweighted** RTCI mean. Methodology **1.1.0** later chose the population-weighted Nationwide Full Sample rate instead. The tables below were not rewritten. The published week of 2026-10-02 stays **57.04** under methodology **1.0.0** until a later weekly publish. `compute_index` endpoints and weights, the bands, the weekly history, and schema version 1 are unchanged by this note.

## Conclusion

Giving each published week the newest RTCI month available that day would have raised the index by **1.28 to 1.44** points. All 25 weeks would still have read **Moderate Stability**. The published range in this history is 56.28 to 57.15. The live-crime range is 57.70 to 58.59.

On the 2026-10-02 basket the published crime input is **2723.0** and the score is **57.04**. The text-sort month in that file, **September 2025 at 2234.66**, scores **58.13**. The newest calendar month in that same file, **April 2026 at 2074.97**, scores **58.48**. Both stay Moderate.

| Basket | Crime value | RTCI month | Score | Band |
| --- | ---: | ---: | ---: | ---: |
| Published 2026-10-02 | 2723.0 | Locked input | 57.04 | Moderate |
| Same other inputs, text-sort month | 2234.66 | September 2025 | 58.13 | Moderate |
| Same other inputs, newest month in that file | 2074.97 | April 2026 | 58.48 | Moderate |

The lock was deliberate. [Pull request #78](https://github.com/adammontville/bugoutindex/pull/78) (commit [`9a7594a`](https://github.com/adammontville/bugoutindex/commit/9a7594a85c7b44bbd514438ccbd20959c6d4ad61), merged 22 September 2026) started the weekly download of the AH-Datalytics file and stored **2723.0** as `PUBLISHED_INCIDENT_RATE` in the same change. The pull request says accepting another rate is a separate reviewed revision. Methodology 1.1.0 is that revision: the scored input is the Nationwide Full Sample rate, not this note's unweighted column. `PUBLISHED_INCIDENT_RATE` remains the 1.0.0 baseline used above.

## Where 2723.0 comes from

Before that pull request the fetcher read the local file `runtime/data/final_sample.csv`. Every row's `Last Updated` is **2025-02-19**. The usable sample is **399** agencies. The fetcher took the lexicographic maximum of the `Date` text, which is **September 2024**, and the unweighted mean of agency rates that month is **2723.0**. That is the locked input.

The latest calendar month in that same local file is **December 2024** at **2654.48**. "September" sorts after "December", so the text-sort rule stayed on September 2024 while a later month was already in the file. The weekly runs kept reprinting 2723.0 because the local file and that sort rule did not move.

The current file's September 2024 rate is **2481.82** on **621** agencies. 2723.0 is the old file's September 2024 print. It is a different sample from the rates in the tables below.

## How the live-crime column is built

The score is `compute_index`. Crime endpoints stay **500 to 8000**. The crime weight stays **0.12**. The other five weights are unchanged, so a full row still divides by **0.72**. Trust stays inverted. Bands stay 70, 55, and 40.

The crime value is the unweighted mean of usable rows for the latest calendar month in the RTCI cleaned file that was on [AH-Datalytics/rtci](https://github.com/AH-Datalytics/rtci) `main` at the start of that publication date:

`(Violent Crime_mvs_12mo + Property Crime_mvs_12mo) / FBI.Population.Covered × 100,000`

Rows with a missing count or a non-positive population are left out. Each remaining row counts once, including RTCI aggregate rows (state and nationwide Full Sample, and population-band aggregates). That is the same construction as the crime diagnostic, and it is what produces the locked 2723.0 on the old local file. It is not the population-weighted national total. That alternative is the sum of crimes over the sum of population on the same rows; on the cleaned file it matches the Nationwide Full Sample rate. It is stored on the vintage file and is not scored. This replay does not change that construction.

Committed index history runs from **2026-04-21** through **2026-10-02**. There is no earlier six-metric publication to rescore. Weeks between RTCI releases keep the latest month already in the file.

| What changed | What stayed |
| --- | --- |
| Crime raw value | Inflation, unemployment, debt-to-GDP, homelessness, and trust on that weekly row |
| Which RTCI month supplied that value | v1.0.0 endpoints, weights, trust inversion, clamp, and divide-by-sum-of-weights |

## RTCI file on each publication date

The four files below are the `docs/app_data/final_sample.csv` commits on RTCI `main` during this history. The May 18 row is the later commit that day (`40c9ab09`), after the population regenerate. No weekly publication falls on an RTCI commit date, so the publication date is enough to pick the file.

| RTCI file | Publications | Latest month | Crime value | Agencies | Text-sort month | Text-sort value |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| [2026-04-16](https://github.com/AH-Datalytics/rtci/commit/6d87764cb042dbb2ec0ba7c2a36e692ecb2c533b) | 2026-04-21 | February 2026 | 2146.38 | 498 | September 2025 | 2285.03 |
| [2026-04-24](https://github.com/AH-Datalytics/rtci/commit/0786cfa2188da0c2730b51d624399db7ef7b22ee) | 2026-04-25 through 2026-05-15 | February 2026 | 2146.42 | 498 | September 2025 | 2285.03 |
| [2026-05-18](https://github.com/AH-Datalytics/rtci/commit/40c9ab093775c537f681a1a860bd90abf3e757f2) | 2026-05-22 through 2026-06-12 | March 2026 | 2092.21 | 612 | September 2025 | 2229.84 |
| [2026-06-16](https://github.com/AH-Datalytics/rtci/commit/bc66ee94d57cae9f85ea738d6a1a8861e8f9d49a) | 2026-06-19 through 2026-10-02 | April 2026 | 2074.97 | 621 | September 2025 | 2234.66 |

February 2026 moved from 2146.38 to 2146.42 on 24 April 2026. Both round to the same index on the weeks that use them. March 2026 and April 2026 are new months, on a larger agency sample (498, then 612, then 621).

## Publication table

Live-crime score: the other five published inputs, with crime set to the latest calendar month in the file above.

| Publication | Locked score | Live-crime score | Difference | Crime value | RTCI month | Agencies |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 2026-04-21 | 57.03 | 58.31 | +1.28 | 2146.38 | February 2026 | 498 |
| 2026-04-25 | 57.03 | 58.31 | +1.28 | 2146.42 | February 2026 | 498 |
| 2026-05-01 | 57.03 | 58.31 | +1.28 | 2146.42 | February 2026 | 498 |
| 2026-05-08 | 57.03 | 58.31 | +1.28 | 2146.42 | February 2026 | 498 |
| 2026-05-15 | 56.62 | 57.90 | +1.28 | 2146.42 | February 2026 | 498 |
| 2026-05-22 | 56.62 | 58.02 | +1.40 | 2092.21 | March 2026 | 612 |
| 2026-05-29 | 56.62 | 58.02 | +1.40 | 2092.21 | March 2026 | 612 |
| 2026-06-05 | 56.62 | 58.02 | +1.40 | 2092.21 | March 2026 | 612 |
| 2026-06-12 | 56.30 | 57.70 | +1.40 | 2092.21 | March 2026 | 612 |
| 2026-06-19 | 56.28 | 57.72 | +1.44 | 2074.97 | April 2026 | 621 |
| 2026-06-26 | 56.30 | 57.74 | +1.44 | 2074.97 | April 2026 | 621 |
| 2026-07-03 | 56.36 | 57.80 | +1.44 | 2074.97 | April 2026 | 621 |
| 2026-07-10 | 56.36 | 57.80 | +1.44 | 2074.97 | April 2026 | 621 |
| 2026-07-17 | 56.95 | 58.39 | +1.44 | 2074.97 | April 2026 | 621 |
| 2026-07-24 | 56.95 | 58.39 | +1.44 | 2074.97 | April 2026 | 621 |
| 2026-08-01 | 56.95 | 58.39 | +1.44 | 2074.97 | April 2026 | 621 |
| 2026-08-07 | 57.02 | 58.46 | +1.44 | 2074.97 | April 2026 | 621 |
| 2026-08-14 | 57.15 | 58.59 | +1.44 | 2074.97 | April 2026 | 621 |
| 2026-08-21 | 57.15 | 58.59 | +1.44 | 2074.97 | April 2026 | 621 |
| 2026-08-29 | 57.15 | 58.59 | +1.44 | 2074.97 | April 2026 | 621 |
| 2026-09-05 | 57.15 | 58.59 | +1.44 | 2074.97 | April 2026 | 621 |
| 2026-09-12 | 57.11 | 58.55 | +1.44 | 2074.97 | April 2026 | 621 |
| 2026-09-19 | 57.11 | 58.55 | +1.44 | 2074.97 | April 2026 | 621 |
| 2026-09-25 | 57.11 | 58.55 | +1.44 | 2074.97 | April 2026 | 621 |
| 2026-10-02 | 57.04 | 58.48 | +1.44 | 2074.97 | April 2026 | 621 |

## Text-sort month, for the snapshot figure

The pre-lock fetcher selected `Date.max()`, a text sort. On every file in this window that sort lands on **September 2025**. The 2 October publish stored that month as the candidate (**2234.66**). `latest_month` on the same snapshot was already the calendar month. The fetcher now writes the calendar month into the candidate as well. The scored input stays **2723.0**. The text-sort rate itself moved as the sample grew: 2285.03 (498 agencies), then 2229.84 (612), then **2234.66** (621). On the 2026-10-02 basket, 2234.66 scores **58.13** against the published **57.04**.

Across the 25 weeks this rule lifts the index by **0.97 to 1.10** points. The band stays Moderate Stability.

| Publication | Locked score | Text-sort score | Difference | Crime value | RTCI month | Agencies |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 2026-04-21 | 57.03 | 58.01 | +0.98 | 2285.03 | September 2025 | 498 |
| 2026-04-25 | 57.03 | 58.01 | +0.98 | 2285.03 | September 2025 | 498 |
| 2026-05-01 | 57.03 | 58.01 | +0.98 | 2285.03 | September 2025 | 498 |
| 2026-05-08 | 57.03 | 58.01 | +0.98 | 2285.03 | September 2025 | 498 |
| 2026-05-15 | 56.62 | 57.59 | +0.97 | 2285.03 | September 2025 | 498 |
| 2026-05-22 | 56.62 | 57.72 | +1.10 | 2229.84 | September 2025 | 612 |
| 2026-05-29 | 56.62 | 57.72 | +1.10 | 2229.84 | September 2025 | 612 |
| 2026-06-05 | 56.62 | 57.72 | +1.10 | 2229.84 | September 2025 | 612 |
| 2026-06-12 | 56.30 | 57.39 | +1.09 | 2229.84 | September 2025 | 612 |
| 2026-06-19 | 56.28 | 57.37 | +1.09 | 2234.66 | September 2025 | 621 |
| 2026-06-26 | 56.30 | 57.38 | +1.08 | 2234.66 | September 2025 | 621 |
| 2026-07-03 | 56.36 | 57.45 | +1.09 | 2234.66 | September 2025 | 621 |
| 2026-07-10 | 56.36 | 57.45 | +1.09 | 2234.66 | September 2025 | 621 |
| 2026-07-17 | 56.95 | 58.03 | +1.08 | 2234.66 | September 2025 | 621 |
| 2026-07-24 | 56.95 | 58.03 | +1.08 | 2234.66 | September 2025 | 621 |
| 2026-08-01 | 56.95 | 58.03 | +1.08 | 2234.66 | September 2025 | 621 |
| 2026-08-07 | 57.02 | 58.10 | +1.08 | 2234.66 | September 2025 | 621 |
| 2026-08-14 | 57.15 | 58.23 | +1.08 | 2234.66 | September 2025 | 621 |
| 2026-08-21 | 57.15 | 58.23 | +1.08 | 2234.66 | September 2025 | 621 |
| 2026-08-29 | 57.15 | 58.23 | +1.08 | 2234.66 | September 2025 | 621 |
| 2026-09-05 | 57.15 | 58.23 | +1.08 | 2234.66 | September 2025 | 621 |
| 2026-09-12 | 57.11 | 58.19 | +1.08 | 2234.66 | September 2025 | 621 |
| 2026-09-19 | 57.11 | 58.19 | +1.08 | 2234.66 | September 2025 | 621 |
| 2026-09-25 | 57.11 | 58.19 | +1.08 | 2234.66 | September 2025 | 621 |
| 2026-10-02 | 57.04 | 58.13 | +1.09 | 2234.66 | September 2025 | 621 |

## Monthly RTCI on the current file

`runtime/backtest/fixtures/v2/RTCI_monthly.csv` is the June 16 file (commit `bc66ee94`, pull recorded 26 September 2026). It contains September 2025 **2234.66** and April 2026 **2074.97**, 621 agencies, population-weighted April 2026 **2443.27**.

The table scores each month from September 2024 through April 2026 on the **2026-10-02** inputs. Inflation, unemployment, debt, homelessness, and trust stay on that one row. These are revised rates in the current file. An earlier Friday's file had a smaller sample and a different rate for the same month. The publication table above is the rate that was available that day.

| RTCI month | Crime value | Agencies | Score on 2026-10-02 inputs | Difference from 57.04 |
| --- | ---: | ---: | ---: | ---: |
| September 2024 | 2481.82 | 621 | 57.58 | +0.54 |
| October 2024 | 2467.79 | 621 | 57.61 | +0.57 |
| November 2024 | 2453.24 | 621 | 57.64 | +0.60 |
| December 2024 | 2434.44 | 621 | 57.68 | +0.64 |
| January 2025 | 2411.36 | 621 | 57.73 | +0.69 |
| February 2025 | 2379.13 | 621 | 57.81 | +0.77 |
| March 2025 | 2363.42 | 621 | 57.84 | +0.80 |
| April 2025 | 2345.56 | 621 | 57.88 | +0.84 |
| May 2025 | 2325.48 | 621 | 57.92 | +0.88 |
| June 2025 | 2304.72 | 621 | 57.97 | +0.93 |
| July 2025 | 2282.94 | 621 | 58.02 | +0.98 |
| August 2025 | 2258.54 | 621 | 58.07 | +1.03 |
| September 2025 | 2234.66 | 621 | 58.13 | +1.09 |
| October 2025 | 2206.54 | 621 | 58.19 | +1.15 |
| November 2025 | 2178.66 | 621 | 58.25 | +1.21 |
| December 2025 | 2150.72 | 621 | 58.31 | +1.27 |
| January 2026 | 2130.84 | 621 | 58.36 | +1.32 |
| February 2026 | 2116.11 | 621 | 58.39 | +1.35 |
| March 2026 | 2096.18 | 621 | 58.43 | +1.39 |
| April 2026 | 2074.97 | 621 | 58.48 | +1.44 |

September 2024 in this file is 2481.82 and scores 57.58 on the latest basket. April 2026 is 2074.97 and scores 58.48. The path between them is a lower rate on a fixed 621-agency sample. The further gap from the locked 2723.0 down to 2481.82 is the old 399-agency print against this revised sample.

## How to run

From the repository root:

```bash
python -m runtime.backtest.crime_live_replay
```

That rewrites this note, `runtime/backtest/output/crime_live_publications.csv`, and `runtime/backtest/output/crime_live_monthly.csv`. No network and no `FRED_API_KEY`. The vintage rates are checked in at `runtime/backtest/fixtures/crime_asof_vintages.csv`.

## What stays put

`docs/data/latest.json` and `runtime/data/weekly_bugout_index.csv` still carry crime **2723.0** and the 2026-10-02 index **57.04** under methodology 1.0.0. This note does not republish that week. Methodology 1.1.0 scores the population-weighted Nationwide Full Sample rate on later publishes. The tables above remain the unweighted counterfactual.
