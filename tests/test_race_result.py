from pathlib import Path

import pytest

from big_half.artefact_guard import chart_hash_matches, sha256_of_file
from big_half.race_comparison import (
    CALIBRATED_RANGE_LABEL,
    FAST_ANCHOR_RANGE_LABEL,
)
from big_half.race_result import (
    analyse_race_result,
    render_artefact,
    write_artefact_set,
)


@pytest.fixture(scope="module")
def analysis():
    return analyse_race_result()


@pytest.fixture(scope="module")
def document(analysis) -> str:
    return render_artefact(
        analysis, generated_at="2026-09-16 09:00 UTC", chart_hash="abc"
    )


def test_analysis_covers_three_anchors_and_three_windows(analysis) -> None:
    assert len(analysis.calibration_ranges) == 3
    assert len(analysis.comparisons) == 3
    assert analysis.race.moving_time_s == 6769.0


def test_artefact_reports_every_published_window(document: str) -> None:
    assert "1:57:55 to 2:05:20" in document  # calibrated, two nearest anchors
    assert "1:47:00 to 2:07:26" in document  # baseline union
    assert "1:47:00 to 1:57:04" in document  # 5k anchor alone
    assert CALIBRATED_RANGE_LABEL in document
    assert FAST_ANCHOR_RANGE_LABEL in document


def test_artefact_quotes_gaps_to_a_tenth_of_a_second(document: str) -> None:
    assert "306.2 s" in document  # faster than the calibrated window
    assert "349.4 s / 876.9 s" in document  # inside the baseline union
    assert "349.4 s / 255.5 s" in document  # inside the 5k anchor window


def test_artefact_headline_leads_with_the_fast_anchor_finding(document: str) -> None:
    headline = document.split("## Headline")[1].split("##")[0]
    assert "falls inside the range belonging to the 5k anchor alone" in headline
    assert "5:06 faster than the range" in headline


def test_artefact_records_what_each_anchor_implied(document: str) -> None:
    # Only the near-maximal 5k anchor implies an exponent Riegel can produce
    assert "| 1.0872 | 1.0399 | 0.98 to 1.04 |" in document
    assert "| 0.7016 | 0.8858 | 0.90 to 1.00 |" in document
    assert "| 0.9406 | 0.9147 | 0.95 to 1.00 |" in document


def test_write_artefact_set_pins_the_chart_it_wrote(analysis, tmp_path: Path) -> None:
    artefact = tmp_path / "race_result.md"
    chart = tmp_path / "race_result_comparison.png"
    written_artefact, written_chart = write_artefact_set(analysis, artefact, chart)
    assert written_artefact.exists() and written_chart.exists()
    assert chart_hash_matches(written_artefact, written_chart)
    assert sha256_of_file(written_chart) in written_artefact.read_text()


def test_write_artefact_set_refuses_a_second_write(analysis, tmp_path: Path) -> None:
    artefact = tmp_path / "race_result.md"
    chart = tmp_path / "race_result_comparison.png"
    write_artefact_set(analysis, artefact, chart)
    original_artefact = artefact.read_bytes()
    original_chart = chart.read_bytes()
    with pytest.raises(FileExistsError):
        write_artefact_set(analysis, artefact, chart)
    assert artefact.read_bytes() == original_artefact
    # The refusal must come before the chart is redrawn, not after
    assert chart.read_bytes() == original_chart


def test_write_artefact_set_refuses_when_only_the_chart_survives(
    analysis, tmp_path: Path
) -> None:
    artefact = tmp_path / "race_result.md"
    chart = tmp_path / "race_result_comparison.png"
    write_artefact_set(analysis, artefact, chart)
    artefact.unlink()
    original_chart = chart.read_bytes()
    with pytest.raises(FileExistsError):
        write_artefact_set(analysis, artefact, chart)
    assert chart.read_bytes() == original_chart
    assert not artefact.exists()
