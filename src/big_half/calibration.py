"""Generate the timestamped calibration prediction artefact and chart.

Adds the final pre-race progression run as a third Riegel anchor
alongside the two baseline anchors. The frozen baseline artefact is
never touched; this module writes its own separate artefact set.

Run with: python -m big_half.calibration
"""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone
from pathlib import Path

from big_half.baseline import FASTEST_5K_EFFORT, RESULTS_DIR
from big_half.charts import FIGURES_DIR, plot_prediction_comparison
from big_half.data_loading import (
    FINAL_RUN_CSV_PATH,
    final_progression_run_effort,
    load_runs,
    longest_run_effort,
)
from big_half.prediction import (
    HALF_MARATHON_KM,
    PROGRESSION_ANCHOR_EFFORT_SCALE_HIGH,
    PROGRESSION_ANCHOR_EFFORT_SCALE_LOW,
    PredictionRange,
    combined_range,
    predict_with_uncertainty,
)
from big_half.riegel import format_hms

logger = logging.getLogger(__name__)

CALIBRATION_ARTEFACT_PATH = RESULTS_DIR / "calibration_prediction.md"
CALIBRATION_CHART_PATH = FIGURES_DIR / "calibration_comparison.png"

CALIBRATION_CHART_TITLE = (
    "Calibration Big Half predictions: three anchors with Monte Carlo ranges\n"
    "(5th-95th percentile under stated assumptions)"
)

# Markdown line prefix under which the chart's hash is recorded, so the
# artefact pins the exact chart it was written alongside.
CHART_HASH_PREFIX = "Chart SHA-256: "


def build_calibration_predictions() -> list[PredictionRange]:
    """The two baseline anchors plus the final progression run anchor."""
    runs = load_runs()
    long_run = longest_run_effort(runs)
    final_run = final_progression_run_effort()
    logger.info("Loaded final progression run from %s", FINAL_RUN_CSV_PATH)
    return [
        predict_with_uncertainty(FASTEST_5K_EFFORT, is_maximal_effort=True),
        predict_with_uncertainty(long_run, is_maximal_effort=False),
        predict_with_uncertainty(
            final_run,
            is_maximal_effort=False,
            effort_scale_bounds=(
                PROGRESSION_ANCHOR_EFFORT_SCALE_LOW,
                PROGRESSION_ANCHOR_EFFORT_SCALE_HIGH,
            ),
        ),
    ]


def _sha256_of_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def render_artefact(
    ranges: list[PredictionRange], generated_at: str, chart_hash: str
) -> str:
    """Render the calibration artefact document as markdown text."""
    overall_low, overall_high = combined_range(ranges)

    lines = [
        "# Calibration Big Half prediction",
        "",
        f"Generated: {generated_at}",
        "",
        "Predictions for the half marathon distance "
        f"({HALF_MARATHON_KM} km), adding the final pre-race progression "
        "run (10.00 km in 55:54) as a third anchor alongside the two "
        "baseline anchors. The frozen baseline artefact at "
        "results/baseline_prediction.md is unchanged; this is a separate, "
        "later record.",
        "",
        "| Anchor | Point (Riegel, b = 1.06) | Monte Carlo range (5th-95th percentile, under stated assumptions) |",
        "|---|---|---|",
    ]
    for prediction in ranges:
        lines.append(
            f"| {prediction.anchor.label} | {format_hms(prediction.point_s)} | "
            f"{format_hms(prediction.low_s)} to {format_hms(prediction.high_s)} |"
        )
    lines += [
        "",
        f"Overall calibration range: **{format_hms(overall_low)} to "
        f"{format_hms(overall_high)}** (union of the three anchor intervals).",
        "",
        f"{CHART_HASH_PREFIX}{chart_hash}",
        "",
        "See the README Calibration section for how this compares with the "
        "baseline and why the progression anchor's effort-scale assumption "
        "differs from the 15 km anchor's.",
    ]
    return "\n".join(lines) + "\n"


def write_artefact(
    ranges: list[PredictionRange],
    chart_hash: str,
    output_path: Path = CALIBRATION_ARTEFACT_PATH,
) -> Path:
    """Write the calibration prediction as a standalone timestamped document.

    Records the hash of the already-written chart so the artefact pins
    the exact chart it belongs with. Like the baseline, this is a
    one-off pre-race record: it must only ever be created once, so
    refuse to overwrite an existing file.
    """
    if output_path.exists():
        raise FileExistsError(
            f"Calibration artefact already exists at {output_path}. It is a "
            "one-off timestamped record and must not be regenerated; add "
            "any later step as a separate artefact."
        )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    output_path.write_text(render_artefact(ranges, generated_at, chart_hash))
    logger.info("Wrote calibration artefact to %s", output_path)
    return output_path


def _without_timestamp_line(document: str) -> str:
    return "\n".join(
        line for line in document.splitlines() if not line.startswith("Generated:")
    )


def chart_hash_matches(
    artefact_path: Path = CALIBRATION_ARTEFACT_PATH,
    chart_path: Path = CALIBRATION_CHART_PATH,
) -> bool:
    """Whether the chart on disk hashes to the value recorded in the artefact."""
    recorded = next(
        (
            line.removeprefix(CHART_HASH_PREFIX)
            for line in artefact_path.read_text().splitlines()
            if line.startswith(CHART_HASH_PREFIX)
        ),
        None,
    )
    return recorded is not None and recorded == _sha256_of_file(chart_path)


def check_against_committed(
    ranges: list[PredictionRange],
    artefact_path: Path = CALIBRATION_ARTEFACT_PATH,
    chart_path: Path = CALIBRATION_CHART_PATH,
) -> bool:
    """Compare freshly recomputed values against the committed artefact set.

    Verifies both parts of the set: the markdown values (ignoring the
    generation timestamp line; the Monte Carlo is seeded, so recomputed
    values should match exactly) and the chart, via the hash recorded
    in the artefact at write time.
    """
    committed = _without_timestamp_line(artefact_path.read_text())
    recomputed = _without_timestamp_line(
        render_artefact(ranges, generated_at="", chart_hash=_sha256_of_file(chart_path))
    )
    return committed == recomputed and chart_hash_matches(artefact_path, chart_path)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    ranges = build_calibration_predictions()
    for prediction in ranges:
        logger.info(
            "%s -> point %s, Monte Carlo range %s to %s",
            prediction.anchor.label,
            format_hms(prediction.point_s),
            format_hms(prediction.low_s),
            format_hms(prediction.high_s),
        )
    # The markdown artefact and the chart form one atomic artefact set:
    # either both are written together on first generation, or neither
    # is touched, so the frozen text and chart can never contradict.
    if CALIBRATION_ARTEFACT_PATH.exists() or CALIBRATION_CHART_PATH.exists():
        if not CALIBRATION_ARTEFACT_PATH.exists():
            logger.warning(
                "Chart exists but the markdown artefact is missing; the "
                "artefact set is incomplete and nothing was written. "
                "Restore the committed set from version control."
            )
        elif not chart_hash_matches():
            logger.warning(
                "Calibration artefact set already exists; nothing written. "
                "The chart on disk DOES NOT MATCH the hash recorded in the "
                "artefact. Restore the committed chart from version control."
            )
        elif check_against_committed(ranges):
            logger.info(
                "Calibration artefact set already exists; nothing written. "
                "Recomputed values MATCH the committed artefact and the "
                "chart matches its recorded hash."
            )
        else:
            logger.warning(
                "Calibration artefact set already exists; nothing written. "
                "Recomputed values DO NOT MATCH the committed artefact."
            )
    else:
        chart_path = plot_prediction_comparison(
            ranges,
            output_path=CALIBRATION_CHART_PATH,
            title=CALIBRATION_CHART_TITLE,
        )
        logger.info("Wrote chart to %s", chart_path)
        write_artefact(ranges, chart_hash=_sha256_of_file(chart_path))


if __name__ == "__main__":
    main()
