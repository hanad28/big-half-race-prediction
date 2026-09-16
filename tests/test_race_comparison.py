from pathlib import Path

import pytest

from big_half.baseline import build_predictions
from big_half.calibration import build_calibration_predictions
from big_half.data_loading import RACE_RESULT_CSV_PATH, Effort, load_race_result
from big_half.prediction import (
    HALF_MARATHON_KM,
    PredictionRange,
    intersection_range,
    predict_with_uncertainty,
    ranges_closest_to_target,
    shortest_anchor_range,
)
from big_half.race_comparison import (
    RangeComparison,
    build_range_comparisons,
    describe_gap,
    exact_gap_seconds,
    format_gap,
    implied_riegel_exponent,
    required_effort_scale,
)
from big_half.riegel import format_hms, predict_time


def test_load_race_result_reads_the_single_race() -> None:
    race = load_race_result()
    assert race.official_distance_km == 21.0975
    assert race.gps_distance_km == 21.3565
    assert race.moving_time_s == 6769.0
    assert race.elapsed_time_s == 6778.0
    assert race.name == "BIG HALF"
    assert race.date == "2026-09-06"


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


def _range(
    low_s: float, high_s: float, distance_km: float = 10.0
) -> PredictionRange:
    anchor = Effort(
        label=f"{distance_km} km", distance_km=distance_km, time_s=3000.0
    )
    return PredictionRange(
        anchor=anchor,
        point_s=(low_s + high_s) / 2,
        low_s=low_s,
        high_s=high_s,
        effort_scale_bounds=(1.0, 1.0),
    )


def test_comparison_inside_range() -> None:
    comparison = RangeComparison("window", low_s=6000.0, high_s=7000.0, actual_s=6400.0)
    assert comparison.contains_actual
    assert comparison.gap_from_fast_end_s == 400.0
    assert comparison.gap_from_slow_end_s == 600.0
    assert comparison.miss_s == 0.0


def test_comparison_faster_than_range() -> None:
    comparison = RangeComparison("window", low_s=6000.0, high_s=7000.0, actual_s=5700.0)
    assert not comparison.contains_actual
    assert comparison.miss_s == 300.0
    assert "faster than the range" in describe_gap(comparison)
    assert exact_gap_seconds(comparison) == "300.0 s"


def test_comparison_slower_than_range() -> None:
    comparison = RangeComparison("window", low_s=6000.0, high_s=7000.0, actual_s=7200.0)
    assert not comparison.contains_actual
    assert comparison.miss_s == -200.0
    assert "slower than the range" in describe_gap(comparison)


def test_comparison_on_the_boundary_counts_as_inside() -> None:
    for actual_s in (6000.0, 7000.0):
        comparison = RangeComparison(
            "window", low_s=6000.0, high_s=7000.0, actual_s=actual_s
        )
        assert comparison.contains_actual
        assert comparison.miss_s == 0.0


def test_format_gap() -> None:
    assert format_gap(306.207) == "5:06"
    assert format_gap(-306.207) == "5:06"
    assert format_gap(59.6) == "1:00"
    assert format_gap(3725.0) == "1:02:05"


def test_intersection_range_is_the_agreed_window() -> None:
    low, high = intersection_range([_range(6000.0, 7000.0), _range(6500.0, 7500.0)])
    assert (low, high) == (6500.0, 7000.0)


def test_intersection_range_rejects_disjoint_intervals() -> None:
    with pytest.raises(ValueError):
        intersection_range([_range(6000.0, 6400.0), _range(6500.0, 7500.0)])


def test_ranges_closest_to_target_picks_by_anchor_distance() -> None:
    ranges = [
        _range(1.0, 2.0, distance_km=5.0),
        _range(1.0, 2.0, distance_km=15.04),
        _range(1.0, 2.0, distance_km=10.0),
    ]
    closest = ranges_closest_to_target(ranges, count=2)
    assert [r.anchor.distance_km for r in closest] == [15.04, 10.0]
    assert shortest_anchor_range(ranges).anchor.distance_km == 5.0


def test_ranges_closest_to_target_rejects_impossible_count() -> None:
    with pytest.raises(ValueError):
        ranges_closest_to_target([_range(1.0, 2.0)], count=2)


def test_published_windows_are_reproduced_exactly() -> None:
    """The three comparison windows must match the committed artefacts."""
    race = load_race_result()
    comparisons = build_range_comparisons(
        build_predictions(), build_calibration_predictions(), race.moving_time_s
    )
    windows = [(format_hms(c.low_s), format_hms(c.high_s)) for c in comparisons]
    assert windows == [
        ("1:57:55", "2:05:20"),  # calibration artefact, two nearest anchors
        ("1:47:00", "2:07:26"),  # baseline artefact, union of both anchors
        ("1:47:00", "1:57:04"),  # calibration artefact, 5k anchor row
    ]


def test_actual_result_lands_inside_the_fast_anchor_range_only() -> None:
    race = load_race_result()
    calibrated, baseline, fast_anchor = build_range_comparisons(
        build_predictions(), build_calibration_predictions(), race.moving_time_s
    )
    assert not calibrated.contains_actual
    assert calibrated.miss_s > 0  # faster than the calibrated window
    assert baseline.contains_actual
    assert fast_anchor.contains_actual


def test_conclusion_holds_for_elapsed_time_as_well_as_moving_time() -> None:
    """The 9 s moving-versus-elapsed difference must not drive the finding."""
    race = load_race_result()
    for actual_s in (race.moving_time_s, race.elapsed_time_s):
        calibrated, _, fast_anchor = build_range_comparisons(
            build_predictions(), build_calibration_predictions(), actual_s
        )
        assert not calibrated.contains_actual
        assert fast_anchor.contains_actual


def test_implied_exponent_round_trips_through_riegel() -> None:
    anchor = Effort(label="5k", distance_km=5.0, time_s=1415.0)
    actual_s = 6769.0
    exponent = implied_riegel_exponent(anchor, actual_s)
    round_tripped = predict_time(
        anchor.distance_km, anchor.time_s, HALF_MARATHON_KM, exponent
    )
    assert round_tripped == pytest.approx(actual_s)
    assert exponent == pytest.approx(1.0872, abs=0.0001)


def test_implied_exponent_below_one_for_a_submaximal_anchor() -> None:
    """A training run slower per km than the race implies an impossible exponent."""
    anchor = Effort(label="long", distance_km=15.04, time_s=88.97 * 60)
    assert implied_riegel_exponent(anchor, 6769.0) < 1.0


def test_implied_exponent_needs_two_distances() -> None:
    anchor = Effort(label="half", distance_km=HALF_MARATHON_KM, time_s=6769.0)
    with pytest.raises(ValueError):
        implied_riegel_exponent(anchor, 6769.0)


def test_required_effort_scale_lands_on_the_actual_time() -> None:
    anchor = Effort(label="long", distance_km=15.04, time_s=88.97 * 60)
    prediction = predict_with_uncertainty(anchor, is_maximal_effort=False)
    scale = required_effort_scale(prediction, actual_s=6769.0)
    assert prediction.point_s * scale == pytest.approx(6769.0)
    assert scale < 0.90  # more generous than the effort assumption allowed for
