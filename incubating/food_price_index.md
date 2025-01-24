# Food Price Index (FPI)

## Description
The Food Price Index (FPI) measures the cost of food relative to a baseline, providing insights into food affordability and accessibility. It is a critical indicator of economic stability, particularly for low-income populations, and can signal the risk of food insecurity during inflationary periods or supply chain disruptions.

## Data Source
- **Primary Source**: The U.S. Bureau of Labor Statistics (BLS) Consumer Price Index (CPI) food component.
- **Alternative Sources**:
  - United Nations Food and Agriculture Organization (FAO) Food Price Index.
  - USDA Economic Research Service.

## Normalization
- **Range**: 0% (Stable food prices) to 10% (Significant food inflation).
- **Formula**:

Normalized Score = (1 - (Food Inflation Rate / 10)) * 100

## Purpose
The FPI is used to track affordability and accessibility of food, particularly in times of economic instability. Sharp increases in food prices often precede societal unrest and highlight the vulnerability of supply chains.

## Draft Status
This metric is part of the "incubating" section of the BugOutIndex and is under active development. The content here is experimental and subject to significant change. It does not represent finalized work or an official stance.

**Disclaimer**: Redistribution or use without explicit written permission is prohibited.