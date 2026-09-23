# Weekly publish pipeline

This directory contains the headless weekly pipeline that powers
<https://adammontville.github.io/bugoutindex/>.

## What it does

Every Friday at 23:30 UTC, GitHub Actions runs this pipeline. The cron in
`.github/workflows/weekly-update.yml` is `30 23 * * 5`. That instant is
18:30 America/Chicago during daylight time (CDT, UTC−5) and 17:30 during
standard time (CST, UTC−6). `workflow_dispatch` can start the same job
by hand.

`publication_date` is the America/Chicago calendar date when the run
starts, not the UTC date. GitHub often starts the scheduled job after
00:00 UTC Saturday; that start is still Friday evening in Chicago, so
the week label stays Friday. Dates already written in the history CSVs
are left as they were stamped.

The Action runs `weekly_run.py`, which:

1. Fetches the six core BugOut Index metrics (inflation, crime,
   unemployment, debt-to-GDP, homelessness, trust in government) using
   the existing modules in `runtime/data/fetch/`.
2. Computes the weighted index per methodology v1.0.0.
3. Fetches spot gold and silver from
   [gold-api.com](https://gold-api.com) and the Broad US Dollar Index
   from FRED (`DTWEXBGS`).
4. Fetches five short-term pulse indicators from FRED:
   initial jobless claims (`ICSA`), UMich consumer sentiment
   (`UMCSENT`), OECD Business Confidence (`BSCICP03USM665S`),
   10y–2y Treasury spread (`T10Y2Y`), and VIX (`VIXCLS`).
5. Fetches the labor-utilization shadow series from FRED:
   prime-age employment-population ratio (`LNS12300060`) and
   prime-age labor-force participation (`LNS11300060`), ages 25–54,
   seasonally adjusted. These are not index inputs. A failed or
   partial shadow fetch does not refuse the publish. When the fetch
   fails and the previous snapshot has the series, that block is
   carried forward and its FRED observation dates are kept.
6. Appends a row to `runtime/data/weekly_bugout_index.csv`,
   `runtime/data/markets_history.csv`,
   `runtime/data/pulse_history.csv`, and, when the shadow series has
   a value, `runtime/data/labor_shadow_history.csv`. Each core raw value is stored next
   to `{metric}_observation_date` (the period the number describes).
   The same field is `observation_date` on each object in
   `metrics` inside `docs/data/latest.json`. A later week that changes
   the raw value and keeps that date is a revision; a different date is
   a new observation period. The week note says so when both weeks have
   a date. Rows written before this column existed were filled only
   where that week's own snapshot still had an honest period (FRED
   observation dates and the Edelman year, which those fetchers stored
   in `source_fetched_at`). Crime and homelessness placeholder
   timestamps were not copied; those cells stay blank except the
   2026-09-19 row, which uses the file value-month end and the HUD
   reference date already in that snapshot.
7. Writes a snapshot to `docs/data/latest.json`.
8. Renders `docs/index.html`, `docs/methodology.html`,
   `docs/history.html`, and `docs/revisions.html` via Jinja2 templates.
   The homepage week note is built in `week_note.py` from this snapshot
   versus the previous history row. It does not call a language model.
   Core and pulse tiles show observation dates and ages. Crime uses the
   local file's value month (not a placeholder timestamp). Homelessness
   and trust come from `runtime/data/annual_inputs.csv` (see
   `runtime/data/ANNUAL_INPUTS.md`). Homelessness is labeled as a manual
   annual input. OECD business confidence is
   marked stale when its observation is more than 365 days before the
   publication date. The labor shadow tiles use the same age line.
   They are labeled not in the BugOut Index.
9. Commits and pushes the results to `main`.

GitHub Pages is configured to serve the `/docs` directory on `main`.

## Running locally

```bash
export FRED_API_KEY=<your key>
export PYTHONPATH=$PWD
python -m runtime.publish.weekly_run
# Preview:
python -m http.server 8765 --directory docs
```

## Files

| File | Purpose |
| --- | --- |
| `weekly_run.py` | Orchestrator. Fetches all inputs, computes index, emits JSON, triggers render. Stamps `publication_date` in America/Chicago. |
| `failure_notice.py` | Text for the Actions job summary when a publish does not land. |
| `render.py` | Jinja2 renderer. Converts the JSON snapshot into HTML pages + inline SVG charts. |
| `templates/*.j2` | Page templates. |
| `static/style.css` | CSS; copied into `docs/assets/` on render. |

## Fetchers used

| Metric | Module | Source |
| --- | --- | --- |
| inflation_rate | `fetch_inflation_rate` | FRED `CPIAUCSL` |
| incident_rate | `fetch_incident_rate` | Real-Time Crime Index cleaned file (`AH-Datalytics/rtci` `docs/app_data/final_sample.csv` via raw.githubusercontent.com). Published input stays 2723.0; the file’s candidate rate is a diagnostic only. |
| unemployment_rate | `fetch_unemployment_rate` | FRED `UNRATE` |
| debt_to_gdp_ratio | `fetch_debt_to_gdp_ratio` | FRED `GFDEGDQ188S` |
| homelessness_rate | `fetch_homelessness_rate` | HUD AHAR row in `runtime/data/annual_inputs.csv` |
| trust_in_government | `fetch_trust_in_government` | Edelman year row in `runtime/data/annual_inputs.csv` |
| gold / silver / DXY | `fetch_markets` | gold-api.com + FRED `DTWEXBGS` |
| pulse indicators | `fetch_pulse` | FRED |
| labor utilization shadow | `fetch_labor_shadow` | FRED `LNS12300060` (prime-age EPOP, 25–54) and `LNS11300060` (prime-age participation). Not in the index. Failure does not abort the publish. |

## Methodology freshness

The six core metrics update on different cadences (weekly-to-annual).
The weekly pipeline recomputes the index regardless of whether the
underlying raw data has changed; this makes the site always reflect the
most current published inputs, even though the BOI itself may not move
week over week.

## When a Friday publish fails

`weekly_run.py` exits **2** when a core metric did not succeed, and exits
**3** when markets or the pulse failed completely. A labor-shadow failure
is not exit 3; the index still publishes. Either exit happens
before history, `docs/data/latest.json`, or HTML is written. Any other
non-zero exit is a crash. The workflow records that code, then fails the
job. The commit step does not run, so GitHub Pages keeps serving the last
successful HTML. The footer line “Published {date}” stays that last good
publication date. There is no failure banner on the site.

The failed run is visible without opening the raw log:

- The job is red. For a scheduled run, GitHub emails the person who last
  changed the cron in `weekly-update.yml`, or who re-enabled the workflow.
  That is GitHub’s built-in Actions notification (repository notification
  settings still apply). A `workflow_dispatch` run notifies the person who
  started it.
- A step with `if: failure()` appends a short summary to
  `$GITHUB_STEP_SUMMARY` and adds an error annotation on the run page. The
  summary says whether this was a refusal (exit 2 or 3) or a crash.

Preview that summary locally:

```bash
python -m runtime.publish.failure_notice 2
python -m runtime.publish.failure_notice 3
python -m runtime.publish.failure_notice 1
```

## Secrets

The workflow requires one repository secret:

- `FRED_API_KEY` — free from <https://fredaccount.stlouisfed.org/apikeys>.

## History file

A legacy `runtime/data/historical_bugout_index.csv` file stores earlier
daily runs in a different schema (values stringified as Python dicts).
The new pipeline writes to `runtime/data/weekly_bugout_index.csv` with a
flat schema and does not modify the legacy file. Core columns are the
publication `date`, `bugout_index`, then each raw value immediately
followed by `{metric}_observation_date`, then the `{metric}_normalized`
scores. Blank observation dates mean the period was not recorded, not
that it equals the publication date.
