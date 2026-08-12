from pydantic import BaseModel


class StintPlan(BaseModel):
    """Um stint de uma estratégia candidata (alternativa): qual o
    composto, e durante quantas voltas, antes da próxima paragem (ou do
    fim da corrida)."""

    compound: str
    number_of_laps: int


class SimulationRequest(BaseModel):
    driver: str
    year: int
    round: int
    session_type: str = "R"
    strategy: list[StintPlan]


class SafetyCarPeriod(BaseModel):
    """Um período contínuo de voltas sob Safety Car/VSC na corrida real, e
    o tempo estimado que o piloto perdeu nele (ver
    simulation.safety_car)."""

    laps: list[int]
    time_lost_seconds: float


class SimulationResult(BaseModel):
    driver: str
    estimated_total_time_seconds: float | None = None
    real_total_time_seconds: float | None = None
    difference_seconds: float | None = None
    # Tempo (real, medido) perdido em Safety Car/VSC durante a corrida,
    # somado ao tempo estimado para que a comparação seja justa — ver
    # simulation.safety_car para a lógica completa.
    safety_car_time_added_seconds: float = 0.0
    safety_car_periods: list[SafetyCarPeriod] = []
    warnings: list[str] = []
