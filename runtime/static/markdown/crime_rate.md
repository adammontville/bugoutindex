## **1. Description**
The **Crime Rate** metric measures the prevalence of criminal activity in a society, encompassing both **violent crime** (e.g., murder, robbery, aggravated assault) and **property crime** (e.g., burglary, theft, motor vehicle theft). It serves as a key indicator of **societal stability and personal security**, directly affecting public perception of safety and governance.

---

## **2. Why It's Included**
Crime is one of the most **visible and immediate indicators of societal distress**. Rising crime rates can signal **economic instability, weakening law enforcement, and growing unrest**, while declining crime rates suggest **effective governance and a stable social order**. The **BugOut Index (BOI)** integrates crime data to track **shifts in public safety** that could contribute to broader instability.

---

## **3. Source & Attribution**
- **Primary Source:** [Real-Time Crime Index (RTCI)](https://realtimecrimeindex.com/)
- **Data URL:** [RTCI GitHub Repository](https://github.com/AH-Datalytics/rtci/blob/development/data/final_sample.csv)
- **Last Updated:** Updated approximately **monthly**, with data spanning **2018 to November 2024**.
- **Data Collection Method:** RTCI aggregates data from **500 law enforcement agencies**, most of which use **state-level Uniform Crime Reporting (UCR) standards**.

---

## **4. Acquisition Method**
- The weekly publisher reads a local RTCI sample file (`runtime/data/final_sample.csv`) via `fetch_incident_rate.py`.
- The fetcher computes an **unweighted mean** across reporting agencies of violent-plus-property rates on a **per 100,000 people** basis (typically using a 12-month moving average when available).
- Coverage is the Real-Time Crime Index sample, not a population-weighted national census of every agency.

---

## **5. Calculation Details**
The **Crime Rate** is calculated using the following approach:

1. **Extract Violent & Property Crime Data**
   - `Violent Crime` = **Murder + Rape + Robbery + Aggravated Assault**
   - `Property Crime` = **Burglary + Theft + Motor Vehicle Theft**
   - `Total Crime` = **Violent Crime + Property Crime**

2. **Adjust for Population Size**
   - The dataset includes `FBI.Population.Covered`, which represents the **total population of areas reporting crime**.
   - The crime rate is then calculated **per 100,000 people**:
     ```
     Crime Rate = (Total Crime / Population Covered) * 100,000
     ```

3. **Smoothing with a Moving Average**
   - If available, a **12-month moving average (`mvs_12mo`)** is used instead of raw monthly counts to account for **seasonal variations and reporting delays**.

4. **National Crime Rate Estimation**
   - Since RTCI does not cover the entire U.S., the **national average is computed from the available dataset** by averaging reported crime rates across all agencies.

---

## **6. Normalization Method**
To integrate the **Crime Rate** into the **BugOut Index**, it must be normalized to a **0-100 scale**.

- **Normalization Range:**  

```angular2html
Min = 500 (low crime)
Max = 8000 (high crime)
```

- **Formula:**  
```angular2html
Normalized Score = (1 - (Crime Rate - 500) / (8000 - 500)) * 100
```

- A **crime rate of 500 per 100k** results in a **BOI contribution of 100 (full stability)**.
- A **crime rate of 8000 per 100k** results in a **BOI contribution of 0 (critical instability)**.

---

## **7. Weighting**
- **Raw weight in BOI:** **0.12**
- **Share of the finished index:** **0.12 / 0.72 ≈ 16.67%** (raw weights sum to 0.72; the publisher divides by that sum)
- **Justification for Weighting:**
  - Crime has a **direct impact on public perception of safety**.
  - Affects **business investment, migration patterns, and governance stability**.
  - Heavily weighted but **balanced against economic indicators** (e.g., inflation, unemployment).

---

## **Summary**
The **Crime Rate** metric provides a weekly public-safety input based on **violent plus property** crime in the RTCI sample. By normalizing on **500–8,000 per 100k** and weighting at **0.12 / 0.72**, the BugOut Index reflects crime fluctuations in line with the weekly publisher.
