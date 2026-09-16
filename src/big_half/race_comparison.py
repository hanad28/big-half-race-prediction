"""Measuring the actual race result against the published prediction ranges.

Three windows were published before the race and each is compared here:
the tighter calibrated range, the wider baseline union, and the range
belonging to the 5k anchor alone. The comparisons are pure functions over
already-computed prediction ranges, so the artefact generator can stay
thin and the arithmetic stays testable.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from big_half.data_loading import Effort
from big_half.prediction import (
    HALF_MARATHON_KM,
    PredictionRange,
    combined_range,
    intersection_range,
    ranges_closest_to_target,
    shortest_anchor_range,
)

# The calibrated headline range came from the two anchors nearest race
# distance, where Riegel extrapolation stretches least.
CALIBRATED_ANCHOR_COUNT: int = 2

CALIBRATED_RANGE_LABEL = "Calibrated range (two anchors closest to race distance)"
BASELINE_RANGE_LABEL = "Baseline range (union of the two baseline anchors)"
FAST_ANCHOR_RANGE_LABEL = "5k anchor range (near-maximal effort)"


@dataclass(frozen=True)
class RangeComparison:
    """An actual finish time measured against one published prediction window."""

    label: str
    low_s: float
    high_s: float
    actual_s: float

    @property
    def gap_from_fast_end_s(self) -> float:
        """Seconds between the fast end of the range and the actual time.

        Positive when the actual time is slower than the fast end.
        """
        return self.actual_s - self.low_s

    @property
    def gap_from_slow_end_s(self) -> float:
        """Seconds between the actual time and the slow end of the range.

        Positive when the actual time is faster than the slow end.
        """
        return self.high_s - self.actual_s

    @property
    def contains_actual(self) -> bool:
        return self.gap_from_fast_end_s >= 0 and self.gap_from_slow_end_s >= 0

    @property
    def miss_s(self) -> float:
        """How far outside the range the actual time landed, 0 when inside.

        Positive means faster than the whole range, negative means slower.
        """
        if self.contains_actual:
            return 0.0
        if self.actual_s < self.low_s:
            return self.low_s - self.actual_s
        return self.high_s - self.actual_s


def build_range_comparisons(
    baseline_ranges: list[PredictionRange],
    calibration_ranges: list[PredictionRange],
    actual_s: float,
    target_km: float = HALF_MARATHON_KM,
) -> list[RangeComparison]:
    """Compare the actual time against each of the three published windows.

    Each window is rebuilt from the same anchors that produced it, rather
    than restated by hand, so the comparison cannot drift from what the
    baseline and calibration artefacts published.
    """
    calibrated_low, calibrated_high = intersection_range(
        ranges_closest_to_target(calibration_ranges, CALIBRATED_ANCHOR_COUNT, target_km)
    )
    baseline_low, baseline_high = combined_range(baseline_ranges)
    fast_anchor = shortest_anchor_range(calibration_ranges)
    return [
        RangeComparison(
            CALIBRATED_RANGE_LABEL, calibrated_low, calibrated_high, actual_s
        ),
        RangeComparison(BASELINE_RANGE_LABEL, baseline_low, baseline_high, actual_s),
        RangeComparison(
            FAST_ANCHOR_RANGE_LABEL, fast_anchor.low_s, fast_anchor.high_s, actual_s
        ),
    ]


def implied_riegel_exponent(
    anchor: Effort, actual_s: float, target_km: float = HALF_MARATHON_KM
) -> float:
    """The exponent that maps an anchor effort exactly onto the actual race time.

    Solves the Riegel relation for b. A value below 1 is outside anything
    the model can produce from a maximal effort: it says the longer race
    was run at a faster pace than the anchor, which means the anchor was
    run well below race effort.
    """
    if anchor.distance_km == target_km:
        raise ValueError("Anchor and target distances must differ to imply an exponent")
    return math.log(actual_s / anchor.time_s) / math.log(target_km / anchor.distance_km)


def required_effort_scale(prediction: PredictionRange, actual_s: float) -> float:
    """The effort scale that would have made this anchor predict the actual time.

    Riegel predictions scale linearly with the anchor time, so this is the
    multiplier on the logged time needed to land on the actual result. It
    is directly comparable with the effort-scale bounds assumed before the
    race, which is the point of computing it.
    """
    return actual_s / prediction.point_s


def format_gap(seconds: float) -> str:
    """Format a gap between two times as M:SS, or H:MM:SS once it reaches an hour."""
    rounded = int(round(abs(seconds)))
    hours, remainder = divmod(rounded, 3600)
    minutes, whole_seconds = divmod(remainder, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{whole_seconds:02d}"
    return f"{minutes}:{whole_seconds:02d}"


def describe_gap(comparison: RangeComparison) -> str:
    """One phrase saying where the actual time landed relative to the range."""
    if not comparison.contains_actual:
        direction = "faster than" if comparison.miss_s > 0 else "slower than"
        return f"{format_gap(comparison.miss_s)} {direction} the range"
    return (
        f"inside, {format_gap(comparison.gap_from_fast_end_s)} clear of the fast end, "
        f"{format_gap(comparison.gap_from_slow_end_s)} clear of the slow end"
    )


def exact_gap_seconds(comparison: RangeComparison) -> str:
    """The same gap to a tenth of a second, so nothing rests on the rounding."""
    if not comparison.contains_actual:
        return f"{abs(comparison.miss_s):.1f} s"
    return (
        f"{comparison.gap_from_fast_end_s:.1f} s / "
        f"{comparison.gap_from_slow_end_s:.1f} s"
    )
