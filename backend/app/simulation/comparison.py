"""Compara várias estratégias candidatas para o mesmo piloto/corrida lado a
lado, reutilizando engine.simulate_strategy para cada uma — este módulo só
orquestra (corre, ordena, calcula deltas), não reimplementa nenhuma lógica
de simulação.

CRITÉRIO DE ORDENAÇÃO (decisão explícita): só estratégias com uma
estimativa COMPLETA (`result.is_complete_estimate` — todos os stints
puderam ser calculados, cobrindo a mesma distância que a estratégia
pedida) competem pelo "melhor tempo" e entram na ordenação por tempo
estimado crescente. Tudo o resto — sem estimativa numérica nenhuma (ex.:
todos os compostos pedidos sem dados suficientes) OU com uma estimativa
INCOMPLETA (algum stint excluído por falta de dados, cobrindo menos
voltas do que o resto) — fica sempre no fim, pela ordem em que foi
submetida. Nunca é descartada silenciosamente, mas também nunca ganha o
rótulo de "melhor" nem um `delta_to_best_seconds`: comparar um tempo que
cobre menos voltas contra o tempo real (ou contra outra estratégia
completa) da corrida toda produzia diferenças fisicamente impossíveis
(ex.: "-1477s", "sobe para P1") — ver engine.simulate_strategy.
"""

from app.schemas.session import Lap, Stint
from app.schemas.simulation import (
    ComparisonResult,
    NamedStrategy,
    SimulationResult,
    StintPlan,
    StrategyComparisonEntry,
)
from app.simulation.engine import simulate_strategy
from app.simulation.fuel_model import DEFAULT_FUEL_MODEL_CONFIG, FuelModelConfig


def compare_strategies(
    driver: str,
    year: int,
    round: int,
    session_type: str,
    driver_laps: list[Lap],
    real_stints: list[Stint],
    pit_stop_cost: float | None,
    named_strategies: list[NamedStrategy],
    fuel_config: FuelModelConfig = DEFAULT_FUEL_MODEL_CONFIG,
) -> ComparisonResult:
    """`pit_stop_cost` is the same value session_repository/pitstop_model
    computes for GET .../simulate — pass the raw (possibly None) average,
    not a pre-defaulted one. None means the session has no recorded pit
    stops to estimate a cost from; each multi-stint strategy still runs
    (with an implicit 0s pit stop cost), but gets its own explanatory
    warning, exactly like POST /api/v1/simulate does for a single
    strategy.
    """
    labelled_results = [
        (
            named.label,
            _simulate_with_pit_stop_warning(
                driver=driver,
                driver_laps=driver_laps,
                real_stints=real_stints,
                strategy=named.strategy,
                pit_stop_cost=pit_stop_cost,
                fuel_config=fuel_config,
            ),
        )
        for named in named_strategies
    ]

    estimable = [pair for pair in labelled_results if pair[1].is_complete_estimate]
    non_estimable = [pair for pair in labelled_results if not pair[1].is_complete_estimate]
    estimable.sort(key=lambda pair: pair[1].estimated_total_time_seconds)

    best_label: str | None = None
    best_time: float | None = None
    if estimable:
        best_label, best_result = estimable[0]
        best_time = best_result.estimated_total_time_seconds

    entries = [
        StrategyComparisonEntry(
            label=label,
            result=result,
            delta_to_best_seconds=(
                result.estimated_total_time_seconds - best_time
                if result.is_complete_estimate
                and result.estimated_total_time_seconds is not None
                and best_time is not None
                else None
            ),
            has_warnings=bool(result.warnings),
        )
        for label, result in estimable + non_estimable
    ]

    return ComparisonResult(
        driver=driver,
        year=year,
        round=round,
        session_type=session_type,
        best_label=best_label,
        best_estimated_total_time_seconds=best_time,
        strategies=entries,
    )


def _simulate_with_pit_stop_warning(
    driver: str,
    driver_laps: list[Lap],
    real_stints: list[Stint],
    strategy: list[StintPlan],
    pit_stop_cost: float | None,
    fuel_config: FuelModelConfig,
) -> SimulationResult:
    """Same pit-stop-cost-missing warning POST /api/v1/simulate attaches
    for a single strategy — factored out here so every strategy in a
    comparison gets it too, per strategy (a 1-stint strategy in the list
    doesn't need it even if another one does)."""
    result = simulate_strategy(
        driver=driver,
        driver_laps=driver_laps,
        real_stints=real_stints,
        strategy=strategy,
        pit_stop_cost=pit_stop_cost or 0.0,
        fuel_config=fuel_config,
    )

    if pit_stop_cost is None and len(strategy) > 1:
        result.warnings.append(
            "Sem paragens registadas nesta sessão para estimar o custo de pit stop; "
            "assumido 0s por paragem (a estimativa ignora o tempo perdido nas paragens)."
        )

    return result
