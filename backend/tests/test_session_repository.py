import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.session import RaceSession
from app.repositories import session_repository
from app.schemas.session import DriverInfo, Lap, PitStop, SessionData, Stint


def _make_session_data(*, session_type: str = "R", data_complete: bool = True) -> SessionData:
    return SessionData(
        year=2023,
        round=1,
        session_type=session_type,
        event_name="Bahrain Grand Prix",
        country="Bahrain",
        total_laps=57,
        data_complete=data_complete,
        laps=[
            Lap(
                driver="VER",
                lap_number=1,
                lap_time_seconds=99.019,
                compound="SOFT",
                tyre_life=4,
                position=1,
            ),
            Lap(
                driver="VER",
                lap_number=2,
                lap_time_seconds=97.974,
                compound="SOFT",
                tyre_life=5,
                position=1,
            ),
        ],
        pit_stops=[PitStop(driver="VER", lap_number=1, duration_seconds=23.5)],
        stints=[Stint(driver="VER", stint_number=1, compound="SOFT", start_lap=1, end_lap=2)],
        drivers=[
            DriverInfo(
                code="VER", full_name="Max Verstappen", number=1, team_name="Red Bull Racing"
            )
        ],
    )


async def test_get_session_returns_none_when_not_found(db_session: AsyncSession) -> None:
    result = await session_repository.get_session(db_session, year=2023, round=1, session_type="R")

    assert result is None


async def test_save_then_get_session_round_trips(db_session: AsyncSession) -> None:
    await session_repository.save_session(db_session, _make_session_data())

    result = await session_repository.get_session(db_session, year=2023, round=1, session_type="R")

    assert result is not None
    assert result.year == 2023
    assert result.round == 1
    assert result.session_type == "R"
    assert result.event_name == "Bahrain Grand Prix"
    assert result.country == "Bahrain"
    assert result.total_laps == 57
    assert result.data_complete is True

    assert len(result.drivers) == 1
    assert result.drivers[0].code == "VER"
    assert result.drivers[0].full_name == "Max Verstappen"
    assert result.drivers[0].number == 1
    assert result.drivers[0].team_name == "Red Bull Racing"

    assert len(result.laps) == 2
    assert result.laps[0].driver == "VER"
    assert result.laps[0].lap_time_seconds == pytest.approx(99.019)

    assert len(result.pit_stops) == 1
    assert result.pit_stops[0].duration_seconds == pytest.approx(23.5)

    assert len(result.stints) == 1
    assert result.stints[0].compound == "SOFT"
    assert result.stints[0].start_lap == 1
    assert result.stints[0].end_lap == 2


async def test_save_session_is_idempotent_and_replaces_children(db_session: AsyncSession) -> None:
    """Saving the same (year, round, session_type) twice must update the
    existing row, not create a duplicate — and children from the first save
    must not linger alongside children from the second."""
    await session_repository.save_session(db_session, _make_session_data())

    updated = _make_session_data(data_complete=False)
    updated.laps = updated.laps[:1]
    updated.drivers = []
    await session_repository.save_session(db_session, updated)

    result = await session_repository.get_session(db_session, year=2023, round=1, session_type="R")
    assert result is not None
    assert result.data_complete is False
    assert len(result.laps) == 1
    assert result.drivers == []

    session_count = await db_session.scalar(select(func.count()).select_from(RaceSession))
    assert session_count == 1


async def test_save_session_keeps_different_session_types_separate(
    db_session: AsyncSession,
) -> None:
    """Same year/round but a different session_type (e.g. race vs.
    qualifying) is a different session, not an update of the same row."""
    await session_repository.save_session(db_session, _make_session_data(session_type="R"))
    await session_repository.save_session(db_session, _make_session_data(session_type="Q"))

    session_count = await db_session.scalar(select(func.count()).select_from(RaceSession))
    assert session_count == 2

    race = await session_repository.get_session(db_session, year=2023, round=1, session_type="R")
    quali = await session_repository.get_session(db_session, year=2023, round=1, session_type="Q")
    assert race is not None
    assert quali is not None
    assert race.session_type == "R"
    assert quali.session_type == "Q"
