from app.schemas.session import PitStop

# Abaixo deste número de paragens PRÓPRIAS com duração válida, a média do
# piloto é uma amostra pequena demais para ser fiável (uma única paragem
# pode ser uma anomalia — furo, problema mecânico, paragem para reparação —
# não representativa do custo normal de parar aquele carro naquela
# corrida). Nesse caso cai-se para a média de toda a sessão como estimativa
# mais estável — ver calculate_driver_pit_stop_cost.
MIN_DRIVER_PIT_STOPS_FOR_OWN_AVERAGE = 2


def calculate_average_pit_stop_cost(pit_stops: list[PitStop]) -> float | None:
    """Custo médio de tempo de uma paragem nas boxes, em segundos, sobre o
    conjunto de paragens dado (pode ser as de um piloto ou as de toda a
    sessão — ver calculate_driver_pit_stop_cost para qual usar em cada
    caso).

    LIMITAÇÃO CONHECIDA: PitStop.duration_seconds (ver
    fastf1_client._build_pit_stops) é medido desde a entrada nas boxes até
    à saída seguinte, ou seja, já inclui o tempo total de entrada + parado
    + saída da pit lane, não só o tempo parado na box. Os dados de voltas
    do FastF1 não nos dão um delta contra uma volta de corrida normal para
    isolar só a componente de entrada/saída, por isso este valor é usado
    tal como está. É uma aproximação razoável para as comparações de tempo
    total da V1, já que tanto o total "real" como o "simulado" são
    afetados da mesma forma.

    Devolve None se nenhuma paragem tiver uma duração utilizável.
    """
    durations = [stop.duration_seconds for stop in pit_stops if stop.duration_seconds is not None]

    if not durations:
        return None

    return sum(durations) / len(durations)


def calculate_driver_pit_stop_cost(
    driver_pit_stops: list[PitStop], session_pit_stops: list[PitStop]
) -> float | None:
    """Custo de pit stop a usar para SIMULAR estratégias de UM piloto
    específico: a média das PRÓPRIAS paragens reais desse piloto nesta
    sessão, quando há pelo menos MIN_DRIVER_PIT_STOPS_FOR_OWN_AVERAGE com
    duração válida — é a estimativa mais representativa de como a equipa
    dele executa paragens nesta corrida em concreto (diferentes equipas têm
    tempos de paragem consistentemente diferentes). Com uma amostra menor
    (0 ou 1 paragem própria), cai-se para a média de toda a sessão como
    fallback mais estável, em vez de confiar num único valor que pode ser
    uma anomalia.

    Esta é a função que os endpoints /simulate e /compare devem usar — ver
    test_engine_regression.py, que valida o motor com o mesmo critério,
    para o que os testes garantem ser exatamente o que os endpoints
    devolvem.
    """
    valid_driver_durations = [
        stop.duration_seconds for stop in driver_pit_stops if stop.duration_seconds is not None
    ]

    if len(valid_driver_durations) >= MIN_DRIVER_PIT_STOPS_FOR_OWN_AVERAGE:
        return sum(valid_driver_durations) / len(valid_driver_durations)

    return calculate_average_pit_stop_cost(session_pit_stops)
