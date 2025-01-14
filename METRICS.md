# BugOutIndex Metrics and Methodology

**Version**: 1.0.0  
**Effective Date**: January 1, 2025  

---

## **Introduction**

The BugOutIndex is a societal stability scoring system designed to help individuals and communities assess when conditions may deteriorate to a critical point. This document describes the metrics and methodology for **BugOutIndex Version 1.0.0**, the initial release of the system. Each version of the methodology will be documented, ensuring transparency and allowing for historical recalculations.

---

## **Metrics Overview**

The BugOutIndex incorporates metrics across four major categories to evaluate societal stability:

### **1. Economic Metrics**
- **Inflation Rate**: Measures the annual percentage increase in consumer prices.
- **Unemployment Rate**: Tracks the percentage of people in the labor force who are unemployed.
- **Debt-to-GDP Ratio**: Indicates the government’s ability to manage debt relative to its economic output.

### **2. Social Health Metrics**
- **Viloent Crime Rate**: Represents reported violent crimes per 100,000 people.
- **Homelessness Rate**: Measures the percentage of the population experiencing homelessness.
- **Trust in Government**: Reflects public confidence in government institutions (based on surveys or sentiment analysis).

### **3. Infrastructure Metrics**
- **Grid Outages**: Hours of power outages per year, reflecting energy reliability.
- **Food Price Index**: Tracks the average price of staple foods relative to a baseline.
- **Healthcare Capacity**: Measures hospital occupancy rates and access to critical care.

### **4. Environmental Metrics**
- **Natural Disaster Frequency**: Number of significant natural disasters per year.
- **Air Quality Index (AQI)**: Measures air pollution levels, with higher values indicating worse air quality.

---

## **Scoring Methodology**

Each metric is scored on a normalized scale of **0–100**, where:
- **100**: Indicates optimal conditions (low risk).
- **0**: Indicates critical instability (high risk).

### **Normalization Process**
For each metric, raw data is normalized using predefined thresholds:
Normalized Score = (1 - ((Raw Value - Min) / (Max - Min))) × 100

- **Example** (Inflation Rate):
  - Thresholds: 0%–10%.
  - Raw Value: 4%.
  - Normalized Score:
(1 - ((4 - 0) / (10 - 0))) × 100 = 60

---

## **Weighting**

Each metric contributes to its category score, and each category is weighted to calculate the overall BugOutIndex. The weights are as follows:

### **Category Weights**
| **Category**         | **Weight (%)** |
|-----------------------|----------------|
| **Economics**         | 30             |
| **Social Health**     | 25             |
| **Infrastructure**    | 20             |
| **Environment**       | 15             |
| **Global Context**    | 10             |

### **Metric Weights Within Categories**
| **Metric**             | **Category**      | **Weight (%)** |
|-------------------------|-------------------|----------------|
| Inflation Rate          | Economics         | 12             |
| Unemployment Rate       | Economics         | 10             |
| Debt-to-GDP Ratio       | Economics         | 8              |
| Crime Rate              | Social Health     | 10             |
| Homelessness Rate       | Social Health     | 8              |
| Trust in Government     | Social Health     | 7              |
| Grid Outages            | Infrastructure    | 8              |
| Food Price Index        | Infrastructure    | 7              |
| Healthcare Capacity     | Infrastructure    | 5              |
| Natural Disaster Frequency | Environment    | 8              |
| Air Quality Index       | Environment       | 7              |

---

## **Rollup into the BugOutIndex**

### **Step 1: Metric Normalization**
Each metric is normalized to a 0–100 scale based on its thresholds.

### **Step 2: Category Scores**
For each category, the weighted average of metric scores is calculated:

Category Score = Σ (Metric Score × Metric Weight)

### **Step 3: Overall Index Calculation**
The overall BugOutIndex score is calculated as the weighted average of category scores:

BugOutIndex = Σ (Category Score × Category Weight)

---

## **Interpreting the BugOutIndex**

| **Score Range** | **Interpretation**          |
|------------------|-----------------------------|
| **90–100**       | High Stability (Low Risk)  |
| **70–89**        | Moderate Stability (Warning Signs) |
| **50–69**        | Low Stability (Heightened Risk)    |
| **<50**          | Critical Instability (Collapse Likely) |

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
- A **commercial license** for proprietary use. Contact [adam.w.montville@gmail.com] for details.

For more information, see the [LICENSE](./LICENSE.md) file.
