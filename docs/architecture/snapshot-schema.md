# Snapshot schema 1

**Status:** Frozen contract for the published weekly snapshot.  
**Machine check:** `runtime/publish/snapshot_schema.py` (`validate_published_snapshot`).  
**Example:** [`docs/data/latest.json`](../data/latest.json) — `schema_version` 1, `methodology_version` 1.0.0, `bugout_index` 57.04, `publication_date` 2026-10-02. That file is the published 1.0.0 week. It is not rewritten by methodology 1.1.0.

`schema_version` names this JSON shape. `methodology_version` names the formula and the crime input. Methodology 1.1.0 keeps `CORE_METRICS`, the endpoints, the weights, and the bands. It changes the crime series. A new top-level field is a shape change and needs `schema_version` 2. The crime unlock did not add one, so `schema_version` stays 1. Old files stay readable under the version they were written with. New publishes stamp `methodology_version` `"1.1.0"`.

## Envelope

| Field | Required | Role |
| --- | --- | --- |
| `schema_version` | yes | Integer `1` |
| `methodology_version` | yes | String. New publishes stamp `"1.1.0"`. `"1.0.0"` remains valid |
| `generated_at_utc` | yes | ISO-8601 timestamp string |
| `publication_date` | yes | `YYYY-MM-DD` in America/Chicago |
| `bugout_index` | yes | Headline number. Not an object |
| `interpretation` | yes | `band`, `risk`, `band_key` strings from `interpret()` |
| `metrics` | yes | The six scored cores, and only those |
| `markets` | yes | Companion. Not in the score |
| `pulse` | yes | Companion. Not in the score |
| `revisions` | yes | Companion. Not in the score |
| `history` | yes | Last rows from the weekly CSVs (cell values are strings) |
| `labor_shadow` | yes | Companion. `in_bugout_index` is false |
| `food_shadow` | yes | Companion. `in_bugout_index` is false |
| `nyc_dhs_shadow` | yes | Companion. `in_bugout_index` is false |
| `ramsey_shelter_shadow` | yes | Companion. `in_bugout_index` is false |
| `sf_shelter_shadow` | yes | Companion. `in_bugout_index` is false |
| `shelter_region_shadow` | yes | Companion. `in_bugout_index` is false |
| `pew_trust_shadow` | yes | Companion. `in_bugout_index` is false |
| `gallup_confidence_shadow` | yes | Companion. `in_bugout_index` is false |

No other top-level keys are part of schema 1.

## Scored cores

`metrics` keys are exactly `CORE_METRICS`:

`inflation_rate`, `incident_rate`, `unemployment_rate`, `debt_to_gdp_ratio`, `homelessness_rate`, `trust_in_government`.

Each object has:

| Field | Meaning |
| --- | --- |
| `raw` | Number fed to the formula |
| `normalized` | 0–100 stability score for that input |
| `weight` | Raw weight (the publisher still divides by 0.72). Unchanged in 1.1.0 |
| `observation_date` | Period the number describes, or null |
| `source_fetched_at` | Fetcher timestamp when one exists, or null |
| `status` | `"success"` on a snapshot that is allowed to publish |

Optional, and not inputs to `compute_index`:

- `provenance` on crime, homelessness, and trust
- `diagnostics` on crime (candidate rates and which national rate was scored). On a 1.0.0 snapshot `index_input` is false and `raw` is the locked 2723.0. On a 1.1.0 snapshot `index_input` is true and `raw` is the selected national rate. Validation does not require either flag; the shape is the same

A publish requires every core `status` to be `"success"`. Fewer than six successes is exit 2, before history is appended.

## Companions

Companions are fetched and shown. They do not enter `compute_index`. Validation fails a snapshot that sets a shadow's `in_bugout_index` to anything other than false, or that puts a companion name inside `metrics`.

`markets` holds `status`, `fetched_at`, and the series `gold_usd_per_oz`, `silver_usd_per_oz`, `dxy`.

`pulse` holds `status`, `fetched_at`, `values`, and `dates` for `initial_jobless_claims`, `consumer_sentiment_umich`, `business_confidence`, `yield_curve_10y_2y`, and `vix`. A partial pulse (some series missing) may still publish. `status: error` may not.

`revisions` holds `status`, `payems` (vintage rows), and `unrate` (`benchmark_release_date`, `pre_benchmark_snapshot_date`, `rows`). A failed revisions fetch copies the previous block forward.

Shadow blocks share `status`, `in_bugout_index: false`, `series_ids`, `values`, `dates`, `observations`, and `errors`. Checklist shadows also carry periods, sources, and notes. The value names frozen from the current snapshot:

| Block | Value keys |
| --- | --- |
| `labor_shadow` | `prime_age_epop`, `prime_age_lfpr` |
| `food_shadow` | `food_cpi_yoy` |
| `nyc_dhs_shadow` | `nyc_dhs_total_individuals` |
| `ramsey_shelter_shadow` | `ramsey_shelter_total_people` |
| `sf_shelter_shadow` | `sf_shelter_occupancy_rate` |
| `shelter_region_shadow` | `nashville_hmis_people`, `austin_sheltered_people`, `denver_shelter_occupancy` |
| `pew_trust_shadow` | `pew_public_trust` |
| `gallup_confidence_shadow` | `gallup_congress`, `gallup_presidency`, `gallup_supreme_court`, `gallup_core_institutions` |

When a shadow or revisions fetch fails and an earlier block exists, the writer keeps that block and may add `reused_from`, `current_status`, and `current_message`. Those fields are part of schema 1. They are not a new schema. A shadow failure does not refuse the publish, and it does not move the score.

## History

`history` series are `bugout_index`, `markets`, `pulse`, and the same shadow names as the companion blocks. Each series is a list of row objects with a `date`. Core history rows store the raw value, `{metric}_observation_date`, and `{metric}_normalized`.

## Publish checks

The weekly job scrubs secrets, then validates, then writes `docs/data/latest.json` and renders HTML. Validation failure is exit 4: `docs/` is not written, and the GitHub Action does not commit.

| Failure | Exit | What happens |
| --- | --- | --- |
| A core input fails, or fewer than six cores succeed | 2 | Refuse before history is appended. The live site stays the last good HTML |
| Markets or the pulse return `status: error` | 3 | Refuse before history is appended |
| The pulse is partial | 0 | Log it. The page says which series are missing |
| A shadow fails | 0 | Carry forward the previous block and its observation dates when one exists |
| Revisions fetch fails | 0 | Copy the previous revisions block forward and mark it reused. Do not rewrite stored index history |
| Snapshot fails validation (wrong shape, missing required core, companion folded into the score, secret material left in the output) | 4 | Do not write `docs/`. Do not commit |
| Render fails | non-zero | The Action does not commit a half-written `docs/` |

An RTCI download failure, an unreadable crime file, or a latest month with no usable national rate is a core failure (exit 2). The job does not carry the previous crime value forward and does not invent an observation date. That is the core-input row above. Shadows and revisions still carry forward. Crime does not.

`FRED_API_KEY` is read from the environment. The weekly job does not import Streamlit.
