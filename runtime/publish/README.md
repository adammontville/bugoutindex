# Weekly publish pipeline

This directory contains the headless weekly pipeline that powers
<https://adammontville.github.io/bugoutindex/>.

## What it does

Every Friday at 23:30 UTC, GitHub Actions runs this pipeline. The cron in
`.github/workflows/weekly-update.yml` is `30 23 * * 5`. That instant is
18:30 America/Chicago during daylight time (CDT, UTC−5) and 17:30 during
standard time (CST, UTC−6). `workflow_dispatch` can start the same job
by hand.

The job installs from the hashed lock `runtime/requirements.txt`
(`pip install --require-hashes`). Direct dependencies stay in
`runtime/requirements.in`. Actions are pinned to commit SHAs.

Overlapping runs on one branch share
`bugoutindex-weekly-publish-<branch>` (the Pages branch is
`bugoutindex-weekly-publish-main`). `cancel-in-progress` is false, so a
run that has started finishes its commit and push. A second run waits.
If several are queued, GitHub keeps the newest and cancels the older
queued runs. Two runs do not push that branch at the same time.

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
6. Fetches the food-price shadow series from FRED: the 12-month
   percent change in food CPI (`CPIUFDNS`, BLS `CUUR0000SAF1`, not
   seasonally adjusted). It is not an index input. A failed fetch
   does not refuse the publish. When the fetch fails and the previous
   snapshot has the series, that block is carried forward and its
   FRED observation date is kept.
7. Fetches the NYC DHS shelter-census shadow series from NYC Open Data
   dataset `k46n-sa2m`, field `total_individuals_in_shelter` (total
   individuals in the New York City DHS shelter system on the census
   date). It is New York City only. It is not a U.S. rate and it is
   not an index input. HUD AHAR remains the annual national
   homelessness input. A failed fetch does not refuse the publish.
   When the fetch fails and the previous snapshot has the series, that
   block is carried forward and its census date is kept.
8. Fetches the other local shelter companions the same way: Ramsey
   County open data `9mck-bcqu` (monthly sum of `population_enrollees`),
   DataSF `kc49-udxn` measure `279` (San Francisco monthly occupancy
   rate, stored as percent, not a headcount), and the U.S. regional
   checklist in `runtime/data/shelter_region_shadow.csv` (Nashville,
   Austin, and Denver). Each one is outside the index. A failed fetch
   or a bad checklist does not refuse the publish. Update steps are in
   `incubating/shelter_census_companions.md`.
8. Reads the Pew public-trust shadow from `runtime/data/pew_trust_shadow.csv`
   and the Gallup confidence shadow from
   `runtime/data/gallup_confidence_shadow.csv`. Both are companions.
   They are not index inputs. Edelman remains the scored trust input.
   The job does not download Pew or Gallup. A failed read does not
   refuse the publish. When the read fails and the previous snapshot
   has the series, that block is carried forward and its survey date
   is kept. Update steps are in `runtime/data/TRUST_SHADOWS.md`.
9. Appends a row to `runtime/data/weekly_bugout_index.csv`,
   `runtime/data/markets_history.csv`,
   `runtime/data/pulse_history.csv`, and, when a shadow series has
   a value, `runtime/data/labor_shadow_history.csv`,
   `runtime/data/food_shadow_history.csv`,
   `runtime/data/nyc_dhs_shadow_history.csv`, and, when those companions
   have a value, `runtime/data/ramsey_shelter_shadow_history.csv`,
   `runtime/data/sf_shelter_shadow_history.csv`, and
   `runtime/data/shelter_region_shadow_history.csv`. Each core raw value is stored next
   `runtime/data/nyc_dhs_shadow_history.csv`,
   `runtime/data/pew_trust_shadow_history.csv`, and
   `runtime/data/gallup_confidence_shadow_history.csv`. Each core raw value is stored next
   to `{metric}_observation_date` (the period the number describes).
   The same field is `observation_date` on each object in
   `metrics` inside `docs/data/latest.json`. A later week that changes
   the raw value and keeps that date is a revision; a different date is
   a new observation period. The week note says so when both weeks have
   a date. Rows written before this column existed were filled only
   where that week's own snapshot still had an honest period (FRED
   observation dates and the Edelman year, which those fetchers stored
   in `source_fetched_at`). Crime and homelessness placeholder
   timestamps were not copied. Crime stays blank except the 2026-09-19
   row: that week's value month is September 2024, and that month's
   unweighted rate is the locked 2723.0. A later file whose value month
   has a different rate does not fill the cell. Homelessness uses the HUD
   reference date on rows published once that date was recorded (from
   2026-09-19); earlier rows stay blank.
10. Writes a snapshot to `docs/data/latest.json`.
11. Renders `docs/index.html`, `docs/methodology.html`,
   `docs/history.html`, and `docs/revisions.html` via Jinja2 templates.
   The homepage week note is built in `week_note.py` from this snapshot
   versus the previous history row. It does not call a language model.
   Core and pulse tiles show observation dates and ages. Crime uses the
   local file's value month (not a placeholder timestamp). Homelessness
   and trust come from `runtime/data/annual_inputs.csv` (see
   `runtime/data/ANNUAL_INPUTS.md`). Homelessness is labeled as a manual
   annual input. OECD business confidence is
   marked stale when its observation is more than 365 days before the
   publication date. The labor, food, and shelter shadow tiles use the same age line.
   They are labeled not in the BugOut Index. Each shelter tile names
   its place. The Denver and San Francisco tiles are occupancy rates, not headcounts.
   publication date.    The labor, food, NYC DHS, Pew, and Gallup shadow tiles are labeled
   not in the BugOut Index. The NYC tile is labeled New York City only.
   Pew and Gallup use the checklist survey date and are not marked with
   the pulse stale rule. Edelman remains the trust input.
12. Commits and pushes the results to `main`.

GitHub Pages is configured to serve the `/docs` directory on `main`.

## Running locally

A laptop or a Raspberry Pi uses the same command as the weekly job. Set
`FRED_API_KEY` in the environment (a shell export or the process
environment). The pipeline does not read Streamlit secrets and does not
import Streamlit.

```bash
export FRED_API_KEY=<your key>
export PYTHONPATH=$PWD
python -m runtime.publish.weekly_run
# Preview the files GitHub Pages serves:
python -m http.server 8765 --directory docs
```

Optional viewer, if you still want one: from `runtime/`, `streamlit run main.py`.
It reads `docs/data/latest.json`. It does not write the weekly site.

The snapshot contract is
[`docs/architecture/snapshot-schema.md`](../../docs/architecture/snapshot-schema.md)
(`schema_version` 1, `methodology_version` 1.0.0). A snapshot that fails
that check exits 4 and does not write `docs/`.

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
| food price shadow | `fetch_food_shadow` | FRED `CPIUFDNS` (BLS `CUUR0000SAF1`), food CPI 12-month percent change, not seasonally adjusted. Not in the index. Failure does not abort the publish. |
| NYC DHS shelter census shadow | `fetch_nyc_dhs_shadow` | NYC Open Data `k46n-sa2m`, field `total_individuals_in_shelter`. New York City only. Not a U.S. rate and not the HUD AHAR input. Not in the index. Failure does not abort the publish. |
| Ramsey County shelter census shadow | `fetch_ramsey_shelter_shadow` | Ramsey County open data `9mck-bcqu`. Monthly sum of `population_enrollees` across household types. Ramsey County, Minnesota only. Not in the index. Failure does not abort the publish. |
| U.S. regional shelter checklist | `fetch_shelter_region_shadow` | Checklist `runtime/data/shelter_region_shadow.csv`. Nashville–Davidson monthly HMIS people, Austin/Travis sheltered card, Denver HOST pilot occupancy rate. Not a U.S. total. Not in the index. A bad checklist does not abort the publish. |
| San Francisco shelter occupancy shadow | `fetch_sf_shelter_shadow` | DataSF `kc49-udxn` measure `279`. Monthly occupancy rate in percent, not a headcount. San Francisco only. Not in the index. Failure does not abort the publish. |
| Pew public trust shadow | `fetch_pew_trust_shadow` | Checklist `runtime/data/pew_trust_shadow.csv`. Share who trust the government in Washington just about always or most of the time. Not the Edelman input. Not in the index. Failure does not abort the publish. |
| Gallup confidence shadow | `fetch_gallup_confidence_shadow` | Checklist `runtime/data/gallup_confidence_shadow.csv`. Current annual “great deal” plus “quite a lot” for Congress, the presidency, the Supreme Court, and the 14-institution average. Not a Gallup archive and not the Edelman input. Not in the index. Failure does not abort the publish. |

## Methodology freshness

The six core metrics update on different cadences (weekly-to-annual).
The weekly pipeline recomputes the index regardless of whether the
underlying raw data has changed; this makes the site always reflect the
most current published inputs, even though the BOI itself may not move
week over week.

## When a Friday publish fails

`weekly_run.py` exits **2** when a core metric did not succeed, and exits
**3** when markets or the pulse failed completely. A labor-shadow,
food-shadow, NYC DHS, Ramsey County, San Francisco, or regional-checklist shelter shadow failure is not exit 3; the index still publishes. Either exit happens
food-shadow, NYC DHS, Pew, or Gallup shadow failure is not exit 3; the index still publishes. Either exit happens
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

The workflow requires one repository secret, passed in as an environment
variable. Fetchers read it with `runtime/util/secrets_compat.py`. They do
not import Streamlit.

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
