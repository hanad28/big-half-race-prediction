"""Chart generation for the baseline predictions."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from big_half.prediction import PredictionRange
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
