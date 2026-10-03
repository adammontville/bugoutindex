# v1.0.0 FRED replay

Mechanical replay of the locked methodology on historical FRED levels. This is the start of [issue #55](https://github.com/adammontville/bugoutindex/issues/55), not the finished historical essay. It is not a methodology version bump. The live weekly score, formula, bands, and published site numbers are unchanged.

Every index in the output is `runtime.processing.formula.compute_index`: the v1.0.0 endpoints, weights, trust inversion, 0–100 clamp, and divide-by-sum-of-weights. On the 19 September 2026 inputs that function still returns **57.11**.

## Results at a glance

Checked-in fixture, FRED vintage **2026-09-23**. Bands are the v1.0.0 bands applied to `replay_index`. Neither `replay_index` is the published six-metric BugOut Index.

In this vintage the Great Recession unemployment peak is **10.0%** (October 2009), not ~12%.

### 2020 window (Jan–Dec 2020)

- **Partial:** index range **45.51–60.48**. Bands: Moderate 5 months, Low 7 months. April 2020 (unemployment 14.8) is **45.51 Low**. December 2020 is **55.01 Moderate**.
- **Held constant** (crime, homelessness, and trust pinned to the published 2723 / 0.23 / 41): range **51.67–59.78**. Bands: Moderate 8 months, Low 4 months. April is **51.67 Low**. December is **56.82 Moderate**.

### 2008 window (Dec 2007–Dec 2009)

- **Partial:** **55.17–64.40**. All **25** months are Moderate. October 2009 (unemployment 10.0) is **59.72 Moderate**. December 2009 is **55.17 Moderate**.
- **Held constant:** **56.90–61.90**. All **25** months are Moderate. October 2009 is **59.37 Moderate**. December 2009 is **56.90 Moderate**.

The formula moves into Low Stability under COVID-scale unemployment. Through a Great Recession–shaped FRED shock it stays Moderate when crime, homelessness, and trust are excluded or held at the 2026 baselines. That is useful for calibration. It is not a full historical BugOut Index.

## What is historical

| Input | Series | How the row is built |
| --- | --- | --- |
| Inflation | `CPIAUCSL` | Year-over-year percent, same construction as `fetch_inflation_rate`: `((current - year_ago) / year_ago) * 100`, where year-ago is the same calendar date one year earlier |
| Unemployment | `UNRATE` | The monthly level, same as `fetch_unemployment_rate`. A missing month is `excluded`. It is not carried forward |
| Debt-to-GDP | `GFDEGDQ188S` | The quarterly level, same as `fetch_debt_to_gdp_ratio`. On a quarter-start month the status is `observed`. On other months the latest quarter on or before that month is used and the status is `carried_forward`, with that quarter's observation date. That is the published print, not an interpolation |

FRED returns the **current revised value** for each observation date. This harness does not query ALFRED. A 2008 row is the vintage FRED had on `fred_download_date`, not the print available during the crisis. The checked-in tables use `2026-09-23`. A live pull stamps the day it ran.

The checked-in series were downloaded from the public FRED graph CSV on **2026-09-23**:

- <https://fred.stlouisfed.org/series/CPIAUCSL>
- <https://fred.stlouisfed.org/series/UNRATE>
- <https://fred.stlouisfed.org/series/GFDEGDQ188S>

In that vintage, August 2026 CPI year-over-year, August 2026 `UNRATE` (4.1), and the 2026-01-01 `GFDEGDQ188S` print (122.59387) match the 19 September 2026 weekly row. The fixture also keeps August 2025 CPI, August 2026 CPI, August 2026 unemployment, and that debt print so an offline check can rebuild those three inputs. Those dates are not in the crisis windows.

## What is not historical

Crime, homelessness, and trust are sparse. The harness does not invent them. Two modes, both written:

1. **`partial`** — those three are `excluded`. `compute_index` skips them and the weight denominator shrinks to the sum of the weights that were actually present (0.39 when inflation, unemployment, and debt are all present: 0.15 + 0.12 + 0.12). It does **not** divide by 0.72. `inputs_present` and `inputs_excluded` name the inputs on every row. The value columns are blank.
2. **`held_constant`** — those three are pinned to the named baseline `published_2026-09-19`: incident rate **2723**, homelessness **0.23**, trust **41**. Every one of those cells is `held_constant`. `inputs_held_constant` lists them. They are the published 19 September 2026 inputs, not observations from 2008 or 2020. When the three FRED series are also present the denominator is the full **0.72**.

Do not read either `replay_index` as the published six-metric BugOut Index for that month. `score_mode` and `score_note` say which kind of row it is. `methodology_version` stays `1.0.0`.

## Windows

| Name | Dates | Why |
| --- | --- | --- |
| `2008` | 2007-12-01 through 2009-12-01 | NBER Great Recession, December 2007–June 2009, extended through December 2009 so the October 2009 unemployment peak (10.0 in this vintage) is in the table |
| `2020` | 2020-01-01 through 2020-12-01 | NBER COVID-19 recession, February–April 2020. January shows the pre-shock unemployment rate. The rest of the year shows the partial rebound. April 2020 unemployment is 14.8 in this vintage |

Dates are the FRED first-of-month observation dates.

In this vintage, April 2020 unemployment is 14.8 and debt-to-GDP is observed at 132.66287. The partial replay index for that month is 45.51 and the held-constant replay index is 51.67. Both fall in the v1.0.0 Low Stability band. October 2009 unemployment is 10.0. Those replay indexes are not the published six-metric BugOut Index.

## How to run

From the repository root, with dependencies from `runtime/requirements.txt`:

```bash
python -m runtime.backtest
python -m runtime.backtest --check-locked
```

The default source is `runtime/backtest/fixtures/`. No `FRED_API_KEY` is required. That writes:

- `runtime/backtest/output/replay_partial.csv`
- `runtime/backtest/output/replay_held_constant.csv`

`--check-locked` scores the 19 September 2026 row of `runtime/data/weekly_bugout_index.csv` through `compute_index` and prints `57.11`. It still needs all six published inputs. It will not drop crime or trust and call the result the locked score.

A live pull uses the same FRED observations endpoint and `FRED_API_KEY` environment variable as the weekly fetchers. It requests the whole window (CPI starts one year earlier), not only the latest point. If the key is missing, the command exits without writing a table.

```bash
FRED_API_KEY=... python -m runtime.backtest --source fred --output /tmp/boi-backtest
```

Tests use the fixtures. `pytest` does not need a key.

## How to read a row

`inputs_present` is a `|` list in core-metric order. In the partial file a full month looks like `inflation_rate|unemployment_rate|debt_to_gdp_ratio`, and `inputs_excluded` is `incident_rate|homelessness_rate|trust_in_government`.

`inflation_cpi` and `inflation_cpi_prior` are the CPI levels behind the year-over-year rate. `debt_to_gdp_ratio_observation_date` is the quarter that supplied the debt figure when the status is `carried_forward`.

An empty `inputs_present` would be the formula's zero (nothing was scored), not a measured collapse. The committed 2008 and 2020 windows are not in that state: each month has all three FRED inputs.

## Out of scope

Issue #55 still asks for Depression, WWII, and 1970s reconstructions, population-adjusted crime, and a page about the analysis. This directory does not do that work, and it does not add a page to the public site.

## v2 candidate hypothesis

[`V2_CANDIDATE.md`](V2_CANDIDATE.md) is a separate replay for methodology v2.0 planning. It does not change this v1.0.0 command, `compute_index`, or the weekly publish. The note's current basket is hypothesis h2. Run it with `python -m runtime.backtest.v2_candidate`. The results note is meant to be read without a local run.
