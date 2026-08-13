"""Unit-style tests for POST /api/v1/compare against the mocked in-memory
DB (see conftest.py) with fastf1_client.load_session_data mocked out — no
network, no real FastF1 session, no real Postgres. Complements
test_compare_api.py (integration, real session + real DB) by covering the
"only one FastF1 fetch for N strategies" guarantee and the empty-list edge
case, neither of which the integration test can assert deterministically.
"""

from unittest.mock import patch

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
            {"label": "valid", "strategy": [{"compound": "SOFT", "number_of_laps": 3}]},
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
