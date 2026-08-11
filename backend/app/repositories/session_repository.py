from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.session import Lap as LapModel
from app.models.session import PitStop as PitStopModel
from app.models.session import RaceSession
from app.models.session import Stint as StintModel
from app.schemas.session import Lap, PitStop, SessionData, Stint

_EAGER_LOAD_CHILDREN = (
    selectinload(RaceSession.laps),
    selectinload(RaceSession.pit_stops),
    selectinload(RaceSession.stints),
)


async def save_session(db: AsyncSession, session_data: SessionData) -> None:
    """Persist a SessionData, keyed by (year, round, session_type).

    Idempotent: if a matching session already exists, its fields and all of
    its laps/pit_stops/stints are replaced with the incoming data rather
    than duplicated. Children are replaced wholesale (not diffed row by
    row) since FastF1 always hands back the full session, not a delta.
    """
    race_session = await _get_race_session(
        db, session_data.year, session_data.round, session_data.session_type
    )

    if race_session is None:
        race_session = RaceSession(
            year=session_data.year,
            round=session_data.round,
            session_type=session_data.session_type,
        )
        db.add(race_session)

    race_session.event_name = session_data.event_name
    race_session.data_complete = session_data.data_complete

    race_session.laps = [
        LapModel(
            driver=lap.driver,
            lap_number=lap.lap_number,
            lap_time_seconds=lap.lap_time_seconds,
            sector_1_seconds=lap.sector_1_seconds,
            sector_2_seconds=lap.sector_2_seconds,
            sector_3_seconds=lap.sector_3_seconds,
            compound=lap.compound,
            tyre_life=lap.tyre_life,
            position=lap.position,
        )
        for lap in session_data.laps
    ]
    race_session.pit_stops = [
        PitStopModel(
            driver=stop.driver, lap_number=stop.lap_number, duration_seconds=stop.duration_seconds
        )
        for stop in session_data.pit_stops
    ]
    race_session.stints = [
        StintModel(
            driver=stint.driver,
            stint_number=stint.stint_number,
            compound=stint.compound,
            start_lap=stint.start_lap,
            end_lap=stint.end_lap,
        )
        for stint in session_data.stints
    ]

    await db.commit()


async def get_session(
    db: AsyncSession, year: int, round: int, session_type: str
) -> SessionData | None:
    """Read a previously-saved session back in the same SessionData shape
    that fastf1_client.load_session_data() returns, so callers don't need
    to know whether the data came from FastF1 or the database."""
    race_session = await _get_race_session(db, year, round, session_type)
    if race_session is None:
        return None

    return SessionData(
        year=race_session.year,
        round=race_session.round,
        session_type=race_session.session_type,
        event_name=race_session.event_name,
        data_complete=race_session.data_complete,
        laps=[
            Lap(
                driver=lap.driver,
                lap_number=lap.lap_number,
                lap_time_seconds=lap.lap_time_seconds,
                sector_1_seconds=lap.sector_1_seconds,
                sector_2_seconds=lap.sector_2_seconds,
                sector_3_seconds=lap.sector_3_seconds,
                compound=lap.compound,
                tyre_life=lap.tyre_life,
                position=lap.position,
            )
            for lap in race_session.laps
        ],
        pit_stops=[
            PitStop(
                driver=stop.driver,
                lap_number=stop.lap_number,
                duration_seconds=stop.duration_seconds,
            )
            for stop in race_session.pit_stops
        ],
        stints=[
            Stint(
                driver=stint.driver,
                stint_number=stint.stint_number,
                compound=stint.compound,
                start_lap=stint.start_lap,
                end_lap=stint.end_lap,
            )
            for stint in race_session.stints
        ],
    )


async def _get_race_session(
    db: AsyncSession, year: int, round: int, session_type: str
) -> RaceSession | None:
    stmt = (
        select(RaceSession)
        .where(
            RaceSession.year == year,
            RaceSession.round == round,
            RaceSession.session_type == session_type,
        )
        .options(*_EAGER_LOAD_CHILDREN)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()
