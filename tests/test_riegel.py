import math

import pytest

from big_half.riegel import format_hms, predict_time


def test_same_distance_returns_same_time() -> None:
    assert predict_time(10.0, 3000.0, 10.0) == pytest.approx(3000.0)


def test_known_reference_20min_5k_to_10k() -> None:
    # A 20:00 5k predicts a 10k of 20 * 2^1.06 = 41.70 min (Riegel, 1981)
    predicted = predict_time(5.0, 20 * 60, 10.0)
    assert predicted == pytest.approx(20 * 60 * 2**1.06)
    assert predicted == pytest.approx(2502.2, abs=0.5)


def test_known_reference_5k_to_half_marathon() -> None:
    # 23:35 5k -> half marathon: 1415 * (21.0975/5)^1.06 = about 1:48:29
    predicted = predict_time(5.0, 1415.0, 21.0975)
    expected = 1415.0 * (21.0975 / 5.0) ** 1.06
    assert predicted == pytest.approx(expected)
    assert math.isclose(predicted, 6509.3, abs_tol=1.0)


def test_downward_extrapolation() -> None:
    # Predicting a shorter distance gives a proportionally faster pace
    predicted = predict_time(10.0, 3000.0, 5.0)
    assert predicted < 1500.0


def test_custom_exponent() -> None:
    linear = predict_time(5.0, 1500.0, 10.0, exponent=1.0)
    assert linear == pytest.approx(3000.0)


@pytest.mark.parametrize(
    "distance_km, time_s, target_km",
    [(0.0, 1500.0, 10.0), (5.0, 0.0, 10.0), (5.0, 1500.0, -1.0)],
)
def test_invalid_inputs_raise(distance_km: float, time_s: float, target_km: float) -> None:
    with pytest.raises(ValueError):
        predict_time(distance_km, time_s, target_km)


def test_format_hms() -> None:
    assert format_hms(6509.0) == "1:48:29"
    assert format_hms(59.6) == "0:01:00"
    assert format_hms(3600.0) == "1:00:00"
