from pathlib import Path

import pytest

from big_half import baseline, calibration, race_result
from big_half.artefact_guard import (
    CHART_HASH_PREFIX,
    TIMESTAMP_LINE_PREFIX,
    ArtefactSetState,
    chart_hash_matches,
    inspect_artefact_set,
    recorded_chart_hash,
    sha256_of_file,
    without_timestamp_line,
    write_once,
)

# Every artefact set the repository has committed. None of them may ever
# change as a side effect of running a stage again.
COMMITTED_ARTEFACT_PATHS = [
    baseline.BASELINE_ARTEFACT_PATH,
    baseline.BASELINE_CHART_PATH,
    calibration.CALIBRATION_ARTEFACT_PATH,
    calibration.CALIBRATION_CHART_PATH,
    race_result.RACE_RESULT_ARTEFACT_PATH,
    race_result.RACE_RESULT_CHART_PATH,
]

STAGE_GENERATORS = [baseline.main, calibration.main, race_result.main]



def _render(chart_hash: str, values: str = "point 1:52:49") -> str:
    return (
        f"# Stage\n\n{TIMESTAMP_LINE_PREFIX}2026-09-16 09:00 UTC\n\n"
        f"{values}\n\n{CHART_HASH_PREFIX}{chart_hash}\n"
    )


@pytest.fixture
def artefact_set(tmp_path: Path) -> tuple[Path, Path]:
    chart = tmp_path / "chart.png"
    chart.write_bytes(b"chart bytes")
    artefact = tmp_path / "stage.md"
    write_once(artefact, _render(sha256_of_file(chart)))
    return artefact, chart


def test_write_once_refuses_to_overwrite(tmp_path: Path) -> None:
    artefact = tmp_path / "stage.md"
    write_once(artefact, "first\n")
    with pytest.raises(FileExistsError):
        write_once(artefact, "second\n")
    assert artefact.read_text() == "first\n"


def test_write_once_creates_missing_parent_directories(tmp_path: Path) -> None:
    artefact = tmp_path / "nested" / "stage.md"
    assert write_once(artefact, "body\n").read_text() == "body\n"


def test_without_timestamp_line_strips_only_the_timestamp() -> None:
    stripped = without_timestamp_line(_render("abc"))
    assert TIMESTAMP_LINE_PREFIX not in stripped
    assert "point 1:52:49" in stripped
    assert CHART_HASH_PREFIX in stripped


def test_recorded_chart_hash_reads_back_what_was_written() -> None:
    assert recorded_chart_hash(_render("abc123")) == "abc123"
    assert recorded_chart_hash("# Stage\n\nno hash here\n") is None



def test_chart_hash_matches_is_false_without_a_chart(
    artefact_set: tuple[Path, Path]
) -> None:
    artefact, chart = artefact_set
    chart.unlink()
    assert not chart_hash_matches(artefact, chart)


def test_inspect_reports_absent_when_nothing_is_written(tmp_path: Path) -> None:
    state = inspect_artefact_set(tmp_path / "stage.md", tmp_path / "chart.png", _render)
    assert state is ArtefactSetState.ABSENT


def test_inspect_reports_a_clean_set_as_matching(
    artefact_set: tuple[Path, Path]
) -> None:
    artefact, chart = artefact_set
    state = inspect_artefact_set(artefact, chart, _render)
    assert state is ArtefactSetState.VALUES_MATCH


def test_inspect_ignores_a_changed_timestamp(artefact_set: tuple[Path, Path]) -> None:
    artefact, chart = artefact_set
    artefact.write_text(
        artefact.read_text().replace("2026-09-16 09:00", "2027-01-01 00:00")
    )
    state = inspect_artefact_set(artefact, chart, _render)
    assert state is ArtefactSetState.VALUES_MATCH


def test_inspect_detects_changed_values(artefact_set: tuple[Path, Path]) -> None:
    artefact, chart = artefact_set
    artefact.write_text(_render(sha256_of_file(chart), values="point 9:99:99"))
    state = inspect_artefact_set(artefact, chart, _render)
    assert state is ArtefactSetState.VALUES_DIFFER


def test_inspect_detects_a_tampered_chart(artefact_set: tuple[Path, Path]) -> None:
    artefact, chart = artefact_set
    chart.write_bytes(b"different chart bytes")
    state = inspect_artefact_set(artefact, chart, _render)
    assert state is ArtefactSetState.CHART_HASH_MISMATCH


def test_inspect_detects_half_a_set(artefact_set: tuple[Path, Path]) -> None:
    artefact, chart = artefact_set
    artefact.unlink()
    state = inspect_artefact_set(artefact, chart, _render)
    assert state is ArtefactSetState.ARTEFACT_MISSING

    artefact.write_text(_render(sha256_of_file(chart)))
    chart.unlink()
    state = inspect_artefact_set(artefact, chart, _render)
    assert state is ArtefactSetState.CHART_MISSING


def test_committed_artefacts_still_pin_their_own_charts() -> None:
    """Each committed artefact must still pin the chart it was written with."""
    assert chart_hash_matches(
        calibration.CALIBRATION_ARTEFACT_PATH, calibration.CALIBRATION_CHART_PATH
    )
    assert chart_hash_matches(
        race_result.RACE_RESULT_ARTEFACT_PATH, race_result.RACE_RESULT_CHART_PATH
    )


def test_rerunning_every_stage_leaves_committed_artefacts_byte_identical() -> None:
    """The end-to-end guard check: no stage may rewrite what is committed."""
    missing = [path for path in COMMITTED_ARTEFACT_PATHS if not path.exists()]
    assert not missing, f"committed artefacts missing from the working tree: {missing}"

    before = {path: sha256_of_file(path) for path in COMMITTED_ARTEFACT_PATHS}
    for generate_stage in STAGE_GENERATORS:
        generate_stage()
    after = {path: sha256_of_file(path) for path in COMMITTED_ARTEFACT_PATHS}
    assert after == before
