# Trust in Government

## **1. Description**
The **Trust in Government** metric measures public confidence in key government institutions. It reflects how much people believe their government is competent, transparent, and acting in their best interests. **Higher trust in government typically indicates greater stability**, while **declining trust can signal unrest, governance failures, or weakening institutional legitimacy**.

---

## **2. Why It's Included**
Public trust in government is a **leading indicator of societal stability**. A decline in trust often **precedes unrest, protests, political crises, and institutional breakdowns**. This metric helps assess:
- **Confidence in leadership and institutions** (executive, legislative, and judicial branches).
- **Public willingness to comply with laws, policies, and government directives**.
- **Potential for civil unrest, protests, or political upheaval**.

A high level of trust indicates **strong institutional stability**, while low trust **suggests growing discontent and possible instability**.

---

## **3. Source & Attribution**
- **Primary Source:** [Edelman Trust Barometer](https://www.edelman.com/trust-barometer)
- **Data URL:** [Edelman Trust Interactive Module](https://infogr8.github.io/edelman-trust-institute-interactive-module/)
- **Last Updated:** Data is updated **annually**.
- **Data Collection Method:**  
  - The **Edelman Trust Barometer** conducts surveys in multiple countries, including the U.S.
  - Trust in government is measured as the **percentage of respondents who express confidence** in government institutions.

---

## **4. Acquisition Method**
- The **latest trust score** is retrieved from **Edelman’s dataset**.
- The fetcher script extracts **the latest available year** for the "Government" category.
- The score is then **stored locally** and used in BugOut Index calculations.

---

## **5. Calculation Details**
The **Trust in Government** score is provided as a **percentage (0-100%)** of people expressing confidence in government institutions.

The metric is calculated as follows:

```angular2html
Trust Score (%) = Percentage of respondents expressing confidence in government
```

Since trust in government is **inversely related to instability**, we **invert** the value to reflect **distrust**:

```angular2html
Distrust Score (%) = 100 - Trust Score
```

**Example Calculation:**
- **Edelman Trust Score (2025):** 41%
```angular2html
Distrust Score = 100 - 41
= 59%
```

This **distrust score** is then normalized within the BugOut Index.

---

## **6. Normalization Method**
To integrate **Trust in Government** into the **BugOut Index**, it must be normalized to a **0-100 scale**.

- **Normalization Range:**  

```angular2html
Min = 0% (Full Trust in Government)
Max = 80% (Widespread Distrust)
```

- **Formula:**  

```angular2html
Normalized Score = (1 - (Distrust Score - 0) / (80 - 0)) * 100
```

- A **distrust score of 0% (high trust)** results in a **BOI contribution of 100 (full stability)**.
- A **distrust score of 80% or higher** results in a **BOI contribution of 0 (critical instability)**.

---

## **7. Weighting**
- **Trust in Government Weight in BOI:** **0.12 (12%)**
- **Justification for Weighting:**
  - Trust in government **is a strong predictor of political and social stability**.
  - **Moderate weight ensures trust trends impact BOI scores**, but do not dominate over economic or crime-related factors.
  - Helps capture **long-term instability risks** (e.g., erosion of democracy, growing civil disobedience).

---

## **Summary**
The **Trust in Government** metric provides a key indicator of **institutional stability, governance effectiveness, and public confidence**. By integrating **annual Edelman Trust data, normalizing within a reasonable range, and weighting appropriately**, the BugOut Index ensures that **rising distrust in government is accurately reflected as a sign of increasing instability**.