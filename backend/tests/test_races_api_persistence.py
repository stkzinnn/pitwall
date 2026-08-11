"""Tests the DB-first caching behavior of GET /api/v1/races/{year}/{round}
against an isolated, mocked in-memory database (see conftest.py), with
fastf1_client.load_session_data mocked out — no network, no real FastF1
session, no real Postgres.
"""

from unittest.mock import patch

from httpx import AsyncClient

from app.schemas.session import Lap, PitStop, SessionData, Stint


def _fake_session_data() -> SessionData:
    return SessionData(
        year=2023,
        round=1,
        session_type="R",
        event_name="Bahrain Grand Prix",
        data_complete=True,
        laps=[Lap(driver="VER", lap_number=1, lap_time_seconds=99.019, compound="SOFT")],
        pit_stops=[PitStop(driver="VER", lap_number=1, duration_seconds=23.5)],
        stints=[Stint(driver="VER", stint_number=1, compound="SOFT", start_lap=1, end_lap=1)],
    )


async def test_second_request_is_served_from_db_without_calling_fastf1(client: AsyncClient) -> None:
    with patch(
        "app.api.v1.races.load_session_data", return_value=_fake_session_data()
    ) as mock_load_session_data:
        first_response = await client.get("/api/v1/races/2023/1")
        assert first_response.status_code == 200
        assert mock_load_session_data.call_count == 1

        second_response = await client.get("/api/v1/races/2023/1")
        assert second_response.status_code == 200
        assert mock_load_session_data.call_count == 1

    assert first_response.json() == second_response.json()


async def test_response_matches_data_saved_to_db(client: AsyncClient) -> None:
    with patch("app.api.v1.races.load_session_data", return_value=_fake_session_data()):
        response = await client.get("/api/v1/races/2023/1")

    assert response.status_code == 200
    body = response.json()
    assert body["event_name"] == "Bahrain Grand Prix"
    assert len(body["laps"]) == 1
    assert body["laps"][0]["driver"] == "VER"
    assert len(body["pit_stops"]) == 1
    assert len(body["stints"]) == 1


async def test_404_for_invalid_round_is_not_cached(client: AsyncClient) -> None:
    from app.data_sources.fastf1_client import SessionNotFoundError

    with patch(
        "app.api.v1.races.load_session_data", side_effect=SessionNotFoundError("boom")
    ) as mock_load_session_data:
        response = await client.get("/api/v1/races/2023/999")
        assert response.status_code == 404
        assert mock_load_session_data.call_count == 1

        # A second request for the same (missing) race must hit FastF1
        # again, since a 404 was never saved to the database.
        response = await client.get("/api/v1/races/2023/999")
        assert response.status_code == 404
        assert mock_load_session_data.call_count == 2
