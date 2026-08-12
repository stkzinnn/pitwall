from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.data_sources.fastf1_client import SessionNotFoundError, load_session_data
from app.db.session import get_db
from app.repositories import session_repository
from app.schemas.simulation import SimulationRequest, SimulationResult
from app.simulation.engine import simulate_strategy
from app.simulation.pitstop_model import calculate_average_pit_stop_cost

router = APIRouter(prefix="/simulate", tags=["simulation"])


@router.post("", response_model=SimulationResult)
async def simulate(
    request: SimulationRequest, db: AsyncSession = Depends(get_db)
) -> SimulationResult:
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

    result = simulate_strategy(
        driver=request.driver,
        driver_laps=driver_laps,
        real_stints=driver_stints,
        strategy=request.strategy,
        pit_stop_cost=pit_stop_cost or 0.0,
    )

    if pit_stop_cost is None and len(request.strategy) > 1:
        result.warnings.append(
            "Sem paragens registadas nesta sessão para estimar o custo de pit stop; "
            "assumido 0s por paragem (a estimativa ignora o tempo perdido nas paragens)."
        )

    return result
