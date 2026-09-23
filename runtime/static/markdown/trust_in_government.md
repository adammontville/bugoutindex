## **1. Description**
The **Trust in Government** metric measures public confidence in key government institutions. It reflects how much people believe their government is competent, transparent, and acting in their best interests. **Higher trust in government typically indicates greater stability**, while **declining trust can signal unrest, governance failures, or weakening institutional legitimacy**.

This is the **core** BugOut Index input from the Edelman Trust Barometer. It is distinct from the incubating **Government Authoritarianism Index**, which is not part of the v1.0.0 score.

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
- The weekly fetcher reads the `trust_in_government` row of `runtime/data/annual_inputs.csv`.
- The published value remains **41** for Edelman survey year **2025**. The observation is that year only. The row does not store a month or day.
- `runtime/data/edelman-trust-barometer-us.csv` is a historical archive. A new year column in that file does not change the score.
- A person updates the checklist row once a year, using the steps in `runtime/data/ANNUAL_INPUTS.md`. The weekly job copies `reviewed_at` from the row and does not invent a fetch timestamp.

---

## **5. Calculation Details**
The **Trust in Government** score is provided as a **percentage (0–100%)** of people expressing confidence in government institutions.

```
Trust Score (%) = Percentage of respondents expressing confidence in government
```

The publisher uses this trust percent **directly** as the raw input. It does **not** convert to a distrust score first.

**Example (2025 Edelman reading used in the live score):**
- **Trust Score:** 41%

---

## **6. Normalization Method**
To integrate **Trust in Government** into the **BugOut Index**, it is normalized to a **0–100 scale** with endpoints **0 to 80** and `inverse=True` (higher trust → higher stability).

In `weekly_run.normalize`, the default transform is:

```
normalized = (1 − (raw − min) / (max − min)) × 100
```

With `inverse=True`, the result is flipped (`100 − normalized`). For the 0–80 trust window that is equivalent to:

```
normalized = ((Trust Score − 0) / (80 − 0)) × 100
```

- A **trust score of 0%** results in a **normalized score of 0** (critical instability).
- A **trust score of 80% or higher** results in a **normalized score of 100** (full stability), after clamping.
- **Worked example:** trust **41** → **51.25**.

```
normalized = (41 / 80) × 100 = 51.25
```

---

## **7. Weighting**
- **Raw weight in BOI:** **0.12**
- **Share of the finished index:** **0.12 / 0.72 ≈ 16.67%** (raw weights sum to 0.72; the publisher divides by that sum)
- **Justification for Weighting:**
  - Trust in government **is a strong predictor of political and social stability**.
  - **Moderate weight ensures trust trends impact BOI scores**, but do not dominate over economic or crime-related factors.
  - Helps capture **long-term instability risks** (e.g., erosion of democracy, growing civil disobedience).

---

## **Summary**
The **Trust in Government** metric provides a key indicator of **institutional stability, governance effectiveness, and public confidence**. By integrating **annual Edelman Trust data**, mapping the trust percent linearly on **0–80** with inversion, and weighting at **0.12 / 0.72**, the BugOut Index reflects declining institutional confidence as lower stability — matching the weekly publisher.
