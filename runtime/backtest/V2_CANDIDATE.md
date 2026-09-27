# v2 candidate replay (hypothesis h2)

This is a research note for methodology v2.0 planning. It is not a methodology version, and it is not the live BugOut Index. The tables below are **hypothesis h2**. Hypothesis h1 was the previous labeled basket on this branch: food CPI year-over-year range 0 to 10, labor blend range 70 to 83, and weights CPI 0.22, food 0.14, labor 0.28, VIX 0.18, crime 0.18. h1 is not recomputed here. Its six comparison months are copied from that earlier replay so the two baskets can be read side by side.

The published score stays the locked v1.0.0 formula. On the 19 September 2026 inputs that formula still returns **57.11 Moderate Stability**. Nothing in this replay is wired into `compute_index`, the weekly publisher, or `docs/data/latest.json`. Merging the branch does not publish to GitHub Pages.

Read this file. You do not need to run the harness. The month-by-month numbers are in [`output/v2_candidate_monthly.csv`](output/v2_candidate_monthly.csv). Window ranges and band counts are in [`output/v2_candidate_summary.csv`](output/v2_candidate_summary.csv). A small chart of the same series is [`output/v2_candidate_chart.svg`](output/v2_candidate_chart.svg).

v1 columns are `runtime.processing.formula.compute_index` (endpoints, weights, trust inversion, clamp, divide-by-sum-of-weights). v2 columns use `formula.normalize` and the same divide-by-sum rule on a **different basket**. Trial weights and ranges below are hypothesis h2. They are not a fitted contract.

## What hypothesis h2 changes

| Piece | h1 | h2 (this note) | Why h2 |
| --- | --- | --- | --- |
| Food CPI YoY range | 0 to 10 | −2 to 15 | The 0–10 draft clamped nine 2022–23 months at fully unstable and treated mild food deflation as fully stable. |
| Labor blend range | 70 to 83 | 72 to 82 | October 2009 (blend about 77, UNRATE 10.0) scored too calm next to the VIX-timed October 2008 Low. A tighter band pulls that labor stress up. This is not a participation penalty. |
| CPI / food / labor / VIX / crime weights | 0.22 / 0.14 / 0.28 / 0.18 / 0.18 | 0.20 / 0.14 / 0.30 / 0.16 / 0.20 | Nudge labor up and VIX down so the Great Recession window is less pure-VIX and the late-2009 unemployment era registers more. Crime stays in the same ballpark. |

Headline CPI endpoints, the VIX range, the crime range, the labor blend formula (`0.70 × EPOP + 0.30 × LFPR`), and the crime trial rule are unchanged. Crime is still excluded when the RTCI month is absent. 2008 is not backfilled. The published crime input stays locked at 2723.

### h1 versus h2 on six months

h1 figures are the prior committed replay. h2 figures are this run. v1 held is the locked formula and does not change between hypotheses.

| Month | h1 v2 | h1, crime off | h2 v2 | h2, crime off | v1 held |
| --- | --- | --- | --- | --- | --- |
| 2008-10-01 | 45.62 Low | 45.62 Low | 50.79 Low | 50.79 Low | 59.31 Moderate |
| 2009-10-01 | 68.72 Moderate | 68.72 Moderate | 65.79 Moderate | 65.79 Moderate | 59.37 Moderate |
| 2020-03-01 | 60.58 Moderate | 58.28 Moderate | 62.82 Moderate | 60.76 Moderate | 59.78 Moderate |
| 2020-04-01 | 48.32 Low | 43.24 Low | 44.34 Low | 37.56 Critical | 51.67 Low |
| 2022-06-01 | 52.87 Low | 48.85 Low | 59.19 Moderate | 56.19 Moderate | 55.56 Moderate |
| 2026-08-01 | 74.51 High | 74.51 High | 77.28 High | 77.28 High | 57.11 Moderate |

## What the h2 basket is

| Trial input | Weight | Range | Direction | Where it comes from |
| --- | --- | --- | --- | --- |
| Headline CPI YoY (`CPIAUCSL`) | 0.20 | −10 to 15 | higher is less stable | Same construction as the live inflation fetcher. Endpoints are the v1.0.0 endpoints. Unchanged from h1. |
| Food CPI YoY (`CPIUFDNS`) | 0.14 | −2 to 15 | higher is less stable | Same one-decimal public print as `fetch_food_shadow`. h2 range. The live site does not apply it. |
| Labor blend | 0.30 | 72 to 82 | higher is more stable | `0.70 × LNS12300060 + 0.30 × LNS11300060`. A simple composite, not the incubating essay's unspecified participation penalty. h2 range. |
| VIX monthly mean (`VIXCLS`) | 0.16 | 10 to 65 | higher is less stable | Mean of daily closes in the calendar month. The month's maximum close is stored and not scored. Range unchanged from h1. |
| Crime trial (RTCI) | 0.20 | 500 to 8,000 | higher is less stable | Unweighted agency mean, same construction as the crime diagnostic. v1 endpoints. Included only when that month is in the file. |

When an input is missing, its weight drops out and the denominator shrinks. The four non-crime weights sum to **0.80**. All five sum to **1.00**.

Demoted from the v2 primary, on purpose, so the side-by-side can be discussed:

- **Debt-to-GDP** is out of the primary. The sensitivity `v2_if_debt_included` adds it back at the v1 raw weight **0.12** and the v1 endpoints (0 to 200).
- **Mortgage delinquency** and **credit-card delinquency** are out of the primary. They are side columns (`v2_if_housing`, `v2_if_consumer_credit`, `v2_if_housing_and_consumer`) at trial weight 0.12 each. They answer a coverage question. They do not replace h2.
- **Rent burden** is out of the primary. `v2_if_rent_burden` adds the ACS 30%+ share at trial weight 0.12. `v2_if_rent_burden_and_consumer` adds that share and card delinquency. The 50%+ share is stored and not scored. `v2_if_rent_cpi_proxy` is rent-of-primary-residence inflation, labeled as a proxy, not as rent burden.
- **Treasury yields** are out of the primary. `v2_if_dgs10` adds the 10-year yield, `v2_if_real_yield` adds the 10-year real yield, and `v2_if_rates` adds both. Corporate credit spreads stay out.
- **`v2_if_kept_debt_hud_trust`** puts debt (when a print exists) and the locked HUD and Edelman pins back on h2 at their v1.0.0 weights. It is a replacement check before demotion. It is not a historical path for homelessness or trust, and it does not unlock crime.
- **Homelessness** and **Edelman trust** are out of every v2 column. There is still no monthly history. The "if removed" columns are the locked formula with that held-constant input left out.
- **UNRATE alone** is not the v2 labor input. `v2_if_unrate` puts headline unemployment back in the labor slot (v1 range 0 to 25, weight 0.30) so the composite can be compared with the series it would replace.
- **`v2_if_epop_only`** uses prime-age EPOP alone (hypothesis range 68 to 82) instead of the 0.70/0.30 blend.
- **`v2_if_crime_held`** pins crime at the locked published input **2723** and labels it held constant. That pin is the 19 September 2026 baseline (`published_2026-09-19`), not a 2008 or 2020 observation.

`v2_without_crime` is the same basket with crime always excluded. Use it when comparing 2008 (no RTCI) with later years (RTCI present).

Bands on every column are the v1.0.0 bands from `interpret`: High ≥ 70, Moderate ≥ 55, Low ≥ 40, Critical below 40. Applying those bands to a different basket is part of the hypothesis, not a retune.

## Results

| Window | v1 partial | v1 held | v2 candidate | v2, crime always off |
| --- | --- | --- | --- | --- |
| 2008 (Dec 2007–Dec 2009) | 55.17 (2009-12-01) to 64.40 (2008-12-01) | 56.90 (2009-12-01) to 61.90 (2008-12-01) | 50.79 (2008-10-01) to 70.26 (2008-05-01) | 50.79 (2008-10-01) to 70.26 (2008-05-01) |
| 2020 (Jan–Dec) | 45.51 (2020-04-01) to 60.48 (2020-03-01) | 51.67 (2020-04-01) to 59.78 (2020-03-01) | 44.34 (2020-04-01) to 77.91 (2020-01-01) | 37.56 (2020-04-01) to 79.62 (2020-01-01) |
| Recent (Jan 2022–Aug 2026) | 38.72 (2025-10-01) to 65.14 (2025-04-01) | 53.55 (2025-10-01) to 61.74 (2025-04-01) | 59.19 (2022-06-01) to 80.82 (2025-10-01) | 56.19 (2022-06-01) to 85.30 (2025-10-01) |

Ranges are the lowest and highest scored month in that column. A blank month is not in the range. October 2025 is scored from whatever inputs exist that month, so it is inside these ranges and it is not a full-basket reading. See the recent-path section.

Band counts use the v1.0.0 thresholds on whatever number that column produced. A blank month is not counted.

| Window | Scenario | High | Moderate | Low | Critical |
| --- | --- | --- | --- | --- | --- |
| 2008 | v1_partial | 0 | 25 | 0 | 0 |
| 2008 | v1_held | 0 | 25 | 0 | 0 |
| 2008 | v2 | 1 | 22 | 2 | 0 |
| 2008 | v2_without_crime | 1 | 22 | 2 | 0 |
| 2020 | v1_partial | 0 | 5 | 7 | 0 |
| 2020 | v1_held | 0 | 8 | 4 | 0 |
| 2020 | v2 | 2 | 8 | 2 | 0 |
| 2020 | v2_without_crime | 2 | 6 | 3 | 1 |
| recent | v1_partial | 0 | 43 | 12 | 1 |
| recent | v1_held | 0 | 55 | 1 | 0 |
| recent | v2 | 41 | 15 | 0 | 0 |
| recent | v2_without_crime | 41 | 15 | 0 | 0 |

### Key months

h2 is still the primary candidate. Housing delinquency, card delinquency, rent burden, and the rent-CPI proxy are side columns for the coverage question “August 2026 High feels wrong.” They are not a new primary basket and they are not in the live score. UNRATE-instead and debt-added stay in this table; v1 partial stays in the monthly CSV. The rent-burden comparison is in the next section.

| Month | Why it is here | v1 held | h2 | h2, crime off | h2 + housing | h2 + consumer credit | h2 + both | v2, UNRATE instead | v2, debt added |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2007-12-01 | Great Recession window starts | 60.87 Moderate | 69.75 Moderate | 69.75 Moderate | 71.21 High | 66.99 Moderate | 68.60 Moderate | 67.05 Moderate | 69.61 Moderate |
| 2008-10-01 | VIX monthly mean jumps | 59.31 Moderate | 50.79 Low | 50.79 Low | 50.57 Low | 48.56 Low | 48.62 Low | 49.36 Low | 52.43 Low |
| 2008-11-01 | VIX monthly-mean peak in this pull | 61.30 Moderate | 52.40 Low | 52.40 Low | 51.97 Low | 49.96 Low | 49.86 Low | 51.31 Low | 53.83 Low |
| 2009-10-01 | UNRATE peak in the locked vintage (10.0) | 59.37 Moderate | 65.79 Moderate | 65.79 Moderate | 59.09 Moderate | 60.32 Moderate | 55.03 Moderate | 68.60 Moderate | 64.77 Moderate |
| 2009-12-01 | Great Recession window ends | 56.90 Moderate | 62.65 Moderate | 62.65 Moderate | 56.37 Moderate | 57.59 Moderate | 52.62 Low | 66.70 Moderate | 62.05 Moderate |
| 2020-01-01 | Pre-COVID month | 59.39 Moderate | 77.91 High | 79.62 High | 78.97 High | 77.69 High | 78.66 High | 75.54 High | 74.56 High |
| 2020-03-01 | COVID VIX monthly-mean peak | 59.78 Moderate | 62.82 Moderate | 60.76 Moderate | 65.49 Moderate | 64.21 Moderate | 66.49 Moderate | 62.64 Moderate | 61.08 Moderate |
| 2020-04-01 | COVID unemployment and prime-age EPOP trough | 51.67 Low | 44.34 Low | 37.56 Critical | 48.80 Low | 48.08 Low | 51.75 Low | 54.60 Low | 43.19 Low |
| 2020-12-01 | COVID window ends | 56.82 Moderate | 64.40 Moderate | 62.39 Moderate | 66.51 Moderate | 66.53 Moderate | 68.23 Moderate | 68.93 Moderate | 61.48 Moderate |
| 2022-06-01 | Food CPI year-over-year 10.4 (inside h2; a hard floor under h1) | 55.56 Moderate | 59.19 Moderate | 56.19 Moderate | 62.63 Moderate | 62.29 Moderate | 65.10 Moderate | 59.22 Moderate | 59.19 Moderate |
| 2022-09-01 | Food CPI year-over-year high in this pull | 56.43 Moderate | 60.44 Moderate | 57.86 Moderate | 63.86 Moderate | 63.07 Moderate | 65.90 Moderate | 59.48 Moderate | 60.44 Moderate |
| 2025-10-01 | BLS publication gap in this pull | 53.55 Low | 80.82 High | 85.30 High | 83.82 High | 78.65 High | 81.49 High | 80.82 High | 70.30 High |
| 2026-04-01 | Last month in the RTCI trial file | 56.62 Moderate | 76.53 High | 75.91 High | 78.21 High | 76.21 High | 77.76 High | 72.48 High | 72.48 High |
| 2026-08-01 | Latest headline CPI month; locked-score inputs | 57.11 Moderate | 77.28 High | 77.28 High | 79.23 High | 76.80 High | 78.57 High | 73.76 High | 72.25 High |

### Household stress side columns

These two series are household payment difficulty, not corporate credit spreads. The public FRED graph CSV did not return a body on this pull. The levels are the Federal Reserve Board charge-off and delinquency release (CHGDEL), the release FRED uses for these series, downloaded 2026-09-26. The package observations run through 2026-06-30. Each print is stored on the quarter-start month. Later months in the harness use that print as `carried_forward`, the same rule as debt-to-GDP. A month with no print on or before it would drop the weight. None of the three windows are in that state.

| Series | FRED id | What it measures | Frequency | Trial weight | Trial range |
| --- | --- | --- | --- | --- | --- |
| Mortgage delinquency | `DRSFRMACBS` | Delinquency rate on loans secured by one- to four-family residential property, including home-equity lines, all commercial banks, seasonally adjusted, percent. Fed table column “Residential,” booked in domestic offices. | Quarterly | 0.12 | 1 to 12 |
| Credit-card delinquency | `DRCCLACBS` | Delinquency rate on consumer credit card loans, all commercial banks, seasonally adjusted, percent. Issue #48. Not a bond spread. | Quarterly | 0.12 | 1 to 8 |

Higher delinquency is less stable. This pull’s sample runs from 1991 Q1 through 2026 Q2: mortgage delinquency 1.41 to 11.48, card delinquency 1.53 to 6.77. The ranges leave those peaks short of a hard floor. Weight 0.12 matches the debt side column. It is a hypothesis, not a fitted share of h2.

| Month | Mortgage % | Mortgage as-of | Card % | Card as-of | h2 | + housing | + consumer | + both |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2008-10-01 | 6.60 | 2008-10-01 observed | 5.64 | 2008-10-01 observed | 50.79 Low | 50.57 Low | 48.56 Low | 48.62 Low |
| 2009-10-01 | 10.41 | 2009-10-01 observed | 6.33 | 2009-10-01 observed | 65.79 Moderate | 59.09 Moderate | 60.32 Moderate | 55.03 Moderate |
| 2020-04-01 | 2.54 | 2020-04-01 observed | 2.45 | 2020-04-01 observed | 44.34 Low | 48.80 Low | 48.08 Low | 51.75 Low |
| 2022-06-01 | 1.96 | 2022-04-01 carried_forward | 1.83 | 2022-04-01 carried_forward | 59.19 Moderate | 62.63 Moderate | 62.29 Moderate | 65.10 Moderate |
| 2026-08-01 | 1.86 | 2026-04-01 carried_forward | 2.85 | 2026-04-01 carried_forward | 77.28 High | 79.23 High | 76.80 High | 78.57 High |

August 2026 is **77.28 High** on h2, **79.23 High** with mortgage delinquency, **76.80 High** with card delinquency, and **78.57 High** with both. The rates that month are the 2026 Q2 prints carried forward (1.86% mortgages, 2.85% cards, observation 2026-04-01). There is no 2026 Q3 print in this file. Mortgage delinquency is near the calm end of the sample, so adding it does not pull August toward Moderate. Card delinquency is above its trough and far below the 2009 peak, and the 0.12 weight does not move August out of High either.

October 2009 is where the mortgage series does the work h2’s labor blend did not. Mortgage delinquency is 10.41% and card delinquency is 6.33%. h2 is **65.79 Moderate**. With both side series it is **55.03 Moderate**. October 2008 is already a VIX Low on h2 (**50.79 Low**); adding both household series scores **48.62 Low**.

April 2020 is the opposite case. Bank delinquency was low while prime-age employment had already broken, which is what forbearance does to this series. h2 is **44.34 Low**. With both household series it is **51.75 Low**. These columns do not mark the COVID labor trough.

### Rent burden side column

There is no monthly national rent-burden series. Rent burden here is the share of renter households whose gross rent is at least 30% of household income, the Census cost-burden convention. It is not mortgage delinquency (`DRSFRMACBS`) and it is not corporate credit.

The source is ACS table **B25070**, Gross Rent as a Percentage of Household Income in the Past 12 Months, national 1-year estimates. The scored share is `(30–34.9% + 35–39.9% + 40–49.9% + 50% or more) / (total − not computed) × 100`, rounded half-up to one decimal. “Not computed” stays out of the denominator. The **50%+** share uses the same denominator and is the severe-burden convention. It is a subset of the 30% group, so it is stored on the row and not given a second weight.

| Piece | Choice |
| --- | --- |
| Series | `B25070` national 1-year. 2007–2009 from the ACS summary file (sequences 134, 138, and 148; United States logrecno 1). 2010–2019 and 2021–2024 from `data.census.gov` product `ACSDT1Y{year}.B25070`, geography United States. Pulled 2026-09-27. |
| What is missing | **2020** has no standard 1-year ACS (the experimental 2020 1-year is not used). **2025** is not in that API on this pull. No month is invented. |
| Frequency and lag | Annual. The 1-year ACS for survey year Y is usually released the following September. This file dates the print at January of the survey year, the same revised-vintage convention as the rest of this note, not the release month and not ALFRED. Later months carry that print forward until the next survey year. 2020 carries 2019. August 2026 carries 2024. |
| Trial weight and range | 0.12, endpoints 40 to 60. Higher share is less stable. In this file the annual 30%+ share runs **48.4** (2019-01-01) to **53.4** (2011-01-01). The range leaves that low short of fully stable and that high short of a hard floor. It was not chosen to push August under 70. A missing year drops the weight. None of these windows start before 2007. |

`v2_if_rent_burden` is h2 plus that 30% share. `v2_if_rent_burden_and_consumer` also adds `DRCCLACBS` at weight 0.12. h2 stays the primary.

The last column is an honest high-frequency **proxy**, not rent burden. It is BLS `CUUR0000SEHA`, CPI-U rent of primary residence, not seasonally adjusted, 12-month percent change, same construction as headline CPI. Pulled 2026-09-27. Trial weight 0.12, range −2 to 12. October 2025 is blank in this series (the appropriations lapse), so that month drops the proxy weight. The highest proxy print in these windows is **8.81** on 2023-03-01.

| Month | 30%+ | 50%+ (not scored) | Burden as-of | h2 | + rent burden | + burden and cards | Rent CPI YoY | + rent CPI proxy |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2008-10-01 | 49.8 | 25.1 | 2008-01-01 carried_forward | 50.79 Low | 50.82 Low | 48.84 Low | 3.68 | 51.92 Low |
| 2009-10-01 | 51.5 | 26.4 | 2009-01-01 carried_forward | 65.79 Moderate | 62.75 Moderate | 58.26 Moderate | 1.23 | 67.24 Moderate |
| 2020-04-01 | 48.4 | 23.7 | 2019-01-01 carried_forward | 44.34 Low | 45.80 Low | 49.04 Low | 3.49 | 46.10 Low |
| 2022-06-01 | 51.9 | 26.7 | 2022-01-01 carried_forward | 59.19 Moderate | 57.19 Moderate | 60.18 Moderate | 5.78 | 57.61 Moderate |
| 2026-08-01 | 51.8 | 26.1 | 2024-01-01 carried_forward | 77.28 High | 72.55 High | 72.67 High | 2.75 | 75.82 High |

August 2026 is **77.28 High** on h2. The rent-burden input that month is the **2024** ACS print carried forward: **51.8%** of renters at the 30% line and **26.1%** at the 50% line (observation 2024-01-01). Adding the 30% share scores **72.55 High**. Adding the 30% share and card delinquency scores **72.67 High**. The rent-CPI proxy that month is **2.75%** and scores **75.82 High**. The 2022, 2023, and 2024 surveys sit on top of each other near 52%, so carrying 2024 into August 2026 is not hiding a later collapse that this file contains. It also cannot see a 2025 or 2026 change in the income share, because those ACS years are not published here. Shelter inflation has cooled from the 2023-03 peak, which is why the proxy moves August less than the burden share does. Neither column puts August in Moderate.

October 2009’s burden print is the 2009 survey (**51.5%** at 30%+, observation 2009-01-01). h2 is **65.79 Moderate**. With the burden share it is **62.75 Moderate**. Rent of primary residence that month is only **1.23%** year over year, so the proxy scores **67.24 Moderate**. The income share and the rent-price change are different facts: burden rose through the recession while rent inflation slowed.

April 2020 has no 2020 ACS 1-year. The burden cell is the **2019** survey carried forward (**48.4%**, the low in this file). h2 is **44.34 Low**. With that carried print it is **45.80 Low**. That is not a COVID rent-burden observation.

October 2008 uses the 2008 survey (**49.8%**), which was not published until the following year. h2 is **50.79 Low** and h2 plus burden is **50.82 Low**. June 2022 uses the 2022 survey (**51.9%**). h2 is **59.19 Moderate** and h2 plus burden is **57.19 Moderate**.

### Financing stress: Treasury yields

These columns are the cost of long-term borrowing. They are not mortgage delinquency, not rent burden, and not a corporate bond spread. BBB and high-yield OAS stay out of the replay.

The scored nominal series is the monthly mean of the daily 10-year Treasury constant-maturity yield, FRED `DGS10`. The companion is the monthly mean of the 10-year real yield, FRED `DFII10` (TIPS). Both files are the FRED graph CSV pulled 2026-09-27, daily prints through 24 September 2026, collapsed to a month mean. The fixture keeps January 2003 through August 2026. September 2026 is a partial month on this pull and is not stored. A missing month would drop the weight. Every month in these windows has a print, so the status is `observed`.

The scored input is the **level**, not the year-over-year change. August 2026 is 4.68% on the 10-year. That is the mortgage benchmark. A small change from a high level would still be expensive financing, and a drop during a crisis (October 2008, April 2020) is flight to Treasuries, not a sign that household borrowing was easy in every other sense. Higher yield is less stable.

| Piece | Choice |
| --- | --- |
| Nominal | `DGS10` monthly mean. Trial weight 0.12. Range 0 to 6. In this file the monthly mean runs **0.62** (2020-07-01) to **5.11** (2006-05-01). |
| Real | `DFII10` monthly mean. Trial weight 0.12. Range −2 to 4. In this file **-1.07** (2021-08-01) to **2.89** (2008-11-01). |
| Why this range | Daily `DGS10` goes back to 1962 and the monthly mean peaked near 15 in the early 1980s. A 0-to-16 range would score a 4–5% yield as mostly calm. This side column is financing conditions in the same era as the real-yield series, which starts in 2003. The endpoints sit just outside that sample. They were not chosen to push August under 70. |
| Not scored | `T10Y2Y` (10-year minus 2-year) and `T10YIE` (breakeven inflation) were on the same FRED pull. The term spread steepened in the 2008 crisis while the real yield spiked, and a positive spread is not cheap long-term borrowing. Breakevens are already inside `DFII10`. Neither is a column. |

`v2_if_dgs10` is h2 plus the nominal yield. `v2_if_real_yield` is h2 plus the real yield. `v2_if_rates` is h2 plus both. h2 stays the primary.

| Month | 10y % | Real 10y % | h2 | + 10y | + real yield | + both rates |
| --- | --- | --- | --- | --- | --- | --- |
| 2008-10-01 | 3.81 | 2.75 | 50.79 Low | 48.92 Low | 46.88 Low | 45.67 Low |
| 2009-10-01 | 3.39 | 1.48 | 65.79 Moderate | 62.89 Moderate | 62.68 Moderate | 60.47 Moderate |
| 2020-04-01 | 0.66 | -0.45 | 44.34 Low | 49.13 Low | 47.52 Low | 51.54 Low |
| 2022-06-01 | 3.14 | 0.53 | 59.19 Moderate | 57.95 Moderate | 59.05 Moderate | 57.95 Moderate |
| 2026-08-01 | 4.68 | 2.40 | 77.28 High | 70.06 High | 70.69 High | 65.06 Moderate |

August 2026 is **77.28 High** on h2, **70.06 High** with the 10-year at 4.68%, **70.69 High** with the real yield at 2.40%, and **65.06 Moderate** with both. The 10-year level alone leaves August in High. Nominal and real yields together put August in Moderate. That combined column gives long yields two side-column weights (0.24). Read the 10-year column first.

October 2008 is the month the two yields disagree in a useful way. h2 is already **50.79 Low** on VIX. The nominal mean is 3.81% and h2 plus that yield is **48.92 Low**, a nudge. The real yield is 2.75% because breakevens had collapsed, close to the file high of 2.89 in 2008-11-01. h2 plus the real yield is **46.88 Low**. Both together are **45.67 Low**. The nominal 10-year is not the stress in that month. The real yield is.

April 2020 is the other case. The 10-year mean is 0.66% and the real yield is -0.45%. h2 is **44.34 Low**. With the 10-year it is **49.13 Low**. Long rates were easy while employment had broken, so these columns do not mark the COVID labor trough.

October 2009 nominal is 3.39% (h2 **65.79 Moderate**, plus the 10-year **62.89 Moderate**). June 2022 nominal is 3.14% (h2 **59.19 Moderate**, plus the 10-year **57.95 Moderate**, plus both yields **57.95 Moderate**).

### If debt, HUD, and Edelman stayed

h2 drops debt, homelessness, and Edelman trust. v1 held keeps them, and on the live formula August is the locked **57.11**. Those are different baskets. This section is the literal replacement on **h2**, before treating the drop as settled.

`v2_if_debt_included` adds debt-to-GDP at weight 0.12 and the v1 endpoints (0 to 200) when that month has a print. `v2_if_kept_debt_hud_trust` adds that same debt rule plus homelessness **0.23** at the v1 weight 0.09 (range 0 to 0.5) and trust **41** at the v1 weight 0.12 (range 0 to 80, higher trust more stable). The HUD and Edelman numbers are the 19 September 2026 pins on every month. They are not a historical series. Crime stays on the h2 rule: absent months stay absent. The crime lock is not put back.

| Month | h2 | Debt status | h2 + debt | h2 + debt, HUD pin, Edelman pin | v1 held |
| --- | --- | --- | --- | --- | --- |
| 2008-10-01 | 50.79 Low | observed | 52.43 Low | 52.43 Low | 59.31 Moderate |
| 2009-10-01 | 65.79 Moderate | observed | 64.77 Moderate | 62.48 Moderate | 59.37 Moderate |
| 2020-04-01 | 44.34 Low | observed | 43.19 Low | 44.65 Low | 51.67 Low |
| 2022-06-01 | 59.19 Moderate | excluded | 59.19 Moderate | 58.02 Moderate | 55.56 Moderate |
| 2026-08-01 | 77.28 High | carried_forward | 72.25 High | 68.57 Moderate | 57.11 Moderate |

August 2026 on h2 is **77.28 High**. Debt that month is the carried 2026 print (status carried_forward). h2 plus debt is **72.25 High**. h2 plus debt and the two pins is **68.57 Moderate**. The live held basket is **57.11 Moderate**. On that live basket, dropping debt scores **60.79 Moderate**, dropping homelessness scores **57.55 Moderate**, and dropping trust scores **58.28 Moderate**. Putting the three demoted inputs back on h2 does not reproduce 57.11. The live score still uses unemployment, the crime lock, and the v1 weights. h2 that month has a calm labor blend, calm VIX, and no crime trial.

June 2022 has no debt print in this replay (excluded), so the kept column that month is h2 plus the two pins only: **58.02 Moderate** against h2 **59.19 Moderate**. October 2008 and April 2020 do have debt. Their kept scores are **52.43 Low** and **44.65 Low**.

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

**Great Recession window.** The locked partial replay (inflation, unemployment, debt only) runs 55.17 (2009-12-01) to 64.40 (2008-12-01). All 25 months are Moderate. Held-constant crime, homelessness, and trust keep that window Moderate as well (56.90 (2009-12-01) to 61.90 (2008-12-01)). The v2 candidate runs 50.79 (2008-10-01) to 70.26 (2008-05-01). The low is **October 2008 at 50.79 Low**, with a VIX monthly mean of 61.18. November is the VIX-mean peak at 62.67 (highest daily close 80.86) and scores **52.40 Low**, a bit higher than October because headline CPI had already cooled. The Low months are 2008-10-01 (50.79), 2008-11-01 (52.40). October 2009, the UNRATE peak at 10.0 and a labor blend of 77.25, is v1 partial **59.72 Moderate** and h2 **65.79 Moderate**. h1 scored October 2008 at 45.62 Low and October 2009 at 68.72 Moderate. October 2009 moved closer to October 2008 (15.00 points apart, versus 23.10 under h1). It is still Moderate, and October 2008 is still the lower score. The tighter labor band did not make late 2009 the window's trough. There is no RTCI month in this window, so the v2 candidate and the crime-off series are the same path. No v2 month in that window is Critical. None of the locked partial months leave Moderate.

**COVID window.** Locked partial runs 45.51 (2020-04-01) to 60.48 (2020-03-01). April 2020 is **45.51 Low** partial and **51.67 Low** held constant (UNRATE 14.8, debt-to-GDP 132.66). Taking debt out of that held basket moves April to **55.27 Moderate**. Taking homelessness or trust out does not clear the Low band. Through the Great Recession window the held basket stays Moderate with or without debt, homelessness, or trust. The v2 candidate runs 44.34 (2020-04-01) to 77.91 (2020-01-01). March 2020, the VIX monthly-mean peak at 57.74 (highest daily close 82.69), scores **62.82 Moderate** because the labor blend is still 80.30. April, when prime-age EPOP is 69.6 and the blend is 72.66, scores **44.34 Low** (h1 was 48.32 Low). With crime excluded that month is **37.56 Critical**, because the labor trough is a larger share of the 0.80 denominator. That is the same month without the trial crime input, not a second shock. Replacing the blend with UNRATE that month scores **54.60 Low**. The trial crime rate that month is 2642.84, not 2723. Held-constant v1 for the whole year runs 51.67 (2020-04-01) to 59.78 (2020-03-01).

**Recent path.** January 2022 through August 2026. Debt is excluded on the v1 partial column before October 2025: this pull does not contain 2022–2025Q3 `GFDEGDQ188S` prints, and those months are not filled by carrying 2020 forward. The 2022 v1 partial lows are inflation plus unemployment only. June 2022 is **51.42 Low** on that two-input v1 basket, and **55.56 Moderate** once crime, homelessness, and trust are pinned at the 2026 baselines.

October 2025 is a BLS gap. CPI, food, unemployment, EPOP, and participation were non-numeric (`-(X)` or `-(9)`) and are blank. v1 partial that month is debt alone (**38.72 Critical**). The v2 candidate uses only `vix_month_mean|incident_rate` (denominator 0.36) and prints **80.82 High**. That pair is the same thin month, not a crash and not a boom. Among recent months with all five trial inputs present, the v2 candidate runs 59.19 (2022-06-01) to 79.19 (2026-01-01).

From October 2025 the debt print on v1 is the published 122.56815. From January 2026 it is the fixture print 122.59387, carried the way the live publisher carries a quarter. August 2026 held-constant v1 is **57.11**, the same six inputs as the locked 57.11. The v2 candidate that month is **77.28 High** with crime excluded (the RTCI file ends April 2026, trial rate 2074.97). The gap versus 57.11 is the basket: debt, homelessness, and trust are out, and the labor blend and VIX are calm. It is not a claim that stability improved inside v1.0.0.

Food CPI year-over-year uses the h2 range −2 to 15. No month in these windows has food inflation above 15, so the food component does not hit the fully-unstable clamp. No month in these windows has food inflation below −2, so the food component does not hit the fully-stable clamp. 4 months have negative food inflation inside that range, so they lean stable without scoring fully stable. 9 months are above the h1 ceiling of 10 (2022-05-01, 2022-06-01, 2022-07-01, 2022-08-01, 2022-09-01, 2022-10-01, 2022-11-01, 2022-12-01, 2023-01-01). Under h1 those months clamped food at fully unstable. June 2022 food is 10.4 and September 2022 is 11.2; the h2 candidate those months is 59.19 and 60.44. June 2022 moves from h1 **52.87** to h2 **59.19**. That is less stressed than h1's hard floor on food, which is what the wider range was for. The recent-window low on the v2 candidate, including thin months, is **59.19 on 2022-06-01**.

## Crime trial, and why 2008 cannot use it

The RTCI cleaned file in this pull covers **January 2018 through April 2026**. The 2008 window has no trial rate. Fair replay does not backfill those months with the locked 2723, with a later RTCI month, or with a different crime series.

The live fetcher still returns `incident_rate` **2723** and does not score the file. Its diagnostic month rule is the lexicographic maximum of the `Date` text, which is why a later calendar month can lose to "September". This replay uses the calendar month instead, and it does not change that lock. September 2025 in the file is a trial rate of about 2234.66, not 2723. Every usable month in this download has **621** agencies. That is a balanced sample, not a national census, and the rate's level is not comparable to a historical UCR series that this repo does not reconstruct.

From May 2026 through August 2026 the primary candidate excludes crime again, so the denominator changes. Compare those months with `v2_without_crime_index` before reading a jump as stress or relief.

## Debt, homelessness, trust, and UNRATE

Homelessness and trust cannot be replayed. The held-constant columns pin them at **0.23** and **41**. Removing one of them is `v1_held_without_homelessness` or `v1_held_without_trust` in the monthly CSV. That is the locked formula with one held input left out. It is not a historical path for that series.

Debt is historical inside the 2008 and 2020 windows (the locked fixture, including ordinary within-quarter carry-forward). It is not historical for most of the recent window. Adding it back onto the v2 basket only changes the score in months where a print is actually in hand.

UNRATE remains the v1 labor input. The composite is lower in April 2020 than a calm month, and it does not by itself mark October 2009 as the Great Recession trough. `v2_if_unrate` and `v2_if_epop_only` are in the CSV for that comparison. The blend and the EPOP-only range are hypotheses that bracket this sample. They are not estimated endpoints.

## What still blocks a v2.0 contract

- These weights and ranges are hypothesis h2. They were not fit to a loss, a utility function, or a decision threshold. h1 is the prior labeled basket, not a rejected contract.
- Rent burden is a side column, not part of h2. It is ACS 1-year `B25070` (30%+ of income), annual, carried forward from the survey-year January. The latest survey in this pull is 2024. There is no 2020 standard 1-year and no 2025 1-year here, and neither gap is filled. The 50%+ share is diagnostic only. `CUUR0000SEHA` year-over-year is a labeled rent-inflation proxy, not the income share. Neither series is in the live score.
- A household survey of missed housing payments is still not in the replay. Bank delinquency still ends at 2026 Q2.
- Treasury yields are side columns, not part of h2. `DGS10` is the nominal 10-year level and `DFII10` is the real 10-year level. `T10Y2Y` and `T10YIE` are not scored. Corporate credit spreads are still not in the replay. VIX is an equity-volatility index, not a credit spread. Card delinquency (`DRCCLACBS`, issue #48) is a side column only. It is not a BBB or high-yield OAS series.
- The labor composite is not the incubating participation penalty. That penalty still has no formula. The h2 band 72–82 is a tighter hypothesis range, not that penalty.
- The h2 food range −2 to 15 is still a draft. Prints outside it still clamp. h1's 0–10 range is what clamped the 2022 peak at fully unstable and mild deflation at fully stable.
- Crime has no fair 2008 path from RTCI. The published input remains locked at 2723. Agency coverage and the 12-month RTCI definition are not a national historical crime rate.
- Homelessness and Edelman trust still have no monthly history. `v2_if_kept_debt_hud_trust` pins them at the 19 September 2026 values so the demotion can be compared with leaving them in. That pin is not a 2008 or 2020 observation.
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
