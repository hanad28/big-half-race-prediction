"""Loading and summarising the training run dataset and the race result."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
RUNS_CSV_PATH = REPO_ROOT / "data" / "strava_runs_big_half.csv"
FINAL_RUN_CSV_PATH = REPO_ROOT / "data" / "final_long_run.csv"
RACE_RESULT_CSV_PATH = REPO_ROOT / "data" / "race_result.csv"


@dataclass(frozen=True)
class Effort:
    """A single running effort used as an extrapolation anchor."""

    label: str
    distance_km: float
    time_s: float

    @property
    def pace_s_per_km(self) -> float:
        return self.time_s / self.distance_km


@dataclass(frozen=True)
class RaceResult:
    """The actual race outcome, as logged and cleaned.

    Two distances are kept deliberately. The predictions were made for the
    official race distance, so that is what any comparison must use; the
    GPS distance is retained only to document the discrepancy between them.
    """

    label: str
    official_distance_km: float
    gps_distance_km: float
    moving_time_s: float
    elapsed_time_s: float

    @property
    def pace_s_per_km(self) -> float:
        """Race pace over the official distance, which is what was predicted."""
        return self.moving_time_s / self.official_distance_km

    @property
    def gps_distance_excess_km(self) -> float:
        return self.gps_distance_km - self.official_distance_km


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


def load_race_result(csv_path: Path = RACE_RESULT_CSV_PATH) -> RaceResult:
    """Load the single actual race result.

    Moving time is the figure comparable with the published predictions:
    those predicted a time for the official distance, and the race had no
    meaningful stops, so moving and elapsed time differ by seconds.
    """
    results = pd.read_csv(csv_path, parse_dates=["date"])
    if len(results) != 1:
        raise ValueError(
            f"Expected exactly one race result in {csv_path}, found {len(results)}"
        )
    race = results.iloc[0]
    return RaceResult(
        label=f"{race['name']} ({race['date'].date()})",
        official_distance_km=float(race["official_distance_km"]),
        gps_distance_km=float(race["gps_distance_km"]),
        moving_time_s=float(race["moving_time_s"]),
        elapsed_time_s=float(race["elapsed_time_s"]),
    )
