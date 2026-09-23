## **1. Description**
The **Homelessness Rate** measures the percentage of the population experiencing homelessness at a given time. It serves as a critical indicator of **economic distress, housing affordability, and social stability**. Rising homelessness rates suggest **worsening economic conditions, lack of affordable housing, and potential failures in social safety nets**, making this metric a key component of the BugOut Index.

---

## **2. Why It's Included**
Homelessness is both a **social and economic stability indicator**. A rising homelessness rate is often correlated with:
- **Economic downturns**
- **Housing market instability**
- **High inflation and unemployment**
- **Reduced effectiveness of government support programs**

Including this metric in the **BugOut Index** provides insight into the broader effects of economic and policy changes on vulnerable populations.

---

## **3. Source & Attribution**
- **Primary Source:** [U.S. Department of Housing and Urban Development (HUD)](https://www.huduser.gov/)
- **Data URL:** [HUD Exchange - PIT Count](https://www.hudexchange.info/programs/hdx/pit-hic/)
- **Last Updated:** Data is updated **annually**, with the latest report from **2024**.
- **Data Collection Method:**  
  - The **Point-in-Time (PIT) Count**, conducted **every January**, provides a nationwide estimate of sheltered and unsheltered homeless populations.
  - Data is compiled into the **Annual Homeless Assessment Report (AHAR)**.

---

## **4. Acquisition Method**
- The weekly fetcher reads the `homelessness_rate` row of `runtime/data/annual_inputs.csv`.
- HUD does not provide a real-time API. A person updates that row once a year, using the steps in `runtime/data/ANNUAL_INPUTS.md`.
- The published value remains **0.23%** from the **2024** AHAR. The HUD reference date on that row is **2024-01-01**.
- The weekly job copies `reviewed_at` from the row. It does not invent a fetch timestamp.

---

## **5. Calculation Details**
The **Homelessness Rate** is calculated as:

```angular2html
Homelessness Rate (%) = (Total Homeless Population / Total U.S. Population) * 100
```

Where:
- **Total Homeless Population (2024)** = 771,480
- **Total U.S. Population Estimate (2024)** = 335,000,000

**Example Calculation:**

```angular2html
Homelessness Rate = (771,480 / 335,000,000) * 100
≈ 0.23%
```

---

## **6. Normalization Method**
To integrate the **Homelessness Rate** into the **BugOut Index**, it must be normalized to a **0-100 scale**.

- **Normalization Range:**  

```angular2html
Min = 0% (No homelessness)
Max = 0.5% (Severe homelessness crisis)
```

- **Formula:**  

```angular2html
Normalized Score = (1 - (Homelessness Rate - 0) / (0.5 - 0)) * 100
```

- A **homelessness rate of 0%** results in a **BOI contribution of 100 (full stability)**.
- A **homelessness rate of 0.5% or higher** results in a **BOI contribution of 0 (critical instability)**.

---

## **7. Weighting**
- **Raw weight in BOI:** **0.09**
- **Share of the finished index:** **0.09 / 0.72 = 12.50%** (raw weights sum to 0.72; the publisher divides by that sum)
- **Justification for Weighting:**
  - Homelessness is a **direct measure of economic hardship and social breakdown**.
  - Higher homelessness rates indicate **severe economic distress** and **a failure in public services**.
  - While critical, it is **not as immediate a crisis factor as inflation or crime**, leading to a **moderate weighting in the index**.

---

## **Summary**
The **Homelessness Rate** provides a crucial indicator of **economic and social well-being**, offering insight into the effectiveness of public policies and economic conditions. By integrating **authoritative HUD data**, normalizing on **0–0.5%**, and weighting at **0.09 / 0.72**, the BugOut Index reflects rising homelessness as lower stability — matching the weekly publisher.