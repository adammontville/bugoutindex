# Trust shadow checklists

Pew public trust and Gallup confidence in institutions sit beside the BugOut Index. They are not inputs. `compute_index` does not read them. They have no weight. The scored trust input stays the Edelman row in [`annual_inputs.csv`](annual_inputs.csv): **41**, survey year **2025**.

These levels are not interchangeable with that 41. A new Pew wave or a new Gallup year does not change the live score. Issue [#81](https://github.com/adammontville/bugoutindex/issues/81) tracks whether a more frequent public series should ever replace the annual core inputs. That decision is a later methodology version.

The weekly job reads the two files below. It does not download Pew or Gallup. A missing file, a missing series, a blank value, or a bad date fails that companion. The index still publishes. When a previous block exists, that block is carried forward with its survey date.

## Pew public trust

File: [`pew_trust_shadow.csv`](pew_trust_shadow.csv).

Series: Pew Research Center, [Public Trust in Government: 1958–2025](https://www.pewresearch.org/politics/2025/12/04/public-trust-in-government-1958-2025/). The value is the share who trust the government in Washington to do what is right **just about always or most of the time** — the combined figure Pew prints on that chart, not a sum recomputed from the topline.

Cadence: irregular. Do this when Pew publishes a new wave. Skip the week if there is no new wave.

The file is a short excerpt of recent Pew waves (the current rows are May 2024 **22**, February 2025 **17**, and September 2025 **17**). Do not paste the 1958–2025 archive, and do not commit Pew’s downloadable CSV. Excerpts are stored with attribution. The weekly job does not fetch that file.

1. Open the new Pew public-trust article and read the chart’s individual-poll figure for “just about always / most of the time.”
2. Append one `pew_public_trust` row. Leave the older excerpt rows unless you are replacing a corrected figure.
3. Set `value` to the whole-number percent Pew prints.
4. Set `observation_period` to the fieldwork window, such as `September 22-28 2025`.
5. Set `observation_date` to the last day of that window (`YYYY-MM-DD`). Do not use the day you opened the page, and do not use the article’s publication date.
6. Set `source` to a short citation and `source_url` to the article URL.
7. Set `reviewed_at` to the calendar date you checked the source (`YYYY-MM-DD`). It must not be earlier than `observation_date`.

Keep at most 12 rows. A longer file fails the companion fetch.

## Gallup confidence in institutions

File: [`gallup_confidence_shadow.csv`](gallup_confidence_shadow.csv).

Series: Gallup [Confidence in Institutions](https://news.gallup.com/poll/1597/confidence-institutions.aspx). The current rows were read from the [July 13, 2026 article](https://news.gallup.com/poll/712436/confidence-institutions-remains-near-time-low.aspx) for the June 1–15, 2026 poll: Congress **9**, the presidency **27**, the U.S. Supreme Court **27**, and the average of the **14** institutions measured each year since 1993, **27**. Each figure is “a great deal” plus “quite a lot.”

Cadence: annual, typically June. Do this when Gallup publishes the next annual update. Skip the year if the article is not out.

The file holds one row per series for the current year. Replace those four rows. Do not append earlier years, and do not paste Gallup’s historical tables. Continuous republication of Gallup data on this site may require permission. This checklist is a cited current reading, not an archive, and the weekly job does not scrape Gallup.

The 14 institutions in that average are the presidency, Congress, the public schools, the Supreme Court, the military, the criminal justice system, the police, banks, big business, organized labor, the medical system, newspapers, television news, and the church or organized religion. The nine-institution average is a different series. Store the 14-institution average only when the cited article prints it. If a future article drops that average, remove the `gallup_core_institutions` row only after the fetcher’s required list is changed in the same commit. Until then a missing row fails this companion.

1. Open the new Gallup Confidence in Institutions write-up and the trends page if you need to confirm the same year.
2. Replace `value` on each of the four rows with the new “great deal / quite a lot” percent.
3. Set `observation_period` to the fieldwork window, such as `June 1-15 2026`.
4. Set `observation_date` to the last day of fieldwork (`YYYY-MM-DD`). Do not write only the year, and do not use the article’s publication date.
5. Set `source` and `source_url` to the article you read.
6. Set `reviewed_at` to the calendar date you checked the source.

## Columns

Both files use the same columns.

| Column | What to write |
| --- | --- |
| `series` | `pew_public_trust`, or one of `gallup_congress`, `gallup_presidency`, `gallup_supreme_court`, `gallup_core_institutions` |
| `value` | The published percent, 0–100 |
| `observation_period` | Fieldwork window |
| `observation_date` | Last day of fieldwork, `YYYY-MM-DD` |
| `source` | Short document name |
| `source_url` | `https://` URL of the page you read |
| `reviewed_at` | Calendar date you checked the source, `YYYY-MM-DD` |

Write a date. Do not write a clock time, and do not write `2025-01-01T00:00:00Z`.
