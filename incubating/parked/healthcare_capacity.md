# Healthcare Capacity

**Status: PARKED** (Adam Montville, 2026-09-23). Off the active incubating list. Not near-term work. Not in the BugOut Index. `fetch_healthcare_capacity` is fail-closed (`NOT_WIRED`) and the weekly publisher does not call it.

The note below is the original stub. Hospital-bed and ICU snapshots matter in a health crisis. They are not a standing weekly input, and this essay never defined a national series the publisher could cite.

## Description
Healthcare capacity measures the ability of healthcare systems to meet routine and emergency demands, including hospital bed availability, ICU capacity, and staffing levels.

## Data Source
- **Primary Source**: HHS Protect Public Data Hub ([https://protect-public.hhs.gov/](https://protect-public.hhs.gov/))
- **Alternative Sources**: WHO Global Health Observatory, CMS data.

## Normalization
- **Range**: 0 (Low capacity) to 100 (High capacity)
- **Formula**:
