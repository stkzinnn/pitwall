from app.schemas.session import Lap, Stint
from app.schemas.simulation import SafetyCarPeriod, SimulationResult, StintPlan
from app.simulation.fuel_model import (
    DEFAULT_FUEL_MODEL_CONFIG,
    FuelModelConfig,
    fuel_correction_seconds,
)
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
    fuel_config: FuelModelConfig = DEFAULT_FUEL_MODEL_CONFIG,
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

    Cada PaceModel já representa ritmo "puro" de pneu, corrigido do efeito
    de combustível (ver fuel_model.py e pace_model.compute_stint_pace).
    Para reconstruir um tempo de volta REALISTA para a corrida simulada,
    soma-se de volta a correção de combustível correspondente ao número de
    volta ABSOLUTO nessa corrida simulada (contagem acumulada ao longo de
    toda a estratégia, não a posição dentro do stint) — a mesma convenção
    usada para medir a degradação, só que invertida (ver
    fuel_model.fuel_correction_seconds).

    À estimativa é ainda somado o tempo real perdido em Safety Car/VSC na
    corrida real (ver simulation.safety_car) — esses períodos ocorreriam
    de qualquer forma, independentemente da estratégia escolhida, por isso
    sem esta soma a estimativa representaria uma corrida "impossivelmente
    limpa", inflacionando artificialmente a vantagem de qualquer
    estratégia alternativa.
    """
    warnings: list[str] = []

    total_laps = max((lap.lap_number for lap in driver_laps), default=0)

    if total_laps > 0:
        _warn_if_strategy_lap_count_differs_from_race(strategy, total_laps, warnings)

    real_total_time_seconds = _sum_real_lap_times(driver_laps, warnings)
    real_stint_models = build_driver_stint_pace_models(
        driver_laps, real_stints, total_laps, fuel_config
    )
    safety_car_periods = calculate_safety_car_time_lost(
        driver_laps, real_stints, real_stint_models, total_laps, fuel_config
    )
    safety_car_time_added_seconds = sum(period.time_lost_seconds for period in safety_car_periods)

    estimated_total_time_seconds = 0.0
    computed_stints = 0
    skipped_stints = 0
    race_lap_counter = 0

    for index, stint_plan in enumerate(strategy):
        # Every stint (including the first) has an opening lap — the
        # standing-start lap for the very first stint, the pit-out lap for
        # every stint after — that consumes a race lap NUMBER but is never
        # itself simulated (StintPlan.number_of_laps only counts "clean"
        # laps, matching how pace_model.compute_stint_pace fits real
        # stints — see positioned_clean_laps). The counter has to advance
        # for it too, or every clean lap after the 1st stint would be
        # matched against the wrong (earlier) point in the fuel curve.
        race_lap_counter += 1

        pace = _select_pace_model(index, stint_plan, real_stint_models)

        if pace is None:
            skipped_stints += 1
            warnings.append(
                f"Composto {stint_plan.compound!r} sem dados suficientes para "
                f"{driver} nesta corrida; stint {index + 1} excluído da estimativa."
            )
            # As voltas acontecem na corrida na mesma (só não conseguimos
            # estimar o seu ritmo de pneu) — o contador tem de avançar
            # para as correções de combustível dos stints seguintes
            # continuarem corretas.
            race_lap_counter += stint_plan.number_of_laps
            continue

        stint_time_seconds = 0.0
        for lap_index in range(stint_plan.number_of_laps):
            race_lap_counter += 1
            pure_tyre_pace = pace.base_pace_seconds + pace.degradation_seconds_per_lap * lap_index
            stint_time_seconds += pure_tyre_pace + fuel_correction_seconds(
                race_lap_counter, total_laps, fuel_config
            )

        estimated_total_time_seconds += stint_time_seconds
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


def _warn_if_strategy_lap_count_differs_from_race(
    strategy: list[StintPlan], total_laps: int, warnings: list[str]
) -> None:
    """Se o total de voltas planeado na estratégia não bater certo com o
    número real de voltas da corrida, avisa explicitamente: mais (ou menos)
    voltas do que a corrida real significa mais (ou menos) tempo de pista
    total só por causa disso — uma diferença que não tem nada a ver com a
    qualidade da estratégia de pneus escolhida, e por isso não deve ser
    lida como tal ao comparar com o tempo real.

    `strategy_total_laps` é a soma direta de StintPlan.number_of_laps —
    a mesma contagem que o frontend já mostra ao utilizador (ver
    StrategyEditor.tsx), para o aviso do backend e o do frontend
    concordarem sempre no mesmo número.
    """
    strategy_total_laps = sum(stint_plan.number_of_laps for stint_plan in strategy)
    lap_delta = strategy_total_laps - total_laps

    if lap_delta == 0:
        return

    warnings.append(
        f"Estratégia planeada tem {strategy_total_laps} volta(s); a corrida teve {total_laps} "
        f"({lap_delta:+d} volta(s)) — essa diferença afeta o tempo estimado só por si, "
        "independentemente da escolha de pneus."
    )


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
