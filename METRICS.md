# BugOutIndex Metrics and Methodology

**Version**: 1.0.0  
**Effective Date**: January 1, 2025  

---

## **Introduction**

The BugOutIndex is a societal stability scoring system designed to help individuals and communities assess when conditions may deteriorate to a critical point. This document describes the metrics and methodology for **BugOutIndex Version 1.0.0**, the initial release of the system. Each version of the methodology will be documented, ensuring transparency and allowing for historical recalculations.

---

## **Metrics Overview**

The BugOutIndex incorporates the following metrics to evaluate societal stability:

### **Economic Metrics**
- **Inflation Rate**: Measures the annual percentage increase in consumer prices.
- **Unemployment Rate**: Tracks the percentage of people in the labor force who are unemployed.
- **Debt-to-GDP Ratio**: Indicates the government’s ability to manage debt relative to its economic output.

### **Social Health Metrics**
- **Crime Rate**: Represents reported violent crimes per 100,000 people.
- **Homelessness Rate**: Measures the percentage of the population experiencing homelessness.

---

## **Scoring Methodology**

Each metric is scored on a normalized scale of **0–100**, where:
- **100**: Indicates optimal conditions (low risk).
- **0**: Indicates critical instability (high risk).

### **Normalization Process**
For each metric, raw data is normalized using predefined thresholds:

Normalized Score = (1 - ((Raw Value - Min) / (Max - Min))) * 100

- **Example** (Inflation Rate):
  - Thresholds: 0%–10%.
  - Raw Value: 4%.
  - Normalized Score:

(1 - ((4 - 0) / (10 - 0))) * 100 = 60

---

## **Weights and Normalization Ranges**

| **Metric**           | **Weight** | **Normalization Range**       |
|-----------------------|------------|--------------------------------|
| **Inflation Rate**    | 0.15       | 0%–10%                        |
| **Crime Rate**        | 0.12       | 500–2000 incidents per 100,000 |
| **Unemployment Rate** | 0.10       | 0%–20%                        |
| **Debt-to-GDP Ratio** | 0.07       | 0%–200%                       |
| **Homelessness Rate** | 0.09       | 0%–1%                         |
| **Trust in Government Score** | 0.09 | 0%-100% |

---

## **Rollup into the BugOutIndex**

### **Step 1: Metric Normalization**
Each metric is normalized to a 0–100 scale based on its thresholds.

### **Step 2: Metric Weighting**
Each normalized metric score is multiplied by its weight to calculate its contribution to the overall score:

Metric Weighted Score = Normalized Score * Metric Weight

### **Step 3: Overall Index Calculation**
The overall BugOutIndex score is the sum of all weighted metric scores:

BugOutIndex = Σ (Metric Weighted Score)

---

## **Interpreting the BugOutIndex**

| **Score Range**  | **Interpretation**                              | **Suggested Actions**                                |
|------------------|------------------------------------------------|-----------------------------------------------------|
| **90.00–100.00** | **High Stability (Low Risk)**                  | Focus on long-term planning and gradual improvements. |
| **70.00–89.99**  | **Moderate Stability (Warning Signs)**         | Monitor trends closely; prepare contingency plans.   |
| **50.00–69.99**  | **Low Stability (Heightened Risk)**            | Initiate preparedness measures; consider evacuation triggers. |
| **<50.00**       | **Critical Instability (Collapse Likely)**     | Activate bug-out plans; immediate action recommended. |

---

## **Version History**

| **Version** | **Date**       | **Changes**                                           |
|-------------|----------------|-----------------------------------------------------|
| 1.0.0       | January 1, 2025 | Initial release with core metrics and methodology. |

---

## **Versioning and Licensing**

The BugOutIndex uses a versioning system to ensure transparency as the methodology evolves. Historical scores can be recalculated using past versions.

BugOutIndex is dual-licensed:
- **AGPL-3.0** for open-source use.
- A **commercial license** for proprietary use. Contact [adam.w.montville@gmail.com](mailto:adam.w.montville@gmail.com) for details.

For more information, see the [LICENSE](./LICENSE.md) file.

## **Future Metrics in Development**

The BugOutIndex team is actively exploring additional metrics to expand the scoring system. These metrics are currently in the "incubating" phase and are not part of the core scoring methodology.

You can find detailed documentation for these incubating metrics in the **[incubating folder](./incubating/)**.

### Incubating Metrics
- [Food Price Index](./incubating/food_price_index.md)
- [Air Quality Index](./incubating/air_quality_index.md)
- [Healthcare Capacity](./incubating/healthcare_capacity.md)
- [Epidemic Spread Index](./incubating/Epidemic_Spread_Index.md)
- [Grid Outages](./incubating/grid_outages.md)
- [Natural Disaster Frequency](./incubating/natural_disaster_frequency.md)
- [Trust in Government](./incubating/Government_Authoritarianism_Index.md)
