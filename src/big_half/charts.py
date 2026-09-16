"""Chart generation for the prediction stages and the race result."""

from __future__ import annotations

from pathlib import Path
from textwrap import fill

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

from big_half.prediction import PredictionRange
from big_half.race_comparison import RangeComparison
from big_half.riegel import format_hms

FIGURES_DIR = Path(__file__).resolve().parents[2] / "results" / "figures"

BASELINE_COMPARISON_TITLE = (
    "Baseline Big Half predictions: point estimates with Monte Carlo ranges\n"
    "(5th-95th percentile under stated assumptions)"
)


def plot_prediction_comparison(
    ranges: list[PredictionRange],
    output_path: Path = FIGURES_DIR / "baseline_comparison.png",
    title: str = BASELINE_COMPARISON_TITLE,
) -> Path:
    """Plot each anchor's point prediction with its Monte Carlo range."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    figure, axis = plt.subplots(figsize=(9, 4.5))

    for position, prediction in enumerate(ranges):
        point_min = prediction.point_s / 60
        low_min = prediction.low_s / 60
        high_min = prediction.high_s / 60
        axis.errorbar(
            [point_min],
            [position],
            xerr=[[point_min - low_min], [high_min - point_min]],
            fmt="o",
            capsize=6,
            markersize=8,
        )
        axis.annotate(
            f"{format_hms(prediction.point_s)} "
            f"({format_hms(prediction.low_s)} to {format_hms(prediction.high_s)})",
            (point_min, position),
            textcoords="offset points",
            xytext=(0, 12),
            ha="center",
        )

    axis.set_yticks(range(len(ranges)))
    axis.set_yticklabels([prediction.anchor.label for prediction in ranges])
    axis.set_ylim(-0.5, len(ranges) - 0.5)
    axis.set_xlabel("Predicted half marathon time (minutes)")
    axis.set_title(title)
    axis.grid(axis="x", alpha=0.3)
    figure.tight_layout()
    figure.savefig(output_path, dpi=150)
    plt.close(figure)
    return output_path


RESULT_COMPARISON_TITLE = (
    "Big Half: actual result against the ranges published before the race\n"
    "(Monte Carlo 5th-95th percentile under stated assumptions)"
)

# Ranges that contained the result are drawn in the strong colour and
# ranges that missed it in the muted one, so the chart answers "which
# windows were right" before any label is read.
RANGE_HIT_COLOUR = "#4c72b0"
RANGE_MISS_COLOUR = "#b0aba4"
ACTUAL_RESULT_COLOUR = "#c44e52"

RANGE_BAR_HEIGHT = 0.4
# Long window names need wrapping to stay readable as y-axis labels.
RANGE_LABEL_WRAP_CHARS = 30


def _range_bar_colour(comparison: RangeComparison) -> str:
    return RANGE_HIT_COLOUR if comparison.contains_actual else RANGE_MISS_COLOUR


def _range_legend_handles() -> list[Patch]:
    return [
        Patch(color=RANGE_HIT_COLOUR, label="Range contained the result"),
        Patch(color=RANGE_MISS_COLOUR, label="Range missed the result"),
        Line2D(
            [],
            [],
            color=ACTUAL_RESULT_COLOUR,
            linestyle="--",
            label="Actual result",
        ),
    ]


def plot_result_against_ranges(
    comparisons: list[RangeComparison],
    actual_s: float,
    output_path: Path = FIGURES_DIR / "race_result_comparison.png",
    title: str = RESULT_COMPARISON_TITLE,
) -> Path:
    """Plot each published prediction window against the actual finish time."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    figure, axis = plt.subplots(figsize=(9.5, 4.8))

    for position, comparison in enumerate(comparisons):
        low_min = comparison.low_s / 60
        high_min = comparison.high_s / 60
        axis.barh(
            position,
            width=high_min - low_min,
            left=low_min,
            height=RANGE_BAR_HEIGHT,
            color=_range_bar_colour(comparison),
        )
        axis.annotate(
            f"{format_hms(comparison.low_s)} to {format_hms(comparison.high_s)}",
            ((low_min + high_min) / 2, position),
            textcoords="offset points",
            xytext=(0, 14),
            ha="center",
            fontsize=9,
        )

    actual_min = actual_s / 60
    axis.axvline(actual_min, color=ACTUAL_RESULT_COLOUR, linestyle="--", linewidth=2)
    axis.annotate(
        f"Actual {format_hms(actual_s)}",
        (actual_min, len(comparisons) - 0.5),
        textcoords="offset points",
        xytext=(6, -12),
        ha="left",
        color=ACTUAL_RESULT_COLOUR,
        fontweight="bold",
    )

    axis.set_yticks(range(len(comparisons)))
    axis.set_yticklabels(
        [fill(comparison.label, RANGE_LABEL_WRAP_CHARS) for comparison in comparisons]
    )
    axis.set_ylim(-0.6, len(comparisons) - 0.4)
    axis.invert_yaxis()
    axis.set_xlabel("Half marathon time (minutes)")
    axis.set_title(title)
    axis.grid(axis="x", alpha=0.3)
    axis.legend(handles=_range_legend_handles(), loc="lower right", fontsize=9)
    figure.tight_layout()
    figure.savefig(output_path, dpi=150)
    plt.close(figure)
    return output_path
