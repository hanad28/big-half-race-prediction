from big_half.data_loading import Effort, load_runs, longest_run_effort
from big_half.prediction import combined_range, point_prediction, predict_with_uncertainty


FAST_5K = Effort(label="5k", distance_km=5.0, time_s=1415.0)


def test_point_prediction_matches_riegel() -> None:
    assert abs(point_prediction(FAST_5K) - 6509.3) < 1.0


def test_uncertainty_range_brackets_reasonable_values() -> None:
    prediction = predict_with_uncertainty(FAST_5K, is_maximal_effort=True)
    assert prediction.low_s < prediction.point_s < prediction.high_s
    # Range should stay within a plausible window around the point estimate
    assert prediction.low_s > prediction.point_s * 0.9
    assert prediction.high_s < prediction.point_s * 1.15


def test_submaximal_anchor_range_shifts_downwards() -> None:
    long_run = Effort(label="long", distance_km=15.04, time_s=88.97 * 60)
    prediction = predict_with_uncertainty(long_run, is_maximal_effort=False)
    # Effort adjustment allows outcomes faster than the naive point estimate
    assert prediction.low_s < prediction.point_s * 0.95


def test_reproducible_with_seed() -> None:
    first = predict_with_uncertainty(FAST_5K, is_maximal_effort=True, seed=7)
    second = predict_with_uncertainty(FAST_5K, is_maximal_effort=True, seed=7)
    assert (first.low_s, first.high_s) == (second.low_s, second.high_s)


def test_combined_range_is_union() -> None:
    fast = predict_with_uncertainty(FAST_5K, is_maximal_effort=True)
    long_run = Effort(label="long", distance_km=15.04, time_s=88.97 * 60)
    slow = predict_with_uncertainty(long_run, is_maximal_effort=False)
    low, high = combined_range([fast, slow])
    assert low == min(fast.low_s, slow.low_s)
    assert high == max(fast.high_s, slow.high_s)


def test_load_runs_and_longest_run() -> None:
    runs = load_runs()
    assert len(runs) == 11
    longest = longest_run_effort(runs)
    assert longest.distance_km == 15.04
    assert abs(longest.time_s - 88.97 * 60) < 1.0
