# Local shelter companions — not in the score

The weekly publisher shows four local shelter readings beside the BugOut Index. Each one is labeled with its place and **not in the BugOut Index**. None has a weight. None is an input to `compute_index` or `CORE_METRICS`. A failed fetch does not abort the publish. When a previous block exists, that block is carried forward with its observation date.

This note is the issue [#81](https://github.com/adammontville/bugoutindex/issues/81) companion for homelessness frequency. It does not change the live score.

## What stays in the score

HUD AHAR Part 1 remains the annual national homelessness anchor. The published input is still **0.23**, HUD reference date **2024-01-01**, read from `runtime/data/annual_inputs.csv`. Trust stays the Edelman United States Government figure. Crime stays **2723.0**. Methodology version stays **1.0.0**.

## Companions that ship

| Companion | Publisher | Series | Cadence | Geography | What the number is |
| --- | --- | --- | --- | --- | --- |
| [NYC DHS](nyc_dhs_shelter_census.md) | NYC Department of Homeless Services, via NYC Open Data [`k46n-sa2m`](https://data.cityofnewyork.us/Social-Services/DHS-Daily-Report/k46n-sa2m) | `total_individuals_in_shelter` | Daily | New York City only | People in the DHS shelter system on the census date |
| Ramsey County | Ramsey County open data [`9mck-bcqu`](https://data.ramseycountymn.gov/dataset/Emergency-shelter-population-and-utilization/9mck-bcqu) | Sum of `population_enrollees` across household types | Monthly | Ramsey County, Minnesota (St. Paul area) only | People in emergency shelter that month |
| Toronto | City of Toronto Open Data, [Daily Shelter & Overnight Service Occupancy & Capacity](https://open.toronto.ca/dataset/daily-shelter-overnight-service-occupancy-capacity/) | Sum of `SERVICE_USER_COUNT` on the current resource named "Daily shelter overnight occupancy" | Daily | Toronto only | Service users reported by overnight programs that night. Not a deduplicated person count |
| San Francisco | DataSF Scorecard Measures [`kc49-udxn`](https://data.sf.gov/City-Management-and-Ethics/Scorecard-Measures/kc49-udxn), measure `279`, Department of Homelessness and Supportive Housing | `actual`, stored by the city as a ratio and shown here in percent | Monthly | San Francisco only | Average occupancy rate of year-round temporary shelter and crisis intervention programs. **Not a headcount** |

Checked against the live APIs on 2026-10-07. Ramsey’s newest month stamp was 2026-08-01. Toronto’s newest occupancy date was 2026-10-05. San Francisco’s newest month with an `actual` was 2026-08-31 (the September row was present with a blank actual and is dropped).

Ramsey keeps a month only when Families, Single Men, Single Women, and Youth (18-24) are all present. A missing type would undercount, so that month is skipped. Toronto follows the city’s current datastore file by name and does not read the year-stamped archives. San Francisco does not read measure `7274` (bed inventory). That series is capacity, not people in shelter.

## How these differ from HUD AHAR

HUD AHAR is a national point-in-time rate, sheltered and unsheltered, about once a year. These companions are local, mostly sheltered, and more frequent. Toronto is not in the United States. San Francisco is a rate of beds or units in use, not a count of people and not a percent of the U.S. population. Same topic, different place, different definition, different cadence. That is why they sit beside the index.

## Recommendation

**Add as shadows. Keep the annual HUD checklist for the score.** A later methodology version would be required before any of these series could enter `compute_index`.

## Candidates checked and not used

These were evaluated because they are public and on the topic. They are not fetched.

| Candidate | Why it is not a companion |
| --- | --- |
| Los Angeles / LAHSA interim housing dashboard | Public dashboard of occupancy, not a stable open-data API. LAHSA describes it as not updated daily. The real-time bed inventory is inside HMIS for authorized users. |
| Chicago emergency temporary shelter census (`a4p3-hxgg` and the related new-arrivals tables) | City of Chicago marks the datasets historical. They stopped updating on 2025-11-05. They also count city-funded new-arrival shelters, not the general homeless shelter system. |
| Chicago DFSS monthly shelter utilization (`vg8w-2w9y`) | Open data, but the dataset was last updated 2023-08-14. |
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
