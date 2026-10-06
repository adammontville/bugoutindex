# Pew public trust in government — companion only

The weekly publisher shows one Pew series as a shadow companion. It is labeled **not in the BugOut Index**. It has **no weight**, and it is not an input to `compute_index` or `CORE_METRICS`. A failed checklist read does not abort the publish. When a previous block exists, that block is carried forward with its survey date.

This note is the issue [#81](https://github.com/adammontville/bugoutindex/issues/81) companion for trust frequency. It does not change the live score.

## What stays in the score

Edelman Trust Barometer, United States, Government, remains the annual trust anchor. The published input is still **41** for survey year **2025**, read from `runtime/data/annual_inputs.csv`. Methodology version stays **1.0.0**.

## What this companion is

| | |
| --- | --- |
| Publisher | Pew Research Center |
| Article | [Public Trust in Government: 1958–2025](https://www.pewresearch.org/politics/2025/12/04/public-trust-in-government-1958-2025/) |
| Question | Trust the government in Washington to do what is right |
| Value | Share answering just about always or most of the time (the combined figure on Pew’s chart) |
| Latest stored wave | September 22–28, 2025, chart date 2025-09-28, **17%** |
| Cadence | Irregular |
| Checklist | `runtime/data/pew_trust_shadow.csv` |

The checklist also keeps a short excerpt of the May 2024 wave (**22%**, chart date 2024-05-19) and the February 2025 wave (**17%**, chart date 2025-02-09). That is not the 1958–2025 archive. The weekly job does not download Pew’s CSV.

## How it differs from Edelman

Edelman is the percent who trust government in the Trust Barometer, stored as a survey year with no month or day. Pew is a different question, a different sample, and an irregular wave with a fieldwork window. **17 and 41 are not interchangeable.** Substituting the Pew share for the Edelman input would change the score without a methodology version. That is why this series sits beside the index.

## How to update

Follow `runtime/data/TRUST_SHADOWS.md` when Pew publishes a new wave.

## Recommendation

**Add as a shadow/companion. Keep the Edelman checklist for the score.** A later methodology version would be required before this series could enter `compute_index`.
