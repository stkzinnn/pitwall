from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.data_sources.fastf1_client import SessionNotFoundError, load_session_data
from app.db.session import get_db
from app.repositories import session_repository
from app.schemas.simulation import ComparisonRequest, ComparisonResult
from app.simulation.comparison import compare_strategies
from app.simulation.pitstop_model import calculate_average_pit_stop_cost

router = APIRouter(prefix="/compare", tags=["simulation"])


@router.post("", response_model=ComparisonResult)
async def compare(
    request: ComparisonRequest, db: AsyncSession = Depends(get_db)
) -> ComparisonResult:
    # Session data (laps/stints/pit stops) is fetched ONCE here, then
    # reused for every strategy in the request — compare_strategies never
    # touches the database or FastF1 itself, it just calls
    # engine.simulate_strategy per strategy on this already-loaded data.
    session_data = await session_repository.get_session(
        db, year=request.year, round=request.round, session_type=request.session_type
    )

    if session_data is None:
        try:
            session_data = load_session_data(
                year=request.year, round=request.round, session_type=request.session_type
            )
        except SessionNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        await session_repository.save_session(db, session_data)

    driver_laps = [lap for lap in session_data.laps if lap.driver == request.driver]
    if not driver_laps:
        raise HTTPException(
            status_code=404,
            detail=f"Sem dados de voltas para o piloto {request.driver!r} nesta sessão.",
        )
    driver_stints = [stint for stint in session_data.stints if stint.driver == request.driver]

    pit_stop_cost = calculate_average_pit_stop_cost(session_data.pit_stops)

    return compare_strategies(
        driver=request.driver,
        year=request.year,
        round=request.round,
        session_type=request.session_type,
        driver_laps=driver_laps,
        real_stints=driver_stints,
        pit_stop_cost=pit_stop_cost,
        named_strategies=request.strategies,
    )
