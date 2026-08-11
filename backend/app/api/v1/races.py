from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.data_sources.fastf1_client import SessionNotFoundError, load_session_data
from app.db.session import get_db
from app.repositories import session_repository
from app.schemas.session import SessionData

router = APIRouter(prefix="/races", tags=["races"])


@router.get("/{year}/{round}", response_model=SessionData)
async def get_race_session(
    year: int,
    round: int,
    session_type: str = Query(
        default="R", description="FastF1 session identifier, e.g. R, Q, FP1"
    ),
    db: AsyncSession = Depends(get_db),
) -> SessionData:
    cached = await session_repository.get_session(
        db, year=year, round=round, session_type=session_type
    )
    if cached is not None:
        return cached

    try:
        session_data = load_session_data(year=year, round=round, session_type=session_type)
    except SessionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    await session_repository.save_session(db, session_data)
    return session_data
