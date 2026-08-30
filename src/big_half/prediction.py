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

MONTE_CARLO_DRAWS: int = 20_000
PREDICTION_INTERVAL_QUANTILES: tuple[float, float] = (0.05, 0.95)


@dataclass(frozen=True)
class PredictionRange:
    """A point prediction with a 90% Monte Carlo interval, in seconds."""

    anchor: Effort
    point_s: float
    low_s: float
    high_s: float


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
) -> PredictionRange:
    """Monte Carlo prediction range over plausible exponent and effort values.

    Maximal-effort anchors (a best 5k) get a small symmetric time
    uncertainty; sub-maximal anchors (a steady long run) get a downward
    effort adjustment, since a race over the anchor distance would be
    faster than the logged training time.
    """
    rng = np.random.default_rng(seed)
    if is_maximal_effort:
        scale_low, scale_high = FAST_ANCHOR_TIME_SCALE_LOW, FAST_ANCHOR_TIME_SCALE_HIGH
    else:
        scale_low, scale_high = LONG_ANCHOR_EFFORT_SCALE_LOW, LONG_ANCHOR_EFFORT_SCALE_HIGH
    samples = _monte_carlo_times(anchor, scale_low, scale_high, rng, target_km)
    low_q, high_q = PREDICTION_INTERVAL_QUANTILES
    return PredictionRange(
        anchor=anchor,
        point_s=point_prediction(anchor, target_km),
        low_s=float(np.quantile(samples, low_q)),
        high_s=float(np.quantile(samples, high_q)),
    )


def combined_range(ranges: list[PredictionRange]) -> tuple[float, float]:
    """A single honest overall range: the union of the anchor intervals."""
    return min(r.low_s for r in ranges), max(r.high_s for r in ranges)
