## **1. Description**
The **Debt-to-GDP Ratio** measures a country's total government debt as a percentage of its **Gross Domestic Product (GDP)**. It indicates the **government’s ability to manage its debt relative to economic output** and is a key measure of **fiscal stability and economic sustainability**.

---

## **2. Why It's Included**
Government debt can be a **leading indicator of economic instability**. A rising **Debt-to-GDP ratio** suggests that a country is accumulating debt faster than its economy is growing, potentially leading to:
- **Higher interest rates**
- **Reduced investor confidence**
- **Economic recession risks**
- **Austerity measures or government instability**
Conversely, a **declining Debt-to-GDP ratio** generally signals **stronger economic stability and fiscal health**.

---

## **3. Source & Attribution**
- **Primary Source:** [Federal Reserve Economic Data (FRED)](https://fred.stlouisfed.org/)
- **Data URL:** [Debt-to-GDP Ratio (FRED)](https://fred.stlouisfed.org/series/GFDEGDQ188S)
- **Last Updated:** Data is typically updated **quarterly**.
- **Data Collection Method:**  
  - FRED sources U.S. government debt data from the **U.S. Department of the Treasury** and GDP data from the **Bureau of Economic Analysis (BEA)**.

---

## **4. Acquisition Method**
- The latest **Debt-to-GDP ratio** is retrieved using the **FRED API**.
- The fetcher script queries the most recent **quarterly release** and extracts the Debt-to-GDP percentage.
- The value is then **stored locally** and used in BugOut Index calculations.

---

## **5. Calculation Details**
The **Debt-to-GDP Ratio** is calculated using:

```
Debt-to-GDP Ratio = (Total Public Debt / Gross Domestic Product) * 100
```

Where:
- **Total Public Debt** = Sum of all outstanding government liabilities.
- **GDP** = Total economic output for the same period.
- The ratio is expressed as a **percentage**.

**Example Calculation:**
- **Total Public Debt:** $34 trillion
- **GDP:** $27 trillion

```
Debt-to-GDP Ratio = (34 / 27) * 100 = 125.9%
```

---

## **6. Normalization Method**
To integrate the **Debt-to-GDP Ratio** into the **BugOut Index**, it must be normalized to a **0-100 scale**.

- **Normalization Range:**  

```angular2html
Min = 0% (No Debt)
Max = 200% (Extreme Debt Burden)
```

- **Formula:**  

```angular2html
Normalized Score = (1 - (Debt-to-GDP - 0) / (200 - 0)) * 100
```

- A **Debt-to-GDP ratio of 0%** results in a **BOI contribution of 100 (full stability)**.
- A **Debt-to-GDP ratio of 200%** results in a **BOI contribution of 0 (critical instability)**.

---

## **7. Weighting**
- **Debt-to-GDP Ratio Weight in BOI:** **0.12 (12%)**
- **Justification for Weighting:**
  - While important, the **Debt-to-GDP ratio does not create immediate instability**, unlike crime or inflation.
  - However, sustained high debt levels **increase long-term economic risk** (e.g., recession, inflation, currency devaluation).
  - **Moderate weight ensures it influences BOI trends without over-dominating short-term economic indicators.**

---

## **Summary**
The **Debt-to-GDP Ratio** is a critical measure of **government fiscal health**, influencing investor confidence, inflation risk, and economic stability. By integrating **real-time FRED data, normalizing within a reasonable risk range, and weighting appropriately**, the BugOut Index ensures that **rising national debt is factored into overall stability assessments.**