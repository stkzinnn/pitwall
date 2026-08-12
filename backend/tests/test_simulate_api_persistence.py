"""Unit-style tests for POST /api/v1/simulate against the mocked in-memory
DB (see conftest.py) with fastf1_client.load_session_data mocked out — no
network, no real FastF1 session, no real Postgres. Complements
test_simulate_api.py (integration, real session + real DB) by covering the
cache-miss/ingestion path and the "no pit stop data" warning branch, which
a session that's already cached with real pit stops never exercises.
"""

from unittest.mock import patch

import pytest
from httpx import AsyncClient

from app.data_sources.fastf1_client import SessionNotFoundError
from app.schemas.session import Lap, SessionData, Stint


def _fake_session_data(*, with_pit_stops: bool = True) -> SessionData:
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
    from app.schemas.session import PitStop

    pit_stops = (
        [PitStop(driver="VER", lap_number=4, duration_seconds=23.0)] if with_pit_stops else []
    )

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


async def test_simulate_ingests_and_caches_session_on_cache_miss(client: AsyncClient) -> None:
    """Nothing in the (mocked, empty) DB yet -> the endpoint must fall back
    to FastF1, ingest it, and still return a coherent result."""
    payload = {
        "driver": "VER",
        "year": 2023,
        "round": 1,
        "session_type": "R",
        "strategy": [
            {"compound": "SOFT", "number_of_laps": 3},
            {"compound": "HARD", "number_of_laps": 3},
        ],
    }

    with patch(
        "app.api.v1.simulate.load_session_data", return_value=_fake_session_data()
    ) as mock_load:
        response = await client.post("/api/v1/simulate", json=payload)
        assert response.status_code == 200
        assert mock_load.call_count == 1

    body = response.json()
    assert body["driver"] == "VER"
    # SOFT stint: base 90.0 + 0.1s/lap degradation over 3 laps -> 270.3
    # HARD stint: base 92.0 + 0.1s/lap degradation over 3 laps -> 276.3
    # plus 1 pit stop * 23.0 = 270.3 + 276.3 + 23.0 = 569.6
    assert body["estimated_total_time_seconds"] == pytest.approx(569.6)


async def test_simulate_returns_404_when_session_not_found(client: AsyncClient) -> None:
    payload = {
        "driver": "VER",
        "year": 2023,
        "round": 999,
        "session_type": "R",
        "strategy": [{"compound": "SOFT", "number_of_laps": 10}],
    }

    with patch(
        "app.api.v1.simulate.load_session_data", side_effect=SessionNotFoundError("boom")
    ):
        response = await client.post("/api/v1/simulate", json=payload)

    assert response.status_code == 404


async def test_simulate_returns_404_for_driver_absent_from_session(client: AsyncClient) -> None:
    payload = {
        "driver": "ZZZ",
        "year": 2023,
        "round": 1,
        "session_type": "R",
        "strategy": [{"compound": "SOFT", "number_of_laps": 10}],
    }

    with patch("app.api.v1.simulate.load_session_data", return_value=_fake_session_data()):
        response = await client.post("/api/v1/simulate", json=payload)

    assert response.status_code == 404


async def test_simulate_warns_when_no_pit_stop_data_for_multi_stint_strategy(
    client: AsyncClient,
) -> None:
    payload = {
        "driver": "VER",
        "year": 2023,
        "round": 1,
        "session_type": "R",
        "strategy": [
            {"compound": "SOFT", "number_of_laps": 3},
            {"compound": "HARD", "number_of_laps": 3},
        ],
    }

    with patch(
        "app.api.v1.simulate.load_session_data",
        return_value=_fake_session_data(with_pit_stops=False),
    ):
        response = await client.post("/api/v1/simulate", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert any("pit stop" in warning.lower() for warning in body["warnings"])
