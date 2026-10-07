# BugOutIndex
# Copyright (C) 2025 Adam Montville
# Dual-licensed under AGPL-3.0 and a commercial license.
"""
Research replay: v1.0.0 with a live crime input.

Each committed weekly publication is rescored with
``runtime.processing.formula.compute_index``. The five non-crime inputs stay
on the published row. Crime is the unweighted RTCI agency mean for the latest
calendar month in the AH-Datalytics file that was on ``main`` that day.

This module does not publish. It does not change the formula, the weekly
history, ``docs/data/latest.json``, or schema version 1.
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Mapping, Optional, Sequence

from runtime.backtest.harness import WEEKLY_CSV
from runtime.data.fetch.fetch_incident_rate import PUBLISHED_INCIDENT_RATE
from runtime.processing.formula import (
    CORE_METRICS,
    METRIC_RANGES,
    WEIGHTS,
    compute_index,
    interpret,
)

PACKAGE_DIR = Path(__file__).resolve().parent
FIXTURE_DIR = PACKAGE_DIR / "fixtures"
VINTAGE_CSV = FIXTURE_DIR / "crime_asof_vintages.csv"
CURRENT_RTCI_CSV = FIXTURE_DIR / "v2" / "RTCI_monthly.csv"
LOCAL_RTCI_CSV = PACKAGE_DIR.parents[1] / "runtime" / "data" / "final_sample.csv"
OUTPUT_DIR = PACKAGE_DIR / "output"
NOTE_NAME = "CRIME_LIVE_REPLAY.md"
PUBLICATION_CSV_NAME = "crime_live_publications.csv"
MONTHLY_CSV_NAME = "crime_live_monthly.csv"

# Current-file months shown beside the weekly history. September 2024 is the
# month label on the locked 2723 print. April 2026 is the newest month in the
# file behind the 2 October 2026 snapshot.
MONTHLY_FROM = "2024-09-01"
LATEST_PUBLICATION = "2026-10-02"
SNAPSHOT_CANDIDATE_MONTH = "2025-09-01"
SNAPSHOT_CANDIDATE_RATE = 2234.66

_MONTHS = {
    "January": 1,
    "February": 2,
    "March": 3,
    "April": 4,
    "May": 5,
    "June": 6,
    "July": 7,
    "August": 8,
    "September": 9,
    "October": 10,
    "November": 11,
    "December": 12,
}
_MONTH_NAME = {number: name for name, number in _MONTHS.items()}


def _num(value: float, digits: int = 2) -> str:
    return f"{float(value):.{digits}f}"


def _month_label(iso_day: str) -> str:
    year, month, _day = iso_day.split("-")
    return f"{_MONTH_NAME[int(month)]} {year}"


def _chrono_key(label: str) -> tuple[int, int]:
    parts = label.split()
    if len(parts) == 2 and parts[0] in _MONTHS and parts[1].isdigit():
        return (int(parts[1]), _MONTHS[parts[0]])
    return (0, 0)


def score_raws(raws: Mapping[str, float]) -> dict:
    """Six-input v1.0.0 score. The caller chooses the crime value."""
    missing = [metric for metric in CORE_METRICS if metric not in raws]
    if missing:
        raise ValueError(f"score needs all six inputs; missing {', '.join(missing)}")
    payload = {metric: {"data": {metric: float(raws[metric])}} for metric in CORE_METRICS}
    scored = compute_index(payload)
    band = interpret(scored["index"])
    return {
        "index": scored["index"],
        "band": band["band"],
        "incident_normalized": scored["metrics"]["incident_rate"]["normalized"],
    }


def load_vintages(path: Path = VINTAGE_CSV) -> list[dict]:
    """RTCI files that were on main during the committed weekly history.

    Rates are the unweighted agency mean from that file, same construction as
    ``fetch_incident_rate._rates_for_month``. A later file can revise an
    earlier month. These rows keep the rate that was in the file that day.
    """
    vintages = []
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            vintages.append(
                {
                    "rtci_commit_date": row["rtci_commit_date"],
                    "rtci_sha": row["rtci_sha"],
                    "rtci_commit_message": row["rtci_commit_message"],
                    "file_updated": row["file_updated"],
                    "calendar_month": row["calendar_month"],
                    "calendar_label": row["calendar_label"],
                    "unweighted": float(row["unweighted"]),
                    "population_weighted": float(row["population_weighted"]),
                    "agencies": int(row["agencies"]),
                    "lex_month": row["lex_month"],
                    "lex_label": row["lex_label"],
                    "lex_unweighted": float(row["lex_unweighted"]),
                    "lex_population_weighted": float(row["lex_population_weighted"]),
                    "lex_agencies": int(row["lex_agencies"]),
                }
            )
    if not vintages:
        raise ValueError(f"{path} has no RTCI vintages")
    return vintages


def vintage_asof(vintages: Sequence[Mapping[str, object]], publication_date: str) -> Mapping[str, object]:
    """Latest RTCI commit date on or before the publication date."""
    chosen = None
    for vintage in vintages:
        if str(vintage["rtci_commit_date"]) <= publication_date:
            chosen = vintage
    if chosen is None:
        raise ValueError(f"no RTCI vintage on or before {publication_date}")
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


def build_publication_rows(
    publications: Optional[Sequence[Mapping[str, object]]] = None,
    vintages: Optional[Sequence[Mapping[str, object]]] = None,
) -> list[dict]:
    """One row per committed publication. Crime is the only substituted input."""
    pubs = list(load_publications() if publications is None else publications)
    files = list(load_vintages() if vintages is None else vintages)
    rows = []
    for pub in pubs:
        raws = dict(pub["raws"])
        locked = score_raws(raws)
        if locked["index"] != float(pub["published_index"]):
            raise ValueError(
                f"{pub['date']} recomputed {locked['index']} "
                f"and the weekly file stores {pub['published_index']}"
            )
        vintage = vintage_asof(files, str(pub["date"]))
        live_raws = dict(raws)
        live_raws["incident_rate"] = float(vintage["unweighted"])
        live = score_raws(live_raws)
        lex_raws = dict(raws)
        lex_raws["incident_rate"] = float(vintage["lex_unweighted"])
        lex = score_raws(lex_raws)
        rows.append(
            {
                "date": pub["date"],
                "locked_index": locked["index"],
                "locked_band": locked["band"],
                "live_index": live["index"],
                "live_band": live["band"],
                "live_difference": round(live["index"] - locked["index"], 2),
                "crime_value": float(vintage["unweighted"]),
                "rtci_month": vintage["calendar_label"],
                "rtci_month_start": vintage["calendar_month"],
                "agencies": int(vintage["agencies"]),
                "population_weighted": float(vintage["population_weighted"]),
                "rtci_commit_date": vintage["rtci_commit_date"],
                "rtci_sha": vintage["rtci_sha"],
                "rtci_commit_message": vintage["rtci_commit_message"],
                "lex_index": lex["index"],
                "lex_band": lex["band"],
                "lex_difference": round(lex["index"] - locked["index"], 2),
                "lex_crime_value": float(vintage["lex_unweighted"]),
                "lex_rtci_month": vintage["lex_label"],
                "lex_month_start": vintage["lex_month"],
                "lex_agencies": int(vintage["lex_agencies"]),
            }
        )
    return rows


def load_current_monthly(path: Path = CURRENT_RTCI_CSV, start: str = MONTHLY_FROM) -> list[dict]:
    """Revised monthly rates from the v2 RTCI fixture (the June 2026 file)."""
    months = []
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            day = row["observation_date"]
            if day < start:
                continue
            months.append(
                {
                    "rtci_month_start": day,
                    "rtci_month": _month_label(day),
                    "crime_value": float(row["incident_rate_unweighted"]),
                    "population_weighted": float(row["incident_rate_population_weighted"]),
                    "agencies": int(row["agencies"]),
                }
            )
    if not months:
        raise ValueError(f"{path} has no months on or after {start}")
    return months


def build_monthly_rows(
    publication_rows: Sequence[Mapping[str, object]],
    monthly: Optional[Sequence[Mapping[str, object]]] = None,
) -> list[dict]:
    """Current-file months scored on the latest publication's other inputs."""
    latest = publication_rows[-1]
    pubs = load_publications()
    basket = next(pub for pub in pubs if pub["date"] == latest["date"])
    locked_index = float(latest["locked_index"])
    rows = []
    for month in load_current_monthly() if monthly is None else monthly:
        raws = dict(basket["raws"])
        raws["incident_rate"] = float(month["crime_value"])
        scored = score_raws(raws)
        rows.append(
            {
                "rtci_month": month["rtci_month"],
                "rtci_month_start": month["rtci_month_start"],
                "crime_value": float(month["crime_value"]),
                "population_weighted": float(month["population_weighted"]),
                "agencies": int(month["agencies"]),
                "score": scored["index"],
                "band": scored["band"],
                "difference": round(scored["index"] - locked_index, 2),
                "basket_publication": latest["date"],
                "locked_index": locked_index,
            }
        )
    return rows


def rates_by_month(path: Path) -> dict[str, dict]:
    """Unweighted and population-weighted means, one entry per Date label.

    Same row rule as ``fetch_incident_rate._rates_for_month``: a missing
    count or a non-positive population is left out.
    """
    buckets: dict[str, list[float]] = {}
    updated: dict[str, int] = {}
    with path.open(newline="", encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            label = (row.get("Date") or "").strip()
            stamp = (row.get("Last Updated") or "").strip()[:10]
            if stamp:
                updated[stamp] = updated.get(stamp, 0) + 1
            try:
                violent = float(row["Violent Crime_mvs_12mo"])
                prop = float(row["Property Crime_mvs_12mo"])
                pop = float(row["FBI.Population.Covered"])
            except (TypeError, ValueError, KeyError):
                continue
            if pop <= 0:
                continue
            bucket = buckets.setdefault(label, [0.0, 0.0, 0.0, 0.0])
            total = violent + prop
            bucket[0] += (total / pop) * 100000
            bucket[1] += total
            bucket[2] += pop
            bucket[3] += 1
    usable = {label: values for label, values in buckets.items() if _chrono_key(label) != (0, 0)}
    if not usable:
        raise ValueError(f"{path} has no usable RTCI months")
    rates = {}
    for label, (sum_rates, sum_crime, sum_pop, count) in usable.items():
        rates[label] = {
            "unweighted": round(sum_rates / count, 2),
            "population_weighted": round(sum_crime / sum_pop * 100000, 2),
            "agencies": int(count),
        }
    labels = list(rates)
    lex = max(labels)
    calendar = max(labels, key=_chrono_key)
    file_updated = max(updated, key=updated.get) if updated else ""
    return {
        "by_label": rates,
        "lex_label": lex,
        "calendar_label": calendar,
        "file_updated": file_updated,
        "lex": rates[lex],
        "calendar": rates[calendar],
    }


def _spans(rows: Sequence[Mapping[str, object]]) -> list[dict]:
    spans = []
    for row in rows:
        if not spans or spans[-1]["rtci_sha"] != row["rtci_sha"]:
            spans.append(dict(row))
            spans[-1]["first_publication"] = row["date"]
            spans[-1]["last_publication"] = row["date"]
        else:
            spans[-1]["last_publication"] = row["date"]
    return spans


def _span_text(span: Mapping[str, object]) -> str:
    first = span["first_publication"]
    last = span["last_publication"]
    if first == last:
        return str(first)
    return f"{first} through {last}"


def _commit_link(sha: str, day: str) -> str:
    return f"[{day}](https://github.com/AH-Datalytics/rtci/commit/{sha})"


def _table(headers: Sequence[str], body: Sequence[Sequence[str]]) -> str:
    align = ["---"] + ["---:"] * (len(headers) - 1)
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(align) + " |",
    ]
    for row in body:
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def render_markdown(
    publication_rows: Sequence[Mapping[str, object]],
    monthly_rows: Sequence[Mapping[str, object]],
    local_file: Optional[Mapping[str, object]] = None,
) -> str:
    """Results note. Safe to read without rerunning the replay."""
    local = rates_by_month(LOCAL_RTCI_CSV) if local_file is None else local_file
    latest = publication_rows[-1]
    first = publication_rows[0]
    live_deltas = [float(row["live_difference"]) for row in publication_rows]
    lex_deltas = [float(row["lex_difference"]) for row in publication_rows]
    bands = sorted({str(row["live_band"]) for row in publication_rows})
    lo, hi = METRIC_RANGES["incident_rate"]
    weight = WEIGHTS["incident_rate"]
    candidate = next(row for row in monthly_rows if row["rtci_month_start"] == SNAPSHOT_CANDIDATE_MONTH)
    newest = monthly_rows[-1]
    sep_2024 = monthly_rows[0]

    now_table = _table(
        ["Basket", "Crime value", "RTCI month", "Score", "Band"],
        [
            [
                f"Published {latest['date']}",
                _num(PUBLISHED_INCIDENT_RATE, 1),
                "Locked input",
                _num(latest["locked_index"]),
                str(latest["locked_band"]).replace(" Stability", ""),
            ],
            [
                "Same other inputs, snapshot candidate",
                _num(candidate["crime_value"]),
                str(candidate["rtci_month"]),
                _num(candidate["score"]),
                str(candidate["band"]).replace(" Stability", ""),
            ],
            [
                "Same other inputs, newest month in that file",
                _num(newest["crime_value"]),
                str(newest["rtci_month"]),
                _num(newest["score"]),
                str(newest["band"]).replace(" Stability", ""),
            ],
        ],
    )
    vintage_table = _table(
        [
            "RTCI file",
            "Publications",
            "Latest month",
            "Crime value",
            "Agencies",
            "Text-sort month",
            "Text-sort value",
        ],
        [
            [
                _commit_link(str(span["rtci_sha"]), str(span["rtci_commit_date"])),
                _span_text(span),
                str(span["rtci_month"]),
                _num(span["crime_value"]),
                str(span["agencies"]),
                str(span["lex_rtci_month"]),
                _num(span["lex_crime_value"]),
            ]
            for span in _spans(publication_rows)
        ],
    )
    publication_table = _table(
        [
            "Publication",
            "Locked score",
            "Live-crime score",
            "Difference",
            "Crime value",
            "RTCI month",
            "Agencies",
        ],
        [
            [
                str(row["date"]),
                _num(row["locked_index"]),
                _num(row["live_index"]),
                f"{float(row['live_difference']):+.2f}",
                _num(row["crime_value"]),
                str(row["rtci_month"]),
                str(row["agencies"]),
            ]
            for row in publication_rows
        ],
    )
    lex_table = _table(
        [
            "Publication",
            "Locked score",
            "Text-sort score",
            "Difference",
            "Crime value",
            "RTCI month",
            "Agencies",
        ],
        [
            [
                str(row["date"]),
                _num(row["locked_index"]),
                _num(row["lex_index"]),
                f"{float(row['lex_difference']):+.2f}",
                _num(row["lex_crime_value"]),
                str(row["lex_rtci_month"]),
                str(row["lex_agencies"]),
            ]
            for row in publication_rows
        ],
    )
    monthly_table = _table(
        [
            "RTCI month",
            "Crime value",
            "Agencies",
            f"Score on {latest['date']} inputs",
            f"Difference from {_num(latest['locked_index'])}",
        ],
        [
            [
                str(row["rtci_month"]),
                _num(row["crime_value"]),
                str(row["agencies"]),
                _num(row["score"]),
                f"{float(row['difference']):+.2f}",
            ]
            for row in monthly_rows
        ],
    )
    live_low = _num(min(live_deltas))
    live_high = _num(max(live_deltas))
    return f"""# Crime input refresh replay

Research only. Methodology stays **1.0.0**. The live score on {latest['date']} stays **{_num(latest['locked_index'])}**. `compute_index`, the weights, the bands, the weekly history, and schema version 1 are unchanged.

## Conclusion

Giving each published week the newest RTCI month available that day would have raised the index by **{live_low} to {live_high}** points. All {len(publication_rows)} weeks would still have read **{bands[0]}**. The published range in this history is {_num(min(float(row['locked_index']) for row in publication_rows))} to {_num(max(float(row['locked_index']) for row in publication_rows))}. The live-crime range is {_num(min(float(row['live_index']) for row in publication_rows))} to {_num(max(float(row['live_index']) for row in publication_rows))}.

On the {latest['date']} basket the published crime input is **{_num(PUBLISHED_INCIDENT_RATE, 1)}** and the score is **{_num(latest['locked_index'])}**. The snapshot's candidate, **September 2025 at {_num(candidate['crime_value'])}**, scores **{_num(candidate['score'])}**. The newest calendar month in that same file, **April 2026 at {_num(newest['crime_value'])}**, scores **{_num(newest['score'])}**. Both stay Moderate.

{now_table}

The lock was deliberate. [Pull request #78](https://github.com/adammontville/bugoutindex/pull/78) (commit [`9a7594a`](https://github.com/adammontville/bugoutindex/commit/9a7594a85c7b44bbd514438ccbd20959c6d4ad61), merged 22 September 2026) started the weekly download of the AH-Datalytics file and stored **{_num(PUBLISHED_INCIDENT_RATE, 1)}** as `PUBLISHED_INCIDENT_RATE` in the same change. The pull request says accepting another rate is a separate reviewed revision. The weekly job still downloads a fresh file. The candidate and the latest calendar month are diagnostics. `compute_index` still receives {_num(PUBLISHED_INCIDENT_RATE, 1)}.

## Where 2723.0 comes from

Before that pull request the fetcher read the local file `runtime/data/final_sample.csv`. Every row's `Last Updated` is **{local['file_updated']}**. The usable sample is **{local['lex']['agencies']}** agencies. The fetcher took the lexicographic maximum of the `Date` text, which is **{local['lex_label']}**, and the unweighted mean of agency rates that month is **{_num(local['lex']['unweighted'], 1)}**. That is the locked input.

The latest calendar month in that same local file is **{local['calendar_label']}** at **{_num(local['calendar']['unweighted'])}**. "September" sorts after "December", so the text-sort rule stayed on September 2024 while a later month was already in the file. The weekly runs kept reprinting {_num(PUBLISHED_INCIDENT_RATE, 1)} because the local file and that sort rule did not move.

The current file's September 2024 rate is **{_num(sep_2024['crime_value'])}** on **{sep_2024['agencies']}** agencies. {_num(PUBLISHED_INCIDENT_RATE, 1)} is the old file's September 2024 print. It is a different sample from the rates in the tables below.

## How the live-crime column is built

The score is `compute_index`. Crime endpoints stay **{lo:g} to {hi:g}**. The crime weight stays **{weight:.2f}**. The other five weights are unchanged, so a full row still divides by **{sum(WEIGHTS.values()):.2f}**. Trust stays inverted. Bands stay 70, 55, and 40.

The crime value is the unweighted mean of agency rates for the latest calendar month in the RTCI cleaned file that was on [AH-Datalytics/rtci](https://github.com/AH-Datalytics/rtci) `main` at the start of that publication date:

`(Violent Crime_mvs_12mo + Property Crime_mvs_12mo) / FBI.Population.Covered × 100,000`

Rows with a missing count or a non-positive population are left out. That is the same construction as the crime diagnostic. The population-weighted alternative is stored on the vintage file and is not scored.

Committed index history runs from **{first['date']}** through **{latest['date']}**. There is no earlier six-metric publication to rescore. Weeks between RTCI releases keep the latest month already in the file.

| What changed | What stayed |
| --- | --- |
| Crime raw value | Inflation, unemployment, debt-to-GDP, homelessness, and trust on that weekly row |
| Which RTCI month supplied that value | v1.0.0 endpoints, weights, trust inversion, clamp, and divide-by-sum-of-weights |

## RTCI file on each publication date

The four files below are the `docs/app_data/final_sample.csv` commits on RTCI `main` during this history. The May 18 row is the later commit that day (`40c9ab09`), after the population regenerate. No weekly publication falls on an RTCI commit date, so the publication date is enough to pick the file.

{vintage_table}

February 2026 moved from 2146.38 to 2146.42 on 24 April 2026. Both round to the same index on the weeks that use them. March 2026 and April 2026 are new months, on a larger agency sample (498, then 612, then 621).

## Publication table

Live-crime score: the other five published inputs, with crime set to the latest calendar month in the file above.

{publication_table}

## Text-sort month, for the snapshot figure

The pre-lock fetcher selected `Date.max()`, a text sort. On every file in this window that sort lands on **September 2025**. The snapshot diagnostics still report that month: candidate **{_num(SNAPSHOT_CANDIDATE_RATE)}**. The rate itself moved as the sample grew: 2285.03 (498 agencies), then 2229.84 (612), then **{_num(SNAPSHOT_CANDIDATE_RATE)}** (621). On the {latest['date']} basket, {_num(SNAPSHOT_CANDIDATE_RATE)} scores **{_num(candidate['score'])}** against the published **{_num(latest['locked_index'])}**.

Across the {len(publication_rows)} weeks this rule lifts the index by **{_num(min(lex_deltas))} to {_num(max(lex_deltas))}** points. The band stays {bands[0]}.

{lex_table}

## Monthly RTCI on the current file

`runtime/backtest/fixtures/v2/RTCI_monthly.csv` is the June 16 file (commit `bc66ee94`, pull recorded 26 September 2026). It matches the 2 October snapshot: September 2025 **{_num(candidate['crime_value'])}**, April 2026 **{_num(newest['crime_value'])}**, 621 agencies, population-weighted April 2026 **{_num(newest['population_weighted'])}**.

The table scores each month from September 2024 through April 2026 on the **{latest['date']}** inputs. Inflation, unemployment, debt, homelessness, and trust stay on that one row. These are revised rates in the current file. An earlier Friday's file had a smaller sample and a different rate for the same month. The publication table above is the rate that was available that day.

{monthly_table}

September 2024 in this file is {_num(sep_2024['crime_value'])} and scores {_num(sep_2024['score'])} on the latest basket. April 2026 is {_num(newest['crime_value'])} and scores {_num(newest['score'])}. The path between them is a lower rate on a fixed 621-agency sample. The further gap from the locked {_num(PUBLISHED_INCIDENT_RATE, 1)} down to {_num(sep_2024['crime_value'])} is the old 399-agency print against this revised sample.

## How to run

From the repository root:

```bash
python -m runtime.backtest.crime_live_replay
```

That rewrites this note, `runtime/backtest/output/crime_live_publications.csv`, and `runtime/backtest/output/crime_live_monthly.csv`. No network and no `FRED_API_KEY`. The vintage rates are checked in at `runtime/backtest/fixtures/crime_asof_vintages.csv`.

## What stays put

The weekly publisher, `docs/data/latest.json`, and `runtime/data/weekly_bugout_index.csv` still carry crime **{_num(PUBLISHED_INCIDENT_RATE, 1)}** and the {latest['date']} index **{_num(latest['locked_index'])}**. This note is a side calculation for a later decision about whether to accept a new crime input. It is not that decision.
"""


def _write_csv(path: Path, rows: Sequence[Mapping[str, object]], columns: Sequence[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(columns), lineterminator="\n", extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            rendered = {}
            for column in columns:
                value = row[column]
                if isinstance(value, float):
                    rendered[column] = f"{value:.2f}"
                else:
                    rendered[column] = value
            writer.writerow(rendered)


PUBLICATION_COLUMNS = (
    "date",
    "locked_index",
    "locked_band",
    "live_index",
    "live_band",
    "live_difference",
    "crime_value",
    "rtci_month",
    "rtci_month_start",
    "agencies",
    "population_weighted",
    "rtci_commit_date",
    "rtci_sha",
    "lex_index",
    "lex_band",
    "lex_difference",
    "lex_crime_value",
    "lex_rtci_month",
    "lex_month_start",
    "lex_agencies",
)
MONTHLY_COLUMNS = (
    "rtci_month",
    "rtci_month_start",
    "crime_value",
    "agencies",
    "population_weighted",
    "score",
    "band",
    "difference",
    "basket_publication",
    "locked_index",
)


def write_outputs(output_dir: Path = OUTPUT_DIR, note_path: Optional[Path] = None) -> list[Path]:
    publication_rows = build_publication_rows()
    monthly_rows = build_monthly_rows(publication_rows)
    note = PACKAGE_DIR / NOTE_NAME if note_path is None else note_path
    publications = output_dir / PUBLICATION_CSV_NAME
    monthly = output_dir / MONTHLY_CSV_NAME
    _write_csv(publications, publication_rows, PUBLICATION_COLUMNS)
    _write_csv(monthly, monthly_rows, MONTHLY_COLUMNS)
    note.write_text(render_markdown(publication_rows, monthly_rows), encoding="utf-8")
    return [publications, monthly, note]


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m runtime.backtest.crime_live_replay",
        description=(
            "Rescore committed weekly publications with the RTCI month that "
            "was available that day. Does not change the live score."
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
