"""Chart generation for the prediction stages and the race result."""

from __future__ import annotations

from pathlib import Path
from textwrap import fill

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from matplotlib.ticker import FuncFormatter, MultipleLocator

from big_half.prediction import PredictionRange
from big_half.race_comparison import RangeComparison
from big_half.riegel import format_hms

FIGURES_DIR = Path(__file__).resolve().parents[2] / "results" / "figures"

# Every figure in this project is quoted as a clock time, so the axis is
# too. Times are plotted in seconds and the ticks are formatted, rather
# than plotting minutes and labelling in a second unit.
TIME_AXIS_LABEL = "Half marathon time (h:mm:ss)"
TIME_AXIS_TICK_SECONDS = 300  # a tick every five minutes
# Horizontal padding as a fraction of the data range, so annotations
# that overhang the widest interval still fit inside the axes.
RANGE_LABEL_X_MARGIN = 0.20


def _use_clock_time_axis(axis: plt.Axes) -> None:
    axis.xaxis.set_major_locator(MultipleLocator(TIME_AXIS_TICK_SECONDS))
    axis.xaxis.set_major_formatter(FuncFormatter(lambda seconds, _: format_hms(seconds)))
    axis.set_xlabel(TIME_AXIS_LABEL)

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
        axis.errorbar(
            [prediction.point_s],
            [position],
            xerr=[
                [prediction.point_s - prediction.low_s],
                [prediction.high_s - prediction.point_s],
            ],
            fmt="o",
            capsize=6,
            markersize=8,
        )
        axis.annotate(
            f"{format_hms(prediction.point_s)} "
            f"({format_hms(prediction.low_s)} to {format_hms(prediction.high_s)})",
            (prediction.point_s, position),
            textcoords="offset points",
            xytext=(0, 12),
            ha="center",
        )

    axis.set_yticks(range(len(ranges)))
    axis.set_yticklabels([prediction.anchor.label for prediction in ranges])
    axis.set_ylim(-0.5, len(ranges) - 0.5)
    # The value labels sit above the widest interval, so leave room for the
    # text rather than letting it run into the frame.
    axis.margins(x=RANGE_LABEL_X_MARGIN)
    _use_clock_time_axis(axis)
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

# Bars sit well under a y-tick spacing of 1 without touching each other.
RANGE_BAR_HEIGHT = 0.4
# Long window names need wrapping to stay readable as y-axis labels.
RANGE_LABEL_WRAP_CHARS = 30


def _range_bar_colour(comparison: RangeComparison) -> str:
    return RANGE_HIT_COLOUR if comparison.contains_actual else RANGE_MISS_COLOUR


def _range_legend_handles() -> list[Patch | Line2D]:
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
        axis.barh(
            position,
            width=comparison.high_s - comparison.low_s,
            left=comparison.low_s,
            height=RANGE_BAR_HEIGHT,
            color=_range_bar_colour(comparison),
        )
        axis.annotate(
            f"{format_hms(comparison.low_s)} to {format_hms(comparison.high_s)}",
            ((comparison.low_s + comparison.high_s) / 2, position),
            textcoords="offset points",
            xytext=(0, 14),
            ha="center",
            fontsize=9,
        )

    axis.axvline(actual_s, color=ACTUAL_RESULT_COLOUR, linestyle="--", linewidth=2)
    # Pinned to the top of the axes rather than to a bar, so the label
    # stays put whichever range the result happens to fall in.
    axis.annotate(
        f"Actual {format_hms(actual_s)}",
        (actual_s, 1.0),
        xycoords=("data", "axes fraction"),
        textcoords="offset points",
        xytext=(6, -14),
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
    _use_clock_time_axis(axis)
    axis.set_title(title)
    axis.grid(axis="x", alpha=0.3)
    axis.legend(handles=_range_legend_handles(), loc="lower right", fontsize=9)
    figure.tight_layout()
    figure.savefig(output_path, dpi=150)
    plt.close(figure)
    return output_path
