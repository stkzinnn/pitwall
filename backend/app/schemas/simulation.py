from pydantic import BaseModel, Field


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
    # None sempre que `is_complete_estimate` for False — ver esse campo.
    # Nunca comparamos um tempo estimado que cobre menos voltas do que a
    # estratégia pedida contra o tempo real de TODA a corrida: isso
    # produzia diferenças fisicamente impossíveis (ex.: "-1477s", "subiu
    # para P1") quando um stint era excluído por falta de dados.
    difference_seconds: float | None = None
    # Tempo (real, medido) perdido em Safety Car/VSC durante a corrida,
    # somado ao tempo estimado para que a comparação seja justa — ver
    # simulation.safety_car para a lógica completa.
    safety_car_time_added_seconds: float = 0.0
    safety_car_periods: list[SafetyCarPeriod] = []
    warnings: list[str] = []
    # Quantas voltas a estratégia pedida tinha no total, e quantas dessas
    # voltas foram efetivamente estimadas (i.e. não caíram num stint
    # excluído por falta de dados de ritmo — ver engine.simulate_strategy).
    strategy_total_laps: int = 0
    estimated_laps_covered: int = 0
    # False sempre que estimated_laps_covered != strategy_total_laps (ou
    # não há estimativa nenhuma) — só uma estimativa COMPLETA cobre a
    # mesma distância que o tempo real, por isso só ela pode ser
    # comparada com o tempo real ou usada para estimar posição/"melhor
    # estratégia" (ver comparison.py e o frontend).
    is_complete_estimate: bool = False


class NamedStrategy(BaseModel):
    """Uma estratégia candidata identificada por um rótulo, para aparecer
    com esse nome no resultado de POST /api/v1/compare (ex.: "A", "1 stop
    soft-hard")."""

    label: str
    strategy: list[StintPlan]


class ComparisonRequest(BaseModel):
    driver: str
    year: int
    round: int
    session_type: str = "R"
    # min_length=1: uma lista vazia não tem nada para comparar — a
    # validação do Pydantic já devolve 422 sozinha, sem precisar de
    # tratamento explícito no endpoint (ver api/v1/compare.py).
    strategies: list[NamedStrategy] = Field(min_length=1)


class StrategyComparisonEntry(BaseModel):
    label: str
    result: SimulationResult
    # None quando result.estimated_total_time_seconds também é None (a
    # estratégia não pôde ser estimada de todo) — não há um número válido
    # para calcular a diferença. Ver comparison.py.
    delta_to_best_seconds: float | None = None
    # Espelha `bool(result.warnings)`, exposto como campo próprio para o
    # cliente não ter de inspecionar a lista de warnings só para saber se
    # deve desconfiar do número (ver comparison.py).
    has_warnings: bool = False


class ComparisonResult(BaseModel):
    driver: str
    year: int
    round: int
    session_type: str
    # None só se NENHUMA estratégia da lista pôde ser estimada.
    best_label: str | None = None
    best_estimated_total_time_seconds: float | None = None
    # Ordenada por estimated_total_time_seconds crescente; estratégias sem
    # estimativa numérica ficam sempre no fim, por ordem de submissão — ver
    # comparison.compare_strategies.
    strategies: list[StrategyComparisonEntry] = []
