## **1. Description**
The **Crime Rate** metric measures the prevalence of criminal activity in a society, encompassing both **violent crime** (e.g., murder, robbery, aggravated assault) and **property crime** (e.g., burglary, theft, motor vehicle theft). It serves as a key indicator of **societal stability and personal security**, directly affecting public perception of safety and governance.

---

## **2. Why It's Included**
Crime is one of the most **visible and immediate indicators of societal distress**. Rising crime rates can signal **economic instability, weakening law enforcement, and growing unrest**, while declining crime rates suggest **effective governance and a stable social order**. The **BugOut Index (BOI)** integrates crime data to track **shifts in public safety** that could contribute to broader instability.

---

## **3. Source & Attribution**
- **Primary Source:** [Real-Time Crime Index (RTCI)](https://realtimecrimeindex.com/)
- **Data file:** [AH-Datalytics/rtci `docs/app_data/final_sample.csv` on main](https://raw.githubusercontent.com/AH-Datalytics/rtci/main/docs/app_data/final_sample.csv) (raw CSV, not a GitHub blob page). Repository: [AH-Datalytics/rtci](https://github.com/AH-Datalytics/rtci).
- **Last Updated:** RTCI refreshes the cleaned file on its own cadence. The weekly job records that file’s latest month. The published index input stays **2723.0** until a reviewed revision accepts a new rate.
- **Data Collection Method:** RTCI aggregates data from **500 law enforcement agencies**, most of which use **state-level Uniform Crime Reporting (UCR) standards**.

---

## **4. Acquisition Method**
- The weekly publisher downloads the RTCI cleaned sample from the raw URL above via `download_crime_rate_data.py`, then `fetch_incident_rate.py` reads it.
- A download that is empty, HTML, or not the RTCI CSV fails the crime fetcher. The weekly job then refuses to publish. It does not treat that body as a successful crime reading.
- The diagnostic month is the **latest calendar month** in the file. RTCI stores `Date` as a month name (`April 2026`) and also stores numeric `Month` and `Year`. The fetcher parses those fields. It does not take `Date.max()`, which is a text sort: "September" sorts after "April" and "December".
- The fetcher computes an **unweighted mean of usable rows** of violent-plus-property rates on a **per 100,000 people** basis (12-month moving sums in the file) and a population-weighted alternative. Both are **diagnostic fields**. They are not inputs to `compute_index`.
- A row is usable when both 12-month counts are present and `FBI.Population.Covered` is positive. The cleaned file also contains RTCI **aggregate rows** (state and nationwide Full Sample, and population-band aggregates). Those rows are included. Each usable row counts once, so a small agency counts the same as a large one, and an aggregate row counts the same as an agency row. That is the construction behind the locked **2723.0** (399 usable rows on the old local file, September 2024) and the current-file diagnostics (621 usable rows). Dropping the aggregate rows would change the rate. This note does not do that.
- The population-weighted alternative is the sum of violent-plus-property counts divided by the sum of population on those same rows. On the cleaned file it matches RTCI's Nationwide Full Sample rate. It is not the candidate.
- The headline crime input remains the locked **2723.0** until that diagnostic is accepted in a later reviewed change.
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
   - Since RTCI does not cover the entire U.S., the **national figure is the unweighted mean of usable rows** in the latest calendar month (agency rows and RTCI aggregate rows together). It is not the population-weighted Nationwide Full Sample rate. That weighted total is stored beside the candidate and is not the index input.

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
