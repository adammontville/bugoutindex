## **1. Description**
The **Crime Rate** metric measures the prevalence of criminal activity in a society, encompassing both **violent crime** (e.g., murder, robbery, aggravated assault) and **property crime** (e.g., burglary, theft, motor vehicle theft). It serves as a key indicator of **societal stability and personal security**, directly affecting public perception of safety and governance.

---

## **2. Why It's Included**
Crime is one of the most **visible and immediate indicators of societal distress**. Rising crime rates can signal **economic instability, weakening law enforcement, and growing unrest**, while declining crime rates suggest **effective governance and a stable social order**. The **BugOut Index (BOI)** integrates crime data to track **shifts in public safety** that could contribute to broader instability.

---

## **3. Source & Attribution**
- **Primary Source:** [Real-Time Crime Index (RTCI)](https://realtimecrimeindex.com/)
- **Data file:** [AH-Datalytics/rtci `docs/app_data/final_sample.csv` on main](https://raw.githubusercontent.com/AH-Datalytics/rtci/main/docs/app_data/final_sample.csv) (raw CSV, not a GitHub blob page). Repository: [AH-Datalytics/rtci](https://github.com/AH-Datalytics/rtci).
- **Last Updated:** RTCI refreshes the cleaned file on its own cadence. Each weekly run scores the latest calendar month in the file it downloads that week.
- **Data Collection Method:** RTCI aggregates data from **500 law enforcement agencies**, most of which use **state-level Uniform Crime Reporting (UCR) standards**.

---

## **4. Acquisition Method**
- The weekly publisher downloads the RTCI cleaned sample from the raw URL above via `download_crime_rate_data.py`, then `fetch_incident_rate.py` reads it.
- A download that is empty, HTML, or not the RTCI CSV fails the crime fetcher. A latest month with no usable national rate fails it too. The weekly job then refuses to publish. It does not carry the previous crime value forward, and it does not invent an observation date.
- The scored month is the **latest calendar month** in the file. RTCI stores `Date` as a month name (`April 2026`) and also stores numeric `Month` and `Year`. The fetcher parses those fields. It does not take `Date.max()`, which is a text sort: "September" sorts after "April" and "December".
- The scored rate is RTCI’s **Nationwide Full Sample** row for that month (Agency `Full Sample`, State `Nationwide`): violent-plus-property 12-month counts divided by `FBI.Population.Covered`, times 100,000. The row is used when it is the only such row, the counts are usable, and the rate is within 0.02 of the population-weighted total of the other usable rows. On the file the weekly job downloads, those two figures match exactly, so the row is the input. If the row is missing, duplicated, or outside that tolerance, the population-weighted total is scored instead, and the snapshot records which one was used.
- The unweighted mean of usable rows stays in the diagnostics. That mean, including RTCI aggregate rows, is the construction behind the methodology 1.0.0 lock of **2723.0**. It is not the 1.1.0 input.
- The observation date is the last day of the scored month (`2026-04-30` for April 2026). It is parsed from the file. Weeks published under 1.0.0 are not given a new date.
- Coverage is the Real-Time Crime Index sample. The Nationwide Full Sample is population-weighted inside that sample. It is not a census of every U.S. agency.

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
   - Since RTCI does not cover the entire U.S., the **national figure is the Nationwide Full Sample rate** for the latest calendar month: the population-weighted total of violent-plus-property crime in the RTCI sample. The unweighted mean of agency and aggregate rows is stored beside it and is not the index input. Methodology 1.0.0 used a locked unweighted print of **2723.0**. Weeks through 2026-10-02 keep that print.

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
The **Crime Rate** metric provides a public-safety input based on **violent plus property** crime in the RTCI sample. Methodology 1.1.0 updates it from the Nationwide Full Sample rate for the latest month in the file. By normalizing on **500–8,000 per 100k** and weighting at **0.12 / 0.72**, the BugOut Index reflects that rate in line with the weekly publisher.
