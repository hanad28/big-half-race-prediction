"""Write-once guard for the project's timestamped artefact sets.

Every stage publishes a markdown artefact together with the chart that
artefact describes. The two are one atomic set: either both are written
on first generation, or neither is touched. That is what stops a frozen
pre-race document from ever ending up next to a chart that has since been
redrawn, and it is why rerunning a stage after the fact can only report,
never overwrite.

The baseline and calibration stages each carry their own copy of this
logic, written before a third stage existed. This module is the shared
version; the two frozen stages are deliberately left on their own copies
so this change cannot disturb what they already guard.
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path

TIMESTAMP_LINE_PREFIX = "Generated: "
CHART_HASH_PREFIX = "Chart SHA-256: "


class ArtefactSetState(Enum):
    """What a stage's artefact set on disk looks like against a fresh run."""

    ABSENT = "absent"
    ARTEFACT_MISSING = "artefact_missing"
    CHART_MISSING = "chart_missing"
    CHART_HASH_MISMATCH = "chart_hash_mismatch"
    VALUES_MATCH = "values_match"
    VALUES_DIFFER = "values_differ"


def sha256_of_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def generated_at_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def without_timestamp_line(document: str) -> str:
    """The document minus its generation timestamp, for value comparisons.

    Two runs of the same seeded computation differ only in when they ran,
    so the timestamp has to come out before the values can be compared.
    """
    return "\n".join(
        line
        for line in document.splitlines()
        if not line.startswith(TIMESTAMP_LINE_PREFIX)
    )


def recorded_chart_hash(document: str) -> str | None:
    """The chart hash the artefact pinned when it was written, if it has one."""
    return next(
        (
            line.removeprefix(CHART_HASH_PREFIX)
            for line in document.splitlines()
            if line.startswith(CHART_HASH_PREFIX)
        ),
        None,
    )


def chart_hash_matches(artefact_path: Path, chart_path: Path) -> bool:
    """Whether the chart on disk still hashes to the value the artefact pinned."""
    if not chart_path.exists():
        return False
    recorded = recorded_chart_hash(artefact_path.read_text())
    return recorded is not None and recorded == sha256_of_file(chart_path)


def write_once(output_path: Path, document: str) -> Path:
    """Write a stage artefact, refusing to overwrite an existing one.

    A stage artefact is a one-off record of what was known at a point in
    time. Regenerating it would destroy the thing it exists to prove, so
    an existing file is an error rather than something to replace.
    """
    if output_path.exists():
        raise FileExistsError(
            f"Artefact already exists at {output_path}. It is a one-off "
            "timestamped record and must not be regenerated; add any later "
            "stage as a separate artefact."
        )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(document)
    return output_path


def inspect_artefact_set(
    artefact_path: Path,
    chart_path: Path,
    render_document: Callable[[str], str],
) -> ArtefactSetState:
    """Classify the artefact set on disk against a freshly recomputed one.

    `render_document` takes a chart hash and returns the markdown a fresh
    run would produce, so both halves of the set can be checked: the
    values in the text, and the chart via the hash pinned inside it.
    """
    if not artefact_path.exists():
        return (
            ArtefactSetState.ARTEFACT_MISSING
            if chart_path.exists()
            else ArtefactSetState.ABSENT
        )
    if not chart_path.exists():
        return ArtefactSetState.CHART_MISSING
    if not chart_hash_matches(artefact_path, chart_path):
        return ArtefactSetState.CHART_HASH_MISMATCH
    committed = without_timestamp_line(artefact_path.read_text())
    recomputed = without_timestamp_line(render_document(sha256_of_file(chart_path)))
    return (
        ArtefactSetState.VALUES_MATCH
        if committed == recomputed
        else ArtefactSetState.VALUES_DIFFER
    )
