import pytest

from app.schemas.session import Lap, Stint
from app.schemas.simulation import StintPlan
from app.simulation.engine import simulate_strategy


def _lap(
    lap_number: int,
    lap_time_seconds: float | None,
    compound: str = "SOFT",
    track_status: str | None = None,
) -> Lap:
    return Lap(
        driver="VER",
        lap_number=lap_number,
        lap_time_seconds=lap_time_seconds,
        compound=compound,
        track_status=track_status,
    )


def test_simulate_strategy_single_stint_with_zero_degradation() -> None:
    # 1 out lap (100.0, excluded) + 3 flat laps at 90.0 -> base_pace=90.0,
    # degradation=0.0. A single-stint strategy has zero pit stops.
    driver_laps = [_lap(1, 100.0), _lap(2, 90.0), _lap(3, 90.0), _lap(4, 90.0)]
    real_stints = [Stint(driver="VER", stint_number=1, compound="SOFT", start_lap=1, end_lap=4)]
    strategy = [StintPlan(compound="SOFT", number_of_laps=3)]

    result = simulate_strategy(
        driver="VER",
        driver_laps=driver_laps,
        real_stints=real_stints,
        strategy=strategy,
        pit_stop_cost=20.0,
    )

    # estimated = 3 laps * 90.0 + 0 degradation + 0 pit stops (1 stint) = 270.0
    assert result.estimated_total_time_seconds == pytest.approx(270.0)
    # real = 100.0 + 90.0 + 90.0 + 90.0 = 370.0
    assert result.real_total_time_seconds == pytest.approx(370.0)
    assert result.difference_seconds == pytest.approx(270.0 - 370.0)
    assert result.warnings == []
    # No safety car laps in this fixture -> no compensation, no warning.
    assert result.safety_car_time_added_seconds == 0.0
    assert result.safety_car_periods == []


def test_simulate_strategy_two_stints_adds_one_pit_stop_cost() -> None:
    driver_laps = [
        _lap(1, 100.0, compound="SOFT"),
        _lap(2, 90.0, compound="SOFT"),
        _lap(3, 90.0, compound="SOFT"),
        _lap(4, 90.0, compound="SOFT"),
        _lap(5, 95.0, compound="HARD"),
        _lap(6, 92.0, compound="HARD"),
        _lap(7, 92.0, compound="HARD"),
        _lap(8, 92.0, compound="HARD"),
    ]
    real_stints = [
        Stint(driver="VER", stint_number=1, compound="SOFT", start_lap=1, end_lap=4),
        Stint(driver="VER", stint_number=2, compound="HARD", start_lap=5, end_lap=8),
    ]
    strategy = [
        StintPlan(compound="SOFT", number_of_laps=2),
        StintPlan(compound="HARD", number_of_laps=2),
    ]

    result = simulate_strategy(
        driver="VER",
        driver_laps=driver_laps,
        real_stints=real_stints,
        strategy=strategy,
        pit_stop_cost=25.0,
    )

    # estimated = (2 * 90.0) + (2 * 92.0) + 1 pit stop * 25.0
    #           = 180.0 + 184.0 + 25.0 = 389.0
    assert result.estimated_total_time_seconds == pytest.approx(389.0)
    assert result.warnings == []


def test_simulate_strategy_skips_stint_with_unknown_compound_and_warns() -> None:
    driver_laps = [_lap(1, 100.0), _lap(2, 90.0), _lap(3, 90.0), _lap(4, 90.0)]
    real_stints = [Stint(driver="VER", stint_number=1, compound="SOFT", start_lap=1, end_lap=4)]
    # Driver never ran MEDIUM in the real session.
    strategy = [
        StintPlan(compound="SOFT", number_of_laps=3),
        StintPlan(compound="MEDIUM", number_of_laps=10),
    ]

    result = simulate_strategy(
        driver="VER",
        driver_laps=driver_laps,
        real_stints=real_stints,
        strategy=strategy,
        pit_stop_cost=25.0,
    )

    # Only the SOFT stint contributes; still 1 pit stop cost for the
    # 2-stint strategy, plus a partial-estimate warning.
    assert result.estimated_total_time_seconds == pytest.approx(270.0 + 25.0)
    assert any("MEDIUM" in warning for warning in result.warnings)
    assert any("parcial" in warning.lower() for warning in result.warnings)


def test_simulate_strategy_returns_none_when_no_stint_can_be_estimated() -> None:
    driver_laps = [_lap(1, 100.0), _lap(2, 90.0), _lap(3, 90.0), _lap(4, 90.0)]
    real_stints = [Stint(driver="VER", stint_number=1, compound="SOFT", start_lap=1, end_lap=4)]
    strategy = [StintPlan(compound="HARD", number_of_laps=10)]

    result = simulate_strategy(
        driver="VER",
        driver_laps=driver_laps,
        real_stints=real_stints,
        strategy=strategy,
        pit_stop_cost=25.0,
    )

    assert result.estimated_total_time_seconds is None
    assert result.difference_seconds is None
    assert result.real_total_time_seconds == pytest.approx(370.0)
    assert len(result.warnings) >= 1


def test_simulate_strategy_warns_about_missing_real_lap_times() -> None:
    driver_laps = [_lap(1, 100.0), _lap(2, 90.0), _lap(3, None), _lap(4, 90.0)]
    real_stints = [Stint(driver="VER", stint_number=1, compound="SOFT", start_lap=1, end_lap=4)]
    strategy = [StintPlan(compound="SOFT", number_of_laps=3)]

    result = simulate_strategy(
        driver="VER",
        driver_laps=driver_laps,
        real_stints=real_stints,
        strategy=strategy,
        pit_stop_cost=25.0,
    )

    assert result.real_total_time_seconds == pytest.approx(100.0 + 90.0 + 90.0)
    assert any("registado" in warning for warning in result.warnings)


def test_simulate_strategy_warns_when_no_real_lap_times_at_all() -> None:
    driver_laps = [_lap(1, None), _lap(2, None)]
    real_stints = [Stint(driver="VER", stint_number=1, compound="SOFT", start_lap=1, end_lap=2)]
    strategy = [StintPlan(compound="SOFT", number_of_laps=2)]

    result = simulate_strategy(
        driver="VER",
        driver_laps=driver_laps,
        real_stints=real_stints,
        strategy=strategy,
        pit_stop_cost=25.0,
    )

    assert result.real_total_time_seconds is None
    assert result.difference_seconds is None
    assert any("comparação" in warning for warning in result.warnings)


def test_simulate_strategy_adds_safety_car_time_lost_to_the_estimate() -> None:
    driver_laps = [
        _lap(1, 100.0),
        _lap(2, 90.0),
        _lap(3, 90.1),
        _lap(4, 150.0, track_status="4"),  # Safety Car lap
        _lap(5, 90.3),
        _lap(6, 90.4),
    ]
    real_stints = [Stint(driver="VER", stint_number=1, compound="SOFT", start_lap=1, end_lap=6)]
    strategy = [StintPlan(compound="SOFT", number_of_laps=5)]

    result = simulate_strategy(
        driver="VER",
        driver_laps=driver_laps,
        real_stints=real_stints,
        strategy=strategy,
        pit_stop_cost=25.0,
    )

    # Same fit as test_calculate_safety_car_time_lost_for_a_single_affected_lap
    # in test_safety_car.py: base=90.0, degradation=0.1, lap 4 (position 2)
    # lost 150.0 - (90.0 + 0.1*2) = 59.8s.
    assert result.safety_car_time_added_seconds == pytest.approx(59.8, abs=1e-9)
    assert len(result.safety_car_periods) == 1
    assert result.safety_car_periods[0].laps == [4]

    # estimated = 5 clean-pace laps (90.0 + 0.1*i for i in 0..4) + 0 pit
    # stops (1 stint) + the safety car time added on top.
    clean_pace_sum = sum(90.0 + 0.1 * i for i in range(5))
    assert result.estimated_total_time_seconds == pytest.approx(clean_pace_sum + 59.8, abs=1e-6)

    assert any("Safety Car" in warning for warning in result.warnings)
    assert any("4" in warning for warning in result.warnings)
