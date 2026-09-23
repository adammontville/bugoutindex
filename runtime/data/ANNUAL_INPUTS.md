# Annual manual inputs

Homelessness and trust in government are annual figures. The weekly job reads them from [`annual_inputs.csv`](annual_inputs.csv) in this directory. It does not look up a newer HUD report or a newer Edelman year on its own, and it does not invent a value or a timestamp.

The live score stays on the rows in that table. This checklist does not change methodology v1.0.0. The current rows are still homelessness **0.23** and trust **41** (survey year **2025**).

## Once a year

Do this when HUD publishes a new Annual Homeless Assessment Report (AHAR), Part 1, or when Edelman publishes a new Trust Barometer. Skip the week if neither has a new primary source. Leaving the row alone is the correct outcome.

### Homelessness

1. Open the new HUD AHAR Part 1 (point-in-time / PIT count). The current citation is the [2024 AHAR Part 1 PDF](https://www.huduser.gov/portal/sites/default/files/pdf/2024-AHAR-Part-1.pdf). PIT counts are also listed on the [HUD Exchange PIT/HIC page](https://www.hudexchange.info/programs/hdx/pit-hic/).
2. Take the national homelessness **rate as a percent of population** (the published input is `0.23`, not the headcount).
3. Set `observation_date` to the HUD reference date for that count (`YYYY-MM-DD`). The current row uses `2024-01-01`. Use the date HUD gives the count. Do not substitute the day you opened the PDF.
4. Set `observation_period` to a short label such as `January 2024 point-in-time count`.
5. Set `source` to a short citation the week note can quote, such as `2024 HUD AHAR`.

### Trust in government

1. Open the new [Edelman Trust Barometer](https://www.edelman.com/trust-barometer) and read the **United States, Government** row.
2. Put that percent in `value` (the published input is `41`).
3. Set `observation_date` and `observation_period` to the **survey year only** (`2025`). Do not write a month or day. Edelman does not give this pipeline a reference day.
4. `runtime/data/edelman-trust-barometer-us.csv` is a historical archive. A new year column in that file does not change the index. Copy the new Government figure into `annual_inputs.csv` if you want it in the score. You may also append the year to the archive so the series stays complete.

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

`reviewed_at` is the date a person last confirmed the row. On the current rows it is `2025-03-13`, the date those published values were committed to this repository (homelessness in `5a4b00b1`, the Edelman archive in `4a0728c`). That is not a HUD or Edelman release date. The next review replaces it with the date of that check.

Write a date. Do not write a clock time, and do not write `2025-01-01T00:00:00Z`.

## What the weekly job does

`fetch_homelessness_rate.py` and `fetch_trust_in_government.py` read this table.

- A missing file, a missing row, a blank value, a bad date, or a timestamp in `reviewed_at` fails that fetch. The weekly publish then refuses, and the previous site stays up.
- The job does not fill a gap with `0.23` or `41`.
- The job does not take the newest year column in the Edelman archive.
- Homelessness keeps `fetched_at` empty. The HUD reference date stays on `observation_date` / provenance `reference_date`.
- Trust sets `fetched_at` to the survey year from the row (`2025`). It does not invent a month, a day, or a fetch timestamp.
- `reviewed_at` is copied from the cell into provenance. The fetcher does not substitute the run time.
