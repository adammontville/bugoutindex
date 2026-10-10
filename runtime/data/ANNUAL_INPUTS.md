# Annual manual inputs

Homelessness and trust in government are annual figures. The weekly job reads them from [`annual_inputs.csv`](annual_inputs.csv) in this directory. It does not look up a newer HUD report or a newer Edelman year on its own, and it does not invent a value or a timestamp.

The next weekly publish reads the rows in that table and stamps methodology **1.1.1**. That version is a data revision: homelessness **0.22** (2025 HUD AHAR, observation date **2025-01-01**) and trust **39** (Edelman survey year **2026**). Endpoints, weights, and schema version 1 are unchanged. Weeks already published stay as they are. Through 2026-10-02 that is methodology 1.0.0. The 2026-10-09 week is methodology 1.1.0, with homelessness **0.23** and trust **41**. This checklist does not rewrite those weeks, and it does not rewrite `docs/data/latest.json`.

## Once a year

Do this when HUD publishes a new Annual Homeless Assessment Report (AHAR), Part 1, or when Edelman publishes a new Trust Barometer. Skip the week if neither has a new primary source. Leaving the row alone is the correct outcome.

### Homelessness

1. Open the new HUD AHAR Part 1 (point-in-time / PIT count). The current citation is the [2025 AHAR Part 1 PDF](https://www.huduser.gov/portal/sites/default/files/pdf/2025-AHAR-Part-1.pdf) (745,652 people; about 22 per 10,000). PIT counts are also listed on the [HUD Exchange PIT/HIC page](https://www.hudexchange.info/programs/hdx/pit-hic/).
2. Take the national homelessness **rate as a percent of population** (the checklist input is `0.22`, not the headcount). Keep the same two-decimal percent HUD states. Do not store a more precise quotient.
3. Set `observation_date` to the HUD reference date for that count (`YYYY-MM-DD`). The current row uses `2025-01-01`. Use the date HUD gives the count. Do not substitute the day you opened the PDF, and do not substitute the press-release date.
4. Set `observation_period` to a short label such as `January 2025 point-in-time count`.
5. Set `source` to a short citation the week note can quote, such as `2025 HUD AHAR`.

### Trust in government

1. Open the new Edelman Trust Barometer **U.S. report** and read the **United States, Government** institution percent (TRU_INS, general population). The current citation is the [2026 U.S. report PDF](https://www.edelman.com/sites/g/files/aatuss191/files/2026-02/2026%20Edelman%20Trust%20Barometer_U.S.%20Report.pdf). Do not use the Trust Index (the average of business, government, media, and NGOs).
2. Put that percent in `value` (the checklist input is `39`).
3. Set `observation_date` and `observation_period` to the **survey year only** (`2026`). Do not write a month or day. Edelman does not give this pipeline a reference day.
4. `runtime/data/edelman-trust-barometer-us.csv` is a historical archive. A new year column in that file does not change the index. Copy the new Government figure into `annual_inputs.csv` if you want it in the score. You may also append the year to the archive so the series stays complete. The 2026 archive column was not added here: only the Government cell was confirmed from the U.S. report chart.

## What to edit

Edit the matching row in `annual_inputs.csv`. Leave the other row as it is.

| Column | What to write |
| --- | --- |
| `metric` | `homelessness_rate` or `trust_in_government` |
| `value` | The raw number the score uses |
| `observation_period` | PIT label, or the Edelman year |
| `observation_date` | HUD reference date (`YYYY-MM-DD`), or Edelman year (`YYYY`) |
| `source` | Short document name |
| `source_url` | URL of the report or table you read |
| `reviewed_at` | The calendar date you checked the source, `YYYY-MM-DD` |

`reviewed_at` is the date a person last confirmed the row. On the current rows it is `2026-10-10`, the date the 2025 AHAR and the 2026 Edelman U.S. Government cell were checked. That is not a HUD or Edelman release date. The next review replaces it with the date of that check.

Write a date. Do not write a clock time, and do not write `2025-01-01T00:00:00Z`.

## What the weekly job does

`fetch_homelessness_rate.py` and `fetch_trust_in_government.py` read this table.

- A missing file, a missing row, a blank value, a bad date, or a timestamp in `reviewed_at` fails that fetch. The weekly publish then refuses, and the previous site stays up.
- The job does not fill a gap with `0.22` or `39`, and it does not fill a gap with the previous published cells `0.23` or `41`.
- The job does not take the newest year column in the Edelman archive.
- Homelessness keeps `fetched_at` empty. The HUD reference date stays on `observation_date` / provenance `reference_date`.
- Trust sets `fetched_at` to the survey year from the row (`2026`). It does not invent a month, a day, or a fetch timestamp.
- `reviewed_at` is copied from the cell into provenance. The fetcher does not substitute the run time.

## Release-age check

`runtime/data/fetch/annual_release_check.py` warns when the **next** release is past its usual window, plus the grace period in `RELEASE_WINDOWS`. It does not age the observation itself.

HUD describes a January point-in-time night. The next AHAR after the checklist year is the following January, and that report usually appears **12 to 18 months** after that January 1. One further month is grace. The 2025 row (observation `2025-01-01`) is looking for the January 2026 count, due **2027-08-01**. It does not warn on 2026-10-10.

Edelman publishes in **January** of the survey year. The next report after checklist year 2026 is January 2027, then one month of grace, due **2027-02-28**. It does not warn on 2026-10-10.

The due date itself is still on time. The next day warns. A warning is a note for a person. It does not edit this table, it does not run inside the weekly job, and it does not change `compute_index`.

## Future work

Whether a public series can update these two inputs more often than once a year is tracked in issue [#81](https://github.com/adammontville/bugoutindex/issues/81). That research does not change the live score.

The NYC Department of Homeless Services daily shelter census (NYC Open Data `k46n-sa2m`, field `total_individuals_in_shelter`) is a local high-frequency companion. It is New York City only. It is not a U.S. figure and it does not replace this HUD AHAR row. The weekly job stores it beside the index. It is not an input to the score.

The homepage also shows a U.S. regional shelter panel beside that HUD row. Northeast is the NYC census above. Southeast is Nashville–Davidson, South is Austin/Travis County, Midwest is Ramsey County, Minnesota, Southwest is Denver, and West is San Francisco. Ramsey County (`9mck-bcqu`) and San Francisco DataSF measure `279` are fetched from open data. Nashville, Austin, and Denver are a manual checklist in [`shelter_region_shadow.csv`](shelter_region_shadow.csv). Each tile names its place. None of them is in the score. Chicago is not on the panel: DFSS daily reports are not public open data, and the public shelter tables that were checked are stale or historical. How to update the checklist, and which candidates were skipped, is in [`incubating/shelter_census_companions.md`](../../incubating/shelter_census_companions.md).

Pew public trust and Gallup confidence in institutions are trust companions for the same issue. They do not replace the Edelman row above. Trust in the next publish is **39** for survey year **2026**. Weeks through 2026-10-09 stay **41**. The update steps for those two checklists are in [`TRUST_SHADOWS.md`](TRUST_SHADOWS.md).
