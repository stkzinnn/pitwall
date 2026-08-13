import pytest

from app.schemas.session import Lap, Stint
from app.simulation.fuel_model import ZERO_FUEL_EFFECT_CONFIG
from app.simulation.pace_model import (
    _linear_regression,
    average_pace_model,
    build_driver_stint_pace_models,
    compute_stint_pace,
)

# These tests are about the degradation/regression/outlier-filtering math
# itself, not about fuel — pass a zero-effect fuel config throughout so the
# hand-computed expected values in this file aren't also entangled with
# fuel correction (which is tested on its own in test_fuel_model.py).
# total_laps only matters when the fuel effect is non-zero, so any value
# works here.
_TOTAL_LAPS = 100


def _lap(lap_number: int, lap_time_seconds: float | None, compound: str = "SOFT") -> Lap:
    return Lap(
        driver="VER", lap_number=lap_number, lap_time_seconds=lap_time_seconds, compound=compound
    )


def _compute_stint_pace(stint_laps: list[Lap]):
    return compute_stint_pace(stint_laps, _TOTAL_LAPS, ZERO_FUEL_EFFECT_CONFIG)


def _build_driver_stint_pace_models(laps: list[Lap], stints: list[Stint]):
    return build_driver_stint_pace_models(laps, stints, _TOTAL_LAPS, ZERO_FUEL_EFFECT_CONFIG)


def test_compute_stint_pace_fits_known_linear_degradation() -> None:
    # Out lap (excluded) + 4 clean laps rising by exactly 0.1s/lap.
    stint_laps = [
        _lap(1, 105.0),
        _lap(2, 90.0),
        _lap(3, 90.1),
        _lap(4, 90.2),
        _lap(5, 90.3),
    ]

    pace = _compute_stint_pace(stint_laps)

    assert pace is not None
    assert pace.base_pace_seconds == pytest.approx(90.0)
    assert pace.degradation_seconds_per_lap == pytest.approx(0.1, abs=1e-9)
    assert pace.laps_used == 4
    assert pace.first_clean_lap_seconds == pytest.approx(90.0)


def test_compute_stint_pace_returns_none_for_too_few_valid_laps() -> None:
    # Out lap + only 2 clean laps: below MIN_VALID_LAPS_FOR_DEGRADATION (3).
    stint_laps = [_lap(1, 105.0), _lap(2, 90.0), _lap(3, 90.1)]

    assert _compute_stint_pace(stint_laps) is None


def test_compute_stint_pace_ignores_laps_with_missing_lap_time() -> None:
    # Out lap + 4 laps but one is missing a time (e.g. a safety car lap);
    # only 3 remain valid, exactly at the minimum.
    stint_laps = [
        _lap(1, 105.0),
        _lap(2, 90.0),
        _lap(3, None),
        _lap(4, 90.2),
        _lap(5, 90.4),
    ]

    pace = _compute_stint_pace(stint_laps)

    assert pace is not None
    assert pace.laps_used == 3


def test_compute_stint_pace_excludes_mid_stint_outliers_like_a_vsc() -> None:
    """Two artificially slow laps in the middle of the stint (simulating a
    Virtual Safety Car / Safety Car period) must be excluded from the fit,
    leaving a plausible, physically sensible (positive, ~0.1s/lap) result
    instead of a corrupted one."""
    stint_laps = [
        _lap(1, 105.0),  # out lap, always excluded
        _lap(2, 90.0),
        _lap(3, 90.1),
        _lap(4, 90.2),
        _lap(5, 150.0),  # VSC-affected lap
        _lap(6, 140.0),  # VSC-affected lap
        _lap(7, 90.5),
        _lap(8, 90.6),
        _lap(9, 90.7),
    ]

    pace = _compute_stint_pace(stint_laps)

    assert pace is not None
    # 2 outliers excluded from the 8 clean laps -> 6 laps used.
    assert pace.laps_used == 6
    # Degradation must come out positive and close to the true underlying
    # trend (0.1s/lap), not the wildly wrong/negative value that including
    # the two VSC laps would produce.
    assert pace.degradation_seconds_per_lap == pytest.approx(0.1, abs=1e-9)
    assert pace.base_pace_seconds == pytest.approx(90.0, abs=1e-9)


def test_compute_stint_pace_returns_none_if_outlier_filtering_leaves_too_few_laps() -> None:
    # Out lap + exactly 3 clean laps (the minimum), 1 of which is a severe
    # outlier -> filtering it out leaves only 2, below
    # MIN_VALID_LAPS_FOR_DEGRADATION.
    stint_laps = [
        _lap(1, 105.0),
        _lap(2, 90.0),
        _lap(3, 90.1),
        _lap(4, 500.0),
    ]

    assert _compute_stint_pace(stint_laps) is None


def test_compute_stint_pace_reproduces_the_mean_of_its_own_fitted_laps() -> None:
    """For a stint with no outliers, summing base_pace + degradation*i over
    the exact laps used to fit the model must reproduce (very closely) the
    sum of the real lap times used — this is the defining property of an
    ordinary-least-squares fit that includes an intercept term. It also
    demonstrates that base_pace is the fitted intercept, not simply the
    raw first lap's time (91.0 here, clearly different from the fitted
    base_pace below)."""
    stint_laps = [
        _lap(1, 999.0),  # out lap, excluded
        _lap(2, 91.0),
        _lap(3, 90.3),
        _lap(4, 89.9),
        _lap(5, 90.4),
    ]
    real_sum = 91.0 + 90.3 + 89.9 + 90.4

    pace = _compute_stint_pace(stint_laps)

    assert pace is not None
    assert pace.laps_used == 4
    assert pace.first_clean_lap_seconds == pytest.approx(91.0)
    # The fitted intercept must differ from the raw first lap: proof that
    # base_pace_seconds is not just lap_times[0].
    assert pace.base_pace_seconds != pytest.approx(91.0, abs=1e-6)

    predicted_sum = sum(
        pace.base_pace_seconds + pace.degradation_seconds_per_lap * i for i in range(4)
    )
    assert predicted_sum == pytest.approx(real_sum, abs=1e-9)


def test_build_driver_stint_pace_models_keeps_repeated_compounds_separate() -> None:
    """Two stints on the same compound (SOFT, here) must show up as two
    distinct entries with their own independently-fitted PaceModels, not
    merged or overwritten — unlike the old (buggy) 'most recent wins'
    behavior."""
    laps = [
        _lap(1, 105.0, compound="SOFT"),
        _lap(2, 100.0, compound="SOFT"),
        _lap(3, 100.1, compound="SOFT"),
        _lap(4, 100.2, compound="SOFT"),
        _lap(5, 95.0, compound="HARD"),
        _lap(6, 92.0, compound="HARD"),
        _lap(7, 92.1, compound="HARD"),
        _lap(8, 92.2, compound="HARD"),
        _lap(9, 80.0, compound="SOFT"),
        _lap(10, 80.1, compound="SOFT"),
        _lap(11, 80.2, compound="SOFT"),
        _lap(12, 80.3, compound="SOFT"),
    ]
    stints = [
        Stint(driver="VER", stint_number=1, compound="SOFT", start_lap=1, end_lap=4),
        Stint(driver="VER", stint_number=2, compound="HARD", start_lap=5, end_lap=8),
        Stint(driver="VER", stint_number=3, compound="SOFT", start_lap=9, end_lap=12),
    ]

    stint_pace_models = _build_driver_stint_pace_models(laps, stints)

    assert [(m.stint_number, m.compound) for m in stint_pace_models] == [
        (1, "SOFT"),
        (2, "HARD"),
        (3, "SOFT"),
    ]
    first_soft, hard, second_soft = (
        stint_pace_models[0].pace,
        stint_pace_models[1].pace,
        stint_pace_models[2].pace,
    )
    assert first_soft is not None
    assert second_soft is not None
    assert hard is not None
    # The two SOFT stints have visibly different pace (~100 vs ~80) and
    # must NOT have been fused into one.
    assert first_soft.base_pace_seconds == pytest.approx(100.1, abs=0.2)
    assert second_soft.base_pace_seconds == pytest.approx(80.1, abs=0.2)


def test_build_driver_stint_pace_models_skips_stints_with_no_compound_recorded() -> None:
    laps = [
        _lap(1, 105.0, compound="SOFT"),
        _lap(2, 90.0, compound="SOFT"),
        _lap(3, 90.1, compound="SOFT"),
        _lap(4, 90.2, compound="SOFT"),
    ]
    stints = [
        Stint(driver="VER", stint_number=1, compound=None, start_lap=1, end_lap=4),
    ]

    assert _build_driver_stint_pace_models(laps, stints) == []


def test_average_pace_model_averages_across_valid_models_only() -> None:
    laps = [
        _lap(1, 105.0, compound="SOFT"),
        _lap(2, 100.0, compound="SOFT"),
        _lap(3, 100.0, compound="SOFT"),
        _lap(4, 100.0, compound="SOFT"),
        _lap(5, 95.0, compound="SOFT"),
        _lap(6, 80.0, compound="SOFT"),
        _lap(7, 80.0, compound="SOFT"),
        _lap(8, 80.0, compound="SOFT"),
    ]
    stints = [
        Stint(driver="VER", stint_number=1, compound="SOFT", start_lap=1, end_lap=4),
        Stint(driver="VER", stint_number=2, compound="SOFT", start_lap=5, end_lap=8),
    ]
    stint_pace_models = _build_driver_stint_pace_models(laps, stints)

    average = average_pace_model([m.pace for m in stint_pace_models])

    assert average is not None
    # (100.0 + 80.0) / 2 = 90.0
    assert average.base_pace_seconds == pytest.approx(90.0)
    assert average.degradation_seconds_per_lap == pytest.approx(0.0)


def test_average_pace_model_returns_none_when_no_valid_models() -> None:
    assert average_pace_model([None, None]) is None
    assert average_pace_model([]) is None


def test_linear_regression_is_zero_slope_at_mean_for_a_single_x_value() -> None:
    # A degenerate fit (no spread in x) can't have a defined slope; the
    # function documents (0.0, y_mean) as the safe fallback instead of
    # dividing by zero.
    slope, intercept = _linear_regression([5.0], [90.0])
    assert slope == 0.0
    assert intercept == 90.0
