import pytest

from app.schemas.session import Lap, Stint
from app.schemas.simulation import NamedStrategy, StintPlan
from app.simulation.comparison import compare_strategies
from app.simulation.fuel_model import ZERO_FUEL_EFFECT_CONFIG

# Pin a zero-effect fuel config throughout: these tests are about ordering
# and delta math, not fuel — fuel correction has its own tests.


def _lap(lap_number: int, lap_time_seconds: float | None, compound: str = "SOFT") -> Lap:
    return Lap(
        driver="VER", lap_number=lap_number, lap_time_seconds=lap_time_seconds, compound=compound
    )


def test_compare_strategies_orders_by_estimated_time_ascending() -> None:
    driver_laps = [
        _lap(1, 100.0, compound="SOFT"),
        _lap(2, 90.0, compound="SOFT"),
        _lap(3, 90.0, compound="SOFT"),
        _lap(4, 90.0, compound="SOFT"),
        _lap(5, 95.0, compound="HARD"),
        _lap(6, 80.0, compound="HARD"),
        _lap(7, 80.0, compound="HARD"),
        _lap(8, 80.0, compound="HARD"),
    ]
    real_stints = [
        Stint(driver="VER", stint_number=1, compound="SOFT", start_lap=1, end_lap=4),
        Stint(driver="VER", stint_number=2, compound="HARD", start_lap=5, end_lap=8),
    ]
    named_strategies = [
        NamedStrategy(label="all-soft", strategy=[StintPlan(compound="SOFT", number_of_laps=3)]),
        NamedStrategy(label="all-hard", strategy=[StintPlan(compound="HARD", number_of_laps=3)]),
    ]

    result = compare_strategies(
        driver="VER",
        year=2023,
        round=1,
        session_type="R",
        driver_laps=driver_laps,
        real_stints=real_stints,
        pit_stop_cost=20.0,
        named_strategies=named_strategies,
        fuel_config=ZERO_FUEL_EFFECT_CONFIG,
    )

    # all-hard: 3 * 80.0 = 240.0 ; all-soft: 3 * 90.0 = 270.0
    assert [entry.label for entry in result.strategies] == ["all-hard", "all-soft"]
    assert result.best_label == "all-hard"
    assert result.best_estimated_total_time_seconds == pytest.approx(240.0)
    assert result.strategies[0].delta_to_best_seconds == pytest.approx(0.0)
    assert result.strategies[1].delta_to_best_seconds == pytest.approx(30.0)
    assert result.strategies[0].has_warnings is False
    assert result.strategies[1].has_warnings is False


def test_compare_strategies_keeps_non_estimable_strategy_visible_but_sorted_last() -> None:
    driver_laps = [_lap(1, 100.0), _lap(2, 90.0), _lap(3, 90.0), _lap(4, 90.0)]
    real_stints = [Stint(driver="VER", stint_number=1, compound="SOFT", start_lap=1, end_lap=4)]
    named_strategies = [
        NamedStrategy(
            label="unknown-compound", strategy=[StintPlan(compound="HARD", number_of_laps=10)]
        ),
        NamedStrategy(label="ok", strategy=[StintPlan(compound="SOFT", number_of_laps=3)]),
    ]

    result = compare_strategies(
        driver="VER",
        year=2023,
        round=1,
        session_type="R",
        driver_laps=driver_laps,
        real_stints=real_stints,
        pit_stop_cost=20.0,
        named_strategies=named_strategies,
        fuel_config=ZERO_FUEL_EFFECT_CONFIG,
    )

    # "ok" (submitted 2nd) must still sort before "unknown-compound"
    # (submitted 1st): non-estimable strategies always go last.
    assert [entry.label for entry in result.strategies] == ["ok", "unknown-compound"]
    assert result.best_label == "ok"

    unknown_entry = result.strategies[1]
    assert unknown_entry.result.estimated_total_time_seconds is None
    assert unknown_entry.delta_to_best_seconds is None
    assert unknown_entry.has_warnings is True


def test_compare_strategies_marks_partial_estimate_with_warnings_but_still_ranks_by_time() -> None:
    """A strategy with SOME stints excluded (but still a numeric total)
    must stay in the normal time-sorted order, not get pushed to the
    non-estimable tail — it still has a comparable number."""
    driver_laps = [_lap(1, 100.0), _lap(2, 90.0), _lap(3, 90.0), _lap(4, 90.0)]
    real_stints = [Stint(driver="VER", stint_number=1, compound="SOFT", start_lap=1, end_lap=4)]
    named_strategies = [
        NamedStrategy(
            label="partial",
            strategy=[
                StintPlan(compound="SOFT", number_of_laps=3),
                StintPlan(compound="MEDIUM", number_of_laps=50),  # never used -> excluded
            ],
        ),
        NamedStrategy(label="clean", strategy=[StintPlan(compound="SOFT", number_of_laps=3)]),
    ]

    result = compare_strategies(
        driver="VER",
        year=2023,
        round=1,
        session_type="R",
        driver_laps=driver_laps,
        real_stints=real_stints,
        pit_stop_cost=20.0,
        named_strategies=named_strategies,
        fuel_config=ZERO_FUEL_EFFECT_CONFIG,
    )

    # "partial" (270.0 + 1 pit stop = 290.0) is slower than "clean" (270.0),
    # both are numeric, so normal ascending order applies.
    assert [entry.label for entry in result.strategies] == ["clean", "partial"]

    partial_entry = result.strategies[1]
    assert partial_entry.result.estimated_total_time_seconds is not None
    assert partial_entry.has_warnings is True
    assert partial_entry.delta_to_best_seconds == pytest.approx(20.0)


def test_compare_strategies_appends_missing_pit_stop_warning_per_multi_stint_strategy() -> None:
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
    named_strategies = [
        NamedStrategy(label="one-stint", strategy=[StintPlan(compound="SOFT", number_of_laps=3)]),
        NamedStrategy(
            label="two-stint",
            strategy=[
                StintPlan(compound="SOFT", number_of_laps=2),
                StintPlan(compound="HARD", number_of_laps=2),
            ],
        ),
    ]

    result = compare_strategies(
        driver="VER",
        year=2023,
        round=1,
        session_type="R",
        driver_laps=driver_laps,
        real_stints=real_stints,
        pit_stop_cost=None,  # no recorded pit stops this session
        named_strategies=named_strategies,
        fuel_config=ZERO_FUEL_EFFECT_CONFIG,
    )

    by_label = {entry.label: entry for entry in result.strategies}
    assert by_label["one-stint"].result.warnings == []
    assert any("pit stop" in w.lower() for w in by_label["two-stint"].result.warnings)


def test_compare_strategies_returns_none_best_when_nothing_is_estimable() -> None:
    driver_laps = [_lap(1, 100.0), _lap(2, 90.0), _lap(3, 90.0), _lap(4, 90.0)]
    real_stints = [Stint(driver="VER", stint_number=1, compound="SOFT", start_lap=1, end_lap=4)]
    named_strategies = [
        NamedStrategy(label="a", strategy=[StintPlan(compound="HARD", number_of_laps=5)]),
        NamedStrategy(label="b", strategy=[StintPlan(compound="MEDIUM", number_of_laps=5)]),
    ]

    result = compare_strategies(
        driver="VER",
        year=2023,
        round=1,
        session_type="R",
        driver_laps=driver_laps,
        real_stints=real_stints,
        pit_stop_cost=20.0,
        named_strategies=named_strategies,
        fuel_config=ZERO_FUEL_EFFECT_CONFIG,
    )

    assert result.best_label is None
    assert result.best_estimated_total_time_seconds is None
    assert len(result.strategies) == 2
    assert all(entry.delta_to_best_seconds is None for entry in result.strategies)
