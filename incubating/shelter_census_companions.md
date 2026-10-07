# U.S. regional shelter companions — not in the score

The weekly publisher shows six local U.S. shelter readings beside the BugOut Index. Each one is labeled with its place and **not in the BugOut Index**. None has a weight. None is an input to `compute_index` or `CORE_METRICS`. A failed fetch, or a bad checklist, does not abort the publish. When a previous block exists, that block is carried forward with its observation date.

This note is the issue [#81](https://github.com/adammontville/bugoutindex/issues/81) companion for homelessness frequency. It does not change the live score.

The panel is a set of regional bellwethers, not a national total:

| Region | Place |
| --- | --- |
| Northeast | New York City |
| Southeast | Nashville–Davidson, Tennessee |
| South | Austin / Travis County, Texas |
| Midwest | Ramsey County, Minnesota |
| Southwest | Denver, Colorado |
| West | San Francisco |

Chicago is the gap. DFSS daily shelter reports are not public open data. The monthly utilization dataset `vg8w-2w9y` was last updated 2023-08-14. The new-arrivals shelter tables are marked historical and stopped on 2025-11-05. There is no current citywide census to put on this panel.

## What stays in the score

HUD AHAR Part 1 remains the annual national homelessness anchor. The published input is still **0.23**, HUD reference date **2024-01-01**, read from `runtime/data/annual_inputs.csv`. Trust stays the Edelman United States Government figure. Crime stays **2723.0**. Methodology version stays **1.0.0**.

## Companions that ship

| Companion | How it is read | Series | Cadence | Geography | What the number is |
| --- | --- | --- | --- | --- | --- |
| [NYC DHS](nyc_dhs_shelter_census.md) | Open data fetch | `total_individuals_in_shelter` on [`k46n-sa2m`](https://data.cityofnewyork.us/Social-Services/DHS-Daily-Report/k46n-sa2m) | Daily | New York City only | People in the DHS shelter system on the census date |
| Nashville–Davidson | Manual checklist | `nashville_hmis_people` | Monthly PDF | Nashville–Davidson only | People who experienced homelessness that month in HMIS. Not a one-night census. Rescue Mission counts on the same PDF are not included |
| Austin / Travis County | Manual checklist | `austin_sheltered_people` | Monthly dashboard, with publication lag | Austin/Travis County only | People engaged in the prior six months and likely experiencing sheltered homelessness, as printed on the ECHO dashboard |
| Ramsey County | Open data fetch | Sum of `population_enrollees` on [`9mck-bcqu`](https://data.ramseycountymn.gov/dataset/Emergency-shelter-population-and-utilization/9mck-bcqu) | Monthly | Ramsey County, Minnesota only | People in emergency shelter that month |
| Denver | Manual checklist | `denver_shelter_occupancy` | The cited HOST release; the citywide dashboard is monthly | Denver only | Occupancy rate for the seven-shelter HOST pilot. **Not a headcount** |
| San Francisco | Open data fetch | DataSF [`kc49-udxn`](https://data.sf.gov/City-Management-and-Ethics/Scorecard-Measures/kc49-udxn) measure `279` | Monthly | San Francisco only | Average occupancy rate of year-round temporary shelter and crisis intervention programs. **Not a headcount** |

Open-data checks on 2026-10-07: Ramsey’s newest month stamp was 2026-08-01. San Francisco’s newest month with an `actual` was 2026-08-31.

Checklist rows entered 2026-10-07:

- Nashville July 2026 report: **2,907** people experienced homelessness in July 2026. The chart on that PDF supplies July 2025 through July 2026. PDF: [HPC monthly report July 2026](https://www.nashville.gov/sites/default/files/2026-09/HPC_Monthly_Report_July_26_v20.pdf). Index of reports: [HMIS monthly data reports](https://www.nashville.gov/departments/office-homeless-services/homeless-management-information-system/monthly-data-reports).
- Austin: **1,070** on the June 2025 dashboard, published September 10, 2025, data effective 2025-07-01. [ECHO HRS dashboard](https://echoatx.github.io/hrs-dashboard-site/).
- Denver: **93%** occupancy in Q2 2026 for the seven-shelter pilot (769 units), from the [August 4, 2026 HOST release](https://www.denvergov.org/Government/Agencies-Departments-Offices/Agencies-Departments-Offices-Directory/Department-of-Housing-Stability/News/HOST-Announces-Strong-Early-Results-from-Performance-Based-Contracting-Pilot). The monthly citywide page is the [All In Mile High dashboard](https://www.denvergov.org/Government/Agencies-Departments-Offices/Agencies-Departments-Offices-Directory/Mayors-Office/Programs-and-Initiatives/Homelessness-Initiative/All-In-Mile-High-Dashboard).

Ramsey keeps a month only when Families, Single Men, Single Women, and Youth (18-24) are all present. San Francisco does not read measure `7274` (bed inventory).

## How to update the checklist

File: [`runtime/data/shelter_region_shadow.csv`](../runtime/data/shelter_region_shadow.csv).

The weekly job copies these cells. It does not open the PDFs or the dashboards. Skip the week when there is no new cited figure. Leaving the rows alone is the correct outcome. A blank value, a bad date, or a missing series fails this companion only. The index still publishes, and the previous block is carried forward.

Do this when a new source is posted:

1. Nashville: open the [monthly reports page](https://www.nashville.gov/departments/office-homeless-services/homeless-management-information-system/monthly-data-reports) and the newest PDF. Append one `nashville_hmis_people` row with the sentence “N people experienced homelessness in Nashville in [month].” Set `observation_date` to the last day of that month. Do not add the Nashville Rescue Mission count. Keep at most 24 rows.
2. Austin: open the [ECHO HRS dashboard](https://echoatx.github.io/hrs-dashboard-site/). Read the publication date and the data-effective date, and write both into `observation_period` so the lag stays visible. Replace the `austin_sheltered_people` row with the sheltered figure the dashboard prints. Set `observation_date` to the data-effective date (`YYYY-MM-DD`). If a later edition prints the one-day sheltered snapshot (people in emergency shelter, transitional housing, or Safe Haven near the start of the month), store that count and say so in `observation_period`.
3. Denver: open the [All In Mile High dashboard](https://www.denvergov.org/Government/Agencies-Departments-Offices/Agencies-Departments-Offices-Directory/Mayors-Office/Programs-and-Initiatives/Homelessness-Initiative/All-In-Mile-High-Dashboard) or the newest HOST shelter release. Replace `denver_shelter_occupancy` with the occupancy rate or people-in-shelter figure that release actually prints. Keep the value a percent (0–100) while the series is an occupancy rate. If you switch to a headcount, change `VALUE_KINDS` in `fetch_shelter_region_shadow.py` in the same commit and say what the new figure measures in this note.

| Column | What to write |
| --- | --- |
| `series` | `nashville_hmis_people`, `austin_sheltered_people`, or `denver_shelter_occupancy` |
| `value` | Whole number of people, or a percent for Denver occupancy |
| `observation_period` | The month, dashboard window, or quarter the publisher names |
| `observation_date` | Last day of that period, or the data-effective date, `YYYY-MM-DD` |
| `source` | Short document name |
| `source_url` | `https://` URL of the page or PDF you read |
| `reviewed_at` | Calendar date you checked the source, `YYYY-MM-DD`, not earlier than `observation_date` |

Write a date. Do not write a clock time, and do not write `2025-01-01T00:00:00Z`.

## How these differ from HUD AHAR

HUD AHAR is a national point-in-time rate, sheltered and unsheltered, about once a year. These companions are local and more frequent. Nashville’s monthly figure includes outreach and housing programs, not only a shelter night. Austin’s card is a six-month engagement count and the public extract lags the month it names. Denver and San Francisco are occupancy rates. Same topic, different place, different definition, different cadence. That is why they sit beside the index.

## Recommendation

**Add as shadows. Keep the annual HUD checklist for the score.** A later methodology version would be required before any of these series could enter `compute_index`.

## Candidates checked and not used

These were evaluated because they are public and on the topic. They are not fetched.

| Candidate | Why it is not a companion |
| --- | --- |
| Toronto daily shelter occupancy | A working open-data census, removed from this panel because the panel is U.S. places only. |
| Chicago | No current public citywide shelter census. DFSS daily reports are not open data. Monthly utilization `vg8w-2w9y` was last updated 2023-08-14. New-arrivals tables (`a4p3-hxgg` and related) are marked historical and stopped on 2025-11-05. |
| Los Angeles / LAHSA interim housing dashboard | Public dashboard of occupancy, not a stable open-data API. LAHSA describes it as not updated daily. The real-time bed inventory is inside HMIS for authorized users. |
| Seattle / King County (KCRHA) | System performance and PIT dashboards. De-identified HMIS extracts require a data-use agreement. No public census API. `performance.seattle.gov` homelessness series are program objectives, last touched 2025-06-17, and are not a shelter census. |
| Boston | Annual homeless census (PIT). Analyze Boston has no shelter-census dataset. |
| Massachusetts EA family shelter | Mass.gov visualization plus biweekly legislative PDFs. No stable series API. Parsing those PDFs would be brittle. |
| San Francisco HSH live occupancy dashboard | The city says historic capacity and occupancy are not available on that dashboard. It is not a downloadable series. The scorecard rate above is the series that is. |
| Calgary emergency shelter daily occupancy (`7u2t-3wxf`, from Alberta open data) | Official daily occupancy, but the newest census date on 2026-10-07 was 2025-06-30. The provincial file was last modified 2025-09-23. Too stale to show as a current companion. |
| Edmonton daily occupancy (`ni6e-cvyq`) | Last updated 2019-09-13. |
| Alberta province-wide emergency shelter file | Same staleness as Calgary, and it would double-count Calgary if both were used. |
| California HDIS and CA System Performance Measures | Quarterly files of people who received homeless services over a calendar year, and annual performance measures. Not a shelter-night census. |
| Hennepin County weekly shelter report | Dashboard and PDF, not a stable open-data API. |
| Cambridge, Massachusetts and Norfolk, Virginia point-in-time tables | Annual counts. Same cadence class as HUD AHAR, not a high-frequency companion. |
| Ramsey County family shelter waitlist (`g5mu-s9vm`) | Weekly placements and waitlist counts, not a census of people in shelter. |
| Montgomery County, Maryland shelter activation and police calls | Activation flags and call volume, not a shelter census. |
| NYC runaway and homeless youth daily census | Still New York City, and a youth-bed vacancy series rather than a second jurisdiction. |
