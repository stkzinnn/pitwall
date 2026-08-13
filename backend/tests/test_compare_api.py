"""Integration test for POST /api/v1/compare: real FastF1 session (2023
round 1 race, already cached — see test_fastf1_client.py) + the real
database (docker-compose's "db" service must be running and migrated).
"""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.integration
async def test_compare_endpoint_orders_strategies_and_computes_deltas() -> None:
    payload = {
        "driver": "VER",
        "year": 2023,
        "round": 1,
        "session_type": "R",
        "strategies": [
            {
                "label": "replay (2-stop)",
                "strategy": [
                    {"compound": "SOFT", "number_of_laps": 14},
                    {"compound": "SOFT", "number_of_laps": 22},
                    {"compound": "HARD", "number_of_laps": 21},
                ],
            },
            {
                "label": "1-stop",
                "strategy": [
                    {"compound": "SOFT", "number_of_laps": 20},
                    {"compound": "HARD", "number_of_laps": 37},
                ],
            },
            {
                "label": "never-used-compound",
                "strategy": [{"compound": "INTERMEDIATE", "number_of_laps": 10}],
            },
        ],
    }

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/v1/compare", json=payload)

    assert response.status_code == 200
    body = response.json()

    labels = [entry["label"] for entry in body["strategies"]]
    assert set(labels) == {"replay (2-stop)", "1-stop", "never-used-compound"}
    # The strategy with no data at all for its only compound must sort last.
    assert labels[-1] == "never-used-compound"

    estimable_entries = [
        entry
        for entry in body["strategies"]
        if entry["result"]["estimated_total_time_seconds"] is not None
    ]
    assert len(estimable_entries) == 2

    times = [entry["result"]["estimated_total_time_seconds"] for entry in estimable_entries]
    assert times == sorted(times)

    assert body["best_label"] == estimable_entries[0]["label"]
    assert body["best_estimated_total_time_seconds"] == pytest.approx(times[0])
    assert estimable_entries[0]["delta_to_best_seconds"] == pytest.approx(0.0, abs=1e-6)
    for entry in estimable_entries[1:]:
        assert entry["delta_to_best_seconds"] > 0

    never_used_entry = body["strategies"][-1]
    assert never_used_entry["delta_to_best_seconds"] is None
    assert never_used_entry["has_warnings"] is True


@pytest.mark.integration
async def test_compare_endpoint_returns_404_for_unknown_driver() -> None:
    payload = {
        "driver": "ZZZ",
        "year": 2023,
        "round": 1,
        "session_type": "R",
        "strategies": [{"label": "a", "strategy": [{"compound": "SOFT", "number_of_laps": 10}]}],
    }

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/v1/compare", json=payload)

    assert response.status_code == 404
