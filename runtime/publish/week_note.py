# BugOutIndex
# Copyright (C) 2025 Adam Montville
# Dual-licensed under AGPL-3.0 and a commercial license.
"""
Deterministic homepage copy: tile ages and the weekly note.

Every numeral comes from the snapshot (or from subtracting two numerals
that are themselves in the snapshot). No model is called.
"""
from __future__ import annotations

import re
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from runtime.publish.observation_dates import (
    FAKE_FETCH_TIMESTAMPS,
    NEW_PERIOD,
    REVISION,
    UNCHANGED,
    classify_core_change,
    normalize_observation_date,
    observation_column,
)

# Pulse observations older than this, relative to the publication date, are
# labeled stale. A year catches a series stuck on a prior-year print
# (OECD business confidence, dated 2024-01-01) without flagging a quarterly
# core series that is still the latest official reading.
PULSE_STALE_AFTER_DAYS = 365

CORE_ORDER = (
    "inflation_rate",
    "incident_rate",
    "unemployment_rate",
    "debt_to_gdp_ratio",
    "homelessness_rate",
    "trust_in_government",
)

CORE_TITLES = {
    "inflation_rate": "inflation",
    "incident_rate": "crime",
    "unemployment_rate": "unemployment",
    "debt_to_gdp_ratio": "debt-to-GDP",
    "homelessness_rate": "homelessness",
    "trust_in_government": "trust in government",
}

PULSE_ORDER = (
    "initial_jobless_claims",
    "consumer_sentiment_umich",
    "business_confidence",
    "yield_curve_10y_2y",
    "vix",
)

PULSE_TITLES = {
    "initial_jobless_claims": "initial jobless claims",
    "consumer_sentiment_umich": "U. Michigan consumer sentiment",
    "business_confidence": "OECD business confidence",
    "yield_curve_10y_2y": "the Treasury yield spread",
    "vix": "VIX",
}

MARKET_ORDER = (
    ("gold_usd_per_oz", "gold"),
    ("silver_usd_per_oz", "silver"),
    ("dxy", "the US dollar index"),
)

_NUMBER_TOKEN = re.compile(r"[-+]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?")
_ISO_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")


def format_number(value: Any) -> str:
    """Shortest fixed-point spelling that round-trips through float."""
    number = float(value)
    negative = number < 0
    magnitude = abs(number)
    spelling = None
    for digits in range(0, 18):
        text = f"{magnitude:.{digits}f}"
        if float(text) == magnitude:
            spelling = text
            break
    if spelling is None:
        spelling = f"{magnitude:.18f}"
    return ("-" if negative else "") + _comma(spelling)


def format_index(value: Any) -> str:
    """Published index precision is two decimal places."""
    return f"{float(value):.2f}"


def format_change(previous: Any, current: Any) -> str:
    """Signed difference of the spellings ``format_number`` will print."""
    delta = Decimal(format_number(current).replace(",", "")) - Decimal(
        format_number(previous).replace(",", "")
    )
    return _signed_decimal(delta)


def format_index_change(previous: Any, current: Any) -> str:
    delta = Decimal(format_index(current)) - Decimal(format_index(previous))
    return f"{delta:+.2f}"


def describe_core_age(key: str, entry: Optional[dict], publication: str) -> Dict[str, Any]:
    """Age line for one core tile. ``stale`` stays false; core uses honest dating instead."""
    entry = entry or {}
    published = _as_date(publication)
    provenance = entry.get("provenance") or {}
    kind = provenance.get("kind")
    fetched = entry.get("source_fetched_at")
    fake = _is_fake(fetched)

    if kind == "manual" or (key == "homelessness_rate" and (fake or not fetched)):
        return {"text": _manual_age(provenance, published), "stale": False}

    if kind == "file" or (key == "incident_rate" and (fake or not fetched)):
        return {"text": _file_age(provenance, published), "stale": False}

    if kind == "annual" or _is_year(fetched):
        year = str(provenance.get("year") or fetched)
        return {"text": _annual_age(year, published), "stale": False}

    observed = _as_date(_generic_stamp(entry))
    if observed is None or published is None:
        if fetched and not fake:
            return {"text": f"as of {fetched}", "stale": False}
        return {"text": "observation date not recorded", "stale": False}
    days = (published - observed).days
    return {"text": f"observed {observed.isoformat()} · {_days_old(days)}", "stale": False}


def describe_pulse_age(
    observed_on: Optional[str],
    publication: str,
    *,
    flat: bool = False,
) -> Dict[str, Any]:
    """Age line for one pulse tile, including a stale mark when the print is old."""
    published = _as_date(publication)
    observed = _as_date(observed_on)
    if observed is None or published is None:
        return {"text": "observation date not recorded", "stale": False}
    days = (published - observed).days
    stale = days > PULSE_STALE_AFTER_DAYS
    bits = [f"observed {observed.isoformat()}", _days_old(days)]
    if flat:
        bits.append("unchanged across recorded weeks")
    if stale:
        bits.append("stale")
    return {"text": " · ".join(bits), "stale": stale}


def series_is_flat(values: Sequence[Any]) -> bool:
    numbers: List[float] = []
    for value in values:
        if value in ("", None):
            continue
        try:
            numbers.append(float(value))
        except (TypeError, ValueError):
            continue
    # A two-week tie is just "stayed at" for this week. Reserve the
    # "unchanged across recorded weeks" label for a longer flat history.
    if len(numbers) < 4:
        return False
    return max(numbers) - min(numbers) <= 1e-9


def build_week_note(snapshot: Dict[str, Any]) -> List[str]:
    """Four to eight sentences comparing this snapshot with the prior history row."""
    publication = str(snapshot.get("publication_date") or "")
    current_index = snapshot.get("bugout_index")
    prior_core = _prior_row(_history(snapshot, "bugout_index"), publication)
    prior_pulse = _prior_row(_history(snapshot, "pulse"), publication)
    prior_markets = _prior_row(_history(snapshot, "markets"), publication)

    if prior_core is None:
        sentences = [
            f"The BugOut Index is {format_index(current_index)} for the week of {publication}.",
            "No earlier history row is available, so week-over-week changes are not reported.",
            "Core readings: " + "; ".join(_core_level_clauses(snapshot)) + ".",
            _pulse_level_sentence(snapshot),
            _market_level_sentence(snapshot),
            _disclaimer(snapshot),
        ]
        return sentences

    prev_date = prior_core.get("date")
    if _same(current_index, prior_core.get("bugout_index")):
        index_sentence = (
            f"The BugOut Index is {format_index(current_index)}, unchanged from "
            f"{format_index(prior_core.get('bugout_index'))} on {prev_date}."
        )
    else:
        index_sentence = (
            f"The BugOut Index moved from {format_index(prior_core.get('bugout_index'))} "
            f"on {prev_date} to {format_index(current_index)}, a change of "
            f"{format_index_change(prior_core.get('bugout_index'), current_index)} points."
        )

    changed, unchanged = _core_changes(snapshot, prior_core)
    sentences = [index_sentence]
    if changed:
        sentences.append(_join(changed) + ".")
        if unchanged:
            sentences.append("Unchanged core inputs: " + "; ".join(unchanged) + ".")
        else:
            sentences.append("Every core input changed.")
    else:
        sentences.append("No core raw value changed: " + "; ".join(unchanged) + ".")

    pulse_moved, pulse_still = _pulse_changes(snapshot, prior_pulse)
    if pulse_moved:
        sentences.append(_join(pulse_moved) + ".")
    else:
        sentences.append("No pulse series moved" + _pulse_still_tail(pulse_still) + ".")
    if pulse_moved and pulse_still:
        sentences.append("Unchanged pulse series: " + "; ".join(pulse_still) + ".")

    market_moved, market_still = _market_changes(snapshot, prior_markets)
    fetched = (snapshot.get("markets") or {}).get("fetched_at")
    if market_moved:
        sentence = _join(market_moved)
        if fetched:
            sentence += f"; markets fetched {fetched}"
        sentences.append(sentence + ".")
    else:
        detail = (": " + "; ".join(market_still)) if market_still else ""
        fetched_bit = f" (markets fetched {fetched})" if fetched else ""
        sentences.append(f"No market series moved{detail}{fetched_bit}.")

    sentences.append(_disclaimer(snapshot))
    return sentences


def unexplained_numerals(sentences: Sequence[str], snapshot: Dict[str, Any]) -> List[str]:
    """Numeric tokens in the note that are not snapshot values, date parts, or pair deltas."""
    allowed = _allowed_decimals(snapshot)
    missing: List[str] = []
    for sentence in sentences:
        scrubbed = _ISO_DATE.sub(" ", sentence)
        for token in _NUMBER_TOKEN.findall(scrubbed):
            number = Decimal(token.replace(",", ""))
            if number not in allowed:
                missing.append(token)
    return missing


# ---------------------------------------------------------------- internals


def _disclaimer(snapshot: Dict[str, Any]) -> str:
    """Companions stay outside the score. Labor is named only when it is present."""
    labor = snapshot.get("labor_shadow") or {}
    values = labor.get("values") or {}
    present = any(values.get(key) is not None for key in ("prime_age_epop", "prime_age_lfpr"))
    if present:
        return (
            "Markets, the short-term pulse, and the labor-utilization shadow series "
            "are not inputs to the BugOut Index score."
        )
    return "Markets and the short-term pulse are not inputs to the BugOut Index score."


def _manual_age(provenance: dict, published: Optional[date]) -> str:
    last_set = provenance.get("last_set") or "a manual annual input"
    period = provenance.get("observation_period")
    bits = [f"manual, last set {last_set}"]
    if period:
        bits.append(str(period))
    anchor = _as_date(provenance.get("reference_date"))
    if anchor is not None and published is not None:
        days = (published - anchor).days
        bits.append(_days_since(days, anchor))
    return " · ".join(bits)


def _file_age(provenance: dict, published: Optional[date]) -> str:
    value_month = provenance.get("value_month")
    file_through = provenance.get("file_through")
    file_updated = provenance.get("file_updated")
    if not value_month:
        if file_through:
            return f"file vintage · crime file through {file_through}"
        return "file vintage · last known month not recorded in this snapshot"
    if file_through and file_through != value_month:
        bits = [f"file vintage · value month {value_month}"]
    else:
        bits = [f"file vintage · last known month {value_month}"]
    anchor = _as_date(provenance.get("value_month_end"))
    if anchor is not None and published is not None:
        days = (published - anchor).days
        bits.append(_days_since(days, anchor))
    if file_through:
        bits.append(f"crime file through {file_through}")
    if file_updated:
        bits.append(f"file updated {file_updated}")
    return " · ".join(bits)


def _annual_age(year: str, published: Optional[date]) -> str:
    if not _is_year(year):
        return f"annual, last set {year}"
    anchor = date(int(year), 1, 1)
    if published is None:
        return f"annual, last set {year}"
    days = (published - anchor).days
    return f"annual, last set {year} · {_days_since(days, anchor)}"


def _core_level_clauses(snapshot: dict) -> List[str]:
    metrics = snapshot.get("metrics") or {}
    clauses = []
    for key in CORE_ORDER:
        entry = metrics.get(key) or {}
        raw = entry.get("raw")
        if raw is None:
            continue
        clauses.append(f"{CORE_TITLES[key]} is {format_number(raw)} ({_dating_phrase(key, entry)})")
    return clauses


def _core_changes(snapshot: dict, prior: dict) -> Tuple[List[str], List[str]]:
    metrics = snapshot.get("metrics") or {}
    changed: List[str] = []
    unchanged: List[str] = []
    for key in CORE_ORDER:
        entry = metrics.get(key) or {}
        current = entry.get("raw")
        if current is None:
            continue
        title = CORE_TITLES[key]
        dating = _dating_phrase(key, entry)
        previous = prior.get(key)
        kind = classify_core_change(
            previous,
            current,
            prior.get(observation_column(key)),
            entry.get("observation_date"),
        )
        if kind == UNCHANGED:
            unchanged.append(f"{title} stayed at {format_number(current)} ({dating})")
            continue
        changed.append(_change_clause(title, previous, current, dating, kind, prior, key, entry))
    return changed, unchanged


def _change_clause(title, previous, current, dating, kind, prior, key, entry) -> str:
    """One core move. A same-date value change is named as a revision."""
    delta = format_change(previous, current)
    if kind == REVISION:
        observed = normalize_observation_date(entry.get("observation_date"))
        return (
            f"{title} was revised from {format_number(previous)} to {format_number(current)} "
            f"for the same observation date {observed} "
            f"{_change_tail(delta, dating, observed)}"
        )
    if kind == NEW_PERIOD:
        previous_observed = normalize_observation_date(prior.get(observation_column(key)))
        current_observed = normalize_observation_date(entry.get("observation_date"))
        return (
            f"{title} changed from {format_number(previous)} (observed {previous_observed}) "
            f"to {format_number(current)} (observed {current_observed}) "
            f"{_change_tail(delta, dating, previous_observed, current_observed)}"
        )
    return (
        f"{title} changed from {format_number(previous)} to {format_number(current)} "
        f"(change of {delta}; {dating})"
    )


def _change_tail(delta: str, dating: str, *already_stated: Optional[str]) -> str:
    """Skip a dating phrase that only repeats an observation date already in the clause."""
    repeated = any(dating == f"observed {stated}" for stated in already_stated if stated)
    if repeated:
        return f"(change of {delta})"
    return f"(change of {delta}; {dating})"


def _pulse_level_sentence(snapshot: dict) -> str:
    pulse = snapshot.get("pulse") or {}
    values = pulse.get("values") or {}
    dates = pulse.get("dates") or {}
    published = str(snapshot.get("publication_date") or "")
    history = _history(snapshot, "pulse")
    clauses = []
    for key in PULSE_ORDER:
        if values.get(key) is None:
            continue
        flat = series_is_flat([row.get(key) for row in history])
        clauses.append(
            f"{PULSE_TITLES[key]} is {format_number(values[key])} "
            f"({_pulse_dating(dates.get(key), published, flat=flat)})"
        )
    if not clauses:
        return "No pulse values were recorded in this snapshot."
    return "Pulse readings: " + "; ".join(clauses) + "."


def _pulse_changes(snapshot: dict, prior: Optional[dict]) -> Tuple[List[str], List[str]]:
    pulse = snapshot.get("pulse") or {}
    values = pulse.get("values") or {}
    dates = pulse.get("dates") or {}
    published = str(snapshot.get("publication_date") or "")
    history = _history(snapshot, "pulse")
    moved: List[str] = []
    still: List[str] = []
    for key in PULSE_ORDER:
        current = values.get(key)
        if current is None:
            continue
        title = PULSE_TITLES[key]
        flat = series_is_flat([row.get(key) for row in history])
        dating = _pulse_dating(dates.get(key), published, flat=flat)
        previous = None if prior is None else prior.get(key)
        if previous in ("", None) or _same(current, previous):
            still.append(f"{title} stayed at {format_number(current)} ({dating})")
            continue
        moved.append(
            f"{title} changed from {format_number(previous)} to {format_number(current)} "
            f"(change of {format_change(previous, current)}; {dating})"
        )
    return moved, still


def _pulse_still_tail(still: Sequence[str]) -> str:
    if not still:
        return ""
    return ": " + "; ".join(still)


def _market_level_sentence(snapshot: dict) -> str:
    markets = snapshot.get("markets") or {}
    clauses = []
    for key, title in MARKET_ORDER:
        if markets.get(key) is None:
            continue
        clauses.append(f"{title} is {format_number(markets[key])}")
    fetched = markets.get("fetched_at")
    fetched_bit = f" Markets fetched {fetched}." if fetched else ""
    if not clauses:
        return "No market values were recorded in this snapshot." + fetched_bit
    return "Market readings: " + "; ".join(clauses) + "." + fetched_bit


def _market_changes(snapshot: dict, prior: Optional[dict]) -> Tuple[List[str], List[str]]:
    markets = snapshot.get("markets") or {}
    moved: List[str] = []
    still: List[str] = []
    for key, title in MARKET_ORDER:
        current = markets.get(key)
        if current is None:
            continue
        previous = None if prior is None else prior.get(key)
        if previous in ("", None) or _same(current, previous):
            still.append(f"{title} stayed at {format_number(current)}")
            continue
        moved.append(
            f"{title} changed from {format_number(previous)} to {format_number(current)} "
            f"(change of {format_change(previous, current)})"
        )
    return moved, still


def _dating_phrase(key: str, entry: dict) -> str:
    provenance = entry.get("provenance") or {}
    kind = provenance.get("kind")
    fetched = entry.get("source_fetched_at")
    if kind == "manual" or (key == "homelessness_rate" and (_is_fake(fetched) or not fetched)):
        last_set = provenance.get("last_set") or "a manual annual input"
        return f"manual, last set {last_set}"
    if kind == "file" or (key == "incident_rate" and (_is_fake(fetched) or not fetched)):
        month = provenance.get("value_month")
        through = provenance.get("file_through")
        updated = provenance.get("file_updated")
        if not month:
            if through:
                return f"crime file through {through}"
            return "file vintage"
        if through and through != month:
            phrase = f"file vintage, value month {month}; crime file through {through}"
        else:
            phrase = f"file vintage, last known month {month}"
            if through:
                phrase += f"; crime file through {through}"
        if updated:
            phrase += f"; file updated {updated}"
        return phrase
    if kind == "annual" or _is_year(fetched):
        year = provenance.get("year") or fetched
        return f"annual, {year}"
    stamp = _generic_stamp(entry)
    observed = _as_date(stamp)
    if observed is not None:
        return f"observed {observed.isoformat()}"
    if stamp and not _is_fake(stamp):
        return f"observed {stamp}"
    return "observation date not recorded"


def _generic_stamp(entry: dict):
    """Calendar observation date, or ``source_fetched_at`` when that is all we have."""
    observed = normalize_observation_date(entry.get("observation_date"))
    if observed and len(observed) == 10:
        return observed
    return entry.get("source_fetched_at")


def _pulse_dating(observed_on: Optional[str], publication: str, *, flat: bool) -> str:
    if not observed_on or _is_fake(observed_on):
        return "observation date not recorded"
    bits = [f"observed {observed_on}"]
    published = _as_date(publication)
    observed = _as_date(observed_on)
    if published is not None and observed is not None and (published - observed).days > PULSE_STALE_AFTER_DAYS:
        bits.append("stale")
    if flat:
        bits.append("unchanged across recorded weeks")
    return ", ".join(bits)


def _history(snapshot: dict, key: str) -> List[dict]:
    history = snapshot.get("history") or {}
    rows = history.get(key) or []
    return [row for row in rows if isinstance(row, dict)]


def _prior_row(rows: Sequence[dict], publication: str) -> Optional[dict]:
    if not rows:
        return None
    if str(rows[-1].get("date")) == publication:
        if len(rows) < 2:
            return None
        return rows[-2]
    return rows[-1]


def _same(left: Any, right: Any) -> bool:
    try:
        a = float(left)
        b = float(right)
    except (TypeError, ValueError):
        return False
    return abs(a - b) <= 1e-6 * max(1.0, abs(a), abs(b))


def _as_date(value: Any) -> Optional[date]:
    if value is None:
        return None
    text = str(value).strip()
    if not text or _is_fake(text):
        return None
    if len(text) >= 10 and text[4] == "-" and text[7] == "-":
        try:
            return datetime.strptime(text[:10], "%Y-%m-%d").date()
        except ValueError:
            return None
    return None


def _is_year(value: Any) -> bool:
    text = str(value).strip() if value is not None else ""
    return len(text) == 4 and text.isdigit()


def _is_fake(value: Any) -> bool:
    return str(value).strip() in FAKE_FETCH_TIMESTAMPS if value is not None else False


def _comma(spelling: str) -> str:
    if "." in spelling:
        whole, frac = spelling.split(".", 1)
        if whole.isdigit() and int(whole) >= 1000:
            return f"{int(whole):,}.{frac}"
        return spelling
    if spelling.isdigit() and int(spelling) >= 1000:
        return f"{int(spelling):,}"
    return spelling


def _signed_decimal(delta: Decimal) -> str:
    text = format(delta, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    if text in ("", "-"):
        text = "0"
    if text.startswith("-"):
        return "-" + _comma(text[1:])
    return "+" + _comma(text)


def _days_old(days: int) -> str:
    noun = "day" if abs(days) == 1 else "days"
    return f"{days} {noun} old"


def _days_since(days: int, anchor: date) -> str:
    noun = "day" if abs(days) == 1 else "days"
    return f"{days} {noun} since {anchor.isoformat()}"


def _cap_first(text: str) -> str:
    if not text:
        return text
    return text[0].upper() + text[1:]


def _join(clauses: Sequence[str]) -> str:
    parts = list(clauses)
    if not parts:
        return ""
    parts[0] = _cap_first(parts[0])
    if len(parts) == 1:
        return parts[0]
    if len(parts) == 2:
        return f"{parts[0]}, and {parts[1]}"
    return ", ".join(parts[:-1]) + ", and " + parts[-1]


def _allowed_decimals(snapshot: Dict[str, Any]) -> set:
    allowed = set()
    for number in _walk_numbers(snapshot):
        allowed.add(Decimal(format_number(number).replace(",", "")))
    for text in _walk_strings(snapshot):
        for token in re.findall(r"\d+(?:\.\d+)?", text):
            allowed.add(Decimal(token))
    publication = str(snapshot.get("publication_date") or "")
    pairs: List[Tuple[Any, Any]] = []
    prior_core = _prior_row(_history(snapshot, "bugout_index"), publication)
    if prior_core is not None and snapshot.get("bugout_index") is not None:
        pairs.append((prior_core.get("bugout_index"), snapshot.get("bugout_index")))
        metrics = snapshot.get("metrics") or {}
        for key in CORE_ORDER:
            raw = (metrics.get(key) or {}).get("raw")
            if raw is not None and prior_core.get(key) not in ("", None):
                pairs.append((prior_core.get(key), raw))
    prior_pulse = _prior_row(_history(snapshot, "pulse"), publication)
    pulse_values = (snapshot.get("pulse") or {}).get("values") or {}
    if prior_pulse is not None:
        for key in PULSE_ORDER:
            if pulse_values.get(key) is not None and prior_pulse.get(key) not in ("", None):
                pairs.append((prior_pulse.get(key), pulse_values.get(key)))
    prior_markets = _prior_row(_history(snapshot, "markets"), publication)
    markets = snapshot.get("markets") or {}
    if prior_markets is not None:
        for key, _title in MARKET_ORDER:
            if markets.get(key) is not None and prior_markets.get(key) not in ("", None):
                pairs.append((prior_markets.get(key), markets.get(key)))
    for previous, current in pairs:
        try:
            allowed.add(Decimal(format_change(previous, current).replace(",", "")))
            allowed.add(Decimal(format_index_change(previous, current)))
        except (TypeError, ValueError, ArithmeticError):
            continue
    return allowed


def _walk_numbers(node: Any) -> Iterable[float]:
    if isinstance(node, bool):
        return
    if isinstance(node, (int, float)):
        yield float(node)
        return
    if isinstance(node, dict):
        for value in node.values():
            yield from _walk_numbers(value)
        return
    if isinstance(node, list):
        for value in node:
            yield from _walk_numbers(value)


def _walk_strings(node: Any) -> Iterable[str]:
    if isinstance(node, str):
        yield node
        return
    if isinstance(node, dict):
        for value in node.values():
            yield from _walk_strings(value)
        return
    if isinstance(node, list):
        for value in node:
            yield from _walk_strings(value)
