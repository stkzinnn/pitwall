from app.schemas.session import Lap, Stint
from app.schemas.simulation import SafetyCarPeriod, SimulationResult, StintPlan
from app.simulation.pace_model import (
    PaceModel,
    StintPaceModel,
    average_pace_model,
    build_driver_stint_pace_models,
)
from app.simulation.safety_car import calculate_safety_car_time_lost


def simulate_strategy(
    driver: str,
    driver_laps: list[Lap],
    real_stints: list[Stint],
    strategy: list[StintPlan],
    pit_stop_cost: float,
) -> SimulationResult:
    """Estima o tempo total de corrida para uma estratégia alternativa,
    usando modelos de ritmo ajustados às voltas reais deste piloto na
    sessão, e compara-o com o tempo total real de corrida do piloto.

    Para cada stint pedido em `strategy` (na posição `index`), a escolha do
    PaceModel segue esta ordem (ver _select_pace_model):
    1. Se existir um stint real do piloto na mesma posição (`index`) com o
       MESMO composto — ou seja, a estratégia pedida está a "reproduzir" a
       estratégia real ponto por ponto até aqui — usa-se o PaceModel exato
       desse stint real. Isto é o que torna fiel simular a própria
       estratégia real do piloto (replay), incluindo quando ele usou o
       mesmo composto em mais do que um stint com ritmos diferentes.
    2. Caso contrário (estratégia genuinamente hipotética nessa posição),
       usa-se a média dos PaceModels de todos os stints reais desse
       composto (ver pace_model.average_pace_model) — um critério simples
       e explícito, não um "acidente" de qual stint foi processado por
       último.
    Se o piloto nunca usou aquele composto na sessão real (nenhum stint
    correspondente, em posição nenhuma), não há dados para estimar — o
    stint é excluído do total (não é adivinhado), e um aviso indica qual o
    stint e o motivo.

    À estimativa é ainda somado o tempo real perdido em Safety Car/VSC na
    corrida real (ver simulation.safety_car) — esses períodos ocorreriam
    de qualquer forma, independentemente da estratégia escolhida, por isso
    sem esta soma a estimativa representaria uma corrida "impossivelmente
    limpa", inflacionando artificialmente a vantagem de qualquer
    estratégia alternativa.
    """
    warnings: list[str] = []

    real_total_time_seconds = _sum_real_lap_times(driver_laps, warnings)
    real_stint_models = build_driver_stint_pace_models(driver_laps, real_stints)
    safety_car_periods = calculate_safety_car_time_lost(driver_laps, real_stints, real_stint_models)
    safety_car_time_added_seconds = sum(period.time_lost_seconds for period in safety_car_periods)

    estimated_total_time_seconds = 0.0
    computed_stints = 0
    skipped_stints = 0

    for index, stint_plan in enumerate(strategy):
        pace = _select_pace_model(index, stint_plan, real_stint_models)

        if pace is None:
            skipped_stints += 1
            warnings.append(
                f"Composto {stint_plan.compound!r} sem dados suficientes para "
                f"{driver} nesta corrida; stint {index + 1} excluído da estimativa."
            )
            continue

        estimated_total_time_seconds += sum(
            pace.base_pace_seconds + pace.degradation_seconds_per_lap * lap_index
            for lap_index in range(stint_plan.number_of_laps)
        )
        computed_stints += 1

    number_of_pit_stops = max(len(strategy) - 1, 0)
    estimated_total_time_seconds += pit_stop_cost * number_of_pit_stops

    if computed_stints == 0:
        estimated_total_time_seconds = None
        warnings.append(
            "Nenhum stint da estratégia pôde ser estimado — sem dados de ritmo suficientes."
        )
    else:
        estimated_total_time_seconds += safety_car_time_added_seconds
        if skipped_stints:
            warnings.append(
                f"Estimativa parcial: {skipped_stints} de {len(strategy)} stint(s) "
                "excluído(s) do tempo total por falta de dados de ritmo."
            )

    if safety_car_periods:
        periods_description = "; ".join(_describe_period(period) for period in safety_car_periods)
        warnings.append(
            f"Corrida teve {len(safety_car_periods)} período(s) de Safety Car/VSC "
            f"({periods_description}). Adicionados ~{safety_car_time_added_seconds:.1f}s "
            "à estimativa, pois ocorreriam independentemente da estratégia."
        )

    difference_seconds = None
    if estimated_total_time_seconds is not None and real_total_time_seconds is not None:
        difference_seconds = estimated_total_time_seconds - real_total_time_seconds

    return SimulationResult(
        driver=driver,
        estimated_total_time_seconds=estimated_total_time_seconds,
        real_total_time_seconds=real_total_time_seconds,
        difference_seconds=difference_seconds,
        safety_car_time_added_seconds=safety_car_time_added_seconds,
        safety_car_periods=safety_car_periods,
        warnings=warnings,
    )


def _describe_period(period: SafetyCarPeriod) -> str:
    if len(period.laps) == 1:
        return f"volta {period.laps[0]}"
    return f"voltas {period.laps[0]}-{period.laps[-1]}"


def _select_pace_model(
    index: int, stint_plan: StintPlan, real_stint_models: list[StintPaceModel]
) -> PaceModel | None:
    is_positional_replay_match = (
        index < len(real_stint_models) and real_stint_models[index].compound == stint_plan.compound
    )
    if is_positional_replay_match:
        return real_stint_models[index].pace

    same_compound_models = [
        model.pace for model in real_stint_models if model.compound == stint_plan.compound
    ]
    return average_pace_model(same_compound_models)


def _sum_real_lap_times(driver_laps: list[Lap], warnings: list[str]) -> float | None:
    valid_times = [lap.lap_time_seconds for lap in driver_laps if lap.lap_time_seconds is not None]

    if not valid_times:
        warnings.append("Sem tempos de volta reais disponíveis para comparação.")
        return None

    missing = len(driver_laps) - len(valid_times)
    if missing:
        warnings.append(
            f"{missing} volta(s) sem tempo registado, excluída(s) do tempo real total."
        )

    return sum(valid_times)
