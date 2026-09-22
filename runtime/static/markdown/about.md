## **What is the BugOut Index?**
The **BugOut Index (BOI)** is a measure of **societal stability**, combining key economic, crime, and governance indicators into a **single numerical score**. This index is designed to provide a **weekly assessment of risk levels**, helping individuals, policymakers, and analysts understand **shifts in stability** over time.

---

## **Score Interpretation**
| **Score Range** | **Interpretation** |
|-----------------|--------------------|
| **70–100**      | High Stability (Low Risk) |
| **55–69.99**    | Moderate Stability (Warning Signs) |
| **40–54.99**    | Low Stability (Heightened Risk) |
| **Below 40**    | Critical Instability (Collapse Likely) |

A **higher BOI score** indicates **greater societal stability**, while a **lower score** signals **growing risks or breakdowns in critical systems**.

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

This index provides **a clear and quantifiable measure of risk**, helping:
- **Individuals** make informed relocation or investment decisions.
- **Businesses** assess stability for operational planning.
- **Policymakers** identify early warning signs of potential crises.

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
The BOI is designed for **practical application**, whether you are an individual, a business leader, or a policymaker. Here are a few examples:
- **Personal Preparedness:** If the BOI score is dropping, you may want to assess risks in your community.
- **Business Decisions:** Companies operating in high-risk regions can use the BOI to inform long-term planning.
- **Policy Planning:** Governments can use BOI trends to **identify early warning signs** and take corrective action.

---

## **Future Plans**
The BugOut Index is an evolving tool, with **ongoing improvements and additional metrics planned**. Future updates may include:
- **Geographic Breakdown** (regional/state-level BOI scores).
- **Additional Indicators** (energy grid stability, food security) kept beside the headline until a versioned methodology change.
- **Automation Enhancements** (clearer freshness labeling on the weekly site).

If you have feedback or suggestions, feel free to reach out!

## **Establishing Risk Thresholds for the BugOut Index**  

The BugOut Index (BOI) is designed to provide a meaningful, data-driven assessment of societal stability, allowing for clear interpretation of risks based on multiple key indicators. To ensure the BOI serves as a **practical guide for decision-making**, we have established four risk categories matching the weekly publisher:  

- **High Stability (70–100)**  
- **Moderate Stability (55–69.99)**  
- **Low Stability (40–54.99)**  
- **Critical Instability (below 40)**  

These thresholds are designed to reflect **gradual shifts in societal conditions**, avoiding premature alarm while ensuring that warning signs are recognized early enough for action.  

In setting these ranges, we considered a variety of factors, including **historical trends in economic and social stability, the distribution of past BOI scores, and the relative weight of different contributing metrics**. A threshold for **High Stability** at **70 and above** ensures that only societies with strong economic indicators, low crime, and high trust in governance achieve this rating. **Moderate Stability (55–69.99)** reflects societies where risks are emerging—there may be rising inflation, declining institutional trust, or early signs of crime trends worsening, but the overall framework remains intact.  

As risks escalate, the BOI enters **Low Stability (40–54.99),** a range that captures societies experiencing **sustained economic hardship, public unrest, rising crime, and institutional failure at multiple levels**. This is the critical transition period where nations, states, or regions may begin seeing **systemic instability**. Below this, **Critical Instability (<40)** represents conditions that **strongly indicate imminent collapse or severe societal distress**—for example, when crime and unemployment reach historic highs, inflation devalues the currency at extreme rates, and trust in government erodes to the point of mass noncompliance or rebellion.  

Each of these thresholds is shaped by the **relative importance of different metrics** within the BOI.  

- **Inflation (raw weight 0.15 ≈ 20.8% of the finished score)** and **crime (raw weight 0.12 ≈ 16.7%)** are among the most heavily weighted, as these factors have direct, widespread effects on economic security and personal safety.  
- **Unemployment, debt-to-GDP, and trust in government** each carry raw weight **0.12 (≈ 16.7% share)**.  
- **Homelessness** carries raw weight **0.09 (≈ 12.5% share)**.  

These relative weights ensure that while no single factor dominates the BOI, trends in multiple areas must converge before a society shifts into a new risk category.  

By structuring the thresholds this way, the BOI remains a **sensitive yet reliable tool** for understanding and forecasting societal stability. It does not react **too aggressively to short-term fluctuations**, but it also ensures that **prolonged negative trends are recognized and appropriately categorized**. These thresholds provide both **awareness and clarity**, offering individuals, policymakers, and analysts a **practical scale for interpreting risk and planning accordingly**.
