import pytest

from app.schemas.session import Lap, Stint
from app.simulation.fuel_model import ZERO_FUEL_EFFECT_CONFIG
from app.simulation.pace_model import build_driver_stint_pace_models
from app.simulation.safety_car import calculate_safety_car_time_lost, is_safety_car_lap

# These tests are about safety car detection/grouping, not fuel — use a
# zero-effect fuel config so the hand-computed expected values aren't also
# entangled with fuel correction (tested separately in test_fuel_model.py).
_TOTAL_LAPS = 100


def _lap(lap_number: int, lap_time_seconds: float, track_status: str = "1") -> Lap:
    return Lap(
        driver="VER",
        lap_number=lap_number,
        lap_time_seconds=lap_time_seconds,
        compound="SOFT",
        track_status=track_status,
    )


def _build_driver_stint_pace_models(laps: list[Lap], stints: list[Stint]):
    return build_driver_stint_pace_models(laps, stints, _TOTAL_LAPS, ZERO_FUEL_EFFECT_CONFIG)


def _calculate_safety_car_time_lost(laps, stints, stint_pace_models):
    return calculate_safety_car_time_lost(
        laps, stints, stint_pace_models, _TOTAL_LAPS, ZERO_FUEL_EFFECT_CONFIG
    )


def test_is_safety_car_lap_matches_sc_and_vsc_codes() -> None:
    assert is_safety_car_lap("4") is True  # Safety Car
    assert is_safety_car_lap("6") is True  # VSC deployed
    assert is_safety_car_lap("7") is True  # VSC ending
    assert is_safety_car_lap("126") is True  # VSC embedded among other codes
    assert is_safety_car_lap("1") is False  # green only
    assert is_safety_car_lap("12") is False  # green + yellow, no SC/VSC
    assert is_safety_car_lap(None) is False


def test_calculate_safety_car_time_lost_for_a_single_affected_lap() -> None:
    """One VSC-affected lap in the middle of an otherwise-clean stint: the
    time lost must be measured against the stint's own fitted pace model,
    at that lap's exact position in the stint."""
    stint_laps = [
        _lap(1, 105.0),  # out lap
        _lap(2, 90.0),
        _lap(3, 90.1),
        _lap(4, 150.0, track_status="126"),  # VSC-affected
        _lap(5, 90.3),
        _lap(6, 90.4),
    ]
    stint = Stint(driver="VER", stint_number=1, compound="SOFT", start_lap=1, end_lap=6)
    stint_pace_models = _build_driver_stint_pace_models(stint_laps, [stint])

    # Sanity-check the fitted model first (base=90.0, degradation=0.1,
    # matching the surrounding clean laps once the VSC lap is excluded as
    # an outlier from the fit — see test_pace_model.py for the same math).
    pace = stint_pace_models[0].pace
    assert pace is not None
    assert pace.base_pace_seconds == pytest.approx(90.0)
    assert pace.degradation_seconds_per_lap == pytest.approx(0.1, abs=1e-9)

    periods = _calculate_safety_car_time_lost(stint_laps, [stint], stint_pace_models)

    assert len(periods) == 1
    assert periods[0].laps == [4]
    # Lap 4 is at position 2 in the stint's coordinate system (laps 2,3
    # are positions 0,1). Expected clean pace there: 90.0 + 0.1*2 = 90.2.
    # Actual was 150.0 -> lost = 59.8.
    assert periods[0].time_lost_seconds == pytest.approx(59.8, abs=1e-9)


def test_calculate_safety_car_time_lost_groups_consecutive_laps_into_one_period() -> None:
    stint_laps = [
        _lap(1, 105.0),
        _lap(2, 90.0),
        _lap(3, 90.1),
        _lap(4, 130.0, track_status="6"),
        _lap(5, 120.0, track_status="7"),
        _lap(6, 90.4),
        _lap(7, 90.5),
    ]
    stint = Stint(driver="VER", stint_number=1, compound="SOFT", start_lap=1, end_lap=7)
    stint_pace_models = _build_driver_stint_pace_models(stint_laps, [stint])

    periods = _calculate_safety_car_time_lost(stint_laps, [stint], stint_pace_models)

    assert len(periods) == 1
    assert periods[0].laps == [4, 5]
    assert periods[0].time_lost_seconds > 0


def test_calculate_safety_car_time_lost_splits_non_consecutive_laps_into_separate_periods() -> None:
    stint_laps = [
        _lap(1, 105.0),
        _lap(2, 90.0),
        _lap(3, 130.0, track_status="4"),
        _lap(4, 90.2),
        _lap(5, 90.3),
        _lap(6, 90.4),
        _lap(7, 130.0, track_status="4"),
        _lap(8, 90.6),
    ]
    stint = Stint(driver="VER", stint_number=1, compound="SOFT", start_lap=1, end_lap=8)
    stint_pace_models = _build_driver_stint_pace_models(stint_laps, [stint])

    periods = _calculate_safety_car_time_lost(stint_laps, [stint], stint_pace_models)

    assert [period.laps for period in periods] == [[3], [7]]


def test_calculate_safety_car_time_lost_returns_empty_list_when_no_sc_laps() -> None:
    stint_laps = [_lap(1, 105.0), _lap(2, 90.0), _lap(3, 90.1), _lap(4, 90.2), _lap(5, 90.3)]
    stint = Stint(driver="VER", stint_number=1, compound="SOFT", start_lap=1, end_lap=5)
    stint_pace_models = _build_driver_stint_pace_models(stint_laps, [stint])

    assert _calculate_safety_car_time_lost(stint_laps, [stint], stint_pace_models) == []


def test_calculate_safety_car_time_lost_ignores_stints_without_a_reliable_pace_model() -> None:
    # Only 2 usable laps in the stint -> compute_stint_pace returns None,
    # so any SC-flagged lap here can't be quantified and must be skipped
    # rather than guessed.
    stint_laps = [_lap(1, 105.0), _lap(2, 90.0), _lap(3, 130.0, track_status="4")]
    stint = Stint(driver="VER", stint_number=1, compound="SOFT", start_lap=1, end_lap=3)
    stint_pace_models = _build_driver_stint_pace_models(stint_laps, [stint])

    assert stint_pace_models[0].pace is None
    assert _calculate_safety_car_time_lost(stint_laps, [stint], stint_pace_models) == []


def test_calculate_safety_car_time_lost_ignores_the_stints_opening_lap() -> None:
    # The out lap itself flagged as SC/VSC: excluded from quantification,
    # same as it's excluded from the pace fit (no well-defined position).
    stint_laps = [
        _lap(1, 140.0, track_status="4"),
        _lap(2, 90.0),
        _lap(3, 90.1),
        _lap(4, 90.2),
    ]
    stint = Stint(driver="VER", stint_number=1, compound="SOFT", start_lap=1, end_lap=4)
    stint_pace_models = _build_driver_stint_pace_models(stint_laps, [stint])

    assert _calculate_safety_car_time_lost(stint_laps, [stint], stint_pace_models) == []
