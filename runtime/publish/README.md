# Weekly publish pipeline

This directory contains the headless weekly pipeline that powers
<https://adammontville.github.io/bugoutindex/>.

## What it does

Every Friday at 22:00 America/Chicago (03:00 UTC Saturday), a GitHub
Action runs `weekly_run.py`, which:

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
5. Appends a row to `runtime/data/weekly_bugout_index.csv`,
   `runtime/data/markets_history.csv`, and
   `runtime/data/pulse_history.csv`.
6. Writes a snapshot to `docs/data/latest.json`.
7. Renders `docs/index.html`, `docs/methodology.html`, and
   `docs/history.html` via Jinja2 templates.
8. Commits and pushes the results to `main`.

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
| `weekly_run.py` | Orchestrator. Fetches all inputs, computes index, emits JSON, triggers render. |
| `render.py` | Jinja2 renderer. Converts the JSON snapshot into HTML pages + inline SVG charts. |
| `templates/*.j2` | Page templates. |
| `static/style.css` | CSS; copied into `docs/assets/` on render. |

## Fetchers used

| Metric | Module | Source |
| --- | --- | --- |
| inflation_rate | `fetch_inflation_rate` | FRED `CPIAUCSL` |
| incident_rate | `fetch_incident_rate` | Real-Time Crime Index (local CSV) |
| unemployment_rate | `fetch_unemployment_rate` | FRED `UNRATE` |
| debt_to_gdp_ratio | `fetch_debt_to_gdp_ratio` | FRED `GFDEGDQ188S` |
| homelessness_rate | `fetch_homelessness_rate` | HUD AHAR (hardcoded annual) |
| trust_in_government | `fetch_trust_in_government` | Edelman Trust Barometer (local CSV) |
| gold / silver / DXY | `fetch_markets` | gold-api.com + FRED `DTWEXBGS` |
| pulse indicators | `fetch_pulse` | FRED |

## Methodology freshness

The six core metrics update on different cadences (weekly-to-annual).
The weekly pipeline recomputes the index regardless of whether the
underlying raw data has changed; this makes the site always reflect the
most current published inputs, even though the BOI itself may not move
week over week.

## Secrets

The workflow requires one repository secret:

- `FRED_API_KEY` — free from <https://fredaccount.stlouisfed.org/apikeys>.

## History file

A legacy `runtime/data/historical_bugout_index.csv` file stores earlier
daily runs in a different schema (values stringified as Python dicts).
The new pipeline writes to `runtime/data/weekly_bugout_index.csv` with a
flat schema and does not modify the legacy file.
