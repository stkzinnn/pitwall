"""Quantifica o tempo que um piloto perdeu em períodos de Safety Car / VSC
na corrida REAL, para o somar ao tempo ESTIMADO de uma estratégia
alternativa (ver engine.simulate_strategy).

Porquê somar, e não simular o Safety Car em si: um período de SC/VSC
acontece por razões alheias à estratégia de pneus (incidente, detritos na
pista, etc.) — teria ocorrido exatamente da mesma forma independentemente
de que estratégia o piloto estivesse a seguir. O motor V1 não modela
SC/VSC (não sabe prever quando um vai acontecer nem como o piloto reagiria
numa estratégia diferente); o que conseguimos fazer de forma honesta é
medir quanto tempo REAL foi perdido no SC/VSC que de facto aconteceu, e
adicionar esse valor à estimativa "de pista limpa" do motor — assim a
diferença final (estimado vs. real) reflete só o efeito da mudança de
estratégia, não o acaso de ter havido ou não uma neutralização.

As voltas sob SC/VSC já são excluídas da regressão de degradação (ver
pace_model.OUTLIER_STD_DEV_THRESHOLD) — esse filtro e este cálculo são
independentes: um evita que a anomalia contamine o modelo de ritmo, o
outro quantifica o custo real dessa anomalia para a somar de volta.
"""

from dataclasses import dataclass

from app.schemas.session import Lap, Stint
from app.schemas.simulation import SafetyCarPeriod
from app.simulation.fuel_model import (
    DEFAULT_FUEL_MODEL_CONFIG,
    FuelModelConfig,
    fuel_correction_seconds,
)
from app.simulation.pace_model import StintPaceModel, positioned_clean_laps

# Códigos de TrackStatus do FastF1 considerados "sob safety car" para este
# módulo. O TrackStatus de cada volta é uma string com um dígito por cada
# mudança de estado ocorrida durante essa volta (ex.: "126" = esteve verde,
# depois amarela, depois VSC deployed, tudo na mesma volta):
#   1 = verde/normal, 2 = amarela, 4 = Safety Car, 5 = bandeira vermelha,
#   6 = VSC deployed, 7 = VSC ending.
# Consideramos uma volta "sob safety car" se o seu TrackStatus contiver
# QUALQUER UM de 4 (SC), 6 (VSC deployed) ou 7 (VSC ending) — nem que seja
# só parte da volta. O amarelo simples (2) é deliberadamente EXCLUÍDO: uma
# zona amarela local não impõe um ritmo fixo como o SC/VSC impõe, por isso
# não tem um "tempo perdido" tão bem definido para quantificar da mesma
# forma.
SAFETY_CAR_STATUS_CODES = frozenset({"4", "6", "7"})


def is_safety_car_lap(track_status: str | None) -> bool:
    if track_status is None:
        return False
    return any(code in track_status for code in SAFETY_CAR_STATUS_CODES)


@dataclass
class _AffectedLap:
    lap_number: int
    time_lost_seconds: float


def calculate_safety_car_time_lost(
    driver_laps: list[Lap],
    driver_stints: list[Stint],
    stint_pace_models: list[StintPaceModel],
    total_laps: int,
    fuel_config: FuelModelConfig = DEFAULT_FUEL_MODEL_CONFIG,
) -> list[SafetyCarPeriod]:
    """Identifica as voltas do piloto marcadas como sob safety car/VSC e
    estima quanto tempo perdeu em cada uma, agrupando voltas consecutivas
    num só período.

    Para cada volta sob safety car: tempo_perdido = tempo_real_da_volta −
    ritmo_normal_esperado_nessa_posição_do_stint. O "ritmo normal esperado"
    tem duas partes: o ritmo puro de pneu do stint (base_pace + degradação
    × posição, usando o PaceModel desse stint, já corrigido de
    combustível — ver pace_model.compute_stint_pace) MAIS a correção de
    combustível dessa volta em concreto (ver fuel_model.py), porque
    tempo_real_da_volta inclui o efeito real do combustível a bordo nessa
    altura da corrida e não seria justo comparar contra um ritmo "de fim
    de corrida". `total_laps`/`fuel_config` têm de ser os MESMOS usados
    para construir `stint_pace_models`, para a comparação ser consistente
    (ver engine.simulate_strategy).

    Só é possível quantificar voltas com um PaceModel fiável para o stint
    a que pertencem (stints sem dados suficientes — ver
    pace_model.compute_stint_pace — são ignorados, não geram um número
    inventado) e que não sejam a própria volta de saída do stint (essa já
    não tem uma "posição" no sistema de coordenadas da regressão — ver
    pace_model.positioned_clean_laps — e a sua lentidão estrutural de
    saída de boxes tornaria impossível separar o efeito do safety car do
    efeito normal de uma volta de saída).
    """
    laps_by_number = {lap.lap_number: lap for lap in driver_laps}
    pace_by_stint_number = {model.stint_number: model.pace for model in stint_pace_models}

    affected_laps: list[_AffectedLap] = []

    for stint in sorted(driver_stints, key=lambda s: s.stint_number):
        pace = pace_by_stint_number.get(stint.stint_number)
        if pace is None:
            continue

        stint_laps = [
            laps_by_number[lap_number]
            for lap_number in range(stint.start_lap, stint.end_lap + 1)
            if lap_number in laps_by_number
        ]

        for position, lap in positioned_clean_laps(stint_laps):
            if not is_safety_car_lap(lap.track_status):
                continue

            pure_tyre_pace_seconds = (
                pace.base_pace_seconds + pace.degradation_seconds_per_lap * position
            )
            expected_pace_seconds = pure_tyre_pace_seconds + fuel_correction_seconds(
                lap.lap_number, total_laps, fuel_config
            )
            # lap.lap_time_seconds is guaranteed non-None here: it's a
            # precondition of appearing in positioned_clean_laps().
            time_lost = lap.lap_time_seconds - expected_pace_seconds  # type: ignore[operator]
            affected_laps.append(
                _AffectedLap(lap_number=lap.lap_number, time_lost_seconds=time_lost)
            )

    return _group_into_periods(affected_laps)


def _group_into_periods(affected_laps: list[_AffectedLap]) -> list[SafetyCarPeriod]:
    """Agrupa voltas afetadas em períodos de números de volta consecutivos
    (ex.: [12, 13, 14] junta-se num período; [12, 20] fica em dois)."""
    if not affected_laps:
        return []

    ordered = sorted(affected_laps, key=lambda affected: affected.lap_number)

    periods: list[SafetyCarPeriod] = []
    current_laps = [ordered[0].lap_number]
    current_time_lost = ordered[0].time_lost_seconds

    for affected in ordered[1:]:
        if affected.lap_number == current_laps[-1] + 1:
            current_laps.append(affected.lap_number)
            current_time_lost += affected.time_lost_seconds
        else:
            periods.append(SafetyCarPeriod(laps=current_laps, time_lost_seconds=current_time_lost))
            current_laps = [affected.lap_number]
            current_time_lost = affected.time_lost_seconds

    periods.append(SafetyCarPeriod(laps=current_laps, time_lost_seconds=current_time_lost))
    return periods
