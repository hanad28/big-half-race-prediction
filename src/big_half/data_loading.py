"""Loading and summarising the training run dataset."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
RUNS_CSV_PATH = REPO_ROOT / "data" / "strava_runs_big_half.csv"
FINAL_RUN_CSV_PATH = REPO_ROOT / "data" / "final_long_run.csv"


@dataclass(frozen=True)
class Effort:
    """A single running effort used as an extrapolation anchor."""

    label: str
    distance_km: float
    time_s: float

    @property
    def pace_s_per_km(self) -> float:
        return self.time_s / self.distance_km


def load_runs(csv_path: Path = RUNS_CSV_PATH) -> pd.DataFrame:
    """Load the training runs, sorted oldest first."""
    runs = pd.read_csv(csv_path, parse_dates=["date"])
    return runs.sort_values("date").reset_index(drop=True)


def longest_run_effort(runs: pd.DataFrame) -> Effort:
    """The longest run in the dataset, as an extrapolation anchor."""
    longest = runs.loc[runs["distance_km"].idxmax()]
    return Effort(
        label=f"Longest training run ({longest['distance_km']:.2f} km)",
        distance_km=float(longest["distance_km"]),
        time_s=float(longest["moving_time_min"]) * 60.0,
    )


def final_progression_run_effort(csv_path: Path = FINAL_RUN_CSV_PATH) -> Effort:
    """The final pre-race progression run, as an extrapolation anchor.

    The CSV is a single cleaned run: a trailing car-travel segment
    recorded after the run finished was removed at source, so the file
    is taken as the complete, correct effort.
    """
    runs = pd.read_csv(csv_path, parse_dates=["date"])
    if len(runs) != 1:
        raise ValueError(f"Expected exactly one run in {csv_path}, found {len(runs)}")
    run = runs.iloc[0]
    return Effort(
        label=f"Final progression run ({run['distance_km']:.2f} km)",
        distance_km=float(run["distance_km"]),
        time_s=float(run["moving_time_s"]),
    )
