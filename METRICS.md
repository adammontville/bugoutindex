# BugOutIndex Metrics and Methodology

**Version**: 1.0.0  
**Effective Date**: January 1, 2025  

> **Authoritative implementation:** `runtime/processing/formula.py`
> (`CORE_METRICS`, `METRIC_RANGES`, `WEIGHTS`, `normalize`, `compute_index`, `interpret`).
> The weekly publisher (`runtime/publish/weekly_run.py`) and the Streamlit
> simulator import that module. This document describes what the publisher
> already does. It does not define a separate formula.

---

## Introduction

The BugOutIndex is a societal stability scoring system designed to help individuals and communities assess when conditions may deteriorate to a critical point. This document describes the metrics and methodology for **BugOutIndex Version 1.0.0**, the initial release of the system. Each version of the methodology will be documented, ensuring transparency and allowing for historical recalculations.

On a perfect week (every core metric at its most stable endpoint), the index scores **100**. Raw weights sum to **0.72**; the publisher divides by that sum so the six relative weights always fill the 0–100 scale.

---

## Metrics Overview

The BugOutIndex incorporates six core metrics:

### Economic Metrics
- **Inflation Rate**: Year-over-year percentage change in consumer prices (CPI-U via FRED).
- **Unemployment Rate**: Percentage of the labor force that is unemployed (FRED UNRATE).
- **Debt-to-GDP Ratio**: Federal debt as a percentage of GDP (FRED).

### Social Health Metrics
- **Crime Rate** (`incident_rate`): Violent **plus** property crime incidents per 100,000 people (Real-Time Crime Index sample; unweighted mean of reporting agencies).
- **Homelessness Rate**: Percentage of the population experiencing homelessness (HUD PIT / AHAR).

### Governance Metrics
- **Trust in Government**: Percentage of respondents expressing confidence in government (Edelman Trust Barometer). Higher trust maps to higher stability.

---

## Scoring Methodology

Each metric is scored on a normalized scale of **0–100**, where:
- **100**: Indicates optimal conditions (low risk / high stability).
- **0**: Indicates critical instability (high risk).

### Normalization Process

For each metric, raw data is mapped onto 0–100 between fixed endpoints:

```
normalized = (1 − (raw − min) / (max − min)) × 100
```

Values outside the endpoints are clamped to 0 or 100.

**Trust in Government** uses the same linear map with `inverse=True` (higher trust → higher stability). Equivalently:

```
normalized_trust = ((raw − 0) / (80 − 0)) × 100
```

so an Edelman trust reading of **41%** normalizes to **51.25**.

### Worked examples (publisher math)

**Inflation at 4%** (endpoints −10 to 15):

```
normalized = (1 − (4 − (−10)) / (15 − (−10))) × 100
           = (1 − 14/25) × 100
           = 44.00
```

**Trust at 41%** (endpoints 0 to 80, inverted):

```
normalized = ((41 − 0) / (80 − 0)) × 100
           = 51.25
```

---

## Weights and Normalization Ranges

Raw weights are relative coefficients. They sum to **0.72**. After dividing by that sum, each metric’s **share of the index** is `weight / 0.72`.

| Metric | Raw weight | Share of score (weight / 0.72) | Normalization range |
|--------|------------|--------------------------------|---------------------|
| Inflation Rate | 0.15 | 20.83% | −10% to 15% |
| Crime Rate (violent + property) | 0.12 | 16.67% | 500 to 8,000 per 100,000 |
| Unemployment Rate | 0.12 | 16.67% | 0% to 25% |
| Debt-to-GDP Ratio | 0.12 | 16.67% | 0% to 200% |
| Homelessness Rate | 0.09 | 12.50% | 0% to 0.5% |
| Trust in Government | 0.12 | 16.67% | 0% to 80% (inverted) |
| **Total** | **0.72** | **100%** | |

Site tiles that print “Weight 15%” are showing the raw weight × 100, not the post-division share. Inflation’s share of the finished index is about **20.8%**.

---

## Rollup into the BugOutIndex

### Step 1: Metric Normalization
Each available core metric is normalized to a 0–100 scale (trust inverted as above).

### Step 2: Weighted contribution
Each normalized score is multiplied by its raw weight:

```
contribution_i = normalized_i × weight_i
```

### Step 3: Overall Index Calculation
The BugOutIndex is the **weight-normalized** sum (divide by the sum of weights that participated):

```
BugOutIndex = Σ (normalized_i × weight_i) / Σ weight_i
```

With all six metrics present, `Σ weight_i = 0.72`. A week where every metric is at its best endpoint therefore scores **100**, not 72.

Missing metrics are skipped and the denominator shrinks. The weekly publisher refuses to publish unless all six core fetches succeed, so a live publish does not silently drop an input.

### Worked example — week of 19 September 2026

Raw inputs from `docs/data/latest.json` / the weekly CSV:

| Metric | Raw | Normalized | Weight | Contribution (norm × weight) |
|--------|-----|------------|--------|------------------------------|
| Inflation | 3.3530… | 46.59 | 0.15 | 6.9885 |
| Crime (violent + property) | 2723.0 | 70.36 | 0.12 | 8.4432 |
| Unemployment | 4.1 | 83.60 | 0.12 | 10.0320 |
| Debt-to-GDP | 122.59387 | 38.70 | 0.12 | 4.6440 |
| Homelessness | 0.23 | 54.00 | 0.09 | 4.8600 |
| Trust in Government | 41.0 | 51.25 | 0.12 | 6.1500 |
| **Sum** | | | **0.72** | **41.1177** |

```
BugOutIndex = 41.1177 / 0.72 ≈ 57.11
```

Interpretation: **Moderate Stability / Warning Signs** (55–69.99).

A plain sum of the weighted contributions **without** dividing by 0.72 would yield about **41.12** (Low Stability). That is **not** how v1.0.0 publishes.

---

## Interpreting the BugOutIndex

Four risk bands match `interpret()` in the weekly publisher:

| Score Range | Band | Interpretation |
|-------------|------|----------------|
| **70.00–100.00** | **High Stability** | Low Risk — focus on long-term planning. |
| **55.00–69.99** | **Moderate Stability** | Warning Signs — monitor trends; prepare contingencies. |
| **40.00–54.99** | **Low Stability** | Heightened Risk — keep preparedness in mind. |
| **Below 40** | **Critical Instability** | Collapse Likely — activate bug-out plans at your discretion. |

Band wording and thresholds are unchanged from the live site. Recalibrating how “calm” Moderate feels is deferred to an explicit later methodology version.

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | March 16, 2025 | Initial release with core metrics and methodology. |

---

## Versioning and Licensing

The BugOutIndex uses a versioning system to ensure transparency as the methodology evolves. Historical scores can be recalculated using past versions.

A mechanical replay of v1.0.0 on historical FRED inflation, unemployment, and debt-to-GDP lives in [`runtime/backtest/`](./runtime/backtest/README.md). It is not a new methodology version. Crime, homelessness, and trust are excluded or held at the published 19 September 2026 baselines and labeled; they are not filled in from a guessed history.

BugOutIndex is dual-licensed:
- **AGPL-3.0** for open-source use.
- A **commercial license** for proprietary use. Contact [adam.w.montville@gmail.com](mailto:adam.w.montville@gmail.com) for details.

For more information, see the [LICENSE](./LICENSE.md) file.

## Future Metrics in Development

The BugOutIndex team is actively exploring additional metrics to expand the scoring system. These metrics are currently in the "incubating" phase and are **not** part of the core scoring methodology.

You can find detailed documentation for these incubating metrics in the **[incubating folder](./incubating/)**.

### Incubating Metrics
- [Food Price Index](./incubating/food_price_index.md)
- [Air Quality Index](./incubating/air_quality_index.md)
- [Healthcare Capacity](./incubating/healthcare_capacity.md)
- [Epidemic Spread Index](./incubating/Epidemic_Spread_Index.md)
- [Grid Outages](./incubating/grid_outages.md)
- [Natural Disaster Frequency](./incubating/natural_disaster_frequency.md)
- [Government Authoritarianism Index](./incubating/Government_Authoritarianism_Index.md) — incubating; distinct from the core Edelman **Trust in Government** metric already in the score
- [Labor Utilization](./incubating/boi-labor-utilization-incubating.md) — prime-age EPOP (`LNS12300060`) and participation (`LNS11300060`) are shown on the weekly site as a shadow series and are not in v1.0.0; the composite formula is still incubating and needs a backtest before any promotion

### Companion Measures (non-core, no BOI weight)
- [AI Discontinuity Watch (AIDW)](./incubating/boi-ai-discontinuity-watch-incubating.md) — optional watch level; does not change the BOI score.
