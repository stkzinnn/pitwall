"""Unit tests for the data_complete / missing-data branches of fastf1_client.

Unlike test_fastf1_client.py (marked `integration`, hits a real FastF1
session), these tests mock fastf1.get_session() with hand-built DataFrames so
that specific missing-data scenarios are deterministic instead of depending
on finding a real historical session that happens to be incomplete. They run
offline, with no network or real cache access.
"""

import logging

import pandas as pd
import pytest

from app.data_sources import fastf1_client
from app.data_sources.fastf1_client import load_session_data


class FakeSession:
    """Stand-in for fastf1.core.Session, exposing only what the client uses."""

    def __init__(self, laps_df: pd.DataFrame, event_name: str | None = "Fake Grand Prix") -> None:
        self.laps = laps_df
        if event_name is not None:
            self.event = {"EventName": event_name}

    def load(self, **kwargs: object) -> None:
        pass


def _row(driver: str = "VER", lap_number: int = 1, stint: float = 1.0) -> dict:
    """A fully-populated lap row; tests override individual fields to punch
    holes in specific data categories."""
    return {
        "Driver": driver,
        "LapNumber": float(lap_number),
        "LapTime": pd.Timedelta(seconds=90 + lap_number),
        "Stint": stint,
        "PitOutTime": pd.NaT,
        "PitInTime": pd.NaT,
        "Sector1Time": pd.Timedelta(seconds=30),
        "Sector2Time": pd.Timedelta(seconds=35),
        "Sector3Time": pd.Timedelta(seconds=25),
        "Compound": "MEDIUM",
        "TyreLife": float(lap_number),
        "Position": 1.0,
        "TrackStatus": "1",
    }


def _laps_df(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(rows)


@pytest.fixture(autouse=True)
def _skip_real_cache_setup(monkeypatch: pytest.MonkeyPatch) -> None:
    """These are unit tests: never touch the real on-disk FastF1 cache."""
    monkeypatch.setattr(fastf1_client, "configure_fastf1_cache", lambda: None)


def _patch_get_session(monkeypatch: pytest.MonkeyPatch, fake_session: FakeSession) -> None:
    monkeypatch.setattr(fastf1_client.fastf1, "get_session", lambda *a, **k: fake_session)


def test_empty_laps_yields_empty_data_and_incomplete_flag(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    _patch_get_session(monkeypatch, FakeSession(pd.DataFrame()))

    with caplog.at_level(logging.WARNING):
        result = load_session_data(year=2099, round=1, session_type="R")

    assert result.laps == []
    assert result.pit_stops == []
    assert result.stints == []
    assert result.data_complete is False
    assert any("No lap data available" in message for message in caplog.messages)


def test_missing_pit_stop_data_marks_incomplete_but_keeps_other_data(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """Only pit stop timing is missing; compound and sectors are fine. This
    must independently flip data_complete to False (see the comment above
    the data_complete checks in fastf1_client.py) while still returning the
    laps/stints that ARE derivable."""
    rows = [_row("VER", lap_number=n, stint=1.0) for n in (1, 2, 3)]
    _patch_get_session(monkeypatch, FakeSession(_laps_df(rows)))

    with caplog.at_level(logging.WARNING):
        result = load_session_data(year=2099, round=1, session_type="R")

    assert result.pit_stops == []
    assert result.data_complete is False
    assert len(result.laps) == 3
    assert len(result.stints) == 1
    assert result.stints[0].compound == "MEDIUM"
    assert any("No pit stop data available" in message for message in caplog.messages)


def test_missing_compound_data_marks_incomplete(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    rows = [_row("VER", lap_number=n, stint=1.0) for n in (1, 2, 3)]
    for row in rows:
        row["Compound"] = None
    _patch_get_session(monkeypatch, FakeSession(_laps_df(rows)))

    with caplog.at_level(logging.WARNING):
        result = load_session_data(year=2099, round=1, session_type="R")

    assert result.data_complete is False
    assert all(lap.compound is None for lap in result.laps)
    assert result.stints[0].compound is None
    assert any("No tyre compound data available" in message for message in caplog.messages)


def test_missing_sector_time_data_marks_incomplete(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    rows = [_row("VER", lap_number=n, stint=1.0) for n in (1, 2, 3)]
    for row in rows:
        row["Sector1Time"] = pd.NaT
        row["Sector2Time"] = pd.NaT
        row["Sector3Time"] = pd.NaT
    _patch_get_session(monkeypatch, FakeSession(_laps_df(rows)))

    with caplog.at_level(logging.WARNING):
        result = load_session_data(year=2099, round=1, session_type="R")

    assert result.data_complete is False
    assert all(lap.sector_1_seconds is None for lap in result.laps)
    assert any("No sector time data available" in message for message in caplog.messages)


def test_fully_populated_session_marks_complete(monkeypatch: pytest.MonkeyPatch) -> None:
    """Control case: pit stops, compound and sector data are all present, so
    data_complete must be True. Guards against the missing-data checks above
    accidentally always tripping to False."""
    row1 = _row("VER", lap_number=1, stint=1.0)
    row1["PitInTime"] = pd.Timedelta(seconds=100)
    row2 = _row("VER", lap_number=2, stint=2.0)
    row2["PitOutTime"] = pd.Timedelta(seconds=125)
    row3 = _row("VER", lap_number=3, stint=2.0)
    _patch_get_session(monkeypatch, FakeSession(_laps_df([row1, row2, row3])))

    result = load_session_data(year=2099, round=1, session_type="R")

    assert result.data_complete is True
    assert len(result.laps) == 3
    assert len(result.stints) == 2

    assert len(result.pit_stops) == 1
    assert result.pit_stops[0].driver == "VER"
    assert result.pit_stops[0].lap_number == 1
    assert result.pit_stops[0].duration_seconds == pytest.approx(25.0)


def test_event_name_falls_back_to_none_when_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    """session.event can be missing/unreadable on some sessions; this must
    not raise, just yield event_name=None."""
    session = FakeSession(_laps_df([_row()]), event_name=None)
    _patch_get_session(monkeypatch, session)

    result = load_session_data(year=2099, round=1, session_type="R")

    assert result.event_name is None


def test_optional_numeric_lap_fields_become_none_when_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Position/TyreLife/LapTime can be NaN/NaT on a given lap (e.g. a
    retirement or an out-lap); these must surface as None, not crash or get
    coerced to 0/NaN."""
    row = _row("VER", lap_number=1, stint=1.0)
    row["Position"] = float("nan")
    row["TyreLife"] = float("nan")
    row["LapTime"] = pd.NaT
    _patch_get_session(monkeypatch, FakeSession(_laps_df([row])))

    result = load_session_data(year=2099, round=1, session_type="R")

    lap = result.laps[0]
    assert lap.position is None
    assert lap.tyre_life is None
    assert lap.lap_time_seconds is None


def test_laps_with_no_stint_number_are_excluded_from_stints(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A lap can lack a Stint value (e.g. an in-progress/incomplete lap);
    such rows must be skipped when building stints, not crash the grouping."""
    row_with_stint = _row("VER", lap_number=1, stint=1.0)
    row_without_stint = _row("VER", lap_number=2, stint=float("nan"))
    _patch_get_session(monkeypatch, FakeSession(_laps_df([row_with_stint, row_without_stint])))

    result = load_session_data(year=2099, round=1, session_type="R")

    assert len(result.laps) == 2
    assert len(result.stints) == 1
    assert result.stints[0].start_lap == 1
