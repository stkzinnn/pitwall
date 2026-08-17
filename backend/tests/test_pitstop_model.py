import pytest

from app.schemas.session import PitStop
from app.simulation.pitstop_model import (
    calculate_average_pit_stop_cost,
    calculate_driver_pit_stop_cost,
)


def test_calculate_average_pit_stop_cost_averages_valid_durations() -> None:
    pit_stops = [
        PitStop(driver="VER", lap_number=10, duration_seconds=22.0),
        PitStop(driver="HAM", lap_number=12, duration_seconds=24.0),
    ]

    assert calculate_average_pit_stop_cost(pit_stops) == pytest.approx(23.0)


def test_calculate_average_pit_stop_cost_ignores_missing_durations() -> None:
    pit_stops = [
        PitStop(driver="VER", lap_number=10, duration_seconds=22.0),
        PitStop(driver="HAM", lap_number=12, duration_seconds=None),
    ]

    assert calculate_average_pit_stop_cost(pit_stops) == pytest.approx(22.0)


def test_calculate_average_pit_stop_cost_returns_none_when_no_data() -> None:
    assert calculate_average_pit_stop_cost([]) is None
    assert calculate_average_pit_stop_cost([PitStop(driver="VER", lap_number=1)]) is None


def test_calculate_driver_pit_stop_cost_uses_own_average_with_enough_stops() -> None:
    # VER has 2 own stops (>= MIN_DRIVER_PIT_STOPS_FOR_OWN_AVERAGE), averaging
    # 20.0s — clearly different from the session-wide average (which
    # includes much slower stops from other drivers) -> own average wins,
    # this is the /compare and /simulate endpoints' actual behaviour now.
    driver_pit_stops = [
        PitStop(driver="VER", lap_number=10, duration_seconds=19.0),
        PitStop(driver="VER", lap_number=30, duration_seconds=21.0),
    ]
    session_pit_stops = [
        *driver_pit_stops,
        PitStop(driver="HAM", lap_number=12, duration_seconds=45.0),
        PitStop(driver="PER", lap_number=14, duration_seconds=50.0),
    ]

    cost = calculate_driver_pit_stop_cost(driver_pit_stops, session_pit_stops)
    assert cost == pytest.approx(20.0)


def test_calculate_driver_pit_stop_cost_falls_back_to_session_average_with_one_stop() -> None:
    # Only 1 own stop with a valid duration -> too small a sample to trust
    # on its own (could be an anomaly), falls back to the session-wide
    # average instead.
    driver_pit_stops = [PitStop(driver="VER", lap_number=10, duration_seconds=90.0)]
    session_pit_stops = [
        *driver_pit_stops,
        PitStop(driver="HAM", lap_number=12, duration_seconds=22.0),
        PitStop(driver="PER", lap_number=14, duration_seconds=24.0),
    ]

    assert calculate_driver_pit_stop_cost(driver_pit_stops, session_pit_stops) == pytest.approx(
        (90.0 + 22.0 + 24.0) / 3
    )


def test_calculate_driver_pit_stop_cost_falls_back_to_session_average_with_no_stops() -> None:
    session_pit_stops = [
        PitStop(driver="HAM", lap_number=12, duration_seconds=22.0),
        PitStop(driver="PER", lap_number=14, duration_seconds=24.0),
    ]

    assert calculate_driver_pit_stop_cost([], session_pit_stops) == pytest.approx(23.0)


def test_calculate_driver_pit_stop_cost_returns_none_when_nothing_usable_anywhere() -> None:
    assert calculate_driver_pit_stop_cost([], []) is None
