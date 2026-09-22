# BugOutIndex
# Copyright (C) 2025 Adam Montville
# Dual-licensed under AGPL-3.0 and a commercial license.
"""Job-summary copy when the weekly GitHub Action does not publish.

weekly_run.main exits with these codes before it writes history or HTML:

- 2: a core metric did not succeed
- 3: markets or the short-term pulse failed completely
- any other non-zero code: the runner crashed

The live site keeps the previous HTML because the workflow does not commit
after a failed step. Preview the Actions summary locally:

    python -m runtime.publish.failure_notice 2
    python -m runtime.publish.failure_notice 3
    python -m runtime.publish.failure_notice 1
"""
from __future__ import annotations

import sys

EXIT_CORE_REFUSED = 2
EXIT_MARKETS_OR_PULSE_REFUSED = 3


def _classify(exit_code: str | int | None) -> tuple[str, str]:
    text = "" if exit_code is None else str(exit_code).strip()
    if text == str(EXIT_CORE_REFUSED):
        return (
            "Refused (exit 2)",
            "Not every core metric succeeded, so weekly_run stopped before "
            "writing history or HTML.",
        )
    if text == str(EXIT_MARKETS_OR_PULSE_REFUSED):
        return (
            "Refused (exit 3)",
            "Markets or the short-term pulse failed completely, so weekly_run "
            "stopped before writing history or HTML.",
        )
    if text == "0":
        return (
            "Publish step failed after weekly_run",
            "weekly_run exited 0, so this was not a core, markets, or pulse "
            "refusal. A later step failed. The live site stays on the last "
            "commit that was pushed.",
        )
    if text == "" or text == "unknown":
        return (
            "Did not publish",
            "weekly_run did not record an exit code. An earlier step failed, "
            "or the job stopped before the runner finished.",
        )
    return (
        f"Crashed (exit {text})",
        "weekly_run exited without a clean refusal (exit 2 or 3). The "
        "traceback is in the pipeline step log.",
    )


def describe_publish_failure(exit_code: str | int | None) -> str:
    """Markdown for $GITHUB_STEP_SUMMARY."""
    kind, detail = _classify(exit_code)
    lines = [
        "## Weekly publish failed",
        "",
        f"**{kind}.** {detail}",
        "",
        "The live site was not updated. A refused or crashed run does not "
        "replace `docs/`, so the footer still shows the last successful "
        "publication date.",
        "",
        "This summary is on the Actions run page. For a scheduled run, GitHub "
        "also emails the person who last changed the cron in "
        "`.github/workflows/weekly-update.yml` (or who re-enabled that "
        "workflow).",
        "",
    ]
    return "\n".join(lines)


def describe_publish_failure_oneline(exit_code: str | int | None) -> str:
    """Single line for a workflow `::error::` annotation."""
    kind, detail = _classify(exit_code)
    return f"{kind}. {detail} Live site unchanged."


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    oneline = False
    if args and args[0] == "--oneline":
        oneline = True
        args = args[1:]
    code: str | int | None = args[0] if args else "unknown"
    if oneline:
        print(describe_publish_failure_oneline(code))
    else:
        print(describe_publish_failure(code), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
