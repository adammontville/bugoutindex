# BugOutIndex
# Copyright (C) 2025 Adam Montville
# Dual-licensed under AGPL-3.0 and a commercial license.
"""Command line for the v1.0.0 FRED replay. Does not publish the weekly score."""
from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

from runtime.backtest.harness import (
    FIXTURE_DOWNLOAD_DATE,
    METHODOLOGY_VERSION,
    OUTPUT_DIR,
    PUBLISHED_DATE,
    WINDOW_ORDER,
    WINDOWS,
    FredFetchError,
    MissingFredKey,
    fetch_fred_levels,
    interpret,
    load_fixtures,
    load_published_raws,
    score_published_inputs,
    write_windows,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m runtime.backtest",
        description=(
            "Replay v1.0.0 on historical FRED inflation, unemployment, and "
            "debt-to-GDP. Crime, homelessness, and trust are excluded or held "
            "at the 19 September 2026 baselines and labeled. This does not "
            "change the live weekly score."
        ),
    )
    parser.add_argument(
        "--source",
        choices=("fixtures", "fred"),
        default="fixtures",
        help="fixtures (default, no API key) or a live FRED pull (FRED_API_KEY)",
    )
    parser.add_argument(
        "--mode",
        choices=("partial", "held_constant", "both"),
        default="both",
        help="partial drops missing inputs; held_constant pins the sparse three; both writes two CSVs",
    )
    parser.add_argument(
        "--windows",
        default=",".join(WINDOW_ORDER),
        help="Comma-separated window names (default: 2008,2020)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=OUTPUT_DIR,
        help="Directory for replay_partial.csv and replay_held_constant.csv",
    )
    parser.add_argument(
        "--check-locked",
        action="store_true",
        help=f"Print the {PUBLISHED_DATE} six-input score from the weekly CSV before writing",
    )
    args = parser.parse_args(argv)

    windows = tuple(part.strip() for part in args.windows.split(",") if part.strip())
    if not windows:
        parser.error("at least one window is required")
    unknown = [name for name in windows if name not in WINDOWS]
    if unknown:
        parser.error(
            f"unknown window {unknown[0]!r}; known windows: {', '.join(WINDOW_ORDER)}"
        )
    modes = ("partial", "held_constant") if args.mode == "both" else (args.mode,)

    if args.check_locked:
        try:
            scored = score_published_inputs(load_published_raws())
        except (OSError, ValueError, KeyError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        band = interpret(scored["index"])["band"]
        print(
            f"{PUBLISHED_DATE} {scored['index']:.2f} {band} methodology {METHODOLOGY_VERSION}"
        )

    try:
        if args.source == "fixtures":
            levels = load_fixtures()
            download_date = FIXTURE_DOWNLOAD_DATE
        else:
            levels = fetch_fred_levels(windows)
            download_date = date.today().isoformat()
    except MissingFredKey as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except (FredFetchError, OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    for path in write_windows(
        levels, args.output, windows, modes, fred_download_date=download_date
    ):
        print(path)
    return 0
