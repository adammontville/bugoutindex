# BugOut Index — architecture review and roadmap

**Audience:** Product Manager  
**Status:** Proposal for approval. This document does not change the score, the site, or the weekly job.  
**Reviewed against:** repository `main` as of the 2026-09-19 weekly publish (score **57.11**).  
**Live site:** [https://www.bugoutindex.com/](https://www.bugoutindex.com/) (GitHub Pages; `bugoutindex.com` redirects there). The same build is at [https://adammontville.github.io/bugoutindex/](https://adammontville.github.io/bugoutindex/).

Effort sizes used below:

| Size | Meaning |
| --- | --- |
| **S** | One module or one doc, no new data source, no methodology version |
| **M** | A few modules, a new page or fetcher, and tests. The headline number stays on v1.0.0 unless called out |
| **L** | A versioned methodology change, a historical backtest, or a new data partnership |

---

## Executive summary

The BugOut Index is a single 0–100 number for **current U.S. conditions**, not a forecast. Higher means more stable. The public site is a static page rebuilt once a week by GitHub Actions and served by GitHub Pages. The weekly job is cheap, automatic, and, since late April 2026, refuses to publish if a core input fails.

The number itself is a weighted blend of six inputs: year-over-year CPI inflation, a violent-plus-property crime rate, the unemployment rate, federal debt-to-GDP, a homelessness rate, and Edelman trust in government. Each input is stretched onto 0–100 between fixed endpoints, then combined. On 19 September 2026 the published score was **57.11**, in the **Moderate Stability / Warning Signs** band (55–69.99).

Three facts should drive the roadmap:

1. **The score barely moves, by construction.** From the first weekly publish (21 April 2026, 57.03) through 19 September 2026, the index stayed between **56.28 and 57.15**. It changed on 9 of 23 weeks, and it never left Moderate Stability. Crime, homelessness, and trust did not change at all in that window. Inflation and unemployment did.
2. **The written methodology does not match the code that publishes the site.** `METRICS.md`, the public methodology page, and the per-metric essays disagree with each other on the formula, the inflation endpoints, the trust transform, and the risk bands. A reader who follows `METRICS.md` literally gets about **41**, not **57**. Both numbers use the same raw inputs. The gap is the formula, not the data.
3. **There is no weekly qualitative update.** The site shows the gauge, the six tiles, markets, a short-term pulse, and a revisions page. It does not say, in words, what changed and what is stale. That prose can be generated from the numbers already in the repo. A language model is not required for it, and using one to invent causes would weaken the grounding the methodology page promises.

Recommended sequence: make the methodology say what the code does, show how old each input is, add a factual week note, and lock the formula with a test. Do not put new series inside the headline number until a backtest says the new series improves it. Keep any language-model experiment off the score, cheap, weekly, and able to fail back to the factual note.

---

## Current metric methodology

### What the 0–100 score means

The published index describes **where today’s U.S. readings sit between chosen endpoints**. It is not a probability of collapse and not a prediction. The public methodology page says this explicitly (`runtime/publish/templates/methodology.html.j2`). The homepage repeats it.

The publisher (`runtime/publish/weekly_run.py`, `interpret()`) uses four bands:

| Score | Band on the site | Risk label |
| --- | --- | --- |
| 70–100 | High Stability | Low Risk |
| 55–69.99 | Moderate Stability | Warning Signs |
| 40–54.99 | Low Stability | Heightened Risk |
| Below 40 | Critical Instability | Collapse Likely |

`METRICS.md` still lists six bands, including Critical Fragility (35–39.99), Critical Instability (25–34.99), and Systemic Collapse (below 25). **Nothing in the publisher uses those three lower bands.** `runtime/static/markdown/about.md` matches the four-band scale, and it also says the index is “calculated daily” from “real-time” sources. That sentence is out of date. The public site is weekly, and several inputs are annual.

### The six inputs, as the publisher computes them

Authoritative code: `CORE_METRICS`, `METRIC_RANGES`, `WEIGHTS`, and `normalize()` in `runtime/publish/weekly_run.py`. The same ranges and weights are copied in `runtime/processing/calculate_index.py` and `runtime/pages/boi_simulator.py`.

For a “higher raw value is worse” metric:

```text
normalized = (1 − (raw − min) / (max − min)) × 100
normalized = clamp(normalized, 0, 100)
```

Trust is the exception. The code sets `inverse=True`, which replaces that result with `100 − normalized`. Inside the 0–80 window, that is the same as mapping the raw trust percent linearly onto 0–100. Trust of 0 scores 0. Trust of 80 scores 100. Trust of 41 scores **51.25**. Values outside the window are clamped only on the weekly path.

| Input | What is actually fetched | Endpoints in code | Raw weight | Series / file |
| --- | --- | --- | --- | --- |
| Inflation | CPI-U year-over-year, computed in the fetcher from FRED `CPIAUCSL` | −10% to 15% | 0.15 | `fetch_inflation_rate.py` |
| Crime | Unweighted mean of agency rates: (12-month violent + 12-month property) / population × 100,000 | 500 to 8,000 per 100k | 0.12 | Local `runtime/data/final_sample.csv` via `fetch_incident_rate.py` |
| Unemployment | Latest FRED `UNRATE` | 0% to 25% | 0.12 | `fetch_unemployment_rate.py` |
| Debt-to-GDP | Latest FRED `GFDEGDQ188S` | 0% to 200% | 0.12 | `fetch_debt_to_gdp_ratio.py` |
| Homelessness | Constant `0.23` | 0% to 0.5% of population | 0.09 | Hardcoded in `fetch_homelessness_rate.py` |
| Trust in government | Latest year column on the “Government” row of a local Edelman CSV (2025 → 41) | 0 to 80, then inverted | 0.12 | `runtime/data/edelman-trust-barometer-us.csv` |

The raw weights sum to **0.72**, not 1.00.

### How the six numbers become one score

The publisher does this (`compute_index`):

```text
BOI = Σ (normalized_i × weight_i) / Σ weight_i
```

Missing metrics are skipped and the denominator shrinks, which would reweight whatever remains. The weekly job then refuses to publish unless all six succeed (`MIN_REQUIRED_METRICS = 6`), so a live publish does not silently drop an input. That guard was added after a 25 April 2026 FRED outage. The code comment in `runtime/util/http_retry.py` says that outage published an index built from 3 of 6 inputs. The history file’s 25 April row is a complete six-metric score, identical to 21 April, so the bad figure is not what the CSV still shows.

Because the denominator is 0.72, the displayed “Weight 15%” is **not** inflation’s share of the index. The site prints `weight × 100` (`render.py`). Those labels add up to 72%. After the division, the shares are:

| Input | Shown on the site | Actual share of the score |
| --- | --- | --- |
| Inflation | 15.0% | 20.83% (0.15 / 0.72) |
| Crime, unemployment, debt, trust | 12.0% each | 16.67% each |
| Homelessness | 9.0% | 12.50% |

### Worked example: the 19 September 2026 publish

Source: `docs/data/latest.json` and `runtime/data/weekly_bugout_index.csv`.

| Input | Raw | Normalized | Points in the 57.11 (normalized × weight / 0.72) |
| --- | --- | --- | --- |
| Inflation | 3.353% (CPI observation 2026-08-01) | 46.59 | 9.71 |
| Crime | 2,723 per 100k (timestamp hardcoded `2025-01-01`) | 70.36 | 11.73 |
| Unemployment | 4.1% (observation 2026-08-01) | 83.60 | 13.93 |
| Debt-to-GDP | 122.59% (observation 2026-01-01) | 38.70 | 6.45 |
| Homelessness | 0.23% (timestamp hardcoded `2025-01-01`) | 54.00 | 6.75 |
| Trust | 41 (year column `2025`) | 51.25 | 8.54 |
| **Index** | | | **57.11** |

Unemployment is the largest support. Debt-to-GDP is the largest drag. The week-over-week change that week was 0.00. The index had last moved on 12 September, from 57.15 to 57.11, when inflation’s raw value went from 3.304 to 3.353.

If the same normalized values are combined the way `METRICS.md` is written — a plain sum, **without** dividing by 0.72 — the result is about **41.12**. On the four-band scale that is Low Stability, not Moderate Stability. This is the single most important methodology discrepancy in the repo.

### Where the documents disagree

| Topic | What the weekly job does | What a reader finds elsewhere |
| --- | --- | --- |
| Aggregation | Divide by the sum of weights (0.72) | `METRICS.md` “Step 3” is a plain sum. The public methodology page matches the code |
| Inflation endpoints | −10 to 15. A 4% print scores **44** | `METRICS.md` table says −15% to 10%. Its example uses 0% to 10% and says 4% scores **60**. `runtime/static/markdown/inflation_rate.md` matches the code |
| Trust | Linear map of the trust percent on 0–80. 41 → **51.25** | `METRICS.md` does not mention the inversion, so the generic formula scores 41 as **48.75** and treats higher trust as worse. `trust_in_government.md` first computes distrust as `100 − 41 = 59`, then normalizes that on 0–80, which scores **26.25** |
| Crime definition | Violent **plus** property, unweighted mean of agencies in the local file | `METRICS.md` overview says “violent crimes.” The crime essay and the site say violent plus property |
| Risk bands | Four bands. Below 40 is one bucket | `METRICS.md` has six bands |
| Clamping | Weekly normalizer clamps to 0–100 | `runtime/processing/normalize.py` does not clamp. The Streamlit simulator imports that function |
| “Percent weight” | Labels are the raw weights | A reader can reasonably think they are shares of 100 |

`METRICS.md` was supposed to be aligned with the code (closed issue #21, January 2025). It has drifted again. The public methodology page, written with the weekly site in April 2026, is the closest prose to the publisher. It still prints the raw weights as percents, so it does not show the 20.8 / 16.7 / 12.5 shares.

### What is deliberately outside the score

These are fetched and shown, and they do not enter `compute_index`:

- **Markets:** spot gold and silver from gold-api.com, and the Fed’s broad dollar index, FRED `DTWEXBGS`. Not the ICE DXY. The fetcher says `DTWEXBGS` replaced the older broad index in 2020.
- **Pulse:** initial jobless claims (`ICSA`), Michigan sentiment (`UMCSENT`), OECD U.S. business confidence (`BSCICP03USM665S`), the 10-year minus 2-year Treasury spread (`T10Y2Y`), and VIX (`VIXCLS`). The pulse module’s own comment still mentions NFIB; the code uses the OECD series because NFIB is not free on FRED.
- **Revisions:** ALFRED vintages for nonfarm payrolls (`PAYEMS`) and a current-versus-pre-benchmark view of `UNRATE`. This page explains that labor headlines move after release. It does not revise the stored BugOut Index history.

Companion designs that are written down and **not** in the weekly job:

- **Labor Utilization** (`incubating/boi-labor-utilization-incubating.md`). Proposal to replace headline unemployment with a prime-age employment measure, only after a backtest. It is not listed in the incubating section of `METRICS.md`.
- **AI Discontinuity Watch** (`incubating/boi-ai-discontinuity-watch-incubating.md`, v0.1.0). An ordinal 0–5 watch level. The document says it must not receive a weight and must not change the BugOut Index. Not implemented in code.
- Food prices, air quality, healthcare capacity, epidemics, grid outages, natural disasters, and a Government Authoritarianism Index. Essays in `incubating/`. The matching `fetch_*.py` files for food, air quality, healthcare, grid, and disasters **return hardcoded sample numbers and still report `status: success`**. The weekly job does not call them. `METRICS.md` links “Trust in Government” at the incubating Government Authoritarianism essay, which is a different idea from the Edelman series already in the core score.

`runtime/data/bank_failures.csv` is an FDIC-style closure list through January 2025. Nothing in the publisher reads it (open issue #33).

### Grounding rules the repo already states

These are product constraints, not just style notes:

- The index is a description of published statistics relative to fixed endpoints, not a forecast (methodology page).
- One headline number. Extra signals stay beside it until a versioned methodology change (labor-utilization essay; AIDW essay; open issue #53, which says a volatility multiplier must not rewrite the core score).
- Methodology versions are supposed to be explicit so old scores can be recomputed (`METRICS.md` version table: still only 1.0.0, dated both 1 January 2025 and 16 March 2025 in that same file).
- Promotion of a new core input requires a historical check, not a conceptual argument (labor-utilization essay).

### How a score is explained and checked today

| Check | What exists | Limit |
| --- | --- | --- |
| Public explanation | Methodology page lists this week’s raw value, endpoints, normalized score, weight, and source link | Weights are easy to misread. Trust’s essay does not match the math |
| Machine-readable snapshot | `docs/data/latest.json` (`schema_version` 1, `methodology_version` 1.0.0) | One current snapshot, plus 52 weeks of history embedded in it |
| History | `runtime/data/weekly_bugout_index.csv` stores raw and normalized values | It does **not** store each input’s observation date, so a revision and a new print look the same. In June 2026 debt printed 122.57, then 122.77, then 122.59 while unemployment was unchanged. That pattern is a revision of the same quarter, and it moved the index by a few hundredths |
| Recompute claim | Methodology page says check out a commit and rerun `weekly_run.py` | **Not true for past weeks.** Fetchers request the latest FRED observation, not the vintage that existed on that Friday. Rerunning today overwrites history with today’s latest. The committed CSV and JSON are the record |
| Automated tests | `runtime/util/test_http_retry.py`: 5 tests, passing in this review | `tests/test_scoring.py` does not collect. It imports `normalize_metric` from `runtime.processing`, and that package’s `__init__.py` is empty. `runtime/pytest.ini` points `testpaths` at `tests`, which is not where this file lives |
| Backtest | Not implemented | Open issue #55 asks for Depression, WWII, 1970s, and 2008 reconstructions. No harness, no page |

### Known limitations (from the code and the data, not from theory)

- **Freshness.** CPI and unemployment are monthly. Debt-to-GDP is quarterly. Edelman is annual. Homelessness is a manual annual constant. The job still runs every week. The methodology page states this. The homepage does not say which tiles are stale.
- **Crime is frozen in the published series.** Every weekly row, and the March 2025 daily file before that, stores incident rate **2723.0**. The CSV’s newest month is November 2024 and its “Last Updated” field is 19 February 2025. `fetched_at` is the string `2025-01-01T00:00:00Z`, not the file date. The weekly job does not refresh the file. `runtime/util/download_crime_rate_data.py` is not called, and it downloads a GitHub **blob HTML page** (`.../blob/development/data/final_sample.csv`), not a raw CSV. The site’s source link points at `jacobkap/real_time_crime_index`; the downloader points at `AH-Datalytics/rtci`.
- **Crime is an unweighted agency mean**, not a population-weighted national total. Small agencies count as much as large ones. The crime essay says this is an average across reporting agencies. Coverage is the Real-Time Crime Index sample, not the whole country.
- **Homelessness cannot update** until someone edits the return value `0.23`. The essay says the 2024 HUD point-in-time figure is 0.23% and that updates are manual. The timestamp is fake.
- **Trust cannot update** until someone adds a year column to the Edelman CSV. The fetcher does take the max year present, which is good. Nothing fetches a new year.
- **OECD business confidence has not moved.** All 23 pulse rows store `98.96989`. The 19 September snapshot dates that series **2024-01-01**. The tile still appears next to weekly claims and VIX with no stale marker. Hypothesis: FRED no longer advances `BSCICP03USM665S`. The observation date is what the pipeline stored; this review did not call FRED.
- **Deflation scores as healthier than low inflation.** −10% CPI maps to 100 and 15% maps to 0, in a straight line. A 2% print scores higher than a 4% print, and a −2% print scores higher than 2%. That is an explicit choice in `inflation_rate.md`. It is also a product question: deflation has been a crisis signal in other eras.
- **National only.** No state or city score. `about.md` lists geographic breakdown as a future plan.
- **Thresholds are fixed.** A slow move inside the window changes the score a little. A move past the endpoint does not, once clamped. The methodology page says the endpoints are meant to be historically extreme. This review found no backtest that shows they are.
- **Two products still exist in the tree.** The public site is the static renderer. A Streamlit app (`runtime/main.py`, `runtime/pages/`) still reads the old daily CSV and a different trust essay. `runtime/util/deploy.sh` merges `main` into a `deployment` branch and has a commented Raspberry Pi SSH step. `origin/deployment` still exists. `DEVELOPER.md` tells a new contributor to run `presentation/dashboard.py` and to install `requirements.txt` from the repo root. The app entry is `runtime/main.py`, and requirements live at `runtime/requirements.txt`.

---

## System architecture

### Components

```text
Public sources                          This repository                         Readers
─────────────────────                   ───────────────────────────             ───────
FRED / ALFRED  ──┐                      GitHub Action, Fridays
gold-api.com  ───┼──► weekly_run.py ──► CSVs under runtime/data/  ──► commit to main
local CSV/const ─┘         │            docs/data/latest.json
                           └──────────► render.py (Jinja2 + inline SVG)
                                              │
                                              ▼
                                        docs/*.html
                                              │
                                              ▼
                                        GitHub Pages
                                        www.bugoutindex.com
```

| Piece | Role | Runs in production? |
| --- | --- | --- |
| `.github/workflows/weekly-update.yml` | Scheduled job. Python 3.12. One secret, `FRED_API_KEY`. Commits data and `docs/` back to `main` as `bugout-bot` | Yes |
| `runtime/publish/weekly_run.py` | Fetch, score, append history, write JSON, call the renderer. Exits 2 or 3 to refuse a bad publish | Yes |
| `runtime/publish/render.py` plus `runtime/publish/templates/` | Static HTML. No JavaScript required. Pages: current, history, revisions, methodology | Yes |
| `runtime/data/fetch/fetch_{inflation,unemployment,debt,incident,homelessness,trust,markets,pulse,revisions}.py` | Inputs | Yes, from the weekly job |
| `runtime/util/http_retry.py` | Retries timeouts, connection errors, 408, 429, and 5xx. Backoff about 2s, 6s, 14s, 30s, 60s | Yes |
| `runtime/util/secrets_compat.py` and a Streamlit shim inside `weekly_run.py` | `FRED_API_KEY` from the environment in CI, from Streamlit secrets otherwise | Yes |
| `docs/CNAME` | Custom domain `www.bugoutindex.com` | Yes. Checked during this review: both hostnames serve the Pages site. `last-modified` on 22 September 2026 was the 19 September publish |
| Streamlit app, `calculate_index.py`, simulator, incubating fetchers, crime downloader, `deploy.sh` | Older or unfinished paths | No, not on the weekly path |
| `runtime/data/fetch_data.py` | A cache that would refetch some series every 7–365 days | Not called by the weekly job |

Dependencies (`runtime/requirements.txt`): Streamlit, pytest, requests, python-dotenv, pandas, Jinja2. The weekly site does not need a server process. Hosting cost is GitHub Actions minutes (recent scheduled runs are about 2 minutes) plus GitHub Pages. FRED and gold-api.com are used on their free tiers. There is no database and no paid model call.

### Data flow for one Friday

1. Cron `30 23 * * 5` starts the workflow. That is 23:30 UTC Friday, which the workflow comment describes as 18:30 America/Chicago during daylight time, after the U.S. equity close and away from the old 03:00 UTC Saturday slot that collided with FRED maintenance. `workflow_dispatch` can start it by hand.
2. The job checks out `main` with `fetch-depth: 1`, installs dependencies, and runs `python -m runtime.publish.weekly_run` with `FRED_API_KEY`.
3. Core fetchers run. Any core failure aborts before history is appended (exit 2).
4. Markets, pulse, and revisions run. Markets or pulse returning `status: error` abort the publish (exit 3). A **partial** pulse (some series missing) is logged and the site still publishes.
5. One row is appended to `weekly_bugout_index.csv`, `markets_history.csv`, and `pulse_history.csv`. The same calendar date can be appended twice; nothing in `_append_row` replaces an existing date.
6. `docs/data/latest.json` is rewritten. If the revisions fetch fails, the previous snapshot’s revisions block is copied forward and marked `reused_from`.
7. HTML and `docs/assets/style.css` are rendered. History charts use the last 52 rows.
8. The workflow commits those paths and pushes to `main`. GitHub Pages then rebuilds. A recent pages deploy finished in under a minute.

`runtime/publish/README.md` still says the schedule is 22:00 America/Chicago (03:00 UTC Saturday). The workflow file is the schedule that actually runs. Recent September 2026 runs started around 01:09–01:21 UTC **Saturday**, which is consistent with GitHub’s scheduled-job delay. `publication_date` is the UTC date at start, so those publishes are labeled Saturday even though the editorial intent is Friday evening U.S.

### How an update reaches the public site

There is no separate deploy step and no CDN configuration in the repo beyond GitHub Pages serving `/docs` on `main`. A green weekly run plus a green `pages-build-deployment` workflow is the whole path. Recent scheduled runs through 19 September 2026 completed successfully, and the live page showed 57.11 when this review fetched it.

The legacy daily file `runtime/data/historical_bugout_index.csv` (stringified Python dicts, starting 2025-03-16, score about 57.62 on the first rows) is not updated by this pipeline. The Streamlit dashboard still reads it. `runtime/util/sync_history.sh` copies that file from the `deployment` branch back to `main`.

---

## Update cadence today vs gaps

| Signal | Source cadence | What the weekly site actually does | Gap |
| --- | --- | --- | --- |
| Inflation, unemployment | Monthly (BLS, via FRED) | Refetched every Friday. Score moves when the latest print changes | No observation date in the CSV. Revisions and new months look alike |
| Debt-to-GDP | Quarterly | Refetched every Friday | Same. June 2026 shows a same-quarter revision moving the index |
| Crime | RTCI file, roughly monthly when maintained | Same local file every week. Value stuck at 2,723 | File ends November 2024. Downloader is not wired and requests HTML |
| Homelessness | HUD annual point-in-time | Constant 0.23 | No check for a newer AHAR. Fake timestamp |
| Trust | Edelman annual | Constant 41 from the 2025 column | No check for a 2026 barometer |
| Gold, silver, broad dollar | Daily / hourly | New row every publish. These move | Not in the score, which is correct for v1. No sentence explaining the move |
| Jobless claims, yield curve, VIX | Weekly or daily | New values most weeks | Not in the score. Shown without a “this is context” sentence beyond the section intro |
| Michigan sentiment | Monthly | Refetched. 19 Sep snapshot: 55.2 as of 2026-07-01 | Fine as context. Easy to mistake for a core input |
| OECD business confidence | Was monthly | Identical value, dated 2024-01-01, for the entire weekly history | Presented as a live pulse tile |
| Payroll revisions | Monthly vintage history | Rebuilt each successful run | Strong grounding page. Easy to miss from the hero |
| Written week note | — | Does not exist | The score can sit still for weeks with no explanation |
| Issue #26 “define update cadence” | Closed March 2025 | The weekly job is the decision that replaced a daily Streamlit refresh | `about.md` still says daily |

The product tension: people can see a new page every Friday, but the headline often prints “+0.00”. Markets and claims did move on weeks the index did not. The page does not say that in prose.

---

## Strengths

- **The headline is reproducible from public inputs** when you use the weekly code and the committed snapshot. The 19 September figure falls out of the six raw values, the endpoints, the inversion, and the divide-by-0.72 rule.
- **Fail-closed on core data.** A partial index is no longer published. Retries cover the failure mode that bit the project in April 2026.
- **The score is not mixed with commentary, markets, or AI.** That discipline is written into the AIDW and labor essays and into the methodology page. It is the right default.
- **History, JSON, and source links ship with the page.** A reader can leave the gauge and open FRED, the crime repo, HUD, or Edelman.
- **The revisions page is the right pattern for “qualitative but grounded.”** It shows initial versus later payroll prints without touching the BugOut Index.
- **Operations are small.** One workflow, one secret, static files, a custom domain that already resolves, about two minutes of CI a week.
- **Versioning is anticipated.** `methodology_version` is already on the snapshot. v1.1 can be introduced without pretending the old number never existed.

## Risks and gaps

- **A serious reader cannot tell which document is the methodology.** Following `METRICS.md` changes both the level and the band of the current score. Following the trust essay changes trust’s contribution by about 25 points of normalized score.
- **Three copies of the formula** (`weekly_run.py`, `calculate_index.py`, `normalize.py` / `scoring_v1.py`) plus a third trust formula in an essay. They match on today’s in-range inputs except for clamping. They will not stay matched if someone edits one of them.
- **Stale inputs look successful.** Crime and homelessness return `status: success` with a 2025-01-01 timestamp. Incubating fetchers return `status: success` with sample data. A future change that “turns on” those modules would publish fiction.
- **The recompute sentence overclaims.** Past weeks cannot be regenerated by rerunning fetchers.
- **The scoring test does not run,** so a formula edit would not be caught.
- **No alert beyond a red GitHub Action.** A refused publish leaves last week’s site up, which is safe, and it does so quietly unless someone watches the Actions tab.
- **Duplicate-date appends** if the workflow is dispatched twice in one UTC day.
- **`calculate_index.py` fetches data at import time** and appends to the legacy CSV. Running it by accident writes a second history in the old schema.
- **Issue list mixes product work with an unrelated study plan.** Issues #59–#67 (LangChain, multi-agent weeks, “Optional” links to agent blogs) are open on this repo and are not BugOut Index requirements.
- **Credibility risk if a model writes the homepage.** Open issues #42, #51, and #52 point at xAI or OpenAI news summaries and generated images. The acceptance notes correctly say this must not change the score. Ungrounded headlines would still change what the number *seems* to mean.

---

## Ideas already in the repo

Treated as a backlog inventory, not as commitments.

| Source | Idea | Already true? |
| --- | --- | --- |
| `about.md` | State/regional scores; grid and food security; more frequent updates | No |
| `incubating/boi-labor-utilization-incubating.md` | Replace unemployment with prime-age labor utilization after a backtest | No. Best-specified core change in the repo |
| `incubating/boi-ai-discontinuity-watch-incubating.md` | Separate 0–5 AI watch, never inside the score | No |
| Other `incubating/*.md` | Food CPI, AQI, healthcare, epidemics, grid, disasters, authoritarianism | Essays only. Several fetchers are stubs that claim success |
| Issue #53 | Volatility multiplier on *interpretation*, capped near 10%, not on the stored score | No. VIX and sentiment are already on the page as context |
| Issues #47, #50 | VIX and Michigan sentiment as companions | **Fetched already**, as pulse, not as their own modules |
| Issue #48 | Credit-card delinquency, FRED `DRCCLACBS`, quarterly, not in the score | No |
| Issue #49 | Civil unrest feed | No source code |
| Issue #33, `bank_failures.csv` | Failed-bank list as a signal | File only, through Jan 2025 |
| Issue #55 | Historical crisis backtest and a page about it | No |
| Issue #58 | Trend chart of the index and of each metric | **Partly done** on the static site (sparklines and history). The issue targeted the Streamlit dashboard |
| Issues #42, #44, #51, #52 | Current-events feed, twice daily, via xAI or OpenAI, plus images | #42 closed as a design; #51 and #52 still open. Not built |
| Issues #45, #46, #54 | Monetization, distribution, book list | Business ideas. Domain already exists |
| Issue #30 | Mental health as a metric | Open, no design |
| Issue #56 | CVE monitoring for nginx, Streamlit, Raspberry Pi OS | Fits the old Pi deploy, not GitHub Pages |
| Closed #37, #40, `deploy.sh` | Raspberry Pi / `deployment` branch | Branch still on the remote. SSH step commented out |

---

## Prioritized roadmap

Each item leaves v1.0.0 math alone unless the item says otherwise. Ship formula changes only as a numbered methodology version, with the old snapshot still labeled 1.0.0.

### Now

These improve rigor, honesty, and the Friday page without new data sources.

**1. Declare the publisher the methodology, and make the prose match it**

- **Outcome:** One description of v1.0.0. A reader with a calculator gets 57.11 from the 19 September raw inputs. `METRICS.md`, the methodology template, `about.md`, and the six metric essays use the same endpoints, the same trust transform, the same four bands, and the same aggregation.
- **Effort:** S for the words. No code change to `normalize()`.
- **Dependencies:** PM answers the weight question below. Until then, document **what the site does** (divide by 0.72) and show the shares next to the raw weights. Do not “fix” the denominator in code inside a docs pass.
- **Success:** The 4% inflation example, the trust-41 example, and the 19 September full example agree with `weekly_run.compute_index`. The site stops calling raw weights “the weight in the index” without showing the share.

**2. Show age on every tile**

- **Outcome:** Each core and pulse tile shows the observation date and the age in days or “manual, last set …”. Crime and homelessness stop displaying a fake `2025-01-01T00:00:00Z` as if it were a fetch. Business confidence is labeled stale or removed from the pulse row.
- **Effort:** S.
- **Dependencies:** A decision to drop or replace `BSCICP03USM665S` (question below). Removing it does not change the BugOut Index.
- **Success:** A Friday when nothing in the core moved still tells a visitor which three inputs are annual or frozen, and which pulse series is stuck in 2024.

**3. A factual week note, no model**

- **Outcome:** Under the gauge, 4–8 sentences generated only from this week’s snapshot versus last week’s row: which core raw values changed, by how much, their observation dates, which inputs were unchanged, and which pulse or market series moved. The note states that markets and pulse are not in the score.
- **Effort:** S.
- **Dependencies:** Item 2’s dates make the note honest. Can ship with the dates already present in `latest.json` (`source_fetched_at`, pulse `dates`).
- **Success:** The 12 September 2026 week would have said inflation moved and the index moved 0.04 points, and that crime, homelessness, and trust did not. A flat week would say the index was unchanged and would still mention claims, VIX, or metals if those moved. Every number in the note matches the JSON.

**4. Lock the formula with a test, and stop maintaining three copies**

- **Outcome:** One module owns endpoints, weights, inversion, clamping, aggregation, and bands. `weekly_run.py` and the simulator import it. A test fixes the 19 September inputs to 57.11 and the band “Moderate Stability”, and fixes trust 41 → 51.25. `tests/test_scoring.py` collects.
- **Effort:** M.
- **Dependencies:** None, if the extracted function is behavior-preserving, including the clamp.
- **Success:** `pytest` fails if someone removes the division by total weight or the trust inversion. Running the Streamlit simulator on in-range values matches the site.

**5. Make a missed Friday obvious**

- **Outcome:** A failed or refused publish is visible without opening the Actions log. Minimum: GitHub notification on failure, and a “last successful publish” line that is already on the footer stays accurate. Prefer also a short step summary in the workflow.
- **Effort:** S.
- **Dependencies:** None.
- **Success:** A dry-run failure (or the next real FRED refusal) produces a notification. The live site keeps the previous good HTML.

**6. Stamp the publication date in America/Chicago**

- **Outcome:** A run that starts just after 00:00 UTC Saturday is still “week of Friday” when that Friday is the U.S. publication day. `runtime/publish/README.md` quotes the cron that is actually in the workflow.
- **Effort:** S.
- **Dependencies:** None.
- **Success:** The next delayed-start run is labeled Friday. History rows already stamped Saturday stay as they are (do not rewrite history in this change).

### Next

These raise data quality and prepare a real methodology version. They still do not silently change v1.0.0.

**7. Record observation dates in the weekly CSV**

- **Outcome:** Each core row stores the source date next to the raw value. A debt revision is distinguishable from a new quarter.
- **Effort:** S.
- **Dependencies:** Item 4, so the snapshot and the CSV stay in one schema.
- **Success:** A week whose only change is a FRED revision of the same observation date is labeled as a revision in the week note.

**8. Put crime on a real refresh, without changing the index until the number is reviewed**

- **Outcome:** The weekly job can download the RTCI file from a raw URL, record the file’s max month, and fail the crime fetcher if the file is unreadable. Do not let a bad download return success. Compute the candidate rate (and a population-weighted alternative) into the JSON as **diagnostic fields** that are not inputs to `compute_index`, until the PM accepts a data revision.
- **Effort:** M.
- **Dependencies:** Confirm which RTCI repository is canonical (`jacobkap/real_time_crime_index` vs `AH-Datalytics/rtci`). A change to the 2,723 input is a published revision, even if the formula version stays 1.0.0, and should be explained in that week’s note.
- **Success:** The site can say “crime file through {month}”. A broken download does not publish a new index. The headline stays  on 2,723 until an explicit, reviewed switch.

**9. Annual manual inputs get a checklist, not a silent constant**

- **Outcome:** Homelessness and Edelman updates are a documented once-a-year edit: source PDF or table, year, value, and a real `fetched_at`. The fetcher reads that small table. It does not invent a timestamp.
- **Effort:** S.
- **Dependencies:** Someone owns the annual check (question below).
- **Success:** The 2025 trust figure and the 0.23 homelessness figure stay until a newer primary source is written down. When they change, the week note cites the source.

**10. Shadow series for labor utilization**

- **Outcome:** A weekly prime-age employment-to-population (and, if wanted, prime-age participation) series from FRED, charted on the site and labeled **not in the BugOut Index**. No weight.
- **Effort:** M.
- **Dependencies:** The construction in the incubating essay. FRED series IDs chosen in that implementation, not in this document.
- **Success:** For at least one month the shadow series is visible, sourced, and absent from `compute_index`. The incubating doc’s backtest is still required before any v1.1 promotion.

**11. A backtest harness, not a new score**

- **Outcome:** A script that applies v1.0.0 endpoints and weights to historical FRED levels (inflation, unemployment, debt-to-GDP) and writes a table. Crime, homelessness, and trust will be sparse; the harness should say so rather than fill gaps with guesses. This is the start of issue #55, not the finished historical essay.
- **Effort:** L for a full crisis narrative; M for the FRED-only mechanical replay.
- **Dependencies:** Item 4 (one formula). Item 1 (agreement on the 0.72 rule), because the backtest is meaningless if the formula is still disputed.
- **Success:** The harness reproduces 57.11 on the 19 September inputs, and it produces a time series for the three FRED core series over 2008 and 2020 with the missing three inputs explicitly excluded or held constant and labeled.

**12. Retire the second app in the docs, even if the code stays**

- **Outcome:** `DEVELOPER.md` matches `runtime/main.py` and `runtime/requirements.txt`, and it says the public product is the static site. `calculate_index.py` does not fetch on import. The `deployment` branch and Pi script are marked legacy.
- **Effort:** S.
- **Dependencies:** PM confirms the Pi is not still serving users (question below).
- **Success:** A new contributor following `DEVELOPER.md` reaches the weekly pipeline, not a missing `presentation/dashboard.py`.

### Later

Do these only after the Now items and the backtest. Several are already written as incubating ideas; they are later because they change meaning, coverage, or operating burden.

**13. Methodology v1.1, only with a version bump**

- **Outcome:** At most one labor change (headline unemployment vs the shadow labor-utilization series), plus an explicit decision that weights sum to 1.00 or stay relative. Old JSON remains `methodology_version: 1.0.0`. The site can show both during a transition.
- **Effort:** L.
- **Dependencies:** Items 10 and 11. PM sign-off. No stub fetcher may be included.
- **Success:** A short version note lists what changed, a reader can still recompute 19 September 2026 as 57.11 under v1.0.0, and the new score has a backtest paragraph for 2008 and 2020.

**14. Companions that are real series, still outside the score**

- **Outcome:** Credit-card delinquency (`DRCCLACBS`, issue #48) and, if the file is refreshed from FDIC, a bank-closure count (issue #33). Optional: a separate “short-term stress” readout using VIX, claims, and sentiment (issue #53) displayed **beside** the index, not multiplied into it.
- **Effort:** S for delinquency. M for banks and for a stress readout.
- **Dependencies:** The week-note pattern from item 3, so these do not look like secret inputs.
- **Success:** The gauge’s number is bit-for-bit the same the week these ship. Each new tile has a source link and a date.

**15. Food prices as the first incubating metric worth a real fetcher**

- **Outcome:** A FRED or BLS food CPI year-over-year, shown as not in the index. The stub `fetch_food_price_index.py` stops returning a fake success if anyone calls it.
- **Effort:** M.
- **Dependencies:** Item 4’s rule that only `CORE_METRICS` enter the score.
- **Success:** Food inflation on the page with a source and a date. `compute_index` unchanged. The other stub fetchers either raise a clear “not implemented” or are deleted so they cannot return success.

**16. Geographic scores**

- **Outcome:** Not a national gauge replacement. A clearly secondary view, only where the same definition exists (state unemployment is easy; comparable crime, homelessness, and trust are not).
- **Effort:** L.
- **Dependencies:** A written rule for what “the same index” means when an input does not exist at state level. Otherwise this becomes six different indexes.
- **Success:** Any state figure is labeled with which inputs it contains. The national 0–100 remains the BugOut Index.

**17. Civil unrest and authoritarianism**

- **Outcome:** Only if a structured dataset is chosen (the current-events issue mentions GDELT as a later option). Not a model browsing the news. Not folded into v1.1 by default.
- **Effort:** L.
- **Dependencies:** A source that can be re-fetched and cited. A decision that this is a companion, after seeing it run for a quarter.
- **Success:** Every event has a source URL and a date. The index formula file does not import it.

**18. AI Discontinuity Watch as a human-edited page**

- **Outcome:** If the PM wants it public, publish the rubric and a hand-set level with dated evidence notes. No weight. No model-assigned level.
- **Effort:** M for a static page. Ongoing human time after that, which is the actual cost.
- **Dependencies:** The incubating doc’s own rule: retrospective checks against past milestones before it is treated as more than a draft.
- **Success:** The homepage, if it links the watch, says the watch is not the BugOut Index. Changing the watch level does not change  the gauge.

Distribution and monetization (issues #45 and #46) are not engineering items. The domain and the weekly page already cover the “have a site” step in #46. A newsletter would reuse the factual week note from item 3.

---

## Language models: where they help, where they do not

**Not recommended for the score, the weights, the bands, or the AI watch level.** The product’s claim is that a stranger can recompute the number from public series. A model call in that path is a new unpublished input. It also fails in ways the current job is designed to avoid: a timeout, a fluent wrong cause, or a different paragraph on every rerun.

**Not needed for the week note.** Item 3 is a template over fields the pipeline already stores. That is cheaper, stable, and checkable. Prefer it.

**Optional later, and only as a draft beside the template**

| Use | Worth it? | Shape | Cost and failure |
| --- | --- | --- | --- |
| Weekly prose that only restates the JSON diff | No. The template is the product | — | A model adds cost and a way to misstate a delta |
| Tighten wording of the factual note | Low value | One batch call per Friday, after the template exists. Input is the template plus the JSON, not the open web. Reject the draft if any numeral is absent from the JSON | Small model, well under a few dollars a month at one call a week. If the call fails, publish the template. Human read for the first month if the draft replaces the template |
| Cite-locked news sidebar (issues #42, #51) | Only after a non-model source exists | Retrieve items from a named feed or GDELT-style file. Model may summarize **the retrieved text**. Output must include the source URL. Drop any item whose URL was not in the input | Do not browse “recent instability” in an open prompt. That is where invented events and inflated tone come from. Issue #42’s token estimate (~$0.13/month in 2025 prices) is not a safe plan by itself; the failure mode is trust, not the bill. Cap spend in the provider dashboard anyway. Twice-daily is unnecessary while the index is weekly |
| Images for events (issue #52) | No | — | Decorative images do not make the index more true, and generated scenes read as evidence |
| AIDW scoring | No | Humans apply the written rubric | A model will sound more certain than the evidence rule allows |
| Backtest narrative | Maybe, after item 11 | Model writes from the harness table only | Same numeral check as the week note. Do not let it fill missing crime or trust history |
| Choosing new weights | No | — | That is a versioned product decision |

Operating rules if a call is ever added to the Action:

- One batch call per weekly run, not a call per page view. The site stays static.
- Prefer a small model. There is no reasoning task here beyond compression of a table.
- Hard spend ceiling in the provider account. The rest of this system costs about the Actions minutes.
- Fail closed to the deterministic note. A model error must not fail the index publish, and must not be required for it.
- The model does not choose `bugout_index`, weights, or `methodology_version`.
- Keep the prompt, the raw model output, and the published text in the workflow log so a bad week can be audited.

---

## Open questions for the PM

1. **Weights.** The site divides by 0.72 and prints 57.11, Moderate. `METRICS.md` sums the weighted scores and would print about 41, Low Stability, from the same inputs. Which story is the product: relative weights that always fill 0–100, or absolute shares that were meant to sum to 1.00 and never did? This review recommends **keeping the published behavior** until you decide, and saying so in the docs either way.
2. **Deflation.** Should −2% inflation score as more stable than +2%, as the −10 to +15 line does today?
3. **Crime.** Is “unweighted mean of violent plus property rates in the RTCI file” the definition you want to keep, and which GitHub repo is the source of that file?
4. **What “weekly” is for.** Confirm the product is a slow index plus a weekly explanation, not faster inputs inside the score. The data supports the first one. Issues #42 and #53 pull toward the second.
5. **Is the Streamlit app or the Raspberry Pi still in use?** If not, the roadmap treats them as legacy.
6. **Week note voice.** Is a dry, numeric note enough, or do you want a reviewed paragraph later? The roadmap does the dry note first.
7. **Canonical URL.** `www.bugoutindex.com` is what the CNAME and DNS serve. The README had been pointing only at `github.io`. This review names both. Which should lead?
8. **Annual owner.** Who updates HUD and Edelman, and in which month?
9. **Business confidence.** Remove the 2024-dated OECD series from the pulse, or replace it with a series that still updates?
10. **Issues #59–#67.** Close them as unrelated to this product?
11. **Volatility multiplier.** Confirm it must never scale the number on the gauge. A separate stress readout can wait.
12. **AIDW.** Do you want a public watch page in the next build cycle, or should it stay an unpublished incubating note?

---

## Evidence index

Primary code and docs used for this review:

- Score: `runtime/publish/weekly_run.py`, `runtime/processing/normalize.py`, `runtime/processing/scoring_v1.py`, `runtime/processing/calculate_index.py`, `runtime/pages/boi_simulator.py`
- Publish path: `.github/workflows/weekly-update.yml`, `runtime/publish/render.py`, `runtime/publish/templates/`, `runtime/publish/README.md`, `docs/CNAME`
- Fetchers: `runtime/data/fetch/`, `runtime/util/http_retry.py`, `runtime/util/download_crime_rate_data.py`
- Stated methodology: `METRICS.md`, `runtime/static/markdown/*.md`, `runtime/publish/templates/methodology.html.j2`
- Incubating: `incubating/`
- Published numbers: `docs/data/latest.json` (generated 2026-09-19T01:21:36Z, index 57.11), `runtime/data/weekly_bugout_index.csv` (23 rows, 2026-04-21 through 2026-09-19)
- Tests: `tests/test_scoring.py` (collection error), `runtime/util/test_http_retry.py` (5 passed)
- Issues and pull requests on `adammontville/bugoutindex`, including merged PRs #69 (weekly site), #70 (FRED retries), #71 (revisions page)
