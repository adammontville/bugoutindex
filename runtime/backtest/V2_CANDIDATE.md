# v2 candidate replay (baskets A, B, and C)

Research only. This note is not a methodology version, and it is not the live BugOut Index. The scores below are not inputs to `compute_index`, the weekly publisher, `docs/data/latest.json`, or the weekly history. Pew trust, Gallup confidence, and the shelter companions stay outside the score. Merging this branch does not publish to GitHub Pages.

**Stay on methodology 1.1.1.** The current reading is **57.50 Moderate**. Basket A is **61.87 Moderate**, basket B is **60.25 Moderate**, and basket C is **59.85 Moderate**. All four sit in Moderate. The previous hypothesis h2 printed **77.28 High** for August 2026. That basket dropped debt, homelessness, and trust and filled the weight with a calm labor blend and a calm VIX. The High reading was that composition. These three baskets keep the six 1.1.1 inputs. Each add-on that is calm today lifts the reading, and each basket that catches one stress period is calm through another. Headline CPI already puts every month of 2022 in Low Stability on 1.1.1 (12 of 12 months). A new published basket is not required to see that year.

Read this file. You do not need to run the harness. Month-by-month numbers are in [`output/v2_candidate_monthly.csv`](output/v2_candidate_monthly.csv). Window ranges are in [`output/v2_candidate_summary.csv`](output/v2_candidate_summary.csv). Friday-to-Friday moves are in [`output/v2_candidate_weekly.csv`](output/v2_candidate_weekly.csv). A chart of the same monthly series is [`output/v2_candidate_chart.svg`](output/v2_candidate_chart.svg).

The 19 September 2026 published row still scores **57.11 Moderate** through `compute_index` under methodology 1.0.0 (crime 2723, homelessness 0.23, trust 41). The committed `latest.json` is the 9 October 2026 week, methodology 1.1.0, index **57.66**. Scoring those six published raws through `compute_index` returns **57.66 Moderate**. This replay does not rewrite that file. The 1.1.1 restatement changes only the two checklist cells.

## Current reading next to the stress months

The current row uses the 9 October 2026 published raws for inflation, unemployment, debt, and crime, and the 1.1.1 checklist for homelessness (**0.22**, 2025-01-01) and trust (**39**, survey year 2026). Food is the shadow print **2.7** (2026-08-01). Prime-age EPOP is the shadow print **80.7** (2026-09-01). Mortgage delinquency is **1.86** (2026-04-01, carried_forward). Rent burden is **51.8** (2024-01-01, carried_forward). VIX is the week ending **2026-10-09** mean **15.17**. Credit conditions are the Chicago Fed print for **2026-10-02**, **-0.026**.

August 2026 in the monthly file is a different row: unemployment is the August print 4.1, EPOP is 80.4, and VIX is the August monthly mean. Crime on both rows is the April 2026 Nationwide Full Sample rate **2443.27**, carried forward after the RTCI file ends. The unweighted agency mean that month is **2074.97** and is not scored.

| Reading | v1 1.1.1 | A labor and food | B cost of living | C financial stress |
| --- | --- | --- | --- | --- |
| Current (2026-10-09 inputs, 1.1.1 checklist) | 57.50 Moderate | 61.87 Moderate | 60.25 Moderate | 59.85 Moderate |
| 2008-10-01 — VIX and credit conditions jump | 56.89 Moderate | 58.12 Moderate | 55.05 Moderate | 48.10 Low |
| 2008-11-01 — VIX monthly-mean peak; credit week of 5 Dec is the file high | 59.29 Moderate | 59.97 Moderate | 56.92 Moderate | 48.95 Low |
| 2009-10-01 — Unemployment 10.0 and mortgage delinquency 10.41 | 56.97 Moderate | 59.90 Moderate | 54.86 Low | 57.61 Moderate |
| 2009-12-01 — Great Recession window ends; RTCI crime is still absent | 54.01 Low | 57.35 Moderate | 52.69 Low | 56.14 Moderate |
| 2020-03-01 — COVID VIX monthly-mean peak | 59.03 Moderate | 62.70 Moderate | 62.83 Moderate | 53.57 Low |
| 2020-04-01 — Unemployment 14.8 and prime-age EPOP trough; bank delinquency stayed low | 50.98 Low | 48.90 Low | 55.88 Moderate | 49.44 Low |
| 2022-06-01 — Headline CPI and food CPI high | 52.28 Low | 52.90 Low | 52.45 Low | 53.20 Low |
| 2022-09-01 — Food CPI year-over-year high in this pull | 52.95 Low | 53.27 Low | 52.65 Low | 53.86 Low |
| 2025-10-01 — BLS publication gap | 53.76 Low | 53.76 Low | 57.21 Moderate | 57.47 Moderate |
| 2026-04-01 — Last month in the RTCI file | 57.07 Moderate | 61.25 Moderate | 59.69 Moderate | 58.73 Moderate |
| 2026-08-01 — Last headline CPI month in this pull | 57.56 Moderate | 61.73 Moderate | 60.30 Moderate | 59.93 Moderate |

Bands are the live bands from `interpret`: High at or above 70, Moderate at or above 55, Low at or above 40, Critical below 40. Applying those bands to a wider basket is part of the research. The thresholds were not retuned.

## What the three baskets are

Every basket starts from the six live inputs and their live weights. The weights sum to 0.72 before any add-on. Each add-on has raw weight **0.08**. When an input is missing, its weight drops out and the denominator shrinks. The index is `Σ(normalized × weight) / Σ weight`, the same rule as `compute_index`. v1 component scores in the `v1_111` column are `compute_index` itself.

| Input | Raw weight | Range | Direction | Where it sits |
| --- | --- | --- | --- | --- |
| Headline CPI YoY (`CPIAUCSL`) | 0.15 | −10 to 15 | higher is less stable | Live inflation input. In every basket. |
| Crime, RTCI Nationwide Full Sample | 0.12 | 500 to 8,000 | higher is less stable | Live crime input from methodology 1.1.0. Absent before January 2018. Carried after the file's last month. |
| Unemployment (`UNRATE`) | 0.12 | 0 to 25 | higher is less stable | Live labor input. Basket A adds EPOP beside it and does not replace it. |
| Debt-to-GDP (`GFDEGDQ188S`) | 0.12 | 0 to 200 | higher is less stable | Live input. This replay uses the quarterly file through 2026 Q1. |
| Homelessness | 0.09 | 0 to 0.5 | higher is less stable | Held at the 1.1.1 checklist 0.22 (2025-01-01). Not a historical path. |
| Trust in government | 0.12 | 0 to 80 | higher is more stable | Held at the 1.1.1 checklist 39 (survey year 2026). Not a historical path. |
| Food CPI YoY (`CPIUFDNS`) | 0.08 | −2 to 15 | higher is less stable | Baskets A and B. Same one-decimal print as the food shadow. The live score does not use it. |
| Prime-age EPOP (`LNS12300060`) | 0.08 | 68 to 82 | higher is more stable | Basket A only. Not the 0.70/0.30 labor blend. |
| Mortgage delinquency (`DRSFRMACBS`) | 0.08 | 1 to 12 | higher is less stable | Basket B. Quarterly bank series, carried forward within the file. |
| Rent burden, ACS 30%+ (`B25070`) | 0.08 | 40 to 60 | higher is less stable | Basket B. Annual. The 50%+ share is stored and not scored. |
| VIX monthly mean (`VIXCLS`) | 0.08 | 10 to 65 | higher is less stable | Basket C. Mean of daily closes. The weekly path uses that week's mean in the same slot. |
| Credit conditions (`NFCICREDIT`) | 0.08 | −4 to 4 | higher is less stable | Basket C. Chicago Fed NFCI credit subindex, monthly mean of the Friday prints. Not an ICE or Moody's spread. |

Basket A is the live score plus food CPI and prime-age EPOP. Basket B is the live score plus food CPI, mortgage delinquency, and the ACS 30%+ rent-burden share. Basket C is the live score plus the VIX monthly mean and the Chicago Fed NFCI credit subindex. Food is in both A and B so the 2022 food spike is visible in the cost-of-living basket and in the labor basket. The 0.70 × EPOP + 0.30 × participation blend from hypothesis h2 is not used.

Prime-age EPOP in the BLS fixture runs **69.6** (2020-04-01) to **80.9** (2024-09-01). The Chicago Fed credit file in this replay runs **-3.159** (1973-03-16) to **3.490** (1980-05-02). The −4 to 4 credit range sits outside that file. It was not chosen to push the current reading under 70.

### Why the credit input is not an ICE spread

ICE BofA high-yield OAS (`BAMLH0A0HYM2`) and Moody's seasoned Baa yield are the usual credit-spread prints. Both licenses forbid copying the series into this repository. FRED's ICE history is also a rolling three-year window as of April 2026, so that file cannot cover 2008. Basket C uses the Chicago Fed NFCI credit subindex (`NFCICREDIT`), which the Chicago Fed publishes as a weekly credit-conditions index (average 0, standard deviation 1 since 1971). Positive means tighter than that average. It is built from credit-condition measures. It is not a bond spread in percentage points, and it is not labeled as one.

### What hypothesis h2 did

h2 is the previous labeled basket on this branch: CPI, food, a labor blend, VIX, and an unweighted crime trial. Debt, homelessness, and trust were out. Those six months are the prior committed replay. This command does not recompute them.

| Month | Prior h2 |
| --- | --- |
| 2008-10-01 | 50.79 Low |
| 2009-10-01 | 65.79 Moderate |
| 2020-03-01 | 62.82 Moderate |
| 2020-04-01 | 44.34 Low |
| 2022-06-01 | 59.19 Moderate |
| 2026-08-01 | 77.28 High |

August 2026 on h2 was **77.28 High** against a v1 held-constant score of **57.11 Moderate**. The gap was the basket. A calm labor blend and a calm VIX replaced unemployment, and the three slower stressed series were gone. Keeping those three series is why the current 1.1.1 reading and all three new baskets stay in Moderate.

## Full history and the stress windows

The monthly file is every month from January 2007 through August 2026 for which the BLS CPI fixture can form a year-over-year rate. October 2025 stays blank for CPI, food, unemployment, and EPOP. Debt is the quarterly `GFDEGDQ188S` file fetched 2026-10-12, and it covers this span, so 2022 is no longer a debt gap. The earlier h2 note excluded 2022–2025 Q3 debt because that fixture did not contain the quarters. Crime is the population-weighted Nationwide Full Sample rate. Before January 2018 the weight drops out. From May 2026 through August 2026 the April 2026 rate is carried forward and labeled `carried_forward`.

| Window | v1 1.1.1 | A labor and food | B cost of living | C financial stress |
| --- | --- | --- | --- | --- |
| Full history (Jan 2007–Aug 2026) | 50.98 (2020-04-01) to 61.39 (2007-08-01) | 48.90 (2020-04-01) to 65.34 (2007-01-01) | 47.84 (2011-09-01) to 64.43 (2007-01-01) | 48.10 (2008-10-01) to 64.01 (2007-01-01) |
| 2008 (Dec 2007–Dec 2009) | 54.01 (2009-12-01) to 60.01 (2008-12-01) | 57.35 (2009-12-01) to 61.71 (2008-02-01) | 52.69 (2009-12-01) to 60.44 (2007-12-01) | 48.10 (2008-10-01) to 59.30 (2008-05-01) |
| 2020 (Jan–Dec) | 50.98 (2020-04-01) to 59.03 (2020-03-01) | 48.90 (2020-04-01) to 63.30 (2020-02-01) | 55.88 (2020-04-01) to 62.83 (2020-03-01) | 49.44 (2020-04-01) to 61.07 (2020-01-01) |
| 2022 inflation year | 52.28 (2022-06-01) to 54.47 (2022-12-01) | 52.90 (2022-06-01) to 55.18 (2022-01-01) | 52.45 (2022-06-01) to 54.80 (2022-01-01) | 53.20 (2022-06-01) to 56.04 (2022-12-01) |

| Window | Basket | High | Moderate | Low | Critical |
| --- | --- | --- | --- | --- | --- |
| Full history (Jan 2007–Aug 2026) | v1 1.1.1 | 0 | 182 | 54 | 0 |
| Full history (Jan 2007–Aug 2026) | A | 0 | 210 | 26 | 0 |
| Full history (Jan 2007–Aug 2026) | B | 0 | 173 | 63 | 0 |
| Full history (Jan 2007–Aug 2026) | C | 0 | 210 | 26 | 0 |
| 2008 (Dec 2007–Dec 2009) | v1 1.1.1 | 0 | 23 | 2 | 0 |
| 2008 (Dec 2007–Dec 2009) | A | 0 | 25 | 0 | 0 |
| 2008 (Dec 2007–Dec 2009) | B | 0 | 22 | 3 | 0 |
| 2008 (Dec 2007–Dec 2009) | C | 0 | 17 | 8 | 0 |
| 2020 (Jan–Dec) | v1 1.1.1 | 0 | 8 | 4 | 0 |
| 2020 (Jan–Dec) | A | 0 | 8 | 4 | 0 |
| 2020 (Jan–Dec) | B | 0 | 12 | 0 | 0 |
| 2020 (Jan–Dec) | C | 0 | 8 | 4 | 0 |
| 2022 inflation year | v1 1.1.1 | 0 | 0 | 12 | 0 |
| 2022 inflation year | A | 0 | 1 | 11 | 0 |
| 2022 inflation year | B | 0 | 0 | 12 | 0 |
| 2022 inflation year | C | 0 | 3 | 9 | 0 |

No month in this file is High on v1 or on A, B, or C. No month is Critical.

Basket B's full-history low is 47.84 Low on 2011-09-01. Rent burden that month is the 2011 survey peak 53.4 (2011-01-01), and mortgage delinquency is 10.50. Unemployment is 9.0. 1.1.1 is 52.69 Low. The two household add-ons are stressed at once, and that is what pushes B below v1.

## Composition

Component scores use the ranges above. A component above the 1.1.1 reading pulls a basket up. A component below it pulls the basket down. The displayed component is rounded to two decimals. The index uses the unrounded component, then rounds the quotient, the same way `compute_index` does.

**Current reading (2026-10-09).** 1.1.1 is 57.50 Moderate. Food normalizes to 72.35, above the 1.1.1 reading, so it pulls the basket up. Prime-age EPOP normalizes to 90.71, above the 1.1.1 reading, so it pulls the basket up. Mortgage delinquency normalizes to 92.18, above the 1.1.1 reading, so it pulls the basket up. Rent burden normalizes to 41.00, below the 1.1.1 reading, so it pulls the basket down. VIX normalizes to 90.60, above the 1.1.1 reading, so it pulls the basket up. Credit conditions normalizes to 50.32, below the 1.1.1 reading, so it pulls the basket down. The lift in A is mostly EPOP near the top of 68–82. The lift in B is the calm delinquency print overpowering a rent-burden score that does sit below the index. The lift in C is a calm VIX. Credit is about average on the −4 to 4 range and barely moves the reading. None of that is a claim that household stress fell inside the six live inputs.

**October 2008.** 1.1.1 is 56.89 Moderate. Unemployment is 6.5 and crime is excluded, so the financial spike is outside v1. Basket C is 48.10 Low. VIX normalizes to 6.95, below the 1.1.1 reading, so it pulls the basket down. Credit normalizes to 23.29, below the 1.1.1 reading, so it pulls the basket down. That is the month C is for. Basket A is 58.12 Moderate: EPOP was still 78.4 and normalizes to 74.29, above the 1.1.1 reading, so it pulls the basket up. Basket B is 55.05 Moderate. Mortgage delinquency was 6.60, already rising, and the rent-burden print is the 2008 survey carried from January.

**October 2009.** 1.1.1 is 56.97 Moderate with unemployment 10.0. Basket B is 54.86 Low because mortgage delinquency is 10.41 and normalizes to 14.45, below the 1.1.1 reading, so it pulls the basket down. Basket A is 59.90 Moderate. Food CPI was -0.6 and normalizes to 91.76, above the 1.1.1 reading, so it pulls the basket up. That food add-on makes the unemployment-peak month look calmer. EPOP at 75.0 normalizes to 50.00, below the 1.1.1 reading, so it pulls the basket down. Basket C is 57.61 Moderate: the VIX spike was over, and credit had eased, so C does not mark the labor trough of the recession.

**December 2009.** 1.1.1 is 54.01 Low with crime still excluded. The 1.0.0 held-constant column, which pins crime at 2723, is 56.90 Moderate. Part of the gap is the missing crime history. A calm pinned crime rate adds weight on the stable side of the scale. That Low reading is not a 2009 crime spike.

**April 2020.** 1.1.1 is 50.98 Low (unemployment 14.8, Nationwide Full Sample crime 2955.84). The inflation-unemployment-debt partial, the same three-input replay as the locked v1.0.0 harness, is 45.51 Low. The 1.0.0 pins on those FRED inputs are 51.67 Low. Basket A is 48.90 Low. EPOP was 69.6 and normalizes to 11.43, below the 1.1.1 reading, so it pulls the basket down. A marks the labor break harder than v1. Basket B is 55.88 Moderate. Mortgage delinquency was 2.54 and normalizes to 86.00, above the 1.1.1 reading, so it pulls the basket up. Rent burden is the 2019 survey carried forward (48.4, 2019-01-01), the low in this ACS file, and normalizes to 58.00, above the 1.1.1 reading, so it pulls the basket up. Bank delinquency did not show the COVID labor shock. Forbearance kept the series calm, and that calm series pulls B back to Moderate. Basket C is 49.44 Low. VIX and credit were stressed, and both sit below the 1.1.1 reading, so C stays in Low with v1.

**June 2022.** 1.1.1 is 52.28 Low with headline CPI 8.98 and debt 118.20 (2022-04-01, carried_forward). Food CPI was 10.4 and normalizes to 27.06, below the 1.1.1 reading, so it pulls the basket down. EPOP was 79.8 and normalizes to 84.29, above the 1.1.1 reading, so it pulls the basket up. Those two add-ons pull in opposite directions, and basket A is 52.90 Low, a small step above v1 rather than a deeper inflation reading. Basket B is 52.45 Low. Mortgage delinquency was 1.96 and normalizes to 91.27, above the 1.1.1 reading, so it pulls the basket up, which offsets food and the rent-burden score (40.50). Basket C is 53.20 Low. VIX normalizes to 66.85, above the 1.1.1 reading, so it pulls the basket up. Credit normalizes to 47.77, below the 1.1.1 reading, so it pulls the basket down. 2022 was an inflation year. It was not a 2008-style credit break, and C does not treat it as one.

**October 2025.** CPI, food, unemployment, and EPOP are blank. 1.1.1 is 53.76 Low on debt, crime, homelessness, and trust (`incident_rate|debt_to_gdp_ratio|homelessness_rate|trust_in_government`). The inflation-unemployment-debt partial has only the debt print that month and is 38.72 Critical. Basket A is 53.76 Low, the same number as 1.1.1, because both of its add-ons are missing and the denominator does not change. Baskets B and C are 57.21 Moderate and 57.47 Moderate. Calm delinquency and a calm VIX are still present, so they lift a thin month. That is not a recovery.

## Weekly volatility

A Friday publish of methodology 1.1.1, basket A, or basket B does not move inside a calendar month in this vintage. Inflation, unemployment, food, and EPOP update monthly. Debt, delinquency, and rent burden are quarterly or annual and are carried inside the month. Homelessness and trust are the held checklist. Crime is a monthly file rate. Across 790 within-month Friday pairs, v1, A, and B are flat on every pair (share flat 100.0%, mean absolute move 0.00).

Basket C is the weekly series. The credit subindex is a Friday print, and the VIX slot uses that week's mean close. Within-month, the mean absolute move is **0.33**, the standard deviation of the signed move is **0.52**, and 1.4% of those pairs are flat at two decimals. The largest within-month move is **3.60** on the week of 2020-03-13. Inside the 2008 window the largest within-month drop is **-3.34** on the week of 2008-10-10.

The `all_fridays` sample also counts the step into a new month, which is when a new CPI or unemployment print arrives. For v1 that mean absolute Friday-to-Friday move is **0.09** and the largest step is **8.05** on the week of 2020-04-03. That step is a monthly update landing on a Friday, not a week of market noise.

| Basket | Sample | Weeks | Mean abs move | Stdev of move | Share flat | Largest move | Largest drop |
| --- | --- | --- | --- | --- | --- | --- | --- |
| v1 1.1.1 | within_month | 790 | 0.00 | 0.00 | 100.0% | 0.00 (2026-08-28) | 0.00 (2007-01-12) |
| v1 1.1.1 | all_fridays | 1025 | 0.09 | 0.37 | 77.1% | 8.05 (2020-04-03) | -8.05 (2020-04-03) |
| v1 1.1.1 | within_month_2008 | 83 | 0.00 | 0.00 | 100.0% | 0.00 (2009-12-25) | 0.00 (2007-12-14) |
| v1 1.1.1 | within_month_2020 | 40 | 0.00 | 0.00 | 100.0% | 0.00 (2020-12-25) | 0.00 (2020-01-10) |
| v1 1.1.1 | within_month_2022 | 40 | 0.00 | 0.00 | 100.0% | 0.00 (2022-12-30) | 0.00 (2022-01-14) |
| A | within_month | 790 | 0.00 | 0.00 | 100.0% | 0.00 (2026-08-28) | 0.00 (2007-01-12) |
| A | all_fridays | 1025 | 0.11 | 0.60 | 77.5% | 13.80 (2020-04-03) | -13.80 (2020-04-03) |
| A | within_month_2008 | 83 | 0.00 | 0.00 | 100.0% | 0.00 (2009-12-25) | 0.00 (2007-12-14) |
| A | within_month_2020 | 40 | 0.00 | 0.00 | 100.0% | 0.00 (2020-12-25) | 0.00 (2020-01-10) |
| A | within_month_2022 | 40 | 0.00 | 0.00 | 100.0% | 0.00 (2022-12-30) | 0.00 (2022-01-14) |
| B | within_month | 790 | 0.00 | 0.00 | 100.0% | 0.00 (2026-08-28) | 0.00 (2007-01-12) |
| B | all_fridays | 1025 | 0.09 | 0.35 | 77.4% | 6.95 (2020-04-03) | -6.95 (2020-04-03) |
| B | within_month_2008 | 83 | 0.00 | 0.00 | 100.0% | 0.00 (2009-12-25) | 0.00 (2007-12-14) |
| B | within_month_2020 | 40 | 0.00 | 0.00 | 100.0% | 0.00 (2020-12-25) | 0.00 (2020-01-10) |
| B | within_month_2022 | 40 | 0.00 | 0.00 | 100.0% | 0.00 (2022-12-30) | 0.00 (2022-01-14) |
| C | within_month | 790 | 0.33 | 0.52 | 1.4% | 3.60 (2020-03-13) | -3.60 (2020-03-13) |
| C | all_fridays | 1025 | 0.37 | 0.57 | 1.1% | 5.05 (2020-04-03) | -5.05 (2020-04-03) |
| C | within_month_2008 | 83 | 0.49 | 0.70 | 1.2% | 3.34 (2008-10-10) | -3.34 (2008-10-10) |
| C | within_month_2020 | 40 | 0.52 | 0.89 | 0.0% | 3.60 (2020-03-13) | -3.60 (2020-03-13) |
| C | within_month_2022 | 40 | 0.39 | 0.51 | 0.0% | 1.36 (2022-04-29) | -1.36 (2022-04-29) |

This path uses the revised vintage. A Friday in 2008 is scored with the revised print for that month, not with the print that had been published by that Friday. It is not an ALFRED real-time path.

## Cadence, freshness, and source reliability

Freshness is measured against this research pull. The BLS, household, rent, and monthly VIX fixtures are the 2026-09-26 / 2026-09-27 pull. Debt, the credit subindex, and the weekly VIX file were added 2026-10-12. The current row's inflation, unemployment, crime, debt, food, and EPOP are the values already in the committed `latest.json` shadows and metrics.

| Input | Cadence | Latest observation used | Freshness | Reliability |
| --- | --- | --- | --- | --- |
| Headline CPI | Monthly | 2026-08-01 | About six weeks behind a 9 October publication. October 2025 is a real publication gap and stays blank. | BLS CPI-U via the same series as the live fetcher. Revised vintage, not ALFRED. |
| Unemployment | Monthly | 2026-09-01 | The October publication has the September print. The monthly file ends August 2026. | BLS `UNRATE`. Revised vintage. |
| Crime | Monthly file, published as the latest month | 2026-04-30 | The 9 October week still carries April 2026. About five months of lag. | RTCI Nationwide Full Sample, population-weighted violent plus property per 100,000. 621 agencies in this file, a balanced sample, not a census of every U.S. agency. No fair rate before January 2018. |
| Debt-to-GDP | Quarterly | 2026-01-01 | 2026 Q1, carried into October. The next quarter is not in this file. | FRED `GFDEGDQ188S`, OMB debt and BEA GDP, constructed by the St. Louis Fed. Revised. Overlap with the locked 2026-09-23 crisis fixture matches. |
| Homelessness | Annual checklist | 2025-01-01 | 2025 AHAR point-in-time count. Held on every historical month. | HUD AHAR. The checklist value is 0.22. There is no monthly history. |
| Trust | Annual checklist | 2026 | Edelman survey year 2026. Held on every historical month. | Edelman Trust Barometer, United States, Government. A private barometer with a year stamp, not a statistical-agency microdata release. There is no monthly history. |
| Food CPI | Monthly | 2026-08-01 | Same lag and the same October 2025 gap as headline CPI. | BLS `CPIUFDNS` / `CUUR0000SAF1`, the food shadow. Not in the live score. |
| Prime-age EPOP | Monthly | 2026-09-01 | September 2026 on the live shadow. The monthly fixture ends August. | BLS `LNS12300060`. Not in the live score. |
| Mortgage delinquency | Quarterly | 2026-04-01 | 2026 Q2, carried into October. | Federal Reserve CHGDEL, residential column, all commercial banks. It misses household forbearance, which is why April 2020 stays calm. |
| Rent burden | Annual | 2024-01-01 | 2024 ACS 1-year, carried into 2026. No 2020 standard 1-year and no 2025 1-year in this file. | Census ACS `B25070`, national, 30%+ of income. A real household measure. Too slow to move a weekly score, and the latest year is stale. |
| VIX | Daily; scored as a week or month mean | 2026-10-09 | The week of the 9 October publication. Close on 9 October 2026 is in the CBOE file. | CBOE `VIX_History.csv`, the series FRED publishes as `VIXCLS`. An equity-volatility index, not a credit spread. |
| Credit conditions | Weekly, Friday | 2026-10-02 | One week behind the 9 October publication. | Chicago Fed NFCI credit subindex. Public index, revised, not a licensed OAS series. |

## What still blocks a v2.0 contract

- The recommendation is to keep publishing methodology 1.1.1. The weights and ranges above are the baskets that were scored. They were not fit to a loss, a utility function, or a band boundary.
- Basket A lifts today's reading because prime-age employment is strong, and it makes October 2009 look calmer because food prices were falling. It does mark April 2020.
- Basket B marks the 2009 delinquency peak and September 2011, when the rent-burden peak and a 10.5 delinquency print land together. It then treats April 2020 as Moderate, because the bank series did not see the labor break. Rent burden is a flat annual share. The 2024 survey is still the latest print.
- Basket C marks October 2008 and moves every week. It does not mark 2022 inflation, and a calm VIX lifts the current reading. The credit series is a conditions index, not a corporate spread. ICE OAS and Moody's Baa were not copied.
- Homelessness and trust still have no monthly history. Holding the 1.1.1 checklist on 2008 and 2020 is a level shift, not a path for those series.
- Crime has no fair pre-2018 path. Carrying April 2026 into later months copies the live publisher's "latest file month" rule. It is not an August crime observation.
- The pull is a current revised vintage. A 2008 row is not the print available during 2008.
- Companions stay outside the score.

## Reproduce

From the repository root, with the existing test dependencies and no API key:

```bash
python -m runtime.backtest.v2_candidate --check-locked
```

That reprints the locked 57.11 line and the 1.1.1 restatement, and rewrites the CSV files, this note, and the chart. It does not run the weekly publisher.

`python -m runtime.backtest` remains the v1.0.0-only replay. The v2 command does not replace it.

CI runs the backtest tests on pull requests and on manual dispatch. That workflow is read-only. It is not the Friday publish job.
