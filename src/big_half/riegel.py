"""Riegel's endurance model for predicting race times across distances.

Riegel (1981) showed that endurance performance across running distances
follows a power law: t = a * d^b, where b (the "fatigue factor") is about
1.06 for running events lasting roughly 3.5 to 230 minutes. Rearranged to
predict a time at a new distance from a known performance:

    t2 = t1 * (d2 / d1) ** b
"""

from __future__ import annotations

# Riegel (1981) fatigue factor for running in the endurance range
RIEGEL_DEFAULT_EXPONENT: float = 1.06


def predict_time(
    known_distance_km: float,
    known_time_s: float,
    target_distance_km: float,
    exponent: float = RIEGEL_DEFAULT_EXPONENT,
) -> float:
    """Predict the time (seconds) for a target distance from a known effort.

    Raises ValueError if any distance or time is not positive.
    """
    if known_distance_km <= 0 or target_distance_km <= 0:
        raise ValueError("Distances must be positive")
    if known_time_s <= 0:
        raise ValueError("Known time must be positive")
    return known_time_s * (target_distance_km / known_distance_km) ** exponent


def format_hms(total_seconds: float) -> str:
    """Format seconds as H:MM:SS, rounding to the nearest second."""
    rounded = int(round(total_seconds))
    hours, remainder = divmod(rounded, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours}:{minutes:02d}:{seconds:02d}"
