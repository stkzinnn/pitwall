import pytest

from app.schemas.session import Lap, Stint
from app.schemas.simulation import StintPlan
from app.simulation.engine import simulate_strategy as _simulate_strategy
from app.simulation.fuel_model import ZERO_FUEL_EFFECT_CONFIG

# These tests are about pace/pit-stop/safety-car logic, not fuel — pin a
# zero-effect fuel config throughout so the hand-computed expected values
# in this file aren't also entangled with fuel correction (which is tested
# on its own in test_fuel_model.py, plus the measurement<->simulation
# consistency test there).


def simulate_strategy(**kwargs):
    kwargs.setdefault("fuel_config", ZERO_FUEL_EFFECT_CONFIG)
    return _simulate_strategy(**kwargs)


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
    # 1 out lap (100.0, excluded from the pace fit) + 3 flat laps at 90.0 ->
    # base_pace=90.0, degradation=0.0. number_of_laps=4 matches the real
    # stint's full physical length (end_lap - start_lap + 1 = 4), the same
    # convention the frontend and the /compare-style callers use — so this
    # strategy covers exactly the 4-lap "race" and triggers no lap-count
    # warning. A single-stint strategy has zero pit stops.
    driver_laps = [_lap(1, 100.0), _lap(2, 90.0), _lap(3, 90.0), _lap(4, 90.0)]
    real_stints = [Stint(driver="VER", stint_number=1, compound="SOFT", start_lap=1, end_lap=4)]
    strategy = [StintPlan(compound="SOFT", number_of_laps=4)]

    result = simulate_strategy(
        driver="VER",
        driver_laps=driver_laps,
        real_stints=real_stints,
        strategy=strategy,
        pit_stop_cost=20.0,
    )

    # estimated = 4 laps * 90.0 + 0 degradation + 0 pit stops (1 stint) = 360.0
    assert result.estimated_total_time_seconds == pytest.approx(360.0)
    # real = 100.0 + 90.0 + 90.0 + 90.0 = 370.0
    assert result.real_total_time_seconds == pytest.approx(370.0)
    assert result.difference_seconds == pytest.approx(360.0 - 370.0)
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
    # 4 + 4 = 8, matching the fixture's real total_laps (8) exactly (see
    # note in the single-stint test above about the number_of_laps
    # convention) -> no lap-count warning here either.
    strategy = [
        StintPlan(compound="SOFT", number_of_laps=4),
        StintPlan(compound="HARD", number_of_laps=4),
    ]

    result = simulate_strategy(
        driver="VER",
        driver_laps=driver_laps,
        real_stints=real_stints,
        strategy=strategy,
        pit_stop_cost=25.0,
    )

    # estimated = (4 * 90.0) + (4 * 92.0) + 1 pit stop * 25.0
    #           = 360.0 + 368.0 + 25.0 = 753.0
    assert result.estimated_total_time_seconds == pytest.approx(753.0)
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
    # 2-stint strategy, plus an incomplete-estimate warning. The estimate
    # is numeric but covers fewer laps (3) than the strategy planned (13)
    # -> not comparable to the real total, no difference_seconds.
    assert result.estimated_total_time_seconds == pytest.approx(270.0 + 25.0)
    assert any("MEDIUM" in warning for warning in result.warnings)
    assert any("incompleta" in warning.lower() for warning in result.warnings)
    assert result.strategy_total_laps == 13
    assert result.estimated_laps_covered == 3
    assert result.is_complete_estimate is False
    assert result.difference_seconds is None


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


def test_simulate_strategy_replay_is_consistent_with_real_fuel_effect_enabled() -> None:
    """End-to-end version of the measurement<->simulation consistency
    check in test_fuel_model.py, but through the public simulate_strategy
    API with the REAL (non-zero) default fuel config: replaying a stint
    with a known pure-tyre trend, with the fuel effect baked into the raw
    lap times (as FastF1 would have recorded them), must reproduce the
    original total of the SAME laps closely — proving measurement
    (subtract fuel) and simulation (add fuel back) use the same convention
    end-to-end, including engine.py's running race_lap_counter, not just
    at the pace_model level.

    Compared against the sum of the 5 "clean" laps only (excluding the
    out lap, lap 1) — not against real_total_time_seconds, which sums all
    6 laps including the out lap. simulate_strategy's estimate never
    models an out-lap penalty for a StintPlan (a separate, pre-existing
    modeling gap, out of scope here), so comparing against the full real
    total would conflate that with what this test actually targets: fuel
    convention consistency.
    """
    from app.simulation.fuel_model import DEFAULT_FUEL_MODEL_CONFIG, fuel_correction_seconds

    pure_tyre_times = [95.0, 90.0, 90.1, 90.2, 90.3, 90.4]  # index 0 = out lap
    # engine.simulate_strategy derives total_laps from max(driver_laps'
    # lap_number) — must match that here (6 laps, this synthetic stint IS
    # the whole "race") for the fuel convention to be consistent.
    total_laps = len(pure_tyre_times)
    driver_laps = [
        _lap(
            lap_number=i + 1,
            lap_time_seconds=pure_time
            + fuel_correction_seconds(i + 1, total_laps, DEFAULT_FUEL_MODEL_CONFIG),
        )
        for i, pure_time in enumerate(pure_tyre_times)
    ]
    real_stints = [Stint(driver="VER", stint_number=1, compound="SOFT", start_lap=1, end_lap=6)]
    strategy = [StintPlan(compound="SOFT", number_of_laps=5)]

    result = _simulate_strategy(
        driver="VER",
        driver_laps=driver_laps,
        real_stints=real_stints,
        strategy=strategy,
        pit_stop_cost=25.0,
        fuel_config=DEFAULT_FUEL_MODEL_CONFIG,
    )

    original_clean_laps_sum = sum(lap.lap_time_seconds for lap in driver_laps[1:])
    assert result.estimated_total_time_seconds is not None
    assert result.estimated_total_time_seconds == pytest.approx(original_clean_laps_sum, abs=1e-6)


def test_simulate_strategy_warns_when_lap_count_exceeds_the_race_distance() -> None:
    driver_laps = [_lap(1, 100.0), _lap(2, 90.0), _lap(3, 90.0), _lap(4, 90.0)]
    real_stints = [Stint(driver="VER", stint_number=1, compound="SOFT", start_lap=1, end_lap=4)]
    # The race only ran 4 laps; this strategy plans 6 -> 2 laps too many.
    strategy = [StintPlan(compound="SOFT", number_of_laps=6)]

    result = simulate_strategy(
        driver="VER",
        driver_laps=driver_laps,
        real_stints=real_stints,
        strategy=strategy,
        pit_stop_cost=20.0,
    )

    assert any("6" in warning and "4" in warning for warning in result.warnings)
    assert any("+2" in warning for warning in result.warnings)


def test_simulate_strategy_warns_when_lap_count_falls_short_of_the_race_distance() -> None:
    driver_laps = [_lap(1, 100.0), _lap(2, 90.0), _lap(3, 90.0), _lap(4, 90.0)]
    real_stints = [Stint(driver="VER", stint_number=1, compound="SOFT", start_lap=1, end_lap=4)]
    # The race ran 4 laps; this strategy only plans 2 -> 2 laps short.
    strategy = [StintPlan(compound="SOFT", number_of_laps=2)]

    result = simulate_strategy(
        driver="VER",
        driver_laps=driver_laps,
        real_stints=real_stints,
        strategy=strategy,
        pit_stop_cost=20.0,
    )

    assert any("2" in warning and "4" in warning for warning in result.warnings)
    assert any("-2" in warning for warning in result.warnings)


def test_simulate_strategy_no_lap_count_warning_when_strategy_matches_race_distance() -> None:
    driver_laps = [_lap(1, 100.0), _lap(2, 90.0), _lap(3, 90.0), _lap(4, 90.0)]
    real_stints = [Stint(driver="VER", stint_number=1, compound="SOFT", start_lap=1, end_lap=4)]
    strategy = [StintPlan(compound="SOFT", number_of_laps=4)]

    result = simulate_strategy(
        driver="VER",
        driver_laps=driver_laps,
        real_stints=real_stints,
        strategy=strategy,
        pit_stop_cost=20.0,
    )

    assert result.warnings == []
