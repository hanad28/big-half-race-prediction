"""Baseline half marathon predictions and Monte Carlo uncertainty ranges."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from big_half.data_loading import Effort
from big_half.riegel import RIEGEL_DEFAULT_EXPONENT, predict_time

HALF_MARATHON_KM: float = 21.0975

# Plausible Riegel exponent range for a recreational runner. Riegel (1981)
# fitted ~1.06; Vickers and Vertosick (2016) found 1.06 well calibrated up
# to the half marathon but optimistic beyond it, with slower runners better
# described by higher exponents.
EXPONENT_LOW: float = 1.05
EXPONENT_HIGH: float = 1.10

# The 5k anchor is a Strava best-effort extraction from within training
# runs, not a standalone time trial. A fresh standalone 5k could be
# slightly faster or slower, so scale the anchor time by this range.
FAST_ANCHOR_TIME_SCALE_LOW: float = 0.98
FAST_ANCHOR_TIME_SCALE_HIGH: float = 1.04

# The long run was a steady training effort, not a race. A race effort
# over the same distance would plausibly take 90-100% of the logged time.
LONG_ANCHOR_EFFORT_SCALE_LOW: float = 0.90
LONG_ANCHOR_EFFORT_SCALE_HIGH: float = 1.00

# The final 10 km run was a deliberate progression: comfortable early,
# built to near race effort through km 7-9 (HR 167-177), easing in km 10.
# Part of the run was already at race intensity, so the plausible gap
# between a race effort and the logged time is smaller than for the
# steady 15 km long run: up to 5% faster, rather than up to 10%.
PROGRESSION_ANCHOR_EFFORT_SCALE_LOW: float = 0.95
PROGRESSION_ANCHOR_EFFORT_SCALE_HIGH: float = 1.00

MONTE_CARLO_DRAWS: int = 20_000

# Quantiles of the Monte Carlo output reported as the prediction range.
# The inputs are subjective uniform bounds on the assumptions, so this is
# a scenario range under stated assumptions, not a calibrated confidence
# interval derived from observed sampling uncertainty.
MONTE_CARLO_RANGE_QUANTILES: tuple[float, float] = (0.05, 0.95)


@dataclass(frozen=True)
class PredictionRange:
    """A point prediction with a Monte Carlo range (5th-95th percentile
    under stated assumptions), in seconds.

    The range carries the effort-scale bounds it was drawn under, so a
    later stage can compare what was assumed against what happened
    without having to restate the assumption by hand.
    """

    anchor: Effort
    point_s: float
    low_s: float
    high_s: float
    effort_scale_bounds: tuple[float, float]


def point_prediction(anchor: Effort, target_km: float = HALF_MARATHON_KM) -> float:
    """Riegel point prediction (seconds) using the default 1.06 exponent."""
    return predict_time(anchor.distance_km, anchor.time_s, target_km, RIEGEL_DEFAULT_EXPONENT)


def _monte_carlo_times(
    anchor: Effort,
    time_scale_low: float,
    time_scale_high: float,
    rng: np.random.Generator,
    target_km: float,
) -> np.ndarray:
    exponents = rng.uniform(EXPONENT_LOW, EXPONENT_HIGH, MONTE_CARLO_DRAWS)
    time_scales = rng.uniform(time_scale_low, time_scale_high, MONTE_CARLO_DRAWS)
    distance_ratio = target_km / anchor.distance_km
    return anchor.time_s * time_scales * distance_ratio**exponents


def predict_with_uncertainty(
    anchor: Effort,
    is_maximal_effort: bool,
    target_km: float = HALF_MARATHON_KM,
    seed: int = 42,
    effort_scale_bounds: tuple[float, float] | None = None,
) -> PredictionRange:
    """Monte Carlo prediction range over plausible exponent and effort values.

    Maximal-effort anchors (a best 5k) get a small symmetric time
    uncertainty; sub-maximal anchors (a steady long run) get a downward
    effort adjustment, since a race over the anchor distance would be
    faster than the logged training time. Anchors that sit between the
    two, such as a progression run partly at race effort, can pass
    explicit bounds via effort_scale_bounds, overriding the
    is_maximal_effort defaults.
    """
    rng = np.random.default_rng(seed)
    if effort_scale_bounds is not None:
        scale_low, scale_high = effort_scale_bounds
    elif is_maximal_effort:
        scale_low, scale_high = FAST_ANCHOR_TIME_SCALE_LOW, FAST_ANCHOR_TIME_SCALE_HIGH
    else:
        scale_low, scale_high = LONG_ANCHOR_EFFORT_SCALE_LOW, LONG_ANCHOR_EFFORT_SCALE_HIGH
    samples = _monte_carlo_times(anchor, scale_low, scale_high, rng, target_km)
    low_q, high_q = MONTE_CARLO_RANGE_QUANTILES
    return PredictionRange(
        anchor=anchor,
        point_s=point_prediction(anchor, target_km),
        low_s=float(np.quantile(samples, low_q)),
        high_s=float(np.quantile(samples, high_q)),
        effort_scale_bounds=(scale_low, scale_high),
    )


def combined_range(ranges: list[PredictionRange]) -> tuple[float, float]:
    """A single honest overall range: the union of the anchor intervals."""
    return min(r.low_s for r in ranges), max(r.high_s for r in ranges)


def intersection_range(ranges: list[PredictionRange]) -> tuple[float, float]:
    """The window where every supplied anchor interval agrees.

    Raises ValueError if the intervals do not all overlap, since an empty
    intersection has no honest reading as a prediction range.
    """
    low = max(r.low_s for r in ranges)
    high = min(r.high_s for r in ranges)
    if low > high:
        raise ValueError("Anchor intervals do not overlap, so there is no intersection")
    return low, high


def ranges_closest_to_target(
    ranges: list[PredictionRange],
    count: int,
    target_km: float = HALF_MARATHON_KM,
) -> list[PredictionRange]:
    """The `count` anchors whose own distance sits nearest the target distance.

    Riegel extrapolation is most reliable over short distance ratios, so
    proximity to the target is the criterion for which anchors to trust.
    """
    if count > len(ranges):
        raise ValueError(f"Asked for {count} anchors but only {len(ranges)} supplied")
    by_proximity = sorted(
        ranges, key=lambda r: abs(r.anchor.distance_km - target_km)
    )
    return by_proximity[:count]


def shortest_anchor_range(ranges: list[PredictionRange]) -> PredictionRange:
    """The anchor over the shortest distance, which is the near-maximal effort."""
    return min(ranges, key=lambda r: r.anchor.distance_km)
