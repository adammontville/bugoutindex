# BugOutIndex
# Copyright (C) 2025 Adam Montville
# Dual-licensed under AGPL-3.0 and a commercial license.
"""
Research replay: newer homelessness and trust readings.

Each committed weekly publication is rescored with
``runtime.processing.formula.compute_index``. Inflation, unemployment,
debt-to-GDP, and crime stay on that week's published row. Homelessness
and trust are substituted only inside this replay.

This module does not publish. It does not change the formula, the weekly
history, ``docs/data/latest.json``, ``runtime/data/annual_inputs.csv``,
or schema version 1. Companions are not added to ``CORE_METRICS``.
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Mapping, Optional, Sequence

from runtime.backtest.harness import WEEKLY_CSV
from runtime.processing.formula import (
    CORE_METRICS,
    METRIC_RANGES,
    WEIGHTS,
    compute_index,
    interpret,
)

PACKAGE_DIR = Path(__file__).resolve().parent
FIXTURE_DIR = PACKAGE_DIR / "fixtures"
RELEASE_CSV = FIXTURE_DIR / "slow_inputs_releases.csv"
OUTPUT_DIR = PACKAGE_DIR / "output"
NOTE_NAME = "SLOW_INPUTS_REPLAY.md"
PUBLICATION_CSV_NAME = "slow_inputs_publications.csv"

# The live publish the audit was asked to rescore. Later weeks, if any,
# stay in the weekly table. This date is the basket in the conclusion.
BASKET_DATE = "2026-10-09"
# At the homelessness endpoint the normalized score is 0. Any higher raw
# value clamps to the same 0, so this one number is the whole "local rate
# forced into the national slot" result.
CLAMPED_HOMELESSNESS = 0.5
# Congress is a Gallup institution, not the 14-institution average. It is
# scored once on the basket and is not a weekly option.
GALLUP_CONGRESS = 9.0

# Newest same-source readings. The fixture carries the same numbers; these
# constants are the ones the conclusion names.
HUD_REFRESH = 0.22
EDELMAN_REFRESH = 39.0
PEW_LATEST = 17.0
GALLUP_CORE = 27.0


def _num(value: float, digits: int = 2) -> str:
    return f"{float(value):.{digits}f}"


def _signed(value: float) -> str:
    return f"{float(value):+.2f}"


def score_raws(raws: Mapping[str, float]) -> dict:
    """Six-input score. The caller chooses homelessness and trust."""
    missing = [metric for metric in CORE_METRICS if metric not in raws]
    if missing:
        raise ValueError(f"score needs all six inputs; missing {', '.join(missing)}")
    payload = {metric: {"data": {metric: float(raws[metric])}} for metric in CORE_METRICS}
    scored = compute_index(payload)
    band = interpret(scored["index"])
    return {
        "index": scored["index"],
        "band": band["band"],
        "homelessness_normalized": scored["metrics"]["homelessness_rate"]["normalized"],
        "trust_normalized": scored["metrics"]["trust_in_government"]["normalized"],
    }


def load_releases(path: Path = RELEASE_CSV) -> list[dict]:
    """Same-source and companion readings, with the day each became public."""
    releases = []
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            releases.append(
                {
                    "family": row["family"].strip(),
                    "metric": row["metric"].strip(),
                    "value": float(row["value"]),
                    "available_on": row["available_on"].strip(),
                    "observation": row["observation"].strip(),
                    "label": row["label"].strip(),
                }
            )
    if not releases:
        raise ValueError(f"{path} has no releases")
    return releases


def release_asof(
    releases: Sequence[Mapping[str, object]],
    family: str,
    publication_date: str,
) -> Optional[Mapping[str, object]]:
    """Latest release in ``family`` whose public date is on or before the week."""
    chosen = None
    for release in releases:
        if release["family"] != family:
            continue
        if str(release["available_on"]) <= publication_date:
            if chosen is None or str(release["available_on"]) > str(chosen["available_on"]):
                chosen = release
    return chosen


def load_publications(path: Path = WEEKLY_CSV) -> list[dict]:
    rows = []
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            rows.append(
                {
                    "date": row["date"],
                    "published_index": float(row["bugout_index"]),
                    "raws": {metric: float(row[metric]) for metric in CORE_METRICS},
                }
            )
    if not rows:
        raise ValueError(f"{path} has no publications")
    return rows


def _option(raws: Mapping[str, float], **overrides: float) -> dict:
    swapped = dict(raws)
    swapped.update(overrides)
    scored = score_raws(swapped)
    return {"raws": swapped, **scored}


def build_publication_rows(
    publications: Optional[Sequence[Mapping[str, object]]] = None,
    releases: Optional[Sequence[Mapping[str, object]]] = None,
) -> list[dict]:
    """One row per committed publication. Only homelessness and trust move."""
    pubs = list(load_publications() if publications is None else publications)
    files = list(load_releases() if releases is None else releases)
    rows = []
    for pub in pubs:
        raws = dict(pub["raws"])
        locked = score_raws(raws)
        if locked["index"] != float(pub["published_index"]):
            raise ValueError(
                f"{pub['date']} recomputed {locked['index']} "
                f"and the weekly file stores {pub['published_index']}"
            )
        hud = release_asof(files, "hud", str(pub["date"]))
        edelman = release_asof(files, "edelman", str(pub["date"]))
        pew = release_asof(files, "pew", str(pub["date"]))
        gallup = release_asof(files, "gallup", str(pub["date"]))
        if hud is None or edelman is None or pew is None:
            raise ValueError(f"{pub['date']} is before the HUD, Edelman, or Pew fixture")
        hud_only = _option(raws, homelessness_rate=float(hud["value"]))
        edelman_only = _option(raws, trust_in_government=float(edelman["value"]))
        both = _option(
            raws,
            homelessness_rate=float(hud["value"]),
            trust_in_government=float(edelman["value"]),
        )
        pew_only = _option(raws, trust_in_government=float(pew["value"]))
        if gallup is None:
            gallup_only = _option(raws)
            gallup_value = float(raws["trust_in_government"])
            gallup_held = True
            gallup_label = "published Edelman; Gallup 2026 not yet public"
        else:
            gallup_only = _option(raws, trust_in_government=float(gallup["value"]))
            gallup_value = float(gallup["value"])
            gallup_held = False
            gallup_label = str(gallup["label"])
        rows.append(
            {
                "date": pub["date"],
                "published_index": locked["index"],
                "published_band": locked["band"],
                "published_homelessness": float(raws["homelessness_rate"]),
                "published_trust": float(raws["trust_in_government"]),
                "hud_value": float(hud["value"]),
                "hud_observation": hud["observation"],
                "hud_label": hud["label"],
                "hud_index": hud_only["index"],
                "hud_band": hud_only["band"],
                "hud_difference": round(hud_only["index"] - locked["index"], 2),
                "edelman_value": float(edelman["value"]),
                "edelman_observation": edelman["observation"],
                "edelman_label": edelman["label"],
                "edelman_index": edelman_only["index"],
                "edelman_band": edelman_only["band"],
                "edelman_difference": round(edelman_only["index"] - locked["index"], 2),
                "same_homelessness": float(hud["value"]),
                "same_trust": float(edelman["value"]),
                "same_index": both["index"],
                "same_band": both["band"],
                "same_difference": round(both["index"] - locked["index"], 2),
                "pew_value": float(pew["value"]),
                "pew_observation": pew["observation"],
                "pew_label": pew["label"],
                "pew_index": pew_only["index"],
                "pew_band": pew_only["band"],
                "pew_difference": round(pew_only["index"] - locked["index"], 2),
                "gallup_value": gallup_value,
                "gallup_held_published": gallup_held,
                "gallup_label": gallup_label,
                "gallup_index": gallup_only["index"],
                "gallup_band": gallup_only["band"],
                "gallup_difference": round(gallup_only["index"] - locked["index"], 2),
            }
        )
    return rows


def basket_row(rows: Sequence[Mapping[str, object]], basket_date: str = BASKET_DATE) -> Mapping[str, object]:
    for row in rows:
        if row["date"] == basket_date:
            return row
    raise ValueError(f"no publication on {basket_date}")


def basket_extras(publications: Optional[Sequence[Mapping[str, object]]] = None) -> dict:
    """Rejected substitutions on the named basket. Not weekly options."""
    pubs = list(load_publications() if publications is None else publications)
    basket = next(pub for pub in pubs if pub["date"] == BASKET_DATE)
    raws = dict(basket["raws"])
    published = score_raws(raws)
    congress = _option(raws, trust_in_government=GALLUP_CONGRESS)
    clamped = _option(raws, homelessness_rate=CLAMPED_HOMELESSNESS)
    return {
        "published_index": published["index"],
        "congress_index": congress["index"],
        "congress_band": congress["band"],
        "congress_difference": round(congress["index"] - published["index"], 2),
        "clamped_index": clamped["index"],
        "clamped_band": clamped["band"],
        "clamped_difference": round(clamped["index"] - published["index"], 2),
    }


def _table(headers: Sequence[str], body: Sequence[Sequence[str]]) -> str:
    align = ["---"] + ["---:"] * (len(headers) - 1)
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(align) + " |",
    ]
    for row in body:
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def _span(values: Sequence[float]) -> str:
    lo = _num(min(values))
    hi = _num(max(values))
    if lo == hi:
        return lo
    return f"{lo} to {hi}"


def render_markdown(
    publication_rows: Sequence[Mapping[str, object]],
    extras: Mapping[str, object],
) -> str:
    """Results note. Safe to read without rerunning the replay."""
    basket = basket_row(publication_rows)
    hud_weight = WEIGHTS["homelessness_rate"]
    trust_weight = WEIGHTS["trust_in_government"]
    hud_lo, hud_hi = METRIC_RANGES["homelessness_rate"]
    trust_lo, trust_hi = METRIC_RANGES["trust_in_government"]
    same_diffs = [float(row["same_difference"]) for row in publication_rows]
    hud_diffs = [float(row["hud_difference"]) for row in publication_rows if row["hud_value"] != row["published_homelessness"]]
    edelman_diffs = [float(row["edelman_difference"]) for row in publication_rows]
    pew_bands = sorted({str(row["pew_band"]) for row in publication_rows})
    same_bands = sorted({str(row["same_band"]) for row in publication_rows})
    gallup_live = [row for row in publication_rows if not row["gallup_held_published"]]
    gallup_held = [row for row in publication_rows if row["gallup_held_published"]]
    first_gallup = gallup_live[0]["date"] if gallup_live else "none"
    last_held = gallup_held[-1]["date"] if gallup_held else "none"

    basket_table = _table(
        ["Basket", "Homelessness", "Trust", "Score", "Band", "Difference"],
        [
            ["Published 2026-10-09", "0.23", "41", _num(basket["published_index"]), "Moderate", "0.00"],
            ["HUD 2025 AHAR only", _num(basket["hud_value"]), "41", _num(basket["hud_index"]), _short(basket["hud_band"]), _signed(basket["hud_difference"])],
            ["Edelman 2026 only", "0.23", _num(basket["edelman_value"], 0), _num(basket["edelman_index"]), _short(basket["edelman_band"]), _signed(basket["edelman_difference"])],
            ["Both same-source", _num(basket["same_homelessness"]), _num(basket["same_trust"], 0), _num(basket["same_index"]), _short(basket["same_band"]), _signed(basket["same_difference"])],
            ["Pew in the trust slot", "0.23", _num(basket["pew_value"], 0), _num(basket["pew_index"]), _short(basket["pew_band"]), _signed(basket["pew_difference"])],
            ["Gallup 14-institution average", "0.23", _num(basket["gallup_value"], 0), _num(basket["gallup_index"]), _short(basket["gallup_band"]), _signed(basket["gallup_difference"])],
            ["Gallup Congress only", "0.23", _num(GALLUP_CONGRESS, 0), _num(extras["congress_index"]), _short(extras["congress_band"]), _signed(extras["congress_difference"])],
            ["Local rate at the 0.5 endpoint", _num(CLAMPED_HOMELESSNESS), "41", _num(extras["clamped_index"]), _short(extras["clamped_band"]), _signed(extras["clamped_difference"])],
        ],
    )
    weekly_table = _table(
        ["Publication", "Published", "HUD refresh", "Edelman refresh", "Both", "Pew", "Gallup as-of"],
        [
            [
                str(row["date"]),
                _num(row["published_index"]),
                _num(row["hud_index"]),
                _num(row["edelman_index"]),
                _num(row["same_index"]),
                _num(row["pew_index"]),
                _num(row["gallup_index"]),
            ]
            for row in publication_rows
        ],
    )
    return f"""# Slow-input refresh replay

Research only. Homelessness and trust stay on the annual checklist. This note does not change `compute_index`, methodology **1.1.0**, `docs/data/latest.json`, or `runtime/data/weekly_bugout_index.csv`. Companions stay outside the score. The live basket of **{BASKET_DATE}** remains **{_num(basket['published_index'])}**, Moderate Stability, with homelessness **0.23** and trust **41**.

## Recommendation

Refresh both inputs from the same sources on their release cycle. Stamp that catch-up as a **1.1.x** data revision. Do not replace either series, and do not call it 1.2.0.

| Input | Recommendation | Reading to copy | Projected score on the {BASKET_DATE} basket | Band |
| --- | --- | --- | ---: | --- |
| Homelessness | Refresh the 2025 HUD AHAR | **0.22** | **{_num(basket['hud_index'])}** if only homelessness moves | {_short(basket['hud_band'])} |
| Trust | Refresh the 2026 Edelman US Government row | **39** | **{_num(basket['edelman_index'])}** if only trust moves | {_short(basket['edelman_band'])} |
| Both, the catch-up | Copy both cells in one checklist edit | **0.22** and **39** | **{_num(basket['same_index'])}** | {_short(basket['same_band'])} |

Keeping the checklist as it is leaves the score at **{_num(basket['published_index'])}** Moderate. Replacing trust with Pew prints **{_num(basket['pew_index'])}** {_short(basket['pew_band'])}. Replacing it with Gallup's 14-institution average prints **{_num(basket['gallup_index'])}** {_short(basket['gallup_band'])}. Both replacements cross the 55 line. The same-source catch-up does not.

1.1.x is a label for the history step, not a new formula. Endpoints, weights, trust inversion, and the divide-by-0.72 rule stay. Methodology 1.1.0 already tells a person to edit the checklist when HUD or Edelman publishes. The 2025 AHAR has been public since 29 May 2026, and the 2026 Edelman barometer since 18 January 2026. The cells were not updated. A 1.2.0 bump would mean a different series. Pew, Gallup, and the shelter companions are that different series, and they stay beside the index.

Across the {len(publication_rows)} committed weeks, the same-source pair stays **{same_bands[0]}**. The rounded gap versus the published score is **{_span(same_diffs)}** points. HUD alone, on the weeks that can already see the 2025 AHAR, raises the index by **{_span(hud_diffs)}**. Edelman 2026 is public for the whole history and lowers it by **{_span([abs(v) for v in edelman_diffs])}**.

{basket_table}

The last two rows are rejected sensitivities on that one basket. They are not weekly options. Congress at 9 is Gallup's legislative reading, not a government-trust percent. A local shelter rate at or above the **0.5** homelessness endpoint normalizes to 0 and prints **{_num(extras['clamped_index'])}** {_short(extras['clamped_band'])}. The NYC census on this publish is 84,042 people. That headcount is more than 0.5 percent of any population under 16.8 million, so a New York City rate in the national slot clamps on this basket. The score above uses the endpoint itself. Any higher raw value clamps to the same index.

## How the two inputs are fetched today

The scored number is the checklist cell. Crime before methodology 1.1.0 kept `PUBLISHED_INCIDENT_RATE` (2723.0) as the scored input while the fetcher could already see a newer RTCI file. Homelessness and trust have no second candidate sitting beside the cell. The weekly job does not download HUD or Edelman, so a newer report changes the score only after a person edits the cell.

| | Homelessness | Trust in government |
| --- | --- | --- |
| Fetcher | `runtime/data/fetch/fetch_homelessness_rate.py` | `runtime/data/fetch/fetch_trust_in_government.py` |
| Source | HUD AHAR Part 1, national point-in-time rate | Edelman Trust Barometer, United States, Government |
| Where the cell lives | `homelessness_rate` row of `runtime/data/annual_inputs.csv` | `trust_in_government` row of the same file |
| Scored value | **0.23** | **41** |
| Vintage | 2024 AHAR. HUD's phrase is about **23 of every 10,000** people. Headcount **771,480** on a night in the last 10 days of January 2024. The page note also shows 771,480 / 335,000,000 × 100 ≈ 0.23 | Survey year **2025**. The archive row is Government **41** |
| Shown observation date | **2024-01-01** (HUD reference date) | **2025** (survey year only, no month or day) |
| `fetched_at` | Empty. The reference date is not a fetch clock | The survey year, `2025` |
| `reviewed_at` | **2025-03-13**, the day the published cell was committed, not a HUD release date | **2025-03-13**, the day the Edelman archive was committed |
| Update cadence | Annual, when a new AHAR Part 1 is out. The weekly job does not look | Annual, when a new Trust Barometer is out. A new column in `edelman-trust-barometer-us.csv` does not change the score |
| Provenance kind | `manual`, `last_set` = `2024 HUD AHAR` | `annual`, `year` = `2025` |

The weekly publisher calls both fetchers inside `fetch_core_metrics`. All six cores must succeed (`MIN_REQUIRED_METRICS` is 6). A checklist failure returns `status: error`, `fetched_at: null`, and empty `data`, and the publish refuses. The previous site stays up. The fetchers do not fill a gap with 0.23 or 41, and they do not stamp the clock.

Guards in `runtime/data/fetch/annual_inputs.py`:

- The file, the header, and exactly one row for the metric must exist.
- `value` must be a number. `observation_period` and `source` must be non-blank.
- Homelessness `observation_date` must be `YYYY-MM-DD`. Trust `observation_date` must be a four-digit year. A month or day on the trust row fails the fetch.
- `reviewed_at` must be a real calendar date. A timestamp, including `2025-01-01T00:00:00Z`, fails the fetch.
- `source_url`, when present, must start with `http://` or `https://`.
- The loader does not call `datetime.now`, `date.today`, or `utcnow`.

Weights and endpoints, unchanged by this note: homelessness **{hud_lo:g} to {hud_hi:g}**, weight **{hud_weight:.2f}**; trust **{trust_lo:g} to {trust_hi:g}**, inverted, weight **{trust_weight:.2f}**. The six weights still sum to **{sum(WEIGHTS.values()):.2f}**.

## Newer value of the same source

### HUD

The newest national AHAR Part 1 is the **2025** report, posted **May 2026**. HUD's press release is dated **29 May 2026** ([HUD No. 26-037](https://www.hud.gov/news/hud-no-26-037)). The report PDF is [2025 AHAR Part 1](https://www.huduser.gov/portal/sites/default/files/pdf/2025-AHAR-Part-1.pdf). HUD USER lists that file as the current Part 1. There is no 2026 national AHAR as of 10 October 2026. CoCs submitted January 2026 counts in the spring. Local 2026 counts exist. They are not the national rate this checklist uses.

The 2025 report's national sentence is the same shape as the 2024 sentence that became 0.23. On a single night in January 2025, **745,652** people were counted, about **22 of every 10,000**. The 2024 report said **771,480** people, about **23 of every 10,000**. The checklist stores that rate as a percent to two decimals. The same-source successor is **0.22**, observation date **2025-01-01**, period label `January 2025 point-in-time count`.

The weekly job runs at 23:30 UTC on Friday. 29 May 2026 was a Friday, and the HUD page was submitted that afternoon. This replay treats a release as usable on a publication date on or after the release date, so the **2026-05-29** row is the first week that can carry 0.22. Earlier weeks in this history stay on 0.23 because the 2025 report was not public yet. That is the column "HUD refresh."

A machine-readable copy of the same count is the HUD USER workbook "2007–2025 Point-in-Time Estimates by State" (XLSB) linked from the [2025 AHAR page](https://www.huduser.gov/portal/datasets/ahar/2025-ahar-part-1-pit-estimates-of-homelessness-in-the-us.html). It is annual, national once the rows are summed, and a US government work. It can feed the checklist once a year. It is not a weekly series, and this replay does not wire it into the publisher.

On the {BASKET_DATE} basket, homelessness 0.22 with trust still 41 scores **{_num(basket['hud_index'])}** {_short(basket['hud_band'])}.

### Edelman

The newest Trust Barometer is the **2026** report, released **18 January 2026** ([Edelman news release](https://www.edelman.com/news-awards/2026-edelman-trust-barometer-society-slides-into-insularity)). Fieldwork in that release is **23 October through 18 November 2025**. The product page lists a slightly different window, 25 October through 16 November 2025. Either window is still survey year 2026. The checklist stores the year only.

The scored series is United States, **Government**, not the four-institution Trust Index. The global report puts the US Trust Index at **47**, the same average as the 2025 archive (business 55, government 41, media 42, NGOs 50). The government percent used here is **39**:

- [Visual Capitalist, 7 February 2026](https://www.visualcapitalist.com/charted-do-people-trust-the-media-or-government-more/), a country table of the 2026 Edelman government and media scores. United States government **39**, media **44**.
- [Dance USA, 15 June 2026](https://www.danceusa.org/ejournal/2026/06/15/marketing-moves-for-dance-organizations-in-2026), citing the U.S. report "Trust Amid Insularity": Trust Index 47, government **39**, media **44**.
- An Edelman Netherlands note on the same report: government trust **57** in the Netherlands and **39** in the United States.

Media 44 and government 39, with business and NGOs unchanged, keep the Trust Index at 47. That is a consistency check. This environment received HTTP 403 from edelman.com, so the government cell was not re-read from the PDF bytes. A checklist edit should open the U.S. report and copy the Government row. The scores below use **39**.

Every committed week is after 18 January 2026, so the Edelman-refresh column is 39 on all {len(publication_rows)} weeks. The 2025 figure of 41 remains what the live checklist scores. On the {BASKET_DATE} basket, trust 39 with homelessness still 0.23 scores **{_num(basket['edelman_index'])}** {_short(basket['edelman_band'])}. Both substitutions together score **{_num(basket['same_index'])}** {_short(basket['same_band'])}.

There is no public Edelman API. The historical archive in the repo is a small table of US institution percents. It does not feed `compute_index`. Republication of the full barometer is Edelman's report, not an open series.

## Fresher candidates

These were checked because they move more often, or because they are already in the repo. None of them is the HUD rate or the Edelman government percent. Putting one into the existing slot changes the question and, for the trust companions, the band.

| Candidate | Cadence | Coverage | History in hand | License and machine readability | Why it stays out |
| --- | --- | --- | --- | --- | --- |
| NYC DHS `k46n-sa2m`, `total_individuals_in_shelter` | Daily | New York City shelter census. Not unsheltered. Not national | Open-data fetch. The weekly history file has the latest census beside each publish | NYC Open Data. Socrata JSON | A headcount. 84,042 on 2026-10-08. In the national 0–0.5 slot it clamps. See the basket table |
| Nashville–Davidson HMIS | Monthly PDF | People who experienced homelessness that month in one county's HMIS. Not a one-night census | Checklist, July 2025 through July 2026 | Manual. No API | Local, different definition |
| Austin / Travis County ECHO | Monthly dashboard, published late | Six-month engagement count of people likely sheltered | One checklist row, data effective 2025-07-01, published 2025-09-10 | Manual | Local, lagged, different definition |
| Ramsey County `9mck-bcqu` | Monthly | Emergency-shelter enrollees in one county | Open-data fetch. Newest stored month on the companion note was 2026-08-01 | County open data | Local headcount |
| Denver HOST occupancy | The cited release. The city dashboard is monthly | Occupancy rate for a seven-shelter pilot, **93%** in Q2 2026 | One checklist row | Manual | An occupancy rate, not a population rate |
| San Francisco DataSF measure `279` | Monthly | Average occupancy of year-round temporary shelter | Open-data fetch. Newest stored month on the companion note was 2026-08-31 | DataSF open data | An occupancy rate, not a population rate |
| HUD PIT by state, 2007–2025 | Annual | National once summed. Same PIT definition as the scored input | The workbook HUD posted with the 2025 AHAR | US government work. XLSB | Same source, same cadence. Use it to fill the checklist, not to replace it |
| Pew public trust | Irregular waves | Share who trust the government in Washington just about always or most of the time | Excerpt in `pew_trust_shadow.csv`: May 2024 **22**, February 2025 **17**, September 2025 **17**. Pew's chart runs 1958–2025. This repo does not store that archive | Cited excerpt. The weekly job does not download Pew's CSV | Different question. **17** in the trust slot scores **{_num(basket['pew_index'])}** {_short(basket['pew_band'])} on the latest basket, and **{pew_bands[0]}** on every committed week |
| Gallup confidence in institutions | Annual, typically June | "A great deal" plus "quite a lot." 2026 poll is June 1–15, article 13 July 2026. Congress **9**, presidency **27**, Supreme Court **27**, 14-institution average **27** | Current year only, by design. Earlier years are not in the checklist | Gallup. Continuous republication may need permission. The weekly job does not scrape Gallup | Different question, still annual. The 14-institution average scores **{_num(basket['gallup_index'])}** {_short(basket['gallup_band'])} on the latest basket. Congress at 9 scores **{_num(extras['congress_index'])}** |
| GSS confidence items, ANES trust in Washington, OECD trust in government | Biennial, or election years, or about every two years | Related questions. Not the Edelman government percent | Not in this repo | GSS and ANES are public microdata. OECD's trust figure is often the Gallup World Poll | Not a weekly series, and not the same question. They do not update the checklist faster than Edelman's January release |

No blend of these is a national homelessness rate or an Edelman government percent. Averaging 41 and 17 treats two questions as one number. Scaling the national PIT by the change in the NYC shelter census assigns one city's sheltered count to the sheltered-plus-unsheltered national rate. The 2025 AHAR itself says New York and Illinois drove a large part of the national decline, which is a reason not to let New York stand in for the country. The shelter companions stay a labeled panel.

## Weekly scores

Each cell is `compute_index` on that week's published inflation, unemployment, debt-to-GDP, and crime. Only homelessness and trust change.

- **HUD refresh** uses 0.23 through 2026-05-22 and **0.22** from 2026-05-29.
- **Edelman refresh** uses **39** on every row. The 2026 report predates 2026-04-21.
- **Both** is those two together. The band stays Moderate on every row.
- **Pew** uses the September 2025 wave, **17**, public in the 4 December 2025 article. The band is **{pew_bands[0]}** on every row.
- **Gallup as-of** keeps the published Edelman value through **{last_held}**. The 13 July 2026 article is first usable on **{first_gallup}**. From that week the trust input is **27** and the band is Low.

{weekly_table}

## How to run

From the repository root:

```bash
python -m runtime.backtest.slow_inputs_replay
```

That rewrites this note and `runtime/backtest/output/slow_inputs_publications.csv`. No network and no `FRED_API_KEY`. The release table is `runtime/backtest/fixtures/slow_inputs_releases.csv`.

## What stays put

`docs/data/latest.json` still has methodology **1.1.0**, index **{_num(basket['published_index'])}**, homelessness **0.23**, and trust **41** on **{BASKET_DATE}**. `runtime/data/annual_inputs.csv` still has those two cells. `compute_index` does not read this module, the NYC census, the regional shelter panel, Pew, or Gallup.
"""


def _short(band: object) -> str:
    return str(band).replace(" Stability", "")


PUBLICATION_COLUMNS = (
    "date",
    "published_index",
    "published_band",
    "hud_value",
    "hud_index",
    "hud_difference",
    "hud_band",
    "edelman_value",
    "edelman_index",
    "edelman_difference",
    "edelman_band",
    "same_homelessness",
    "same_trust",
    "same_index",
    "same_difference",
    "same_band",
    "pew_value",
    "pew_index",
    "pew_difference",
    "pew_band",
    "gallup_value",
    "gallup_held_published",
    "gallup_index",
    "gallup_difference",
    "gallup_band",
)


def _write_csv(path: Path, rows: Sequence[Mapping[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(PUBLICATION_COLUMNS), extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            rendered = {}
            for column in PUBLICATION_COLUMNS:
                value = row[column]
                if isinstance(value, float):
                    rendered[column] = f"{value:.2f}"
                elif isinstance(value, bool):
                    rendered[column] = "true" if value else "false"
                else:
                    rendered[column] = value
            writer.writerow(rendered)


def write_outputs(output_dir: Path = OUTPUT_DIR, note_path: Optional[Path] = None) -> list[Path]:
    publication_rows = build_publication_rows()
    extras = basket_extras()
    note = PACKAGE_DIR / NOTE_NAME if note_path is None else note_path
    publications = output_dir / PUBLICATION_CSV_NAME
    _write_csv(publications, publication_rows)
    note.write_text(render_markdown(publication_rows, extras), encoding="utf-8")
    return [publications, note]


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m runtime.backtest.slow_inputs_replay",
        description=(
            "Rescore committed weekly publications with newer homelessness "
            "and trust readings. Does not change the live score."
        ),
    )
    parser.add_argument("--output", type=Path, default=OUTPUT_DIR)
    parser.add_argument("--note", type=Path, default=PACKAGE_DIR / NOTE_NAME)
    args = parser.parse_args(argv)
    for path in write_outputs(args.output, args.note):
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
