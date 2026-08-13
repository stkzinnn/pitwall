import pytest

from app.schemas.session import Lap
from app.simulation.fuel_model import (
    DEFAULT_FUEL_MODEL_CONFIG,
    FuelModelConfig,
    fuel_correction_seconds,
)
from app.simulation.pace_model import compute_stint_pace, positioned_clean_laps


def test_fuel_correction_is_zero_at_the_last_lap_of_the_race() -> None:
    # The last lap IS the reference point (lightest car) -> correction 0.
    assert fuel_correction_seconds(57, 57) == pytest.approx(0.0)


def test_fuel_correction_matches_total_fuel_burned_times_effect() -> None:
    """Difference in correction between lap 1 and lap 57 of a 57-lap race
    must equal exactly (laps apart) * fuel_burn_kg_per_lap *
    fuel_effect_seconds_per_kg — the amount of fuel burned between the two
    points, converted to seconds via the per-kg effect."""
    total_laps = 57
    config = FuelModelConfig(fuel_effect_seconds_per_kg=0.03, fuel_burn_kg_per_lap=1.8)

    lap1_correction = fuel_correction_seconds(1, total_laps, config)
    lap57_correction = fuel_correction_seconds(57, total_laps, config)

    assert lap57_correction == pytest.approx(0.0)

    laps_apart = 57 - 1
    expected_difference = (
        laps_apart * config.fuel_burn_kg_per_lap * config.fuel_effect_seconds_per_kg
    )
    assert lap1_correction - lap57_correction == pytest.approx(expected_difference)
    # With the default-ish config above: 56 * 1.8 * 0.03 = 3.024s.
    assert lap1_correction == pytest.approx(3.024)


def test_fuel_correction_decreases_monotonically_over_the_race() -> None:
    total_laps = 30
    corrections = [fuel_correction_seconds(lap, total_laps) for lap in range(1, total_laps + 1)]

    pairs = zip(corrections, corrections[1:], strict=False)
    assert all(earlier >= later for earlier, later in pairs)
    assert corrections[-1] == pytest.approx(0.0)
    assert corrections[0] > corrections[-1]


def test_fuel_correction_never_goes_negative_past_the_last_lap() -> None:
    # Defensive: a lap number beyond total_laps (shouldn't normally happen)
    # must not produce a negative correction.
    assert fuel_correction_seconds(60, 57) == pytest.approx(0.0)


def test_fuel_correction_is_disabled_by_the_zero_effect_test_config() -> None:
    from app.simulation.fuel_model import ZERO_FUEL_EFFECT_CONFIG

    assert fuel_correction_seconds(1, 57, ZERO_FUEL_EFFECT_CONFIG) == 0.0


def test_fuel_correction_round_trip_reproduces_original_lap_times() -> None:
    """Consistency check between measurement (pace_model.compute_stint_pace,
    which SUBTRACTS the fuel correction before fitting) and simulation
    (engine.simulate_strategy, which ADDS it back) — if both sides use the
    same convention, reconstructing lap times from the fitted pure-tyre
    model plus the fuel correction for each lap's absolute race-lap number
    must reproduce the original (fuel-affected) lap times very closely.

    This builds "raw" lap times the way FastF1 would have recorded them:
    a known pure-tyre trend (out lap + linearly degrading laps) with the
    fuel effect added on top, then fits compute_stint_pace() on that raw
    data and reconstructs it the same way engine.py does.
    """
    total_laps = 20
    fuel_config = DEFAULT_FUEL_MODEL_CONFIG
    stint_start_lap = 10

    # index 0 is the out lap (excluded from the fit either way); the rest
    # follow a known pure-tyre trend of +0.1s/lap from a 90.0s base.
    pure_tyre_times = [95.0, 90.0, 90.1, 90.2, 90.3, 90.4]

    raw_laps = [
        Lap(
            driver="VER",
            lap_number=stint_start_lap + i,
            lap_time_seconds=pure_time
            + fuel_correction_seconds(stint_start_lap + i, total_laps, fuel_config),
            compound="SOFT",
        )
        for i, pure_time in enumerate(pure_tyre_times)
    ]

    pace = compute_stint_pace(raw_laps, total_laps, fuel_config)
    assert pace is not None

    # Reconstruct the way engine.simulate_strategy does: pure tyre pace
    # (base + degradation*position) + fuel correction added back for that
    # same absolute race lap number.
    reconstructed_times = [
        pace.base_pace_seconds
        + pace.degradation_seconds_per_lap * position
        + fuel_correction_seconds(lap.lap_number, total_laps, fuel_config)
        for position, lap in positioned_clean_laps(raw_laps)
    ]
    original_times = [lap.lap_time_seconds for _, lap in positioned_clean_laps(raw_laps)]

    assert sum(reconstructed_times) == pytest.approx(sum(original_times), abs=1e-6)
    for reconstructed, original in zip(reconstructed_times, original_times, strict=True):
        assert reconstructed == pytest.approx(original, abs=1e-6)


def test_fuel_correction_inconsistent_convention_would_introduce_bias() -> None:
    """Negative control for the round-trip test above: if simulation used
    a DIFFERENT total_laps than measurement (an inconsistency the docs in
    fuel_model.py warn against), the reconstructed times would NOT match
    the originals — proving the round-trip test above is actually
    sensitive to convention mismatches, not vacuously true."""
    measurement_total_laps = 20
    simulation_total_laps = 40  # inconsistent on purpose
    fuel_config = DEFAULT_FUEL_MODEL_CONFIG
    stint_start_lap = 10

    pure_tyre_times = [95.0, 90.0, 90.1, 90.2, 90.3, 90.4]
    raw_laps = [
        Lap(
            driver="VER",
            lap_number=stint_start_lap + i,
            lap_time_seconds=pure_time
            + fuel_correction_seconds(stint_start_lap + i, measurement_total_laps, fuel_config),
            compound="SOFT",
        )
        for i, pure_time in enumerate(pure_tyre_times)
    ]

    pace = compute_stint_pace(raw_laps, measurement_total_laps, fuel_config)
    assert pace is not None

    reconstructed_times = [
        pace.base_pace_seconds
        + pace.degradation_seconds_per_lap * position
        + fuel_correction_seconds(lap.lap_number, simulation_total_laps, fuel_config)
        for position, lap in positioned_clean_laps(raw_laps)
    ]
    original_times = [lap.lap_time_seconds for _, lap in positioned_clean_laps(raw_laps)]

    assert sum(reconstructed_times) != pytest.approx(sum(original_times), abs=1e-6)
