"""Unit-style tests for POST /api/v1/compare against the mocked in-memory
DB (see conftest.py) with fastf1_client.load_session_data mocked out — no
network, no real FastF1 session, no real Postgres. Complements
test_compare_api.py (integration, real session + real DB) by covering the
"only one FastF1 fetch for N strategies" guarantee and the empty-list edge
case, neither of which the integration test can assert deterministically.
"""

from unittest.mock import patch

import pytest
from httpx import AsyncClient

from app.schemas.session import Lap, PitStop, SessionData, Stint


def _fake_session_data() -> SessionData:
    laps = [
        Lap(driver="VER", lap_number=1, lap_time_seconds=105.0, compound="SOFT"),
        Lap(driver="VER", lap_number=2, lap_time_seconds=90.0, compound="SOFT"),
        Lap(driver="VER", lap_number=3, lap_time_seconds=90.1, compound="SOFT"),
        Lap(driver="VER", lap_number=4, lap_time_seconds=90.2, compound="SOFT"),
        Lap(driver="VER", lap_number=5, lap_time_seconds=95.0, compound="HARD"),
        Lap(driver="VER", lap_number=6, lap_time_seconds=92.0, compound="HARD"),
        Lap(driver="VER", lap_number=7, lap_time_seconds=92.1, compound="HARD"),
        Lap(driver="VER", lap_number=8, lap_time_seconds=92.2, compound="HARD"),
    ]
    stints = [
        Stint(driver="VER", stint_number=1, compound="SOFT", start_lap=1, end_lap=4),
        Stint(driver="VER", stint_number=2, compound="HARD", start_lap=5, end_lap=8),
    ]
    pit_stops = [PitStop(driver="VER", lap_number=4, duration_seconds=23.0)]

    return SessionData(
        year=2023,
        round=1,
        session_type="R",
        event_name="Bahrain Grand Prix",
        data_complete=True,
        laps=laps,
        pit_stops=pit_stops,
        stints=stints,
    )


def _payload(strategies: list[dict]) -> dict:
    return {
        "driver": "VER",
        "year": 2023,
        "round": 1,
        "session_type": "R",
        "strategies": strategies,
    }


async def test_compare_fetches_session_data_only_once_for_multiple_strategies(
    client: AsyncClient,
) -> None:
    payload = _payload(
        [
            {"label": "a", "strategy": [{"compound": "SOFT", "number_of_laps": 3}]},
            {"label": "b", "strategy": [{"compound": "HARD", "number_of_laps": 3}]},
            {
                "label": "c",
                "strategy": [
                    {"compound": "SOFT", "number_of_laps": 2},
                    {"compound": "HARD", "number_of_laps": 2},
                ],
            },
        ]
    )

    with patch(
        "app.api.v1.compare.load_session_data", return_value=_fake_session_data()
    ) as mock_load:
        response = await client.post("/api/v1/compare", json=payload)

        assert response.status_code == 200
        # 3 strategies requested, but FastF1 must only be hit once — the
        # loaded SessionData is reused for every simulate_strategy() call.
        assert mock_load.call_count == 1

    body = response.json()
    assert {entry["label"] for entry in body["strategies"]} == {"a", "b", "c"}


async def test_compare_includes_both_valid_and_unreliable_strategies(
    client: AsyncClient,
) -> None:
    payload = _payload(
        [
            # 8 laps matches the fake session's real total_laps (8) exactly
            # (see engine._warn_if_strategy_lap_count_differs_from_race) —
            # picked deliberately so this strategy stays warning-free.
            {"label": "valid", "strategy": [{"compound": "SOFT", "number_of_laps": 8}]},
            {
                "label": "no-data-for-compound",
                "strategy": [{"compound": "INTERMEDIATE", "number_of_laps": 10}],
            },
        ]
    )

    with patch("app.api.v1.compare.load_session_data", return_value=_fake_session_data()):
        response = await client.post("/api/v1/compare", json=payload)

    assert response.status_code == 200
    body = response.json()

    by_label = {entry["label"]: entry for entry in body["strategies"]}
    assert set(by_label) == {"valid", "no-data-for-compound"}

    assert by_label["valid"]["result"]["estimated_total_time_seconds"] is not None
    assert by_label["valid"]["has_warnings"] is False

    unreliable = by_label["no-data-for-compound"]
    assert unreliable["result"]["estimated_total_time_seconds"] is None
    assert unreliable["has_warnings"] is True
    assert any(
        "INTERMEDIATE" in warning for warning in unreliable["result"]["warnings"]
    )
    assert body["best_label"] == "valid"


async def test_compare_returns_422_for_empty_strategy_list(client: AsyncClient) -> None:
    payload = _payload([])

    response = await client.post("/api/v1/compare", json=payload)

    assert response.status_code == 422


async def test_compare_returns_404_for_unknown_driver(client: AsyncClient) -> None:
    payload = _payload([{"label": "a", "strategy": [{"compound": "SOFT", "number_of_laps": 10}]}])
    payload["driver"] = "ZZZ"

    with patch("app.api.v1.compare.load_session_data", return_value=_fake_session_data()):
        response = await client.post("/api/v1/compare", json=payload)

    assert response.status_code == 404


async def test_compare_uses_the_drivers_own_pit_stop_cost_not_the_session_wide_one(
    client: AsyncClient,
) -> None:
    """/compare must use the SAME pit-stop-cost basis as
    test_engine_regression.py (pitstop_model.calculate_driver_pit_stop_cost)
    — VER's own average when he has enough real stops, ignoring the very
    different session-wide average from other drivers' (much slower) stops.
    """
    session_data = _fake_session_data()
    session_data.pit_stops = [
        PitStop(driver="VER", lap_number=4, duration_seconds=20.0),
        PitStop(driver="VER", lap_number=30, duration_seconds=22.0),
        # Other drivers' stops are much slower — if /compare mistakenly used
        # the session-wide average, the 2-stint strategy below would come
        # out with a visibly higher pit-stop cost baked in.
        PitStop(driver="HAM", lap_number=12, duration_seconds=60.0),
        PitStop(driver="PER", lap_number=14, duration_seconds=65.0),
    ]

    payload = _payload(
        [
            {
                "label": "two-stint",
                # 4 + 4 = 8, matching the fixture's real total_laps (8) —
                # no lap-count-mismatch warning muddying the comparison.
                "strategy": [
                    {"compound": "SOFT", "number_of_laps": 4},
                    {"compound": "HARD", "number_of_laps": 4},
                ],
            }
        ]
    )

    with patch("app.api.v1.compare.load_session_data", return_value=session_data):
        response = await client.post("/api/v1/compare", json=payload)

    assert response.status_code == 200
    body = response.json()
    entry = body["strategies"][0]

    # SOFT stint fit: base=90.0, degradation=0.1/lap (laps 90.0/90.1/90.2 in
    # _fake_session_data) -> 4 laps ~ 90.0+90.1+90.2+90.3 = 360.6. HARD
    # stint fit: base=92.0, degradation=0.1/lap -> 4 laps ~ 368.6 (both
    # within a few hundredths of a second of that, from the default fuel
    # correction /compare applies). Plus VER's own average pit stop cost
    # (21.0), NOT the session-wide one (~41.75) — the ~0.5s gap between the
    # two is much bigger than the fuel-correction noise, so this asserts
    # tight enough to catch the endpoint silently reverting to the
    # session-wide average while tolerating that noise.
    assert entry["result"]["estimated_total_time_seconds"] == pytest.approx(
        360.6 + 368.6 + 21.0, abs=0.2
    )
