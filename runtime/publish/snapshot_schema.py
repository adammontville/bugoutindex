# BugOutIndex
# Copyright (C) 2025 Adam Montville
# Dual-licensed under AGPL-3.0 and a commercial license.
"""
Published snapshot contract, schema_version 1.

``schema_version`` names this JSON shape. ``methodology_version`` names the
formula and the inputs the publisher stamps. Schema 1 did not change for
methodology 1.1.0 or 1.1.1. New publishes stamp ``1.1.1``. Files written
under ``1.0.0`` and ``1.1.0`` stay valid. 1.1.1 changes the annual
homelessness and trust checklist cells. It does not change endpoints,
weights, or the crime series rule from 1.1.0.

The human-readable copy is ``docs/architecture/snapshot-schema.md``.
``docs/data/latest.json`` is the 2026-10-09 publication: methodology 1.1.0,
headline number 57.66. This module does not rewrite it. Weeks already
published stay under the version that produced them.
"""
from __future__ import annotations

import json
import re
from typing import Any, Mapping

from runtime.processing.formula import CORE_METRICS
from runtime.util.redact import redact_secrets

SCHEMA_VERSION = 1
# Stamped on new publishes. 1.0.0 and 1.1.0 remain readable; the JSON shape is the same.
METHODOLOGY_VERSION = "1.1.1"
ACCEPTED_METHODOLOGY_VERSIONS = ("1.0.0", "1.1.0", "1.1.1")

# Envelope keys on a snapshot the weekly job is allowed to publish.
# A new top-level key is a shape change and needs schema_version 2.
REQUIRED_TOP_LEVEL = (
    "schema_version",
    "methodology_version",
    "generated_at_utc",
    "publication_date",
    "bugout_index",
    "interpretation",
    "metrics",
    "markets",
    "pulse",
    "revisions",
    "history",
    "labor_shadow",
    "food_shadow",
    "nyc_dhs_shadow",
    "ramsey_shelter_shadow",
    "sf_shelter_shadow",
    "shelter_region_shadow",
    "pew_trust_shadow",
    "gallup_confidence_shadow",
)

# Companions are outside compute_index. Markets, pulse, and revisions do
# not carry in_bugout_index. Shadow blocks do, and it is false.
COMPANION_BLOCKS = (
    "markets",
    "pulse",
    "revisions",
    "labor_shadow",
    "food_shadow",
    "nyc_dhs_shadow",
    "ramsey_shelter_shadow",
    "sf_shelter_shadow",
    "shelter_region_shadow",
    "pew_trust_shadow",
    "gallup_confidence_shadow",
)

SHADOW_BLOCKS = (
    "labor_shadow",
    "food_shadow",
    "nyc_dhs_shadow",
    "ramsey_shelter_shadow",
    "sf_shelter_shadow",
    "shelter_region_shadow",
    "pew_trust_shadow",
    "gallup_confidence_shadow",
)

# Fields every scored core object has. provenance and diagnostics are
# optional and are not inputs to compute_index.
CORE_METRIC_FIELDS = (
    "raw",
    "normalized",
    "weight",
    "observation_date",
    "source_fetched_at",
    "status",
)

OPTIONAL_CORE_FIELDS = (
    "provenance",
    "diagnostics",
)

INTERPRETATION_FIELDS = (
    "band",
    "risk",
    "band_key",
)

# History series embedded in the snapshot. Cells are CSV strings.
HISTORY_SERIES = (
    "bugout_index",
    "markets",
    "pulse",
    "labor_shadow",
    "food_shadow",
    "nyc_dhs_shadow",
    "pew_trust_shadow",
    "gallup_confidence_shadow",
    "ramsey_shelter_shadow",
    "sf_shelter_shadow",
    "shelter_region_shadow",
)

# Names the current writer stores. A partial pulse may omit a value.
# Missing keys here do not, by themselves, refuse a publish.
PULSE_SERIES = (
    "initial_jobless_claims",
    "consumer_sentiment_umich",
    "business_confidence",
    "yield_curve_10y_2y",
    "vix",
)

MARKET_SERIES = (
    "gold_usd_per_oz",
    "silver_usd_per_oz",
    "dxy",
)

# Shadow value names on a successful block. Documented so a reader can see
# the frozen series. Carry-forward may keep these and add reused_from.
SHADOW_VALUE_KEYS = {
    "labor_shadow": ("prime_age_epop", "prime_age_lfpr"),
    "food_shadow": ("food_cpi_yoy",),
    "nyc_dhs_shadow": ("nyc_dhs_total_individuals",),
    "ramsey_shelter_shadow": ("ramsey_shelter_total_people",),
    "sf_shelter_shadow": ("sf_shelter_occupancy_rate",),
    "shelter_region_shadow": (
        "nashville_hmis_people",
        "austin_sheltered_people",
        "denver_shelter_occupancy",
    ),
    "pew_trust_shadow": ("pew_public_trust",),
    "gallup_confidence_shadow": (
        "gallup_congress",
        "gallup_presidency",
        "gallup_supreme_court",
        "gallup_core_institutions",
    ),
}

# Added when a failed shadow or revisions fetch reuses the previous block.
# They are part of schema 1. They are not a new schema.
CARRY_FORWARD_FIELDS = (
    "reused_from",
    "current_status",
    "current_message",
)

_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_SECRET_KEY = re.compile(
    r"(?i)(api[_-]?key|apikey|access[_-]?token|refresh[_-]?token|"
    r"client[_-]?secret|auth_token|password|passwd|secret)"
)


def _is_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _secret_keys(value: object) -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            if _SECRET_KEY.search(str(key)):
                found.append(str(key))
            found.extend(_secret_keys(item))
    elif isinstance(value, list):
        for item in value:
            found.extend(_secret_keys(item))
    return found


def validate_published_snapshot(snapshot: object) -> list[str]:
    """Problems that refuse a publish. An empty list means schema 1 holds.

    Does not change the snapshot. Callers scrub first, then refuse if this
    list is non-empty, and do not write ``docs/``.
    """
    errors: list[str] = []
    if not isinstance(snapshot, Mapping):
        return ["snapshot must be a JSON object"]

    present = set(snapshot)
    required = set(REQUIRED_TOP_LEVEL)
    missing = sorted(required - present)
    extra = sorted(present - required)
    if missing:
        errors.append("missing top-level fields: " + ", ".join(missing))
    if extra:
        errors.append(
            "unexpected top-level fields (bump schema_version to change the shape): "
            + ", ".join(extra)
        )

    if snapshot.get("schema_version") != SCHEMA_VERSION:
        errors.append(
            f"schema_version must be {SCHEMA_VERSION}, got {snapshot.get('schema_version')!r}"
        )
    if snapshot.get("methodology_version") not in ACCEPTED_METHODOLOGY_VERSIONS:
        errors.append(
            "methodology_version must be one of "
            f"{', '.join(ACCEPTED_METHODOLOGY_VERSIONS)}; "
            f"got {snapshot.get('methodology_version')!r}"
        )

    generated = snapshot.get("generated_at_utc")
    if not isinstance(generated, str) or not generated.strip():
        errors.append("generated_at_utc must be a non-empty string")

    published = snapshot.get("publication_date")
    if not isinstance(published, str) or _DATE.fullmatch(published) is None:
        errors.append("publication_date must be YYYY-MM-DD")

    if not _is_number(snapshot.get("bugout_index")):
        errors.append("bugout_index must be the headline number, not an object")

    interpretation = snapshot.get("interpretation")
    if not isinstance(interpretation, Mapping):
        errors.append("interpretation must be an object")
    else:
        for field in INTERPRETATION_FIELDS:
            if not isinstance(interpretation.get(field), str) or not interpretation.get(field):
                errors.append(f"interpretation.{field} must be a non-empty string")

    metrics = snapshot.get("metrics")
    if not isinstance(metrics, Mapping):
        errors.append("metrics must be an object")
    else:
        expected = list(CORE_METRICS)
        if set(metrics) != set(expected):
            errors.append("metrics must be the six cores " + ", ".join(expected))
        folded = sorted(set(metrics) & set(COMPANION_BLOCKS))
        if folded:
            errors.append("companion folded into metrics: " + ", ".join(folded))
        for name in expected:
            block = metrics.get(name)
            if not isinstance(block, Mapping):
                errors.append(f"metrics.{name} must be an object")
                continue
            for field in CORE_METRIC_FIELDS:
                if field not in block:
                    errors.append(f"metrics.{name} missing {field}")
            for field in ("raw", "normalized", "weight"):
                if field in block and not _is_number(block.get(field)):
                    errors.append(f"metrics.{name}.{field} must be a number")
            if block.get("status") != "success":
                errors.append(
                    f"metrics.{name} status must be success to publish "
                    f"(got {block.get('status')!r})"
                )
            for field in ("observation_date", "source_fetched_at"):
                value = block.get(field)
                if value is not None and not isinstance(value, str):
                    errors.append(f"metrics.{name}.{field} must be a string or null")

    for name in ("markets", "pulse"):
        block = snapshot.get(name)
        if not isinstance(block, Mapping):
            errors.append(f"{name} must be an object")
            continue
        status = block.get("status")
        if status not in ("success", "partial"):
            errors.append(
                f"{name} status must be success or partial to publish (got {status!r})"
            )
    pulse = snapshot.get("pulse")
    if isinstance(pulse, Mapping):
        if not isinstance(pulse.get("values"), Mapping):
            errors.append("pulse.values must be an object")
        if not isinstance(pulse.get("dates"), Mapping):
            errors.append("pulse.dates must be an object")

    revisions = snapshot.get("revisions")
    if not isinstance(revisions, Mapping):
        errors.append("revisions must be an object")
    elif "status" not in revisions:
        errors.append("revisions.status is required")

    for name in SHADOW_BLOCKS:
        block = snapshot.get(name)
        if not isinstance(block, Mapping):
            errors.append(f"{name} must be an object")
            continue
        if block.get("in_bugout_index") is not False:
            errors.append(f"{name}.in_bugout_index must be false")
        if not isinstance(block.get("status"), str):
            errors.append(f"{name}.status must be a string")

    history = snapshot.get("history")
    if not isinstance(history, Mapping):
        errors.append("history must be an object")
    else:
        expected_history = set(HISTORY_SERIES)
        if set(history) != expected_history:
            missing_h = sorted(expected_history - set(history))
            extra_h = sorted(set(history) - expected_history)
            if missing_h:
                errors.append("history missing series: " + ", ".join(missing_h))
            if extra_h:
                errors.append("history has unexpected series: " + ", ".join(extra_h))
        for name, rows in history.items():
            if not isinstance(rows, list):
                errors.append(f"history.{name} must be a list")
                continue
            for index, row in enumerate(rows):
                if not isinstance(row, Mapping) or "date" not in row:
                    errors.append(f"history.{name}[{index}] must be an object with date")
                    break

    secret_names = _secret_keys(snapshot)
    if secret_names:
        errors.append("snapshot contains secret field names: " + ", ".join(sorted(set(secret_names))))
    rendered = json.dumps(snapshot, default=str)
    if redact_secrets(rendered) != rendered:
        errors.append("snapshot still contains secret material after redaction")

    return errors


def assert_published_snapshot(snapshot: Mapping[str, Any]) -> None:
    """Raise ValueError when the snapshot is not schema 1."""
    errors = validate_published_snapshot(snapshot)
    if errors:
        raise ValueError("; ".join(errors))
