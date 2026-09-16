from pathlib import Path

import pytest

from big_half.data_loading import RACE_RESULT_CSV_PATH, load_race_result


def test_load_race_result_reads_the_single_race() -> None:
    race = load_race_result()
    assert race.official_distance_km == 21.0975
    assert race.gps_distance_km == 21.3565
    assert race.moving_time_s == 6769.0
    assert race.elapsed_time_s == 6778.0
    assert "BIG HALF" in race.label


def test_race_result_derived_figures() -> None:
    race = load_race_result()
    # 6769 / 21.0975 = 320.84 s/km, about 5:21/km
    assert race.pace_s_per_km == pytest.approx(320.84, abs=0.01)
    assert race.gps_distance_excess_km == pytest.approx(0.259, abs=0.001)


def test_load_race_result_rejects_multi_row_file(tmp_path: Path) -> None:
    doubled = tmp_path / "race_result.csv"
    rows = RACE_RESULT_CSV_PATH.read_text().splitlines()
    doubled.write_text("\n".join([rows[0], rows[1], rows[1]]) + "\n")
    with pytest.raises(ValueError):
        load_race_result(doubled)
