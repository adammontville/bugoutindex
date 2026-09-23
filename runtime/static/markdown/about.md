## **What is the BugOut Index?**
The **BugOut Index (BOI)** is a **directional reading of stress and stability**. It places six published economic, crime, and governance statistics between fixed endpoints and combines them into a **single 0–100 score**. Higher means those conditions are less stressed. The number is recomputed **weekly**. It shows how hard the published inputs are pressing. It is not a forecast, and it is not an instruction to bug out.

---

## **Score Interpretation**
| **Score Range** | **Interpretation** |
|-----------------|--------------------|
| **70–100**      | High Stability (Low Risk) |
| **55–69.99**    | Moderate Stability (Warning Signs) |
| **40–54.99**    | Low Stability (Heightened Risk) |
| **Below 40**    | Critical Instability (Collapse Likely) |

A **higher score** means the published inputs are **less stressed**. A **lower score** means they are **pressing harder**.

---

## **How It Works**
The BugOut Index is **recomputed every week** (typically Friday evening after US markets close) and published as a static site. Underlying inputs update on their own schedules—monthly, quarterly, or annually—so the weekly number only moves when those sources publish. The BOI aggregates six core indicators, normalizes each to a 0–100 scale, and combines them with relative weights that sum to **0.72**, then **divides by that sum** so a perfect week scores 100. These include:
- **Economic Factors:** Inflation, unemployment, and debt-to-GDP ratio.
- **Crime & Public Safety:** Violent **plus** property crime rates (Real-Time Crime Index sample).
- **Social Stability:** Homelessness rates and institutional trust levels (Edelman).

Each of these metrics is weighted and combined into a single **composite score**, which represents the overall **stability or instability** of a given society. See `METRICS.md` at the repository root for the full worked example.

---

## **Why the BOI Matters**
Unlike other indices that focus **only on the economy or crime**, the **BugOut Index takes a holistic approach**. By incorporating **multiple risk factors**, the BOI helps answer key questions such as:
- Is **economic distress** leading to more crime?
- How does **public trust in institutions** affect stability?
- Are certain regions seeing **worsening conditions over time**?

The number is a reading of those published conditions. It does not say when to relocate, and it does not forecast a crisis.

- **Individuals** can see whether the six inputs are more or less stressed than the fixed endpoints.
- **Anyone reading the weekly page** sees the same score, with companions kept beside it and out of the calculation.

---

## **Metrics Used in the BOI**
| **Metric** | **What It Measures** | **Source** |
|------------|----------------------|------------|
| **Inflation Rate** | Rising costs and purchasing power decline | FRED API |
| **Crime Rate** | Violent and property crime trends | RTCI (Real-Time Crime Index) |
| **Unemployment Rate** | Economic distress and job availability | FRED API |
| **Debt-to-GDP Ratio** | Government fiscal health and risk | FRED API |
| **Homelessness Rate** | Societal and economic well-being | HUD Reports |
| **Trust in Government** | Public confidence in institutions | Edelman Trust Barometer |

Each metric is **normalized** to a common scale and **weighted** based on its impact on stability. Raw weights (0.15, 0.12, 0.12, 0.12, 0.09, 0.12) sum to 0.72; after dividing by that sum, the actual shares of the index are about **20.8% / 16.7% / 16.7% / 16.7% / 12.5% / 16.7%**.

---

## **How to Use the BugOut Index**
Read the weekly score as pressure on the six published inputs.
- A move toward **Low Stability** is a reason to take the reading seriously.
- A path that stays in **Moderate Stability** is not, by itself, a bug-out signal.
- Markets, the short-term pulse, and labor utilization are companions. They are not in the score.

---

## **Future Plans**
The BugOut Index is an evolving tool, with **ongoing improvements and additional metrics planned**. Future updates may include:
- **Geographic Breakdown** (regional/state-level BOI scores).
- **Additional Indicators** (energy grid stability, food security) kept beside the headline until a versioned methodology change.
- **Automation Enhancements** (clearer freshness labeling on the weekly site).

If you have feedback or suggestions, feel free to reach out!

## **Establishing Risk Thresholds for the BugOut Index**  

The BugOut Index (BOI) is a reading of published conditions against fixed endpoints. Four risk categories match the weekly publisher:  

- **High Stability (70–100)**  
- **Moderate Stability (55–69.99)**  
- **Low Stability (40–54.99)**  
- **Critical Instability (below 40)**  

These thresholds describe gradual pressure on the published inputs. A Moderate reading is not a bug-out signal. A move toward Low is the point where the reading asks to be taken seriously.  

In setting these ranges, we considered a variety of factors, including **historical trends in economic and social stability, the distribution of past BOI scores, and the relative weight of different contributing metrics**. A threshold for **High Stability** at **70 and above** ensures that only societies with strong economic indicators, low crime, and high trust in governance achieve this rating. **Moderate Stability (55–69.99)** reflects societies where risks are emerging—there may be rising inflation, declining institutional trust, or early signs of crime trends worsening, but the overall framework remains intact.  

As the published inputs press harder, the BOI can enter **Low Stability (40–54.99)**. That band means take the reading seriously. Below this, **Critical Instability (<40)** means the published inputs sit far toward the unstable ends of their fixed ranges. That is a reading of how hard conditions are. It is not a forecast of collapse, and it is not an instruction to bug out.  

Each of these thresholds is shaped by the **relative importance of different metrics** within the BOI.  

- **Inflation (raw weight 0.15 ≈ 20.8% of the finished score)** and **crime (raw weight 0.12 ≈ 16.7%)** are among the most heavily weighted, as these factors have direct, widespread effects on economic security and personal safety.  
- **Unemployment, debt-to-GDP, and trust in government** each carry raw weight **0.12 (≈ 16.7% share)**.  
- **Homelessness** carries raw weight **0.09 (≈ 12.5% share)**.  

These relative weights ensure that while no single factor dominates the BOI, trends in multiple areas must converge before a society shifts into a new risk category.  

By structuring the thresholds this way, the BOI stays a slow reading of published conditions. It is not a forecast of societal stability. It does not react to every short-term fluctuation, and a move that lasts long enough to shift the published inputs can change the band. The four ranges are a scale for how hard those inputs are pressing.
