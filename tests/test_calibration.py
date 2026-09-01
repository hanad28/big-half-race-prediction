from pathlib import Path

import pytest

from big_half.calibration import (
    build_calibration_predictions,
    check_against_committed,
    write_artefact,
)
from big_half.data_loading import final_progression_run_effort
from big_half.prediction import (
    LONG_ANCHOR_EFFORT_SCALE_LOW,
    PROGRESSION_ANCHOR_EFFORT_SCALE_HIGH,
    PROGRESSION_ANCHOR_EFFORT_SCALE_LOW,
    combined_range,
    point_prediction,
    predict_with_uncertainty,
)


def test_final_progression_run_effort_loads_cleaned_run() -> None:
    effort = final_progression_run_effort()
    assert effort.distance_km == 10.00
    assert effort.time_s == 3354.0  # 55:54


def test_progression_anchor_point_prediction() -> None:
    effort = final_progression_run_effort()
    # 3354 * (21.0975 / 10) ** 1.06 = 7400.3s
    assert abs(point_prediction(effort) - 7400.3) < 1.0


def test_progression_anchor_uses_narrower_effort_scale() -> None:
    assert PROGRESSION_ANCHOR_EFFORT_SCALE_LOW > LONG_ANCHOR_EFFORT_SCALE_LOW
    assert PROGRESSION_ANCHOR_EFFORT_SCALE_HIGH == 1.00


def test_progression_anchor_range_narrower_than_steady_assumption() -> None:
    effort = final_progression_run_effort()
    progression = predict_with_uncertainty(
        effort,
        is_maximal_effort=False,
        effort_scale_bounds=(
            PROGRESSION_ANCHOR_EFFORT_SCALE_LOW,
            PROGRESSION_ANCHOR_EFFORT_SCALE_HIGH,
        ),
    )
    steady = predict_with_uncertainty(effort, is_maximal_effort=False)
    assert progression.low_s < progression.point_s < progression.high_s
    # The narrower effort assumption should not reach as far down
    assert progression.low_s > steady.low_s
    assert progression.high_s - progression.low_s < steady.high_s - steady.low_s


def test_calibration_predictions_have_three_anchors() -> None:
    ranges = build_calibration_predictions()
    assert len(ranges) == 3
    labels = [prediction.anchor.label for prediction in ranges]
    assert any("Final progression run" in label for label in labels)
    low, high = combined_range(ranges)
    assert low == min(prediction.low_s for prediction in ranges)
    assert high == max(prediction.high_s for prediction in ranges)


def test_write_artefact_refuses_to_overwrite(tmp_path: Path) -> None:
    ranges = build_calibration_predictions()
    target = tmp_path / "calibration_prediction.md"
    write_artefact(ranges, output_path=target)
    with pytest.raises(FileExistsError):
        write_artefact(ranges, output_path=target)


def test_check_against_committed(tmp_path: Path) -> None:
    ranges = build_calibration_predictions()
    target = tmp_path / "calibration_prediction.md"
    write_artefact(ranges, output_path=target)
    assert check_against_committed(ranges, artefact_path=target)
    target.write_text(target.read_text().replace("2:0", "9:9"))
    assert not check_against_committed(ranges, artefact_path=target)
