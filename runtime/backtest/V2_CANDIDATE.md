# v2 candidate replay (hypothesis)

This is a research note for methodology v2.0 planning. It is not a methodology version, and it is not the live BugOut Index.

The published score stays the locked v1.0.0 formula. On the 19 September 2026 inputs that formula still returns **57.11 Moderate Stability**. Nothing in this replay is wired into `compute_index`, the weekly publisher, or `docs/data/latest.json`. Merging the branch does not publish to GitHub Pages.

Read this file. You do not need to run the harness. The month-by-month numbers are in [`output/v2_candidate_monthly.csv`](output/v2_candidate_monthly.csv). Window ranges and band counts are in [`output/v2_candidate_summary.csv`](output/v2_candidate_summary.csv). A small chart of the same series is [`output/v2_candidate_chart.svg`](output/v2_candidate_chart.svg).

v1 columns are `runtime.processing.formula.compute_index` (endpoints, weights, trust inversion, clamp, divide-by-sum-of-weights). v2 columns use `formula.normalize` and the same divide-by-sum rule on a **different basket**. Trial weights and ranges below are one hypothesis, chosen so the stress windows are visible. They are not a fitted contract.

## What the hypothesis basket is

| Trial input | Weight | Range | Direction | Where it comes from |
| --- | --- | --- | --- | --- |
| Headline CPI YoY (`CPIAUCSL`) | 0.22 | −10 to 15 | higher is less stable | Same construction as the live inflation fetcher. Endpoints are the v1.0.0 endpoints. |
| Food CPI YoY (`CPIUFDNS`) | 0.14 | 0 to 10 | higher is less stable | Same one-decimal public print as `fetch_food_shadow`. Range is the incubating draft, which the live site does not apply. |
| Labor blend | 0.28 | 70 to 83 | higher is more stable | `0.70 × LNS12300060 + 0.30 × LNS11300060`. A simple composite, not the incubating essay's unspecified participation penalty. |
| VIX monthly mean (`VIXCLS`) | 0.18 | 10 to 65 | higher is less stable | Mean of daily closes in the calendar month. The month's maximum close is stored and not scored. |
| Crime trial (RTCI) | 0.18 | 500 to 8,000 | higher is less stable | Unweighted agency mean, same construction as the crime diagnostic. v1 endpoints. Included only when that month is in the file. |

When an input is missing, its weight drops out and the denominator shrinks. The four non-crime weights sum to **0.82**. All five sum to **1.00**.

Demoted from the v2 primary, on purpose, so the side-by-side can be discussed:

- **Debt-to-GDP** is out of the primary. The sensitivity `v2_if_debt_included` adds it back at the v1 raw weight **0.12** and the v1 endpoints (0 to 200).
- **Homelessness** and **Edelman trust** are out of every v2 column. There is still no monthly history. The "if removed" columns are the locked formula with that held-constant input left out.
- **UNRATE alone** is not the v2 labor input. `v2_if_unrate` puts headline unemployment back in the labor slot (v1 range 0 to 25, weight 0.28) so the composite can be compared with the series it would replace.
- **`v2_if_epop_only`** uses prime-age EPOP alone (hypothesis range 68 to 82) instead of the 0.70/0.30 blend.
- **`v2_if_crime_held`** pins crime at the locked published input **2723** and labels it held constant. That pin is the 19 September 2026 baseline (`published_2026-09-19`), not a 2008 or 2020 observation.

`v2_without_crime` is the same basket with crime always excluded. Use it when comparing 2008 (no RTCI) with later years (RTCI present).

Bands on every column are the v1.0.0 bands from `interpret`: High ≥ 70, Moderate ≥ 55, Low ≥ 40, Critical below 40. Applying those bands to a different basket is part of the hypothesis, not a retune.

## Results

| Window | v1 partial | v1 held | v2 candidate | v2, crime always off |
| --- | --- | --- | --- | --- |
| 2008 (Dec 2007–Dec 2009) | 55.17 (2009-12-01) to 64.40 (2008-12-01) | 56.90 (2009-12-01) to 61.90 (2008-12-01) | 45.62 (2008-10-01) to 70.29 (2009-08-01) | 45.62 (2008-10-01) to 70.29 (2009-08-01) |
| 2020 (Jan–Dec) | 45.51 (2020-04-01) to 60.48 (2020-03-01) | 51.67 (2020-04-01) to 59.78 (2020-03-01) | 48.32 (2020-04-01) to 76.35 (2020-01-01) | 43.24 (2020-04-01) to 77.50 (2020-01-01) |
| Recent (Jan 2022–Aug 2026) | 38.72 (2025-10-01) to 65.14 (2025-04-01) | 53.55 (2025-10-01) to 61.74 (2025-04-01) | 52.87 (2022-06-01) to 81.27 (2025-10-01) | 48.85 (2022-06-01) to 85.30 (2025-10-01) |

Ranges are the lowest and highest scored month in that column. A blank month is not in the range. October 2025 is scored from whatever inputs exist that month, so it is inside these ranges and it is not a full-basket reading. See the recent-path section.

Band counts use the v1.0.0 thresholds on whatever number that column produced. A blank month is not counted.

| Window | Scenario | High | Moderate | Low | Critical |
| --- | --- | --- | --- | --- | --- |
| 2008 | v1_partial | 0 | 25 | 0 | 0 |
| 2008 | v1_held | 0 | 25 | 0 | 0 |
| 2008 | v2 | 1 | 21 | 3 | 0 |
| 2008 | v2_without_crime | 1 | 21 | 3 | 0 |
| 2020 | v1_partial | 0 | 5 | 7 | 0 |
| 2020 | v1_held | 0 | 8 | 4 | 0 |
| 2020 | v2 | 2 | 8 | 2 | 0 |
| 2020 | v2_without_crime | 2 | 7 | 3 | 0 |
| recent | v1_partial | 0 | 43 | 12 | 1 |
| recent | v1_held | 0 | 55 | 1 | 0 |
| recent | v2 | 39 | 12 | 5 | 0 |
| recent | v2_without_crime | 38 | 8 | 10 | 0 |

### Key months

| Month | Why it is here | v1 partial | v1 held | v2 candidate | v2, crime off | v2, UNRATE instead | v2, debt added |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2007-12-01 | Great Recession window starts | 62.49 Moderate | 60.87 Moderate | 65.85 Moderate | 65.85 Moderate | 65.01 Moderate | 66.21 Moderate |
| 2008-10-01 | VIX monthly mean jumps | 59.61 Moderate | 59.31 Moderate | 45.62 Low | 45.62 Low | 45.20 Low | 47.89 Low |
| 2008-11-01 | VIX monthly-mean peak in this pull | 63.29 Moderate | 61.30 Moderate | 47.81 Low | 47.81 Low | 47.54 Low | 49.80 Low |
| 2009-10-01 | UNRATE peak in the locked vintage (10.0) | 59.72 Moderate | 59.37 Moderate | 68.72 Moderate | 68.72 Moderate | 70.16 High | 67.35 Moderate |
| 2009-12-01 | Great Recession window ends | 55.17 Moderate | 56.90 Moderate | 65.90 Moderate | 65.90 Moderate | 68.24 Moderate | 64.89 Moderate |
| 2020-01-01 | Pre-COVID month | 59.76 Moderate | 59.39 Moderate | 76.35 High | 77.50 High | 75.87 High | 73.16 High |
| 2020-03-01 | COVID VIX monthly-mean peak | 60.48 Moderate | 59.78 Moderate | 60.58 Moderate | 58.28 Moderate | 61.46 Moderate | 59.08 Moderate |
| 2020-04-01 | COVID unemployment and prime-age EPOP trough | 45.51 Low | 51.67 Low | 48.32 Low | 43.24 Low | 54.01 Low | 46.75 Low |
| 2020-12-01 | COVID window ends | 55.01 Moderate | 56.82 Moderate | 64.38 Moderate | 62.62 Moderate | 68.06 Moderate | 61.47 Moderate |
| 2022-06-01 | Food CPI year-over-year above the 10% draft | 51.42 Low | 55.56 Moderate | 52.87 Low | 48.85 Low | 54.12 Low | 52.87 Low |
| 2022-09-01 | Food CPI year-over-year high in this pull | 53.35 Low | 56.43 Moderate | 54.57 Low | 51.02 Low | 55.13 Moderate | 54.57 Low |
| 2025-10-01 | BLS publication gap in this pull | 38.72 Critical | 53.55 Low | 81.27 High | 85.30 High | 81.27 High | 70.63 High |
| 2026-04-01 | Last month in the RTCI trial file | 54.65 Low | 56.62 Moderate | 73.45 High | 72.23 High | 71.59 High | 69.73 Moderate |
| 2026-08-01 | Latest headline CPI month; locked-score inputs | 55.55 Moderate | 57.11 Moderate | 74.51 High | 74.51 High | 73.37 High | 69.94 Moderate |

### Inputs behind those months

| Month | CPI YoY | Food YoY | Labor blend | EPOP | LFPR | UNRATE | VIX mean | VIX max | Crime trial |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2007-12-01 | 4.11 | 4.9 | 80.72 | 79.7 | 83.1 | 5.0 | 21.65 | 24.52 | excluded |
| 2008-10-01 | 3.73 | 6.3 | 79.78 | 78.4 | 83.0 | 6.5 | 61.18 | 80.06 | excluded |
| 2008-11-01 | 1.10 | 6.0 | 79.57 | 78.1 | 83.0 | 6.8 | 62.67 | 80.86 | excluded |
| 2009-10-01 | -0.22 | -0.6 | 77.25 | 75.0 | 82.5 | 10.0 | 24.25 | 30.69 | excluded |
| 2009-12-01 | 2.81 | -0.5 | 76.96 | 74.8 | 82.0 | 9.9 | 21.24 | 23.69 | excluded |
| 2020-01-01 | 2.60 | 1.8 | 81.35 | 80.6 | 83.1 | 3.6 | 13.94 | 18.84 | 2667.65 |
| 2020-03-01 | 1.49 | 1.9 | 80.30 | 79.4 | 82.4 | 4.4 | 57.74 | 82.69 | 2670.58 |
| 2020-04-01 | 0.31 | 3.5 | 72.66 | 69.6 | 79.8 | 14.8 | 41.45 | 57.06 | 2642.84 |
| 2020-12-01 | 1.32 | 3.9 | 77.81 | 76.4 | 81.1 | 6.7 | 22.37 | 25.16 | 2569.38 |
| 2022-06-01 | 8.98 | 10.4 | 80.55 | 79.8 | 82.3 | 3.6 | 28.23 | 34.02 | 2659.97 |
| 2022-09-01 | 8.19 | 11.2 | 80.92 | 80.2 | 82.6 | 3.5 | 27.34 | 32.60 | 2694.70 |
| 2025-10-01 | — | — | — | — | — | — | 18.09 | 25.31 | 2206.54 |
| 2026-04-01 | 3.78 | 3.2 | 81.63 | 80.7 | 83.8 | 4.3 | 19.81 | 25.78 | 2074.97 |
| 2026-08-01 | 3.35 | 2.7 | 81.30 | 80.4 | 83.4 | 4.1 | 15.23 | 16.50 | excluded |

### What the windows show

**Great Recession window.** The locked partial replay (inflation, unemployment, debt only) runs 55.17 (2009-12-01) to 64.40 (2008-12-01). All 25 months are Moderate. Held-constant crime, homelessness, and trust keep that window Moderate as well (56.90 (2009-12-01) to 61.90 (2008-12-01)). The v2 candidate runs 45.62 (2008-10-01) to 70.29 (2009-08-01). The low is **October 2008 at 45.62 Low**, with a VIX monthly mean of 61.18. November is the VIX-mean peak at 62.67 (highest daily close 80.86) and scores **47.81 Low**, a bit higher than October because headline CPI had already cooled. The Low months are 2008-10-01 (45.62), 2008-11-01 (47.81), 2008-12-01 (52.21). October 2009, the UNRATE peak at 10.0, is v1 partial **59.72 Moderate** and v2 **68.72 Moderate**. This hypothesis times Great Recession stress on the volatility spike. It does not mark the later unemployment peak. There is no RTCI month in this window, so the v2 candidate and the crime-off series are the same path. No v2 month in that window is Critical. None of the locked partial months leave Moderate.

**COVID window.** Locked partial runs 45.51 (2020-04-01) to 60.48 (2020-03-01). April 2020 is **45.51 Low** partial and **51.67 Low** held constant (UNRATE 14.8, debt-to-GDP 132.66). Taking debt out of that held basket moves April to **55.27 Moderate**. Taking homelessness or trust out does not clear the Low band. Through the Great Recession window the held basket stays Moderate with or without debt, homelessness, or trust. The v2 candidate runs 48.32 (2020-04-01) to 76.35 (2020-01-01). March 2020, the VIX monthly-mean peak at 57.74 (highest daily close 82.69), scores **60.58 Moderate** because the labor blend is still 80.30. April, when prime-age EPOP is 69.6 and the blend is 72.66, scores **48.32 Low**. Replacing the blend with UNRATE that month scores **54.01 Low**. The trial crime rate that month is 2642.84, not 2723. Held-constant v1 for the whole year runs 51.67 (2020-04-01) to 59.78 (2020-03-01).

**Recent path.** January 2022 through August 2026. Debt is excluded on the v1 partial column before October 2025: this pull does not contain 2022–2025Q3 `GFDEGDQ188S` prints, and those months are not filled by carrying 2020 forward. The 2022 v1 partial lows are inflation plus unemployment only. June 2022 is **51.42 Low** on that two-input v1 basket, and **55.56 Moderate** once crime, homelessness, and trust are pinned at the 2026 baselines.

October 2025 is a BLS gap. CPI, food, unemployment, EPOP, and participation were non-numeric (`-(X)` or `-(9)`) and are blank. v1 partial that month is debt alone (**38.72 Critical**). The v2 candidate uses only `vix_month_mean|incident_rate` (denominator 0.36) and prints **81.27 High**. That pair is the same thin month, not a crash and not a boom. Among recent months with all five trial inputs present, the v2 candidate runs 52.87 (2022-06-01) to 76.75 (2024-07-01).

From October 2025 the debt print on v1 is the published 122.56815. From January 2026 it is the fixture print 122.59387, carried the way the live publisher carries a quarter. August 2026 held-constant v1 is **57.11**, the same six inputs as the locked 57.11. The v2 candidate that month is **74.51 High** with crime excluded (the RTCI file ends April 2026, trial rate 2074.97). The gap versus 57.11 is the basket: debt, homelessness, and trust are out, and the labor blend and VIX are calm. It is not a claim that stability improved inside v1.0.0.

Food CPI year-over-year is above the 10% draft in 9 months (2022-05-01, 2022-06-01, 2022-07-01, 2022-08-01, 2022-09-01, 2022-10-01, 2022-11-01, 2022-12-01, 2023-01-01). Those months clamp the food component at 0. June 2022 food is 10.4 and September 2022 is 11.2; the v2 candidate those months is 52.87 and 54.57. The recent-window low on the v2 candidate is **52.87 on 2022-06-01**, and that month does have the full trial basket. 4 months in the three windows have negative food inflation and clamp at 100 on this draft (fully stable).

## Crime trial, and why 2008 cannot use it

The RTCI cleaned file in this pull covers **January 2018 through April 2026**. The 2008 window has no trial rate. Fair replay does not backfill those months with the locked 2723, with a later RTCI month, or with a different crime series.

The live fetcher still returns `incident_rate` **2723** and does not score the file. Its diagnostic month rule is the lexicographic maximum of the `Date` text, which is why a later calendar month can lose to "September". This replay uses the calendar month instead, and it does not change that lock. September 2025 in the file is a trial rate of about 2234.66, not 2723. Every usable month in this download has **621** agencies. That is a balanced sample, not a national census, and the rate's level is not comparable to a historical UCR series that this repo does not reconstruct.

From May 2026 through August 2026 the primary candidate excludes crime again, so the denominator changes. Compare those months with `v2_without_crime_index` before reading a jump as stress or relief.

## Debt, homelessness, trust, and UNRATE

Homelessness and trust cannot be replayed. The held-constant columns pin them at **0.23** and **41**. Removing one of them is `v1_held_without_homelessness` or `v1_held_without_trust` in the monthly CSV. That is the locked formula with one held input left out. It is not a historical path for that series.

Debt is historical inside the 2008 and 2020 windows (the locked fixture, including ordinary within-quarter carry-forward). It is not historical for most of the recent window. Adding it back onto the v2 basket only changes the score in months where a print is actually in hand.

UNRATE remains the v1 labor input. The composite is lower in April 2020 than a calm month, and it does not by itself mark October 2009 as the Great Recession trough. `v2_if_unrate` and `v2_if_epop_only` are in the CSV for that comparison. The blend and the EPOP-only range are hypotheses that bracket this sample. They are not estimated endpoints.

## What still blocks a v2.0 contract

- These weights and ranges are one labeled hypothesis. They were not fit to a loss, a utility function, or a decision threshold.
- Housing payment stress is not in the replay. No mortgage, rent-burden, or housing-delinquency series is fetched.
- Credit spreads are not in the replay. VIX is an equity-volatility index, not a credit spread. Card delinquency (`DRCCLACBS`, issue #48) is still outside the score and is not in this basket.
- The labor composite is not the incubating participation penalty. That penalty still has no formula.
- The food draft range 0–10 clamps deflation to "fully stable" and clamps the 2022 peak to "fully unstable".
- Crime has no fair 2008 path from RTCI. The published input remains locked at 2723. Agency coverage and the 12-month RTCI definition are not a national historical crime rate.
- Homelessness and Edelman trust still have no monthly history.
- Debt-to-GDP for 2022 through 2025Q3 was not in the locked fixture, and the FRED graph download did not return a body on this pull. Those months stay excluded rather than invented.
- The pull is a current revised vintage (BLS / CBOE / RTCI on 2026-09-26; v1 crisis fixture 2026-09-23). It is not ALFRED. A 2008 row is not the print available during 2008.
- Real-time vintage choice, population-adjusted crime, and a published methodology version are still open. This note does not close them.

## Reproduce

From the repository root, with the existing test dependencies and no API key:

```bash
python -m runtime.backtest.v2_candidate --check-locked
```

That reprints the locked 57.11 line and rewrites the CSV, this note, and the chart under `runtime/backtest/output/` and `runtime/backtest/V2_CANDIDATE.md`. It does not run the weekly publisher.

`python -m runtime.backtest` is still the v1.0.0-only replay from pull #83. The v2 command does not replace it.

CI runs the backtest tests on pull requests and on manual dispatch. That workflow is read-only. It is not the Friday publish job.
