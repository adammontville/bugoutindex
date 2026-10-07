# Gallup confidence in institutions — companion only

The weekly publisher shows Gallup’s current annual confidence readings as a shadow companion. They are labeled **not in the BugOut Index**. They have **no weight**, and they are not inputs to `compute_index` or `CORE_METRICS`. A failed checklist read does not abort the publish. When a previous block exists, that block is carried forward with its survey date.

This note is the issue [#81](https://github.com/adammontville/bugoutindex/issues/81) companion for trust frequency. It does not change the live score.

## What stays in the score

Edelman Trust Barometer, United States, Government, remains the annual trust anchor. The published input is still **41** for survey year **2025**, read from `runtime/data/annual_inputs.csv`. Methodology version stays **1.0.0**.

## What this companion is

| | |
| --- | --- |
| Publisher | Gallup |
| Series home | [Confidence in Institutions](https://news.gallup.com/poll/1597/confidence-institutions.aspx) |
| Current article | [Confidence in U.S. Institutions Remains Near All-Time Low](https://news.gallup.com/poll/712436/confidence-institutions-remains-near-time-low.aspx) (July 13, 2026) |
| Value | “A great deal” plus “quite a lot” |
| Poll | June 1–15, 2026. Observation date `2026-06-15` |
| Congress | **9** |
| The presidency | **27** |
| U.S. Supreme Court | **27** |
| 14 institutions since 1993 | **27** |
| Cadence | Annual, typically June |
| Checklist | `runtime/data/gallup_confidence_shadow.csv` |

The 14-institution average is the one Gallup describes as measured each year since 1993. It is not the nine-institution average. In 2026 both averages printed 27; the checklist stores the 14-institution figure because that is the average in the cited article’s lead.

The file has one row per series. It is not Gallup’s historical table. The weekly job does not scrape Gallup. Continuous republication of Gallup data may require permission, so the checklist stays a current cited reading that a person replaces once a year.

## How it differs from Edelman

Edelman is one government-trust percent for a survey year. Gallup asks about named institutions, adds “a great deal” and “quite a lot,” and publishes an annual June poll with a fieldwork window. Congress at 9, the presidency at 27, and Edelman at 41 are different questions. They are not substitutes.

## How to update

Follow `runtime/data/TRUST_SHADOWS.md` when Gallup publishes the next annual update. Replace the four rows. Do not append prior years.

## Recommendation

**Add as a shadow/companion. Keep the Edelman checklist for the score.** A later methodology version would be required before any of these series could enter `compute_index`.
