from app.schemas.session import PitStop


def calculate_average_pit_stop_cost(pit_stops: list[PitStop]) -> float | None:
    """Custo médio de tempo de uma paragem nas boxes nesta sessão, em segundos.

    LIMITAÇÃO CONHECIDA: PitStop.duration_seconds (ver
    fastf1_client._build_pit_stops) é medido desde a entrada nas boxes até
    à saída seguinte, ou seja, já inclui o tempo total de entrada + parado
    + saída da pit lane, não só o tempo parado na box. Os dados de voltas
    do FastF1 não nos dão um delta contra uma volta de corrida normal para
    isolar só a componente de entrada/saída, por isso este valor é usado
    tal como está. É uma aproximação razoável para as comparações de tempo
    total da V1, já que tanto o total "real" como o "simulado" são
    afetados da mesma forma.

    Devolve None se nenhuma paragem da sessão tiver uma duração utilizável.
    """
    durations = [stop.duration_seconds for stop in pit_stops if stop.duration_seconds is not None]

    if not durations:
        return None

    return sum(durations) / len(durations)
