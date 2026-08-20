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
    # number_of_laps=8 for both (single stint) matches the fixture's real
    # total_laps (8) exactly, so neither strategy trips the lap-count
    # mismatch warning this test isn't about — see
    # engine._warn_if_strategy_lap_count_differs_from_race.
    named_strategies = [
        NamedStrategy(label="all-soft", strategy=[StintPlan(compound="SOFT", number_of_laps=8)]),
        NamedStrategy(label="all-hard", strategy=[StintPlan(compound="HARD", number_of_laps=8)]),
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

    # all-hard: 8 * 80.0 = 640.0 ; all-soft: 8 * 90.0 = 720.0
    assert [entry.label for entry in result.strategies] == ["all-hard", "all-soft"]
    assert result.best_label == "all-hard"
    assert result.best_estimated_total_time_seconds == pytest.approx(640.0)
    assert result.strategies[0].delta_to_best_seconds == pytest.approx(0.0)
    assert result.strategies[1].delta_to_best_seconds == pytest.approx(80.0)
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


def test_compare_strategies_pushes_incomplete_estimate_to_the_tail_never_best() -> None:
    """A strategy with SOME stints excluded (numeric total, but covering
    fewer laps than planned) must NOT compete for "best" and must NOT get
    a delta_to_best_seconds — comparing a partial-distance estimate
    against a full-distance one (real or another strategy) produces
    physically impossible differences (see the STR/Bahrain 2023 bug this
    guards against: a strategy missing a 15-lap stint came out "-1477s
    faster" than the real race). It still appears in the response (never
    silently dropped), just at the tail, like a fully non-estimable one."""
    driver_laps = [_lap(1, 100.0), _lap(2, 90.0), _lap(3, 90.0), _lap(4, 90.0)]
    real_stints = [Stint(driver="VER", stint_number=1, compound="SOFT", start_lap=1, end_lap=4)]
    named_strategies = [
        NamedStrategy(
            label="incomplete",
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

    # "incomplete" has a numeric estimated_total_time_seconds (270.0 for
    # the SOFT stint + 1 pit stop = 290.0) but is_complete_estimate is
    # False, so it's treated like a non-estimable strategy: pushed to the
    # tail, not ranked by time against "clean".
    assert [entry.label for entry in result.strategies] == ["clean", "incomplete"]
    assert result.best_label == "clean"

    incomplete_entry = result.strategies[1]
    assert incomplete_entry.result.estimated_total_time_seconds is not None
    assert incomplete_entry.result.is_complete_estimate is False
    assert incomplete_entry.result.difference_seconds is None
    assert incomplete_entry.has_warnings is True
    assert incomplete_entry.delta_to_best_seconds is None

    clean_entry = result.strategies[0]
    assert clean_entry.result.is_complete_estimate is True
    assert clean_entry.delta_to_best_seconds == pytest.approx(0.0)


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
    # number_of_laps sums to 8 for both strategies (matching the fixture's
    # real total_laps) so this test stays focused on the missing-pit-stop
    # warning, without incidentally also tripping the lap-count mismatch
    # warning — see engine._warn_if_strategy_lap_count_differs_from_race.
    named_strategies = [
        NamedStrategy(label="one-stint", strategy=[StintPlan(compound="SOFT", number_of_laps=8)]),
        NamedStrategy(
            label="two-stint",
            strategy=[
                StintPlan(compound="SOFT", number_of_laps=4),
                StintPlan(compound="HARD", number_of_laps=4),
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
