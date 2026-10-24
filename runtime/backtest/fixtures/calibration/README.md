# Calibration fixtures for the combined 2.0 replay

Checked-in inputs for `runtime/backtest/combined_design.py`. They do not feed `compute_index`, the weekly job, or `docs/data/latest.json`.

The reference window is **January 1970 through December 2006**. Files that set endpoints stop in 2006 on purpose. A later print in those files would leak into the percentiles. The VIX file starts in January 1990 because that is when the series starts, and it still stops in December 2006.

| File | What it is | Dates kept |
| --- | --- | --- |
| `CPIAUCSL.csv` | CPI-U, seasonally adjusted, index level | 1969-01-01 through 2006-12-01. The extra year is only there so January 1970 has a year-over-year rate. |
| `UNRATE.csv` | Unemployment rate, percent | 1970-01-01 through 2006-12-01 |
| `GFDEGDQ188S.csv` | Federal debt to GDP, percent | 1970-01-01 through 2006-10-01. Used for the level diagnosis and for debt-change endpoints. |
| `GFDEGDQ188S_replay.csv` | The same debt series, for the replay only | 2006-10-01 through 2026-01-01. Not used to set endpoints. |
| `VIXCLS_monthly.csv` | Calendar-month mean of the daily VIX close | 1990-01-01 through 2006-12-01. The 2006 months match `../v2/VIXCLS_monthly.csv`. |

The CPI, unemployment, and debt files were pulled **2026-10-12** from the public FRED graph CSV. This is a revised vintage, not ALFRED. The VIX reference months are the month means of the CBOE daily close. Overlap with the 2006 months already in `../v2/` matches.

The replay's CPI, unemployment, RTCI crime series, VIX months from 2007, weekly VIX, and NFCI credit weeks are the files in `../v2/`. Crime starts in January 2018. Homelessness and trust stay on the methodology 1.1.1 checklist.
