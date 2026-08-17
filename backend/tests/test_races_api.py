"""End-to-end integration tests: real FastF1 session + the real database
configured via DATABASE_URL (docker-compose's "db" service must be running,
e.g. `docker compose up -d db`, and migrated with `alembic upgrade head`).

Uses httpx.AsyncClient (not fastapi.testclient.TestClient): the sync
TestClient opens a fresh anyio portal — and therefore a fresh asyncio event
loop — on every single call, which breaks the app's module-level asyncpg
connection pool (asyncpg connections are bound to the event loop they were
created on). AsyncClient runs the whole test on one event loop instead,
which matches how the app actually runs under uvicorn.

For persistence behavior tested against an isolated, mocked DB instead of
this real one, see test_races_api_persistence.py.
"""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.integration
async def test_get_race_session_returns_normalized_data() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/races/2023/1")

    assert response.status_code == 200
    body = response.json()
    assert body["event_name"] == "Bahrain Grand Prix"
    assert body["country"] == "Bahrain"
    assert body["total_laps"] == 57
    assert body["data_complete"] is True
    assert len(body["laps"]) > 0
    assert len(body["stints"]) > 0
    assert len(body["pit_stops"]) > 0
    assert len(body["drivers"]) > 0
    ver = next(d for d in body["drivers"] if d["code"] == "VER")
    assert ver["full_name"] == "Max Verstappen"
    assert ver["team_name"] == "Red Bull Racing"

    assert len(body["results"]) > 0
    ver_result = next(r for r in body["results"] if r["code"] == "VER")
    assert ver_result["position"] == 1
    assert ver_result["total_time_seconds"] == pytest.approx(5636.736)


@pytest.mark.integration
async def test_get_race_session_returns_404_for_invalid_round() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/races/2023/999")

    assert response.status_code == 404
