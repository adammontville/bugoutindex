# Unemployment Rate

## **1. Description**
The **Unemployment Rate** measures the percentage of the labor force that is actively seeking but unable to find work. It is a key economic indicator that reflects the **health of the job market, economic stability, and overall financial well-being of a population**. 

A rising unemployment rate can signal **economic distress, declining consumer confidence, and potential recession**, while a low unemployment rate suggests **a stable economy with job opportunities**.

---

## **2. Why It's Included**
Unemployment is a **direct measure of economic health and stability**. A persistently high unemployment rate can lead to:
- **Reduced consumer spending**, slowing economic growth.
- **Increased demand for social assistance programs**, straining government resources.
- **Higher crime rates**, as economic hardship can drive instability.
- **Political and social unrest**, particularly if job losses are widespread.

By including **Unemployment Rate** in the **BugOut Index**, we capture **the economic strain on individuals and communities**, helping to assess overall stability.

---

## **3. Source & Attribution**
- **Primary Source:** [Federal Reserve Economic Data (FRED)](https://fred.stlouisfed.org/)
- **Data URL:** [U.S. Unemployment Rate (FRED)](https://fred.stlouisfed.org/series/UNRATE)
- **Last Updated:** Data is updated **monthly**.
- **Data Collection Method:**  
  - The **Bureau of Labor Statistics (BLS)** publishes the **official U.S. unemployment rate** based on household surveys.
  - FRED provides a standardized, historical record of these unemployment figures.

---

## **4. Acquisition Method**
- The **latest unemployment rate** is retrieved from **FRED’s "UNRATE" series** via an API request.
- The fetcher script extracts the most recent **monthly unemployment percentage**.
- The value is then **stored locally** and used in BugOut Index calculations.

---

## **5. Calculation Details**
The **Unemployment Rate** is calculated as:
```angular2html
Unemployment Rate (%) = (Unemployed Individuals / Total Labor Force) * 100
```

Where:
- **Unemployed Individuals** = People without a job who are actively seeking employment.
- **Total Labor Force** = All employed and unemployed individuals willing and able to work.

**Example Calculation:**
- **Total Unemployed:** 6,600,000
- **Total Labor Force:** 160,000,000

```angular2html
Unemployment Rate = (6,600,000 / 160,000,000) * 100
≈ 4.13%
```

---

## **6. Normalization Method**
To integrate the **Unemployment Rate** into the **BugOut Index**, it must be normalized to a **0-100 scale**.

- **Normalization Range:**  

```angular2html
Min = 0% (Full Employment)
Max = 20% (Severe Unemployment Crisis)
```

- **Formula:**  
```angular2html
Normalized Score = (1 - (Unemployment Rate - 0) / (20 - 0)) * 100
```

- An **unemployment rate of 0%** results in a **BOI contribution of 100 (full stability)**.
- An **unemployment rate of 20% or higher** results in a **BOI contribution of 0 (critical instability)**.

---

## **7. Weighting**
- **Unemployment Rate Weight in BOI:** **0.10 (10%)**
- **Justification for Weighting:**
  - Unemployment is a **key driver of economic instability**.
  - It **correlates with other factors**, such as crime, homelessness, and social unrest.
  - **Moderate weight ensures unemployment significantly influences BOI scores**, without overshadowing short-term economic or crime-related trends.

---

## **Summary**
The **Unemployment Rate** is a fundamental indicator of **economic health, workforce stability, and financial security**. By integrating **real-time FRED data, normalizing within a reasonable range, and weighting appropriately**, the BugOut Index ensures that **rising unemployment is captured as a sign of increasing instability**.