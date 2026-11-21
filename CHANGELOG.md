# Changelog

## Unreleased

### Fixed

- Weekly publish no longer fails when FRED returns `.` or an empty observation. Those rows are missing values. They are skipped for every FRED series used by the core metrics, the companions, and the dollar index. Year-over-year CPI (`CPIAUCSL`) is computed from the latest month that has a real index and a real index twelve months earlier, and that month is the observation date. If the comparison month is missing, the fetcher steps back to the newest month where both exist. It does not interpolate. `methodology_version`, weights, and endpoints are unchanged. The 2026-11-13 and 2026-11-20 publishes failed because `2025-10-01` is `.`, so the October 2026 index had no year-ago comparison (`could not convert string to float: '.'`).
