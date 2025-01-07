**Disclaimer**: This metric is part of the "Incubating" section of the BugOutIndex and is under development. Content is experimental, subject to change, and not finalized. Redistribution or use without explicit permission is prohibited.
# Epidemic Spread Index (ESI)

## Description
The Epidemic Spread Index (ESI) is designed to assess the severity and spread potential of an epidemic or pandemic. This metric is supplemental to the core BugOutIndex and is dynamically activated when a new epidemic arises.

## Key Components
- **Spread Potential (R0):** Measures how easily the disease spreads.
- **Severity (Case Fatality Rate):** Indicates the lethality of the disease.
- **Healthcare Strain (Hospitalization Rate):** Reflects the impact on healthcare systems.
- **Geographic Spread:** Assesses the extent of international or regional spread.
- **Response Capacity (Vaccination Rates):** Captures the effectiveness of vaccination campaigns.
- **Public Compliance (Test Positivity Rate):** Reflects testing adherence and public cooperation.

## Formula
The Epidemic Spread Index is calculated as a weighted combination of its components:
```
ESI = w1 * (R0 / R0_threshold) + w2 * (CFR / CFR_threshold) + w3 * (Hospitalization Rate / Hospitalization Threshold) + ...
```

## Usage
This metric is calculated separately and displayed alongside the BugOutIndex during health crises.

## Considerations
- Historical data from previous pandemics can help define thresholds and weights.
- Real-time data sources, such as WHO and CDC updates, are critical for timely calculations.
- The metric can be extended to include additional components as needed.

---
