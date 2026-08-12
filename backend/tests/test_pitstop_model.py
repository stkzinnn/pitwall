import pytest

from app.schemas.session import PitStop
from app.simulation.pitstop_model import calculate_average_pit_stop_cost


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
