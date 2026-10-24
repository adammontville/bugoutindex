# Endpoint and band calibration (research)

Research only. This note is not a methodology version. It does not change `compute_index`, methodology 1.1.1, `docs/data/latest.json`, or the weekly history. The six inputs and the six weights stay as they are. Pew trust, Gallup confidence, and the shelter companions stay outside the score.

**Stay on methodology 1.1.1.** Do not publish a recalibrated scale from this replay.

October 2008 scores **56.89 Moderate** and the current 1.1.1 restatement scores **57.50 Moderate**. The gap is **0.61** points. The live index from January 2007 through August 2026 runs **50.98** to **61.39**. High and Critical do not occur. A cutoff between those two scores would sit inside ordinary month-to-month movement. Stretching the endpoints can split them, and the stretch that does it pins debt at the stressed end from 2008-07-01 onward. While debt sits there, High Stability is out of reach: the best remaining inputs still score **69.29**, under the live High line of 70. The combination that then calls today High does it with debt already maxed out.

Read this file. You do not need to run the harness. Month-by-month numbers are in [`output/endpoint_calibration_monthly.csv`](output/endpoint_calibration_monthly.csv). Window counts are in [`output/endpoint_calibration_summary.csv`](output/endpoint_calibration_summary.csv). Friday moves are in [`output/endpoint_calibration_weekly.csv`](output/endpoint_calibration_weekly.csv). The chart is [`output/endpoint_calibration_chart.svg`](output/endpoint_calibration_chart.svg).

The 19 September 2026 published row still scores **57.11 Moderate** through `compute_index` under methodology 1.0.0. The committed `latest.json` is the 2026-10-09 week, methodology 1.1.0, index **57.66**. Scoring those six published raws returns **57.66**. This replay does not rewrite that file. The 1.1.1 column changes only homelessness to **0.22** and trust to **39**.

## What compresses the index

Live endpoints and the sample that actually showed up. Inflation, unemployment, and debt are January 2000 through the latest print in this pull. Crime is the RTCI file, January 2018 through April 2026. Homelessness and trust are the 1.1.1 checklist, one point each. "Share of 0–100 used" is the gap between the lowest and highest normalized score divided by 100.

| Input | Sample | Observed raw range | Live endpoints | Normalized range visited | Share of 0–100 used | Weight |
| --- | --- | --- | --- | --- | --- | --- |
| Headline CPI YoY | 2000–2026 (n=319) | -1.96 to 8.98 | -10.00 to 15.00 | 24.08 to 67.84 | 43.8% | 0.15 |
| Unemployment | 2000–2026 (n=319) | 3.40 to 14.80 | 0.00 to 25.00 | 40.80 to 86.40 | 45.6% | 0.12 |
| Debt-to-GDP | 2000–2026 (n=105) | 54.03 to 132.66 | 0.00 to 200.00 | 33.67 to 72.98 | 39.3% | 0.12 |
| Crime, Nationwide Full Sample | 2018–2026 (n=100) | 2443.27 to 3137.69 | 500.00 to 8000.00 | 64.83 to 74.09 | 9.3% | 0.12 |
| Homelessness | checklist only (n=1) | 0.22 to 0.22 | 0.00 to 0.50 | 56.00 to 56.00 | 0.0% | 0.09 |
| Trust in government | checklist only (n=1) | 39.00 to 39.00 | 0.00 to 80.00 | 48.75 to 48.75 | 0.0% | 0.12 |

Homelessness and trust are **0.21** of the **0.72** weight, and they do not move. That is **29.2%** of the index sitting on a fixed contribution (homelessness **56.00**, trust **48.75**). Crime's observed rates, about **2443** to **3138**, use **9.3%** of the 500–8,000 scale and normalize into a band about **64.83** to **74.09**. Inflation, unemployment, and debt each visit under half of their 0–100 scale. The index is the weighted average of a narrow middle.

October 2008 and today land on top of each other because the components trade places. Unemployment was **6.5** then and is **4.2** now (normalized **74.00** then, **83.20** now). Debt was **73.25** then and is **122.59** now (normalized **63.38** then, **38.70** now). Inflation is nearly the same print. Crime is absent in October 2008, so that month's denominator is **0.60**. Today's crime print normalizes to **74.09** and the denominator is **0.72**. The labor improvement and the calm crime print are offset by the debt deterioration. No band edge placed between **56.89** and **57.50** describes a different regime. It describes a rounding choice. The largest month-to-month step on the live index is **8.05**, on the week of 2020-04-03.

## The three options

Weights stay at inflation 0.15, crime 0.12, unemployment 0.12, debt 0.12, homelessness 0.09, trust 0.12. Missing inputs still drop out.

The reference window is **1970-01-01 through 2006-12-01** (debt through **2006-10-01**, the last quarter in that window). Percentiles use the type-7 rule: rank `(p/100) × (n − 1)`, then linear interpolation. The window is fixed. It is not a trailing window, and it is not refit on 2008, 2020, or 2022.

A shorter window, January 2000 through December 2006, is the Great Moderation in these files: inflation p2–p98 **1.18** to **4.24**, unemployment **3.90** to **6.13**, debt **54.15** to **61.68**. Those endpoints would clamp almost every later month. They are not used.

**Option A** replaces three endpoints with the reference window's 2nd and 98th percentiles. The calm end is p2 and the stressed end is p98, because higher inflation, unemployment, and debt are less stable. Crime stays 500–8,000. Homelessness stays 0–0.5. Trust stays 0–80, inverted. Bands stay the live `interpret` cutoffs: High at or above 70, Moderate at or above 55, Low at or above 40, Critical below 40.

| Input | Live endpoints | Option A endpoints |
| --- | --- | --- |
| Headline CPI YoY | -10 to 15 | 1.40 to 12.79 |
| Unemployment | 0 to 25 | 4.00 to 10.10 |
| Debt-to-GDP | 0 to 200 | 30.86 to 64.67 |
| Crime | 500 to 8,000 | unchanged |
| Homelessness | 0 to 0.5 | unchanged |
| Trust | 0 to 80, inverted | unchanged |

**Option B** keeps the live endpoints and moves the bands to two named episodes inside the reference window, scored with the live endpoints and the same held checklist. There is no crime series in that window, so the denominator is 0.60.

- Stress anchor: **1980-03-01**, the reference window's CPI year-over-year peak. The live-endpoint index that month is **50.42**. Critical is strictly below that index. November 1982, the unemployment peak in this file, scores higher than March 1980 on the live formula, because inflation had already fallen. The inflation peak is the lower anchor.
- Calm anchor: the median monthly index from **1995-01-01** through **2006-12-01**, **60.59**. High is at or above that median.
- The midpoint, **55.51**, splits Low and Moderate.

A quantile rule on the same reference index was inspected and not used. The reference index itself only runs from the high 40s to the low 60s, so p80 / p40 / p15 are **60.84** / **58.96** / **56.18**. October 2008 at **56.89** and today at **57.50** both fall between p15 and p40. The tighter cuts manufacture Critical months without splitting the pair the question is about.

**Option C** uses option A's endpoints and the same episode rule scored on those endpoints. The March 1980 index is **50.56**. The 1995–2006 median is **59.28**. The midpoint is **54.92**.

## Readings

The current row uses the published 2026-10-09 raws for inflation (2026-08-01), unemployment (2026-09-01), debt, and crime, and the 1.1.1 checklist for homelessness and trust. August 2026 in the monthly file is a different unemployment print (**4.1**, not **4.2**).

| Reading | v1 1.1.1 | A percentile endpoints | B episode bands | C endpoints and bands |
| --- | --- | --- | --- | --- |
| Current (2026-10-09 inputs, 1.1.1 checklist) | 57.50 Moderate | 60.86 Moderate | 57.50 Moderate | 60.86 High |
| 2008-10-01 — Financial stress, unemployment still 6.5 | 56.89 Moderate | 49.84 Low | 56.89 Moderate | 49.84 Critical |
| 2009-10-01 — Unemployment 10.0 | 56.97 Moderate | 43.48 Low | 56.97 Moderate | 43.48 Critical |
| 2020-04-01 — Unemployment 14.8 | 50.98 Low | 47.17 Low | 50.98 Low | 47.17 Critical |
| 2022-06-01 — Headline CPI peak in this replay | 52.28 Low | 49.81 Low | 52.28 Low | 49.81 Critical |
| 2026-08-01 — Last headline CPI month | 57.56 Moderate | 61.13 Moderate | 57.56 Moderate | 61.13 High |

B prints the v1 index with a different band. C prints the option A index with a different band. The number does not move unless the endpoints move.

| Window | v1 and B (same index) | A and C (same index) |
| --- | --- | --- |
| Full history (Jan 2007–Aug 2026) | 50.98 (2020-04-01) to 61.39 (2007-08-01) | 40.70 (2009-12-01) to 63.57 (2019-01-01) |
| 2008 (Dec 2007–Dec 2009) | 54.01 (2009-12-01) to 60.01 (2008-12-01) | 40.70 (2009-12-01) to 55.08 (2007-12-01) |
| 2020 | 50.98 (2020-04-01) to 59.03 (2020-03-01) | 47.17 (2020-04-01) to 62.51 (2020-03-01) |
| 2022 inflation year | 52.28 (2022-06-01) to 54.47 (2022-12-01) | 49.81 (2022-06-01) to 54.43 (2022-12-01) |
| 2015–2019 | 56.37 (2017-02-01) to 59.75 (2019-06-01) | 57.58 (2015-01-01) to 63.57 (2019-01-01) |

| Window | Option | High | Moderate | Low | Critical |
| --- | --- | --- | --- | --- | --- |
| Full history (Jan 2007–Aug 2026) | v1 | 0 | 182 | 54 | 0 |
| Full history (Jan 2007–Aug 2026) | A | 0 | 128 | 108 | 0 |
| Full history (Jan 2007–Aug 2026) | B | 8 | 159 | 69 | 0 |
| Full history (Jan 2007–Aug 2026) | C | 100 | 29 | 48 | 59 |
| 2008 (Dec 2007–Dec 2009) | v1 | 0 | 23 | 2 | 0 |
| 2008 (Dec 2007–Dec 2009) | A | 0 | 1 | 24 | 0 |
| 2008 (Dec 2007–Dec 2009) | B | 0 | 23 | 2 | 0 |
| 2008 (Dec 2007–Dec 2009) | C | 0 | 1 | 9 | 15 |
| 2020 | v1 | 0 | 8 | 4 | 0 |
| 2020 | A | 0 | 6 | 6 | 0 |
| 2020 | B | 0 | 7 | 5 | 0 |
| 2020 | C | 3 | 3 | 2 | 4 |
| 2022 inflation year | v1 | 0 | 0 | 12 | 0 |
| 2022 inflation year | A | 0 | 0 | 12 | 0 |
| 2022 inflation year | B | 0 | 0 | 12 | 0 |
| 2022 inflation year | C | 0 | 0 | 11 | 1 |
| 2015–2019 | v1 | 0 | 60 | 0 | 0 |
| 2015–2019 | A | 0 | 60 | 0 | 0 |
| 2015–2019 | B | 0 | 60 | 0 | 0 |
| 2015–2019 | C | 51 | 9 | 0 | 0 |

Full-history band totals: v1 is **0** High and **0** Critical. A is **0** High and **0** Critical. B is **8** High and **0** Critical. C is **100** High and **59** Critical. Month-to-month band changes: v1 **14**, A **8**, B **13**, C **24**.

### Do 2008 and 2020 separate from the calm years?

2015–2019 is the calm stretch in this replay: unemployment at or below the mid-4s for long stretches, inflation mostly under 3, crime in the file.

On v1, 2015–2019 is entirely Moderate. The 2008 window is 23 Moderate and 2 Low. October 2008 itself is Moderate, like today. 2020 is 8 Moderate and 4 Low. 2022 is 12 Low. 2022 separates from today. October 2008 does not.

On A, 2015–2019 is entirely Moderate, from **57.58** to **63.57**. October 2008 is **49.84 Low**. October 2009 is **43.48 Low**. April 2020 is **47.17 Low**. June 2022 is **49.81 Low**. Today is **60.86 Moderate**. Those four stress months are Low and today is Moderate. That is the separation. Critical still does not fire. The sample low on A is **40.70** on 2009-12-01, just above 40.

On B, October 2008 and today are both Moderate. The March 1980 anchor at **50.42** is below every month in the replay (the replay low is **50.98**), so Critical does not fire. B's **8** High months run 2007-01-01 through 2007-08-01, the prints above the 1995–2006 median. The episode bands sit next to the live 55 / 40 cutoffs and do not answer the question.

On C, October 2008, October 2009, April 2020, and June 2022 are Critical, and today is **High**. The other eleven months of 2022 are Low. 2015–2019 is **51** High and **9** Moderate. Critical is **59** of **236** months. The word on the live scale for that band is Collapse Likely.

### Why A separates, and what it stops seeing

Option A's debt endpoint tops out at **64.67**. The replay's debt print reaches that on **2008-07-01** and stays at or above it for **218** of **236** months. July 2008 through the present is one debt score: the stressed end. Further increases, from about 67 to today's **122.59**, do not move the index. The gap between October 2008 and today then comes from unemployment (normalized **59.02** then, **96.72** now) and from inflation, which looks calmer on a scale whose stressed end is the 1970s rather than 15. October 2009 inflation was **-0.22**, below the p2 endpoint, so it clamps at fully stable and the unemployment print does the work of pulling that month down.

The ceiling while debt is on that endpoint, homelessness and trust stay on the checklist, and inflation, unemployment, and crime are all at their most stable endpoint, is **69.29**. Live High is 70. High does not just fail to show up in this sample. It cannot show up until debt-to-GDP falls back through **64.67** or the checklist changes.

Crime is still compressed, because its endpoints were not refit. There is no 1970–2006 RTCI sample to refit them from.

## Weekly volatility

Within a calendar month the index does not move. Across **790** within-month Friday pairs, v1, A, B, and C are flat on every pair (share flat **100.0%**). B uses the v1 index. C uses the A index. Changing bands does not add a weekly tick.

Across all Fridays, including the step into a new month, the mean absolute move is **0.09** on v1 and **0.20** on A. The largest A step in the Friday file is **17.54** on the week of 2025-11-07, and the largest drop is **-17.08** on the week of 2025-10-03. Those two steps are the October 2025 blank, when CPI and unemployment are missing, and the return of both series the next month. Option A falls from **60.52** to **43.44** and back to **60.98**. That is a missing-input month, not a weekly shock. Among months that keep inflation and unemployment, the largest A step is **-15.34** into 2020-04-01, and the largest v1 step is **-8.05** into 2020-04-01. The shorter unemployment and inflation scales turn that labor print into a larger index step. This path is the revised vintage, not the print that was public on that Friday.

| Series | Sample | Weeks | Mean abs move | Stdev of move | Share flat | Largest move | Largest drop |
| --- | --- | --- | --- | --- | --- | --- | --- |
| v1 and B | within_month | 790 | 0.00 | 0.00 | 100.0% | 0.00 (2026-08-28) | 0.00 (2007-01-12) |
| v1 and B | all_fridays | 1025 | 0.09 | 0.37 | 77.1% | 8.05 (2020-04-03) | -8.05 (2020-04-03) |
| A and C | within_month | 790 | 0.00 | 0.00 | 100.0% | 0.00 (2026-08-28) | 0.00 (2007-01-12) |
| A and C | all_fridays | 1025 | 0.20 | 1.01 | 77.7% | 17.54 (2025-11-07) | -17.08 (2025-10-03) |

## If this were a version

It would be **methodology 2.0.0**, not 1.2.0. Endpoints are what a point on the 0–100 scale means. Option C would also change what Moderate means. A 57.50 Moderate under 1.1.1 is not a revision of a different number under new endpoints, and the new number is not a revision of 57.50.

The weekly history would keep each row's `methodology_version`. Rows through the last 1.1.1 week would stay 1.1.1. The first 2.0.0 week would be a break in the chart, with one sentence next to it: the scale changed, and the old number is still the old number. `latest.json` would carry 2.0.0 from that week forward. It would not be rewritten backward. The release note would name the reference window, the percentile rule, and the three endpoints that moved, and it would say that crime, homelessness, and trust were left alone because they have no matching history.

This replay does not cut that version.

## What was not adopted

- Option B does not separate October 2008 from today. The live scores are too close, and the 1980 anchor is below the whole replay.
- Option A does separate the stress months from today, and it makes High unreachable for as long as debt-to-GDP stays above the 1970–2006 98th percentile. Debt stops ranking months after 2008-07-01.
- Option C separates them by calling a large share of the replay Critical, Collapse Likely, and by calling the current reading High while debt is on the stressed endpoint.
- Crime, homelessness, and trust still have nothing in the reference window to recalibrate. Together with a clamped debt input, most of the weight is a constant.

## Reproduce

From the repository root, with the existing test dependencies and no API key:

```bash
python -m runtime.backtest.endpoint_calibration --check-locked
```

That reprints the locked 57.11 line and the 1.1.1 restatement, and rewrites the CSV files, this note, and the chart. It does not run the weekly publisher.

`python -m runtime.backtest` remains the v1.0.0-only replay. The v2 candidate command is a different research question and is unchanged.

CI runs the backtest tests on pull requests and on manual dispatch. That workflow is read-only. It is not the Friday publish job.
