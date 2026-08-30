"""Generate the timestamped baseline prediction artefact and chart.

Run with: python -m big_half.baseline
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path

from big_half.charts import plot_prediction_comparison
from big_half.data_loading import RUNS_CSV_PATH, Effort, load_runs, longest_run_effort
from big_half.prediction import (
    HALF_MARATHON_KM,
    PredictionRange,
    combined_range,
    predict_with_uncertainty,
)
from big_half.riegel import format_hms

logger = logging.getLogger(__name__)

RESULTS_DIR = Path(__file__).resolve().parents[2] / "results"
BASELINE_ARTEFACT_PATH = RESULTS_DIR / "baseline_prediction.md"

# Strava's estimated fastest 5k effort (23m35s), from athlete_context.md.
# A best-effort extraction from within training runs, not a standalone race.
FASTEST_5K_EFFORT = Effort(
    label="Fastest 5k effort (Strava estimate, 23:35)",
    distance_km=5.0,
    time_s=23 * 60 + 35,
)


def build_predictions() -> list[PredictionRange]:
    runs = load_runs()
    logger.info("Loaded %d runs from %s", len(runs), RUNS_CSV_PATH)
    long_run = longest_run_effort(runs)
    return [
        predict_with_uncertainty(FASTEST_5K_EFFORT, is_maximal_effort=True),
        predict_with_uncertainty(long_run, is_maximal_effort=False),
    ]


def write_artefact(
    ranges: list[PredictionRange],
    output_path: Path = BASELINE_ARTEFACT_PATH,
) -> Path:
    """Write the baseline prediction as a standalone timestamped document.

    The artefact is a one-off, pre-race record: it must only ever be
    created once. Later calibration steps belong in their own script
    writing their own artefact, so refuse to overwrite an existing file.
    """
    if output_path.exists():
        raise FileExistsError(
            f"Baseline artefact already exists at {output_path}. It is a "
            "one-off timestamped record and must not be regenerated; add "
            "any later calibration as a separate artefact."
        )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    overall_low, overall_high = combined_range(ranges)

    lines = [
        "# Baseline Big Half prediction",
        "",
        f"Generated: {generated_at}",
        "",
        "Predictions for the half marathon distance "
        f"({HALF_MARATHON_KM} km), from the 11-run training dataset only. "
        "This artefact predates the final long training run and race day. "
        "Any later calibration will be added as a separate step, not by "
        "editing this file.",
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
        f"Overall baseline range: **{format_hms(overall_low)} to "
        f"{format_hms(overall_high)}** (union of the two anchor intervals).",
        "",
        "See the README for method, why the two anchors diverge, and "
        "limitations.",
    ]
    output_path.write_text("\n".join(lines) + "\n")
    logger.info("Wrote baseline artefact to %s", output_path)
    return output_path


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    ranges = build_predictions()
    for prediction in ranges:
        logger.info(
            "%s -> point %s, Monte Carlo range %s to %s",
            prediction.anchor.label,
            format_hms(prediction.point_s),
            format_hms(prediction.low_s),
            format_hms(prediction.high_s),
        )
    write_artefact(ranges)
    chart_path = plot_prediction_comparison(ranges)
    logger.info("Wrote chart to %s", chart_path)


if __name__ == "__main__":
    main()
