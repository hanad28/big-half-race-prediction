"""Generate the timestamped race result artefact and chart.

Measures the actual Big Half result against the three windows published
before the race: the tighter calibrated range, the wider baseline union,
and the 5k anchor's own range. The frozen baseline and calibration
artefacts are never touched; this stage writes its own guarded set.

Run with: python -m big_half.race_result
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from big_half.artefact_guard import (
    CHART_HASH_PREFIX,
    TIMESTAMP_LINE_PREFIX,
    ArtefactSetState,
    generated_at_now,
    inspect_artefact_set,
    sha256_of_file,
    write_once,
)
from big_half.baseline import RESULTS_DIR, build_predictions
from big_half.calibration import build_calibration_predictions
from big_half.charts import FIGURES_DIR, plot_result_against_ranges
from big_half.data_loading import RaceResult, load_race_result
from big_half.prediction import HALF_MARATHON_KM, PredictionRange
from big_half.race_comparison import (
    CALIBRATED_RANGE_LABEL,
    FAST_ANCHOR_RANGE_LABEL,
    RangeComparison,
    build_range_comparisons,
    describe_gap,
    exact_gap_seconds,
    format_gap,
    implied_riegel_exponent,
    required_effort_scale,
)
from big_half.riegel import RIEGEL_DEFAULT_EXPONENT, format_hms

logger = logging.getLogger(__name__)

RACE_RESULT_ARTEFACT_PATH = RESULTS_DIR / "race_result.md"
RACE_RESULT_CHART_PATH = FIGURES_DIR / "race_result_comparison.png"


@dataclass(frozen=True)
class RaceResultAnalysis:
    """Everything the artefact reports: the race, the anchors, the gaps."""

    race: RaceResult
    calibration_ranges: list[PredictionRange]
    comparisons: list[RangeComparison]


def analyse_race_result() -> RaceResultAnalysis:
    """Rebuild both published prediction stages and measure the race against them."""
    race = load_race_result()
    calibration_ranges = build_calibration_predictions()
    comparisons = build_range_comparisons(
        build_predictions(), calibration_ranges, race.moving_time_s
    )
    return RaceResultAnalysis(race, calibration_ranges, comparisons)


def _comparison_by_label(
    comparisons: list[RangeComparison], label: str
) -> RangeComparison:
    return next(comparison for comparison in comparisons if comparison.label == label)


def _headline(comparisons: list[RangeComparison]) -> str:
    fast_anchor = _comparison_by_label(comparisons, FAST_ANCHOR_RANGE_LABEL)
    calibrated = _comparison_by_label(comparisons, CALIBRATED_RANGE_LABEL)
    side = "inside" if fast_anchor.contains_actual else "outside"
    return (
        f"The result falls {side} the range belonging to the 5k anchor alone "
        f"({format_hms(fast_anchor.low_s)} to {format_hms(fast_anchor.high_s)}), "
        "the anchor built from a near-maximal short effort. Against the "
        "tighter calibrated range, built from the two steady solo training "
        f"efforts, the result is {describe_gap(calibrated)}."
    )


def _race_figure_rows(race: RaceResult) -> list[str]:
    return [
        "| Figure | Value |",
        "|---|---|",
        f"| Finish time (moving) | {format_hms(race.moving_time_s)} "
        f"({race.moving_time_s:.0f} s) |",
        f"| Elapsed time | {format_hms(race.elapsed_time_s)} "
        f"({race.elapsed_time_s:.0f} s) |",
        f"| Official distance | {race.official_distance_km} km |",
        f"| GPS distance | {race.gps_distance_km} km "
        f"({race.gps_distance_excess_km:.4f} km over the official distance) |",
        f"| Pace over the official distance | "
        f"{format_gap(race.pace_s_per_km)} per km |",
    ]


def _comparison_rows(comparisons: list[RangeComparison]) -> list[str]:
    rows = [
        "| Published range | Window | Actual against the window | Exact gap |",
        "|---|---|---|---|",
    ]
    for comparison in comparisons:
        rows.append(
            f"| {comparison.label} | {format_hms(comparison.low_s)} to "
            f"{format_hms(comparison.high_s)} | {describe_gap(comparison)} | "
            f"{exact_gap_seconds(comparison)} |"
        )
    return rows


def _anchor_implication_rows(
    ranges: list[PredictionRange], actual_s: float
) -> list[str]:
    rows = [
        "| Anchor | Implied Riegel exponent | Time multiplier needed | "
        "Multiplier assumed before the race |",
        "|---|---|---|---|",
    ]
    for prediction in ranges:
        exponent = implied_riegel_exponent(prediction.anchor, actual_s)
        needed = required_effort_scale(prediction, actual_s)
        assumed_low, assumed_high = prediction.effort_scale_bounds
        rows.append(
            f"| {prediction.anchor.label} | {exponent:.4f} | {needed:.4f} | "
            f"{assumed_low:.2f} to {assumed_high:.2f} |"
        )
    return rows


def render_artefact(
    analysis: RaceResultAnalysis, generated_at: str, chart_hash: str
) -> str:
    """Render the race result artefact document as markdown text."""
    race = analysis.race
    lines = [
        "# Big Half race result",
        "",
        f"{TIMESTAMP_LINE_PREFIX}{generated_at}",
        "",
        f"The Big Half was run on {race.date} in "
        f"{format_hms(race.moving_time_s)}, over the official distance of "
        f"{race.official_distance_km} km. This artefact measures that "
        "result against the three windows published before the race. The "
        "frozen artefacts at results/baseline_prediction.md and "
        "results/calibration_prediction.md are unchanged; this is a "
        "separate, later record.",
        "",
        "## Headline",
        "",
        _headline(analysis.comparisons),
        "",
        "## The race as run",
        "",
        *_race_figure_rows(race),
        "",
        "Moving time is the figure comparable with the published "
        "predictions, which predicted a time for the official distance. "
        "The race had no meaningful stops, so elapsed time is 9 s longer "
        "and the comparisons below hold for either figure. The GPS "
        "distance overshoot is ordinary tangent-cutting error on a course "
        "with turns, and the official distance is the one used throughout.",
        "",
        "## Result against each published range",
        "",
        *_comparison_rows(analysis.comparisons),
        "",
        "Gaps for windows containing the result are quoted as distance "
        "from the fast end, then distance from the slow end.",
        "",
        "## What each anchor implied",
        "",
        *_anchor_implication_rows(analysis.calibration_ranges, race.moving_time_s),
        "",
        "The implied exponent is the Riegel exponent that maps each anchor "
        f"exactly onto the actual time. The time multiplier is what the "
        f"anchor's logged time would have to be scaled by, at the standard "
        f"b = {RIEGEL_DEFAULT_EXPONENT} exponent, to land on the actual "
        f"time over {HALF_MARATHON_KM} km. It is directly comparable with "
        "the multiplier assumed before the race, in the last column.",
        "",
        f"{CHART_HASH_PREFIX}{chart_hash}",
        "",
        "See the README Race Day Result section for what this means and "
        "how it relates to the pre-registered limitations.",
    ]
    return "\n".join(lines) + "\n"


def write_artefact_set(
    analysis: RaceResultAnalysis,
    artefact_path: Path = RACE_RESULT_ARTEFACT_PATH,
    chart_path: Path = RACE_RESULT_CHART_PATH,
) -> tuple[Path, Path]:
    """Write the chart, then the artefact that pins that chart's hash.

    Refuses before writing anything if either half of the set is already
    on disk. Writing the chart first and only then discovering the
    artefact exists would overwrite a committed chart, which is the one
    thing the atomic guard exists to prevent.
    """
    already_written = [path for path in (artefact_path, chart_path) if path.exists()]
    if already_written:
        raise FileExistsError(
            "Race result artefact set already exists at "
            f"{', '.join(str(path) for path in already_written)}. It is a "
            "one-off timestamped record and must not be regenerated."
        )
    written_chart = plot_result_against_ranges(
        analysis.comparisons,
        actual_s=analysis.race.moving_time_s,
        output_path=chart_path,
    )
    logger.info("Wrote chart to %s", written_chart)
    document = render_artefact(
        analysis,
        generated_at=generated_at_now(),
        chart_hash=sha256_of_file(written_chart),
    )
    written_artefact = write_once(artefact_path, document)
    logger.info("Wrote race result artefact to %s", written_artefact)
    return written_artefact, written_chart


# What to report when the artefact set is already on disk. Nothing is
# ever rewritten, so each state is a description of what a fresh run
# found, not something the run went on to fix.
EXISTING_SET_REPORTS: dict[ArtefactSetState, tuple[int, str]] = {
    ArtefactSetState.ARTEFACT_MISSING: (
        logging.WARNING,
        "Chart exists but the markdown artefact is missing; the artefact "
        "set is incomplete and nothing was written. Restore the committed "
        "set from version control.",
    ),
    ArtefactSetState.CHART_MISSING: (
        logging.WARNING,
        "Artefact exists but its chart is missing; the artefact set is "
        "incomplete and nothing was written. Restore the committed set "
        "from version control.",
    ),
    ArtefactSetState.CHART_HASH_MISMATCH: (
        logging.WARNING,
        "Race result artefact set already exists; nothing written. The "
        "chart on disk DOES NOT MATCH the hash recorded in the artefact. "
        "Restore the committed chart from version control.",
    ),
    ArtefactSetState.VALUES_MATCH: (
        logging.INFO,
        "Race result artefact set already exists; nothing written. "
        "Recomputed values MATCH the committed artefact and the chart "
        "matches its recorded hash.",
    ),
    ArtefactSetState.VALUES_DIFFER: (
        logging.WARNING,
        "Race result artefact set already exists; nothing written. "
        "Recomputed values DO NOT MATCH the committed artefact.",
    ),
}


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    analysis = analyse_race_result()
    for comparison in analysis.comparisons:
        logger.info(
            "%s (%s to %s) -> %s",
            comparison.label,
            format_hms(comparison.low_s),
            format_hms(comparison.high_s),
            describe_gap(comparison),
        )
    state = inspect_artefact_set(
        RACE_RESULT_ARTEFACT_PATH,
        RACE_RESULT_CHART_PATH,
        lambda chart_hash: render_artefact(analysis, "", chart_hash),
    )
    if state is ArtefactSetState.ABSENT:
        write_artefact_set(analysis)
        return
    level, message = EXISTING_SET_REPORTS[state]
    logger.log(level, message)


if __name__ == "__main__":
    main()
