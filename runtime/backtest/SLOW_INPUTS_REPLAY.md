# Slow-input refresh replay

Research only. Homelessness and trust stay on the annual checklist. This note does not change `compute_index`, methodology **1.1.0**, `docs/data/latest.json`, or `runtime/data/weekly_bugout_index.csv`. Companions stay outside the score. The live basket of **2026-10-09** remains **57.66**, Moderate Stability, with homelessness **0.23** and trust **41**.

## Recommendation

Refresh both inputs from the same sources on their release cycle. Stamp that catch-up as a **1.1.x** data revision. Do not replace either series, and do not call it 1.2.0.

| Input | Recommendation | Reading to copy | Projected score on the 2026-10-09 basket | Band |
| --- | --- | --- | ---: | --- |
| Homelessness | Refresh the 2025 HUD AHAR | **0.22** | **57.91** if only homelessness moves | Moderate |
| Trust | Refresh the 2026 Edelman US Government row | **39** | **57.25** if only trust moves | Moderate |
| Both, the catch-up | Copy both cells in one checklist edit | **0.22** and **39** | **57.50** | Moderate |

Keeping the checklist as it is leaves the score at **57.66** Moderate. Replacing trust with Pew prints **52.66** Low. Replacing it with Gallup's 14-institution average prints **54.75** Low. Both replacements cross the 55 line. The same-source catch-up does not.

1.1.x is a label for the history step, not a new formula. Endpoints, weights, trust inversion, and the divide-by-0.72 rule stay. Methodology 1.1.0 already tells a person to edit the checklist when HUD or Edelman publishes. The 2025 AHAR has been public since 29 May 2026, and the 2026 Edelman barometer since 18 January 2026. The cells were not updated. A 1.2.0 bump would mean a different series. Pew, Gallup, and the shelter companions are that different series, and they stay beside the index.

Across the 26 committed weeks, the same-source pair stays **Moderate Stability**. The rounded gap versus the published score is **-0.42 to -0.16** points. HUD alone, on the weeks that can already see the 2025 AHAR, raises the index by **0.25**. Edelman 2026 is public for the whole history and lowers it by **0.41 to 0.42**.

| Basket | Homelessness | Trust | Score | Band | Difference |
| --- | ---: | ---: | ---: | ---: | ---: |
| Published 2026-10-09 | 0.23 | 41 | 57.66 | Moderate | 0.00 |
| HUD 2025 AHAR only | 0.22 | 41 | 57.91 | Moderate | +0.25 |
| Edelman 2026 only | 0.23 | 39 | 57.25 | Moderate | -0.41 |
| Both same-source | 0.22 | 39 | 57.50 | Moderate | -0.16 |
| Pew in the trust slot | 0.23 | 17 | 52.66 | Low | -5.00 |
| Gallup 14-institution average | 0.23 | 27 | 54.75 | Low | -2.91 |
| Gallup Congress only | 0.23 | 9 | 51.00 | Low | -6.66 |
| Local rate at the 0.5 endpoint | 0.50 | 41 | 50.91 | Low | -6.75 |

The last two rows are rejected sensitivities on that one basket. They are not weekly options. Congress at 9 is Gallup's legislative reading, not a government-trust percent. A local shelter rate at or above the **0.5** homelessness endpoint normalizes to 0 and prints **50.91** Low. The NYC census on this publish is 84,042 people. That headcount is more than 0.5 percent of any population under 16.8 million, so a New York City rate in the national slot clamps on this basket. The score above uses the endpoint itself. Any higher raw value clamps to the same index.

## How the two inputs are fetched today

The scored number is the checklist cell. Crime before methodology 1.1.0 kept `PUBLISHED_INCIDENT_RATE` (2723.0) as the scored input while the fetcher could already see a newer RTCI file. Homelessness and trust have no second candidate sitting beside the cell. The weekly job does not download HUD or Edelman, so a newer report changes the score only after a person edits the cell.

| | Homelessness | Trust in government |
| --- | --- | --- |
| Fetcher | `runtime/data/fetch/fetch_homelessness_rate.py` | `runtime/data/fetch/fetch_trust_in_government.py` |
| Source | HUD AHAR Part 1, national point-in-time rate | Edelman Trust Barometer, United States, Government |
| Where the cell lives | `homelessness_rate` row of `runtime/data/annual_inputs.csv` | `trust_in_government` row of the same file |
| Scored value | **0.23** | **41** |
| Vintage | 2024 AHAR. HUD's phrase is about **23 of every 10,000** people. Headcount **771,480** on a night in the last 10 days of January 2024. The page note also shows 771,480 / 335,000,000 × 100 ≈ 0.23 | Survey year **2025**. The archive row is Government **41** |
| Shown observation date | **2024-01-01** (HUD reference date) | **2025** (survey year only, no month or day) |
| `fetched_at` | Empty. The reference date is not a fetch clock | The survey year, `2025` |
| `reviewed_at` | **2025-03-13**, the day the published cell was committed, not a HUD release date | **2025-03-13**, the day the Edelman archive was committed |
| Update cadence | Annual, when a new AHAR Part 1 is out. The weekly job does not look | Annual, when a new Trust Barometer is out. A new column in `edelman-trust-barometer-us.csv` does not change the score |
| Provenance kind | `manual`, `last_set` = `2024 HUD AHAR` | `annual`, `year` = `2025` |

The weekly publisher calls both fetchers inside `fetch_core_metrics`. All six cores must succeed (`MIN_REQUIRED_METRICS` is 6). A checklist failure returns `status: error`, `fetched_at: null`, and empty `data`, and the publish refuses. The previous site stays up. The fetchers do not fill a gap with 0.23 or 41, and they do not stamp the clock.

Guards in `runtime/data/fetch/annual_inputs.py`:

- The file, the header, and exactly one row for the metric must exist.
- `value` must be a number. `observation_period` and `source` must be non-blank.
- Homelessness `observation_date` must be `YYYY-MM-DD`. Trust `observation_date` must be a four-digit year. A month or day on the trust row fails the fetch.
- `reviewed_at` must be a real calendar date. A timestamp, including `2025-01-01T00:00:00Z`, fails the fetch.
- `source_url`, when present, must start with `http://` or `https://`.
- The loader does not call `datetime.now`, `date.today`, or `utcnow`.

Weights and endpoints, unchanged by this note: homelessness **0 to 0.5**, weight **0.09**; trust **0 to 80**, inverted, weight **0.12**. The six weights still sum to **0.72**.

## Newer value of the same source

### HUD

The newest national AHAR Part 1 is the **2025** report, posted **May 2026**. HUD's press release is dated **29 May 2026** ([HUD No. 26-037](https://www.hud.gov/news/hud-no-26-037)). The report PDF is [2025 AHAR Part 1](https://www.huduser.gov/portal/sites/default/files/pdf/2025-AHAR-Part-1.pdf). HUD USER lists that file as the current Part 1. There is no 2026 national AHAR as of 10 October 2026. CoCs submitted January 2026 counts in the spring. Local 2026 counts exist. They are not the national rate this checklist uses.

The 2025 report's national sentence is the same shape as the 2024 sentence that became 0.23. On a single night in January 2025, **745,652** people were counted, about **22 of every 10,000**. The 2024 report said **771,480** people, about **23 of every 10,000**. The checklist stores that rate as a percent to two decimals. The same-source successor is **0.22**, observation date **2025-01-01**, period label `January 2025 point-in-time count`.

The weekly job runs at 23:30 UTC on Friday. 29 May 2026 was a Friday, and the HUD page was submitted that afternoon. This replay treats a release as usable on a publication date on or after the release date, so the **2026-05-29** row is the first week that can carry 0.22. Earlier weeks in this history stay on 0.23 because the 2025 report was not public yet. That is the column "HUD refresh."

A machine-readable copy of the same count is the HUD USER workbook "2007–2025 Point-in-Time Estimates by State" (XLSB) linked from the [2025 AHAR page](https://www.huduser.gov/portal/datasets/ahar/2025-ahar-part-1-pit-estimates-of-homelessness-in-the-us.html). It is annual, national once the rows are summed, and a US government work. It can feed the checklist once a year. It is not a weekly series, and this replay does not wire it into the publisher.

On the 2026-10-09 basket, homelessness 0.22 with trust still 41 scores **57.91** Moderate.

### Edelman

The newest Trust Barometer is the **2026** report, released **18 January 2026** ([Edelman news release](https://www.edelman.com/news-awards/2026-edelman-trust-barometer-society-slides-into-insularity)). Fieldwork in that release is **23 October through 18 November 2025**. The product page lists a slightly different window, 25 October through 16 November 2025. Either window is still survey year 2026. The checklist stores the year only.

The scored series is United States, **Government**, not the four-institution Trust Index. The global report puts the US Trust Index at **47**, the same average as the 2025 archive (business 55, government 41, media 42, NGOs 50). The government percent used here is **39**:

- [Visual Capitalist, 7 February 2026](https://www.visualcapitalist.com/charted-do-people-trust-the-media-or-government-more/), a country table of the 2026 Edelman government and media scores. United States government **39**, media **44**.
- [Dance USA, 15 June 2026](https://www.danceusa.org/ejournal/2026/06/15/marketing-moves-for-dance-organizations-in-2026), citing the U.S. report "Trust Amid Insularity": Trust Index 47, government **39**, media **44**.
- An Edelman Netherlands note on the same report: government trust **57** in the Netherlands and **39** in the United States.

Media 44 and government 39, with business and NGOs unchanged, keep the Trust Index at 47. That is a consistency check. This environment received HTTP 403 from edelman.com, so the government cell was not re-read from the PDF bytes. A checklist edit should open the U.S. report and copy the Government row. The scores below use **39**.

Every committed week is after 18 January 2026, so the Edelman-refresh column is 39 on all 26 weeks. The 2025 figure of 41 remains what the live checklist scores. On the 2026-10-09 basket, trust 39 with homelessness still 0.23 scores **57.25** Moderate. Both substitutions together score **57.50** Moderate.

There is no public Edelman API. The historical archive in the repo is a small table of US institution percents. It does not feed `compute_index`. Republication of the full barometer is Edelman's report, not an open series.

## Fresher candidates

These were checked because they move more often, or because they are already in the repo. None of them is the HUD rate or the Edelman government percent. Putting one into the existing slot changes the question and, for the trust companions, the band.

| Candidate | Cadence | Coverage | History in hand | License and machine readability | Why it stays out |
| --- | --- | --- | --- | --- | --- |
| NYC DHS `k46n-sa2m`, `total_individuals_in_shelter` | Daily | New York City shelter census. Not unsheltered. Not national | Open-data fetch. The weekly history file has the latest census beside each publish | NYC Open Data. Socrata JSON | A headcount. 84,042 on 2026-10-08. In the national 0–0.5 slot it clamps. See the basket table |
| Nashville–Davidson HMIS | Monthly PDF | People who experienced homelessness that month in one county's HMIS. Not a one-night census | Checklist, July 2025 through July 2026 | Manual. No API | Local, different definition |
| Austin / Travis County ECHO | Monthly dashboard, published late | Six-month engagement count of people likely sheltered | One checklist row, data effective 2025-07-01, published 2025-09-10 | Manual | Local, lagged, different definition |
| Ramsey County `9mck-bcqu` | Monthly | Emergency-shelter enrollees in one county | Open-data fetch. Newest stored month on the companion note was 2026-08-01 | County open data | Local headcount |
| Denver HOST occupancy | The cited release. The city dashboard is monthly | Occupancy rate for a seven-shelter pilot, **93%** in Q2 2026 | One checklist row | Manual | An occupancy rate, not a population rate |
| San Francisco DataSF measure `279` | Monthly | Average occupancy of year-round temporary shelter | Open-data fetch. Newest stored month on the companion note was 2026-08-31 | DataSF open data | An occupancy rate, not a population rate |
| HUD PIT by state, 2007–2025 | Annual | National once summed. Same PIT definition as the scored input | The workbook HUD posted with the 2025 AHAR | US government work. XLSB | Same source, same cadence. Use it to fill the checklist, not to replace it |
| Pew public trust | Irregular waves | Share who trust the government in Washington just about always or most of the time | Excerpt in `pew_trust_shadow.csv`: May 2024 **22**, February 2025 **17**, September 2025 **17**. Pew's chart runs 1958–2025. This repo does not store that archive | Cited excerpt. The weekly job does not download Pew's CSV | Different question. **17** in the trust slot scores **52.66** Low on the latest basket, and **Low Stability** on every committed week |
| Gallup confidence in institutions | Annual, typically June | "A great deal" plus "quite a lot." 2026 poll is June 1–15, article 13 July 2026. Congress **9**, presidency **27**, Supreme Court **27**, 14-institution average **27** | Current year only, by design. Earlier years are not in the checklist | Gallup. Continuous republication may need permission. The weekly job does not scrape Gallup | Different question, still annual. The 14-institution average scores **54.75** Low on the latest basket. Congress at 9 scores **51.00** |
| GSS confidence items, ANES trust in Washington, OECD trust in government | Biennial, or election years, or about every two years | Related questions. Not the Edelman government percent | Not in this repo | GSS and ANES are public microdata. OECD's trust figure is often the Gallup World Poll | Not a weekly series, and not the same question. They do not update the checklist faster than Edelman's January release |

No blend of these is a national homelessness rate or an Edelman government percent. Averaging 41 and 17 treats two questions as one number. Scaling the national PIT by the change in the NYC shelter census assigns one city's sheltered count to the sheltered-plus-unsheltered national rate. The 2025 AHAR itself says New York and Illinois drove a large part of the national decline, which is a reason not to let New York stand in for the country. The shelter companions stay a labeled panel.

## Weekly scores

Each cell is `compute_index` on that week's published inflation, unemployment, debt-to-GDP, and crime. Only homelessness and trust change.

- **HUD refresh** uses 0.23 through 2026-05-22 and **0.22** from 2026-05-29.
- **Edelman refresh** uses **39** on every row. The 2026 report predates 2026-04-21.
- **Both** is those two together. The band stays Moderate on every row.
- **Pew** uses the September 2025 wave, **17**, public in the 4 December 2025 article. The band is **Low Stability** on every row.
- **Gallup as-of** keeps the published Edelman value through **2026-07-10**. The 13 July 2026 article is first usable on **2026-07-17**. From that week the trust input is **27** and the band is Low.

| Publication | Published | HUD refresh | Edelman refresh | Both | Pew | Gallup as-of |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 2026-04-21 | 57.03 | 57.03 | 56.62 | 56.62 | 52.03 | 57.03 |
| 2026-04-25 | 57.03 | 57.03 | 56.62 | 56.62 | 52.03 | 57.03 |
| 2026-05-01 | 57.03 | 57.03 | 56.62 | 56.62 | 52.03 | 57.03 |
| 2026-05-08 | 57.03 | 57.03 | 56.62 | 56.62 | 52.03 | 57.03 |
| 2026-05-15 | 56.62 | 56.62 | 56.20 | 56.20 | 51.62 | 56.62 |
| 2026-05-22 | 56.62 | 56.62 | 56.20 | 56.20 | 51.62 | 56.62 |
| 2026-05-29 | 56.62 | 56.87 | 56.20 | 56.45 | 51.62 | 56.62 |
| 2026-06-05 | 56.62 | 56.87 | 56.20 | 56.45 | 51.62 | 56.62 |
| 2026-06-12 | 56.30 | 56.55 | 55.88 | 56.13 | 51.30 | 56.30 |
| 2026-06-19 | 56.28 | 56.53 | 55.87 | 56.12 | 51.28 | 56.28 |
| 2026-06-26 | 56.30 | 56.55 | 55.88 | 56.13 | 51.30 | 56.30 |
| 2026-07-03 | 56.36 | 56.61 | 55.95 | 56.20 | 51.36 | 56.36 |
| 2026-07-10 | 56.36 | 56.61 | 55.95 | 56.20 | 51.36 | 56.36 |
| 2026-07-17 | 56.95 | 57.20 | 56.53 | 56.78 | 51.95 | 54.03 |
| 2026-07-24 | 56.95 | 57.20 | 56.53 | 56.78 | 51.95 | 54.03 |
| 2026-08-01 | 56.95 | 57.20 | 56.53 | 56.78 | 51.95 | 54.03 |
| 2026-08-07 | 57.02 | 57.27 | 56.60 | 56.85 | 52.02 | 54.10 |
| 2026-08-14 | 57.15 | 57.40 | 56.73 | 56.98 | 52.15 | 54.23 |
| 2026-08-21 | 57.15 | 57.40 | 56.73 | 56.98 | 52.15 | 54.23 |
| 2026-08-29 | 57.15 | 57.40 | 56.73 | 56.98 | 52.15 | 54.23 |
| 2026-09-05 | 57.15 | 57.40 | 56.73 | 56.98 | 52.15 | 54.23 |
| 2026-09-12 | 57.11 | 57.36 | 56.69 | 56.94 | 52.11 | 54.19 |
| 2026-09-19 | 57.11 | 57.36 | 56.69 | 56.94 | 52.11 | 54.19 |
| 2026-09-25 | 57.11 | 57.36 | 56.69 | 56.94 | 52.11 | 54.19 |
| 2026-10-02 | 57.04 | 57.29 | 56.62 | 56.87 | 52.04 | 54.12 |
| 2026-10-09 | 57.66 | 57.91 | 57.25 | 57.50 | 52.66 | 54.75 |

## How to run

From the repository root:

```bash
python -m runtime.backtest.slow_inputs_replay
```

That rewrites this note and `runtime/backtest/output/slow_inputs_publications.csv`. No network and no `FRED_API_KEY`. The release table is `runtime/backtest/fixtures/slow_inputs_releases.csv`.

## What stays put

`docs/data/latest.json` still has methodology **1.1.0**, index **57.66**, homelessness **0.23**, and trust **41** on **2026-10-09**. `runtime/data/annual_inputs.csv` still has those two cells. `compute_index` does not read this module, the NYC census, the regional shelter panel, Pew, or Gallup.
