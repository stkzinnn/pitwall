import pytest

from app.data_sources.fastf1_client import SessionNotFoundError, load_session_data


@pytest.mark.integration
def test_load_session_data_returns_normalized_race_data() -> None:
    session_data = load_session_data(year=2023, round=1, session_type="R")

    assert session_data.event_name == "Bahrain Grand Prix"
    assert session_data.country == "Bahrain"
    assert session_data.total_laps == 57
    assert session_data.data_complete is True

    assert len(session_data.drivers) > 0
    driver = next(d for d in session_data.drivers if d.code == "VER")
    assert driver.full_name == "Max Verstappen"
    assert driver.number == 1
    assert driver.team_name == "Red Bull Racing"

    assert len(session_data.results) > 0
    winner = next(r for r in session_data.results if r.code == "VER")
    assert winner.position == 1
    assert winner.classified_position == "1"
    assert winner.status == "Finished"
    assert winner.total_time_seconds == pytest.approx(5636.736)
    assert winner.gap_to_leader_seconds is None
    runner_up = next(r for r in session_data.results if r.code == "PER")
    assert runner_up.position == 2
    assert runner_up.gap_to_leader_seconds == pytest.approx(11.987)

    assert len(session_data.laps) > 0
    lap = session_data.laps[0]
    assert lap.driver
    assert lap.lap_number >= 1

    assert len(session_data.stints) > 0
    stint = session_data.stints[0]
    assert stint.compound is not None
    assert stint.end_lap >= stint.start_lap

    assert len(session_data.pit_stops) > 0
    pit_stop = session_data.pit_stops[0]
    assert pit_stop.driver
    assert pit_stop.lap_number >= 1


@pytest.mark.integration
def test_load_session_data_raises_for_invalid_round() -> None:
    with pytest.raises(SessionNotFoundError):
        load_session_data(year=2023, round=999, session_type="R")
