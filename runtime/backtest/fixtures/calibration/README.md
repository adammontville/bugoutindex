# Endpoint calibration fixtures

Checked-in inputs for `runtime/backtest/endpoint_calibration.py`. They do not feed `compute_index`, the weekly job, or `docs/data/latest.json`.

The reference window is **January 1970 through December 2006**. Files that set endpoints stop in 2006 on purpose. A later print in those files would leak into the percentiles.

Pulled **2026-10-12** from the public FRED graph CSV. This is a revised vintage, not ALFRED. Overlap with the 2006 months already in `../v2/` matches.

| File | What it is | Dates kept |
| --- | --- | --- |
| `CPIAUCSL.csv` | CPI-U, seasonally adjusted, index level | 1969-01-01 through 2006-12-01. The extra year is only there so January 1970 has a year-over-year rate. |
| `UNRATE.csv` | Unemployment rate, percent | 1970-01-01 through 2006-12-01 |
| `GFDEGDQ188S.csv` | Federal debt to GDP, percent | 1970-01-01 through 2006-10-01 |
| `GFDEGDQ188S_replay.csv` | The same debt series, for the 2007–2026 replay only | 2006-10-01 through 2026-01-01. Not used to set endpoints. Overlap with `GFDEGDQ188S.csv` at 2006-10-01 matches. Overlap with the locked crisis fixture `../GFDEGDQ188S.csv` matches. |

The replay's CPI, unemployment, and RTCI crime series are the existing files in `../v2/`. Crime starts in January 2018. Homelessness and trust stay on the methodology 1.1.1 checklist. Neither has a 1970–2006 history in this replay.
