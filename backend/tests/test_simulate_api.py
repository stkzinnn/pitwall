"""Integration test for POST /api/v1/simulate: real FastF1 session (2023
round 1 race, already cached — see test_fastf1_client.py) + the real
database (docker-compose's "db" service must be running and migrated).

This doesn't assert on the exact simulated time (that depends on real,
ever-present race pace and isn't a stable thing to hardcode) — only that
the endpoint runs end-to-end and returns a well-formed, self-consistent
result.
"""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.integration
async def test_simulate_endpoint_returns_coherent_result() -> None:
    payload = {
        "driver": "VER",
        "year": 2023,
        "round": 1,
        "session_type": "R",
        "strategy": [
            {"compound": "SOFT", "number_of_laps": 15},
            {"compound": "HARD", "number_of_laps": 30},
        ],
    }

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/v1/simulate", json=payload)

    assert response.status_code == 200
    body = response.json()

    assert body["driver"] == "VER"
    assert isinstance(body["warnings"], list)
    assert "real_total_time_seconds" in body
    assert "estimated_total_time_seconds" in body
    assert "difference_seconds" in body

    # The real time comes from VER's actual laps in this race, so it must
    # always be present regardless of which compounds the strategy uses.
    assert body["real_total_time_seconds"] > 0

    if body["estimated_total_time_seconds"] is not None:
        assert body["difference_seconds"] == pytest.approx(
            body["estimated_total_time_seconds"] - body["real_total_time_seconds"]
        )


@pytest.mark.integration
async def test_simulate_endpoint_returns_404_for_unknown_driver() -> None:
    payload = {
        "driver": "ZZZ",
        "year": 2023,
        "round": 1,
        "session_type": "R",
        "strategy": [{"compound": "SOFT", "number_of_laps": 10}],
    }

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/v1/simulate", json=payload)

    assert response.status_code == 404
