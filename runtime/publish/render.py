# BugOutIndex
# Copyright (C) 2025 Adam Montville
# Dual-licensed under AGPL-3.0 and a commercial license.
"""
Static-site renderer. Consumes the snapshot produced by weekly_run.py and
writes three HTML pages (index, methodology, history) into /docs, plus
an SVG gauge and sparklines. No JS runtime required.
"""
from __future__ import annotations

import json
import math
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional

from jinja2 import Environment, FileSystemLoader, select_autoescape

REPO_ROOT = Path(__file__).resolve().parents[2]
DOCS = REPO_ROOT / "docs"
TEMPLATES = Path(__file__).parent / "templates"
STATIC = Path(__file__).parent / "static"


# ------------------------------------------------------------------ SVG helpers

def gauge_svg(value: float, width: int = 420, height: int = 240) -> str:
    """Semi-circular gauge, 0–100, with 4 risk bands."""
    v = max(0.0, min(100.0, float(value)))
    cx, cy, r = width / 2, height - 20, height - 40
    bands = [
        (0, 40, "#c0392b"),      # critical
        (40, 55, "#e67e22"),     # low
        (55, 70, "#f1c40f"),     # moderate
        (70, 100, "#27ae60"),    # high
    ]

    def polar(angle_deg: float) -> tuple:
        # 0 -> left (180°), 100 -> right (0°)
        a = math.radians(180 - angle_deg * 1.8)
        return cx + r * math.cos(a), cy - r * math.sin(a)

    def arc(start: float, end: float, color: str) -> str:
        x1, y1 = polar(start)
        x2, y2 = polar(end)
        large = 0
        return (f'<path d="M{x1:.2f},{y1:.2f} A{r},{r} 0 {large},1 {x2:.2f},{y2:.2f}" '
                f'stroke="{color}" stroke-width="22" fill="none" stroke-linecap="butt"/>')

    arcs = "".join(arc(s, e, c) for s, e, c in bands)
    # Needle
    nx, ny = polar(v)
    needle = (f'<line x1="{cx}" y1="{cy}" x2="{nx:.2f}" y2="{ny:.2f}" '
              f'stroke="#111" stroke-width="4" stroke-linecap="round"/>'
              f'<circle cx="{cx}" cy="{cy}" r="8" fill="#111"/>')
    labels = "".join(
        f'<text x="{polar(p)[0]:.1f}" y="{polar(p)[1]:.1f}" dy="-12" '
        f'text-anchor="middle" font-size="11" fill="#6b7280">{int(p)}</text>'
        for p in (0, 40, 55, 70, 100)
    )
    score = (f'<text x="{cx}" y="{cy - 40}" text-anchor="middle" '
             f'font-size="56" font-weight="700" fill="#111">{v:.1f}</text>'
             f'<text x="{cx}" y="{cy - 16}" text-anchor="middle" '
             f'font-size="12" fill="#6b7280">BugOut Index</text>')

    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
            f'role="img" aria-label="BugOut Index gauge: {v:.1f}">'
            f'{arcs}{labels}{needle}{score}</svg>')


def multiline_chart_svg(
    series: List[Dict[str, Any]],
    x_labels: List[str],
    width: int = 880,
    height: int = 320,
    pad_l: int = 64,
    pad_r: int = 20,
    pad_t: int = 32,
    pad_b: int = 44,
    title: Optional[str] = None,
    y_unit: str = "",
    y_digits: Optional[int] = None,
) -> str:
    """
    Render a multi-line chart as inline SVG.

    `series` is a list of {'label': str, 'color': str, 'values': [Optional[float]]}.
    Lines with all-None values are skipped. Missing points break the polyline
    so gaps show as gaps rather than artificial straight lines.
    """
    # Pull every numeric value to compute the y-domain.
    flat = [v for s in series for v in s["values"] if v is not None]
    if not flat or not x_labels:
        return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}">'
                f'<text x="{width/2}" y="{height/2}" text-anchor="middle" '
                f'font-size="13" fill="#9ca3af">no data yet</text></svg>')

    lo, hi = min(flat), max(flat)
    if hi == lo:
        hi = lo + 1.0
    # Add 5% headroom top and bottom for breathing room.
    span = hi - lo
    lo -= span * 0.05
    hi += span * 0.05
    span = hi - lo

    # Pick y-axis label precision so all 5 ticks are visually distinct.
    if y_digits is None:
        if span >= 100:
            y_digits = 0
        elif span >= 10:
            y_digits = 1
        elif span >= 1:
            y_digits = 2
        else:
            y_digits = 3

    plot_w = width - pad_l - pad_r
    plot_h = height - pad_t - pad_b
    n = len(x_labels)
    step = plot_w / max(1, n - 1)

    def x_at(i: int) -> float:
        return pad_l + i * step

    def y_at(v: float) -> float:
        return pad_t + plot_h - ((v - lo) / span) * plot_h

    # --- gridlines (5 horizontal) + y-axis labels
    gridlines: List[str] = []
    y_labels: List[str] = []
    for i in range(5):
        frac = i / 4
        y = pad_t + plot_h * frac
        val = hi - frac * span
        gridlines.append(
            f'<line x1="{pad_l}" y1="{y:.1f}" x2="{pad_l + plot_w}" y2="{y:.1f}" '
            f'stroke="#e5e7eb" stroke-width="1"/>'
        )
        y_labels.append(
            f'<text x="{pad_l - 8}" y="{y + 4:.1f}" text-anchor="end" '
            f'font-size="11" fill="#6b7280">{val:,.{y_digits}f}{y_unit}</text>'
        )

    # --- x-axis labels: show ~6 ticks evenly spaced.
    x_ticks: List[str] = []
    n_ticks = min(6, n)
    if n_ticks > 1:
        for t in range(n_ticks):
            i = round(t * (n - 1) / (n_ticks - 1))
            x_ticks.append(
                f'<text x="{x_at(i):.1f}" y="{height - 18}" text-anchor="middle" '
                f'font-size="11" fill="#6b7280">{x_labels[i]}</text>'
            )

    # --- lines (with gaps for None)
    line_paths: List[str] = []
    legend_items: List[str] = []
    for s in series:
        vals = s["values"]
        if all(v is None for v in vals):
            continue
        # Build piecewise polylines so missing points create true gaps.
        run: List[str] = []
        runs: List[List[str]] = []
        for i, v in enumerate(vals):
            if v is None:
                if run:
                    runs.append(run)
                    run = []
                continue
            run.append(f"{x_at(i):.1f},{y_at(v):.1f}")
        if run:
            runs.append(run)
        for r in runs:
            line_paths.append(
                f'<polyline points="{" ".join(r)}" fill="none" '
                f'stroke="{s["color"]}" stroke-width="2" stroke-linejoin="round"/>'
            )
        # End-of-line dot + legend swatch
        last = next((v for v in reversed(vals) if v is not None), None)
        if last is not None:
            last_i = max(i for i, v in enumerate(vals) if v is not None)
            line_paths.append(
                f'<circle cx="{x_at(last_i):.1f}" cy="{y_at(last):.1f}" '
                f'r="3" fill="{s["color"]}"/>'
            )
        legend_items.append((s["label"], s["color"]))

    # --- legend (inline, below plot)
    legend = []
    lx = pad_l
    ly = height - 4
    for label, color in legend_items:
        legend.append(
            f'<rect x="{lx}" y="{ly - 9}" width="10" height="10" fill="{color}" rx="2"/>'
            f'<text x="{lx + 14}" y="{ly}" font-size="11" fill="#374151">{label}</text>'
        )
        lx += 14 + (len(label) * 6.5) + 18  # rough advance

    title_svg = (
        f'<text x="{pad_l}" y="18" font-size="12" fill="#374151" '
        f'font-weight="600">{title}</text>'
        if title else ""
    )

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'role="img" class="chart-multiline">'
        f'{title_svg}'
        f'{"".join(gridlines)}{"".join(y_labels)}{"".join(x_ticks)}'
        f'{"".join(line_paths)}{"".join(legend)}'
        f'</svg>'
    )


def sparkline_svg(values: List[Optional[float]], width: int = 120, height: int = 36) -> str:
    clean = [float(v) for v in values if v is not None and not isinstance(v, bool)]
    if len(clean) < 2:
        return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}">'
                f'<text x="{width/2}" y="{height/2+4}" text-anchor="middle" '
                f'font-size="10" fill="#9ca3af">no trend</text></svg>')
    lo, hi = min(clean), max(clean)
    span = hi - lo or 1.0
    pts = []
    for i, v in enumerate(values):
        x = (i / max(1, len(values) - 1)) * (width - 4) + 2
        if v is None:
            continue
        y = height - 2 - ((float(v) - lo) / span) * (height - 4)
        pts.append(f"{x:.1f},{y:.1f}")
    path = f'<polyline points="{ " ".join(pts) }" fill="none" stroke="#374151" stroke-width="1.5"/>'
    last_x, last_y = pts[-1].split(",")
    dot = f'<circle cx="{last_x}" cy="{last_y}" r="2.2" fill="#111"/>'
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
            f'class="sparkline">{path}{dot}</svg>')


# ------------------------------------------------------------------ Formatting

METRIC_LABELS = {
    "inflation_rate": {"label": "Inflation Rate", "unit": "%", "source": "FRED (CPIAUCSL)",
                       "source_url": "https://fred.stlouisfed.org/series/CPIAUCSL"},
    "incident_rate": {"label": "Violent + Property Crime", "unit": "per 100k",
                      "source": "Real-Time Crime Index",
                      "source_url": "https://github.com/jacobkap/real_time_crime_index"},
    "unemployment_rate": {"label": "Unemployment Rate", "unit": "%", "source": "FRED (UNRATE)",
                          "source_url": "https://fred.stlouisfed.org/series/UNRATE"},
    "debt_to_gdp_ratio": {"label": "Debt-to-GDP Ratio", "unit": "%",
                          "source": "FRED (GFDEGDQ188S)",
                          "source_url": "https://fred.stlouisfed.org/series/GFDEGDQ188S"},
    "homelessness_rate": {"label": "Homelessness Rate", "unit": "% of pop.",
                          "source": "HUD AHAR",
                          "source_url": "https://www.huduser.gov/portal/sites/default/files/pdf/2024-AHAR-Part-1.pdf"},
    "trust_in_government": {"label": "Trust in Government", "unit": "% confidence",
                            "source": "Edelman Trust Barometer",
                            "source_url": "https://www.edelman.com/trust"},
}

PULSE_LABELS = {
    "initial_jobless_claims": ("Initial Jobless Claims", "persons", "ICSA"),
    "consumer_sentiment_umich": ("U. Michigan Consumer Sentiment", "index", "UMCSENT"),
    "business_confidence": ("OECD Business Confidence (US)", "index", "BSCICP03USM665S"),
    "yield_curve_10y_2y": ("10y − 2y Treasury Spread", "%", "T10Y2Y"),
    "vix": ("VIX (Volatility)", "index", "VIXCLS"),
}


def _fmt(val, unit: str = "", digits: int = 2) -> str:
    if val is None:
        return "—"
    try:
        f = float(val)
    except (TypeError, ValueError):
        return str(val)
    if unit == "persons":
        return f"{f:,.0f}"
    return f"{f:,.{digits}f}{unit and (' ' + unit)}"


def _pct_delta(current, previous) -> Optional[float]:
    try:
        c, p = float(current), float(previous)
        if p == 0:
            return None
        return (c - p) / p * 100
    except (TypeError, ValueError):
        return None


def _series(history: list, key: str) -> list:
    vals = []
    for r in history:
        v = r.get(key)
        if v in ("", None):
            vals.append(None)
        else:
            try:
                vals.append(float(v))
            except ValueError:
                vals.append(None)
    return vals


# ------------------------------------------------------------------ Rendering

def render_site(snapshot: Dict[str, Any]) -> None:
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES)),
        autoescape=select_autoescape(["html", "xml"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.filters["fmt"] = _fmt

    DOCS.mkdir(exist_ok=True)
    (DOCS / "assets").mkdir(exist_ok=True)
    shutil.copy(STATIC / "style.css", DOCS / "assets" / "style.css")

    # Prepare metric view-models
    boi_history = snapshot.get("history", {}).get("bugout_index", [])
    markets_history = snapshot.get("history", {}).get("markets", [])
    pulse_history = snapshot.get("history", {}).get("pulse", [])

    boi_series = _series(boi_history, "bugout_index")
    metrics_vm = []
    for key, meta in METRIC_LABELS.items():
        entry = snapshot["metrics"].get(key, {})
        metric_series = _series(boi_history, key)
        metrics_vm.append({
            "key": key,
            "label": meta["label"],
            "unit": meta["unit"],
            "source": meta["source"],
            "source_url": meta["source_url"],
            "raw": entry.get("raw"),
            "normalized": entry.get("normalized"),
            "weight_pct": round(entry.get("weight", 0) * 100, 1),
            "sparkline": sparkline_svg(metric_series),
            "as_of": entry.get("source_fetched_at"),
        })

    markets = snapshot.get("markets", {})
    market_tiles = []
    for key, label, unit in [
        ("gold_usd_per_oz", "Gold", "USD/oz"),
        ("silver_usd_per_oz", "Silver", "USD/oz"),
        ("dxy", "US Dollar Index", "DXY"),
    ]:
        series = _series(markets_history, key)
        prev = series[-2] if len(series) >= 2 else None
        curr = markets.get(key)
        delta = _pct_delta(curr, prev)
        market_tiles.append({
            "label": label, "unit": unit, "value": curr,
            "delta": delta, "sparkline": sparkline_svg(series),
        })

    pulse_values = snapshot.get("pulse", {}).get("values", {})
    pulse_dates = snapshot.get("pulse", {}).get("dates", {})
    pulse_tiles = []
    for key, (label, unit, sid) in PULSE_LABELS.items():
        series = _series(pulse_history, key)
        pulse_tiles.append({
            "label": label,
            "unit": unit,
            "value": pulse_values.get(key),
            "as_of": pulse_dates.get(key),
            "source_id": sid,
            "sparkline": sparkline_svg(series),
        })

    # Week-over-week BOI delta
    boi_delta = None
    if len(boi_series) >= 2 and boi_series[-1] is not None and boi_series[-2] is not None:
        boi_delta = boi_series[-1] - boi_series[-2]

    ctx = {
        "snapshot": snapshot,
        "gauge": gauge_svg(snapshot["bugout_index"]),
        "boi_delta": boi_delta,
        "metrics": metrics_vm,
        "markets": market_tiles,
        "pulse": pulse_tiles,
        "history_count": len(boi_history),
    }

    (DOCS / "index.html").write_text(env.get_template("index.html.j2").render(**ctx))
    (DOCS / "methodology.html").write_text(env.get_template("methodology.html.j2").render(**ctx))
    (DOCS / "history.html").write_text(env.get_template("history.html.j2").render(
        boi_history=boi_history, markets_history=markets_history, pulse_history=pulse_history,
        metric_labels=METRIC_LABELS, pulse_labels=PULSE_LABELS, snapshot=snapshot,
    ))

    # Revisions page (PAYEMS vintages + UNRATE benchmark comparison).
    revisions = snapshot.get("revisions") or {}
    rev_ctx = _build_revisions_context(revisions)
    rev_ctx["snapshot"] = snapshot
    (DOCS / "revisions.html").write_text(env.get_template("revisions.html.j2").render(**rev_ctx))


def _build_revisions_context(revisions: Dict[str, Any]) -> Dict[str, Any]:
    """Shape revision data for the revisions template + render its charts."""
    payems_rows = revisions.get("payems") or []
    unrate = revisions.get("unrate") or {}
    unrate_rows = unrate.get("rows") or []

    # PAYEMS chart: three lines on the rolling 24-month window.
    payems_x = [r["observation_date"][:7] for r in payems_rows]  # YYYY-MM
    payems_chart = multiline_chart_svg(
        series=[
            {"label": "Initial release", "color": "#2563eb",
             "values": [r.get("vintage_initial") for r in payems_rows]},
            {"label": "+1 month revision", "color": "#d97706",
             "values": [r.get("vintage_first") for r in payems_rows]},
            {"label": "+2 month revision", "color": "#059669",
             "values": [r.get("vintage_second") for r in payems_rows]},
        ],
        x_labels=payems_x,
        title="Total nonfarm payrolls (PAYEMS), thousands of persons",
        y_unit="",
        y_digits=0,
    ) if payems_rows else multiline_chart_svg([], [])

    # UNRATE chart: current vs pre-benchmark snapshot.
    unrate_x = [r["observation_date"][:7] for r in unrate_rows]
    unrate_chart = multiline_chart_svg(
        series=[
            {"label": "Current vintage", "color": "#2563eb",
             "values": [r.get("value_current") for r in unrate_rows]},
            {"label": "Pre-benchmark vintage", "color": "#d97706",
             "values": [r.get("value_pre_benchmark") for r in unrate_rows]},
        ],
        x_labels=unrate_x,
        title="Unemployment rate (UNRATE), percent — current vs pre-benchmark vintage",
        y_unit="%",
    ) if unrate_rows else multiline_chart_svg([], [])

    # Tabular detail: only show PAYEMS rows that actually have at least one vintage.
    payems_table = [
        r for r in payems_rows
        if any(r.get(k) is not None for k in ("vintage_initial", "vintage_first", "vintage_second"))
    ]

    # Quick callout figure: most recent PAYEMS row with all three vintages.
    callout = None
    for r in reversed(payems_rows):
        if (r.get("vintage_initial") is not None and r.get("vintage_first") is not None
                and r.get("vintage_second") is not None):
            d_first = r["vintage_first"] - r["vintage_initial"]
            d_second = r["vintage_second"] - r["vintage_initial"]
            callout = {
                "observation_date": r["observation_date"],
                "initial": r["vintage_initial"],
                "first": r["vintage_first"],
                "second": r["vintage_second"],
                "delta_first": d_first,
                "delta_second": d_second,
            }
            break

    return {
        "revisions_status": revisions.get("status"),
        "payems_chart": payems_chart,
        "unrate_chart": unrate_chart,
        "payems_rows": list(reversed(payems_table)),  # newest first in the table
        "unrate_meta": {
            "benchmark_release_date": unrate.get("benchmark_release_date"),
            "pre_benchmark_snapshot_date": unrate.get("pre_benchmark_snapshot_date"),
        },
        "unrate_rows": list(reversed(unrate_rows)),
        "callout": callout,
    }


def _load_snapshot() -> dict:
    path = REPO_ROOT / "docs" / "data" / "latest.json"
    return json.loads(path.read_text())


if __name__ == "__main__":
    render_site(_load_snapshot())
    print("rendered.")
