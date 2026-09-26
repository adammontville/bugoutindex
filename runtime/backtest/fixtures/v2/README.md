# v2 candidate fixtures

Checked-in inputs for the trial replay in `runtime/backtest/v2_candidate.py`. They do not feed `compute_index`, the weekly job, or `docs/data/latest.json`.

Pull date for the BLS, CBOE, and RTCI files: **2026-09-26**. This is a current revised vintage, not an ALFRED real-time vintage. The locked v1.0.0 crisis fixtures in the parent directory stay the **2026-09-23** FRED graph vintage.

| File | What it is | Source |
| --- | --- | --- |
| `CPIAUCSL.csv` | CPI-U all items, seasonally adjusted, index level | BLS `CUSR0000SA0`, the series FRED publishes as `CPIAUCSL`. Every date that also sits in `../CPIAUCSL.csv` matches that locked fixture. |
| `CPIUFDNS.csv` | CPI-U food, not seasonally adjusted, index level | BLS `CUUR0000SAF1`, the series FRED publishes as `CPIUFDNS`. The replay stores the 12-month percent change rounded half-up to one decimal, the same public print as `fetch_food_shadow`. |
| `LNS12300060.csv` | Prime-age (25–54) employment-population ratio, percent | BLS / FRED `LNS12300060` |
| `LNS11300060.csv` | Prime-age labor force participation, percent | BLS / FRED `LNS11300060` |
| `LNS14000000.csv` | Headline unemployment rate, percent | BLS `LNS14000000`, the series FRED publishes as `UNRATE`. Overlap with `../UNRATE.csv` matches. |
| `VIXCLS_monthly.csv` | Calendar-month mean and maximum of the daily VIX close | CBOE `VIX_History.csv` close. That close is the series FRED publishes as `VIXCLS`. The scored trial input is the monthly mean. The max is diagnostic only. |
| `RTCI_monthly.csv` | Trial violent-plus-property rate per 100,000 | AH-Datalytics `docs/app_data/final_sample.csv` on `main`, downloaded 2026-09-26. Unweighted mean of agency rates, same construction as `fetch_incident_rate._rates_for_month`: `(Violent Crime_mvs_12mo + Property Crime_mvs_12mo) / FBI.Population.Covered × 100,000`, rows with a missing count or a non-positive population left out. This file's usable agency count is 621 in every month from 2018-01 through 2026-04. |
| `GFDEGDQ188S_published_extra.csv` | One published debt-to-GDP print the v1 fixture does not contain | `122.56815` on `2025-10-01`, copied from `runtime/data/weekly_bugout_index.csv` (rows dated 2026-04-21 through 2026-06-12). Not a new FRED download. |

BLS cells: a trailing footnote such as `4.3(12)` was stored as `4.3`. Non-numeric cells (`-(9)`, `-(X)`) were omitted. In this pull that is **October 2025** for CPI, food CPI, unemployment, prime-age EPOP, and prime-age participation. Those months are not interpolated.

The public FRED graph CSV endpoint did not return a body on this pull. BLS series ids above are the same series the weekly fetchers request from FRED. CBOE is the source behind `VIXCLS`.
