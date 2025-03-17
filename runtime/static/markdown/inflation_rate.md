# Inflation Rate

## **1. Description**
The **Inflation Rate** measures the rate at which the general price level of goods and services is rising, reducing purchasing power over time. It is a critical economic indicator that reflects the **cost of living, monetary stability, and economic confidence**. Persistent high inflation can lead to **reduced consumer spending, economic instability, and social unrest**, making it an essential factor in the BugOut Index.

---

## **2. Why It's Included**
Inflation affects **every level of society**, influencing economic conditions such as:
- **Cost of living increases** (housing, food, healthcare, transportation).
- **Declining purchasing power**, making wages less effective.
- **Higher interest rates**, leading to borrowing and lending challenges.
- **Potential for economic recessions** if inflation runs unchecked.

A **moderate level of inflation** is considered normal, but when inflation **rises too quickly or becomes unpredictable**, it can create economic distress.

---

## **3. Source & Attribution**
- **Primary Source:** [Federal Reserve Economic Data (FRED)](https://fred.stlouisfed.org/)
- **Data URL:** [Consumer Price Index (CPI)](https://fred.stlouisfed.org/series/CPIAUCSL)
- **Last Updated:** Data is updated **monthly**.
- **Data Collection Method:**  
  - The **Consumer Price Index (CPI-U)**, published by the **Bureau of Labor Statistics (BLS)**, is used as the standard measure of inflation.
  - FRED provides historical CPI data, which is used to calculate **year-over-year inflation**.

---

## **4. Acquisition Method**
- The **latest inflation rate** is retrieved from **FRED's CPI-U series**.
- The fetcher script queries the most recent **monthly inflation report**.
- The percentage change in **CPI over the past 12 months** is used as the **inflation rate**.

---

## **5. Calculation Details**
The **Inflation Rate** is calculated as:

```angular2html
Inflation Rate (%) = [(CPI Current - CPI Previous Year) / CPI Previous Year] * 100
```

Where:
- **CPI Current** = Latest Consumer Price Index value.
- **CPI Previous Year** = Consumer Price Index value from 12 months prior.

**Example Calculation:**
- **CPI (Current Month, 2024)** = 316.44
- **CPI (Same Month, 2023)** = 308.73
```angular2html
Inflation Rate = [(316.44 - 308.73) / 308.73] * 100
≈ 2.50%
```

---

## **6. Normalization Method**
To integrate the **Inflation Rate** into the **BugOut Index**, it must be normalized to a **0-100 scale**.

- **Normalization Range:**  
```angular2html
Min = -10% (Low/Stable Inflation)
Max = 15% (High Inflation Crisis)
```

- **Formula:**  
```angular2html
Normalized Score = (1 - (Inflation Rate - (-10)) / (15 - (-10))) * 100
```

- An **inflation rate of -10%** results in a **BOI contribution of 100 (full stability)**.
- An **inflation rate of 15% or higher** results in a **BOI contribution of 0 (critical instability)**.

---

## **7. Weighting**
- **Inflation Rate Weight in BOI:** **0.15 (15%)**
- **Justification for Weighting:**
  - Inflation **directly affects consumer confidence and economic conditions**.
  - High inflation **reduces disposable income**, affecting affordability and social stability.
  - **One of the highest-weighted factors** due to its widespread economic impact.

---

## **Summary**
The **Inflation Rate** is a fundamental economic indicator that affects **cost of living, economic stability, and financial security**. By integrating **real-time FRED data, normalizing within a reasonable range, and weighting appropriately**, the BugOut Index ensures that **rising inflation is captured as a sign of increasing instability**.