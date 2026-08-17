"""Regression check: replay a driver's own real strategy (same compounds,
same stint lengths as what actually happened) through simulate_strategy()
and compare against their real total time.

If the engine's pace model were faithful, this "replay" should land close
to the real total — it's not extrapolating to an unseen number of laps,
just re-deriving the same stints from the same underlying data. A large
gap here means the bug is in the pace model itself, not merely in
extrapolating an alternative strategy to more/fewer laps than were really
run.

HISTORY:
- Originally xfail. VER's 2023 Bahrain race hit a Virtual Safety Car
  during laps 41-42 of his HARD stint (FastF1 TrackStatus: lap 41 "126",
  lap 42 "671" — VSC deployed/ending). The original compute_stint_pace()
  only excluded the stint's opening lap, so those two inflated lap times
  corrupted the HARD stint's degradation regression (~-0.29 s/lap, i.e.
  "getting faster with tyre age" — not physically real), and a replay of
  VER's exact real strategy landed ~90s away from his real total.
- After excluding statistical outliers from the fit + using the
  regression's intercept as base pace + no longer merging same-compound
  stints (see pace_model.py), the replay closed to ~-23s.
- That remaining ~23s was the real time VER lost to the VSC — correctly
  excluded from the "clean pace" fit, but still part of his real total,
  and the engine had no way to add it back. Once simulate_strategy()
  started adding the measured Safety Car/VSC time lost back onto the
  estimate (see safety_car.py) — because that time would have been lost
  under ANY strategy, it's not something changing tyre strategy could
  have avoided — the replay closed to ~+7.4s.
- Lap times were still measured with the "car gets lighter as it burns
  fuel" effect mixed into the tyre degradation regression, biasing it low
  (e.g. VER's HARD stint fit at ~-0.06 s/lap — tyres "getting faster" with
  age, still not physically real, just less wrong than before). Now that
  pace_model.compute_stint_pace() corrects for fuel load before fitting,
  and engine.py adds the fuel effect back per simulated lap (see
  fuel_model.py), the replay closes further to ~+4.3s.
- This test used to compute pit_stop_cost from VER's OWN pit stops
  (calculate_average_pit_stop_cost(driver_pit_stops)), while the
  /simulate and /compare endpoints computed it from EVERY driver's pit
  stops in the session — the test validated a different number than what
  the API actually returned. Both now go through
  pitstop_model.calculate_driver_pit_stop_cost (own average, with a
  session-wide fallback for a small sample — see that function's
  docstring), so this test's tolerance reflects what users actually see.
  For VER here (2 real pit stops, above the fallback threshold), this is
  numerically identical to the old driver-only average, so the ~+4.3s
  figure above is unchanged.
"""

import pytest

from app.data_sources.fastf1_client import load_session_data
from app.schemas.simulation import StintPlan
from app.simulation.engine import simulate_strategy
from app.simulation.pitstop_model import calculate_driver_pit_stop_cost

# Confirmed empirically at ~+4.3s (see HISTORY above) after the fuel
# correction was added, down from ~+7.4s. 8s leaves a small margin while
# still catching a regression back toward the old ~23s (or ~90s / ~340s)
# gap.
MAX_PLAUSIBLE_REPLAY_DIFFERENCE_SECONDS = 8.0


@pytest.mark.integration
def test_replaying_drivers_real_strategy_is_close_to_their_real_time() -> None:
    session_data = load_session_data(year=2023, round=1, session_type="R")

    driver_laps = [lap for lap in session_data.laps if lap.driver == "VER"]
    driver_stints = sorted(
        (stint for stint in session_data.stints if stint.driver == "VER"),
        key=lambda stint: stint.stint_number,
    )
    driver_pit_stops = [stop for stop in session_data.pit_stops if stop.driver == "VER"]

    # The exact strategy VER actually drove: same compounds, same number of
    # laps per stint as the real stints — not an alternative strategy.
    strategy = [
        StintPlan(compound=stint.compound, number_of_laps=stint.end_lap - stint.start_lap + 1)
        for stint in driver_stints
    ]
    pit_stop_cost = calculate_driver_pit_stop_cost(driver_pit_stops, session_data.pit_stops)

    result = simulate_strategy(
        driver="VER",
        driver_laps=driver_laps,
        real_stints=driver_stints,
        strategy=strategy,
        pit_stop_cost=pit_stop_cost or 0.0,
    )

    assert result.estimated_total_time_seconds is not None
    assert result.real_total_time_seconds is not None
    # Confirms the safety car compensation actually engaged for this race
    # (Bahrain 2023 had a VSC on VER's laps 41-42) rather than the
    # tolerance below passing vacuously with zero compensation applied.
    assert result.safety_car_time_added_seconds > 0
    assert abs(result.difference_seconds) < MAX_PLAUSIBLE_REPLAY_DIFFERENCE_SECONDS
