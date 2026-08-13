import statistics
from dataclasses import dataclass

from app.schemas.session import Lap, Stint
from app.simulation.fuel_model import (
    DEFAULT_FUEL_MODEL_CONFIG,
    FuelModelConfig,
    fuel_correction_seconds,
)

# Abaixo deste número de voltas utilizáveis (cronometradas, sem contar a
# volta de saída, e sem contar outliers excluídos), um ajuste linear não é
# considerado fiável o suficiente para reportar — ver compute_stint_pace().
MIN_VALID_LAPS_FOR_DEGRADATION = 3

# Uma volta cujo tempo se desvie da mediana do stint em mais do que este
# número de desvios-padrão é tratada como anomalia (safety car, VSC,
# incidente, tráfego) e excluída do ajuste de degradação. 2.0 desvios-
# padrão é um limiar convencional para "claramente fora do normal" em
# amostras pequenas: um stint limpo tipicamente varia bem menos de 1s
# entre voltas (ruído normal de pneu/pista), enquanto uma volta sob VSC/SC
# costuma ser 10-30% mais lenta — uma diferença de várias dezenas de
# segundos, muito acima de 2 desvios-padrão típicos. Um limiar mais
# apertado (ex. 1.0) arriscava excluir voltas genuínas mas ligeiramente
# mais lentas (tráfego, erro pequeno de pilotagem).
OUTLIER_STD_DEV_THRESHOLD = 2.0


@dataclass
class PaceModel:
    base_pace_seconds: float
    degradation_seconds_per_lap: float
    laps_used: int
    # Valor bruto (SEM correção de combustível) da primeira volta limpa do
    # stint, guardado só para referência/debug — NÃO é usado na fórmula do
    # motor (ver engine.py), que usa antes o intercepto da regressão
    # (base_pace_seconds), já corrigido de combustível.
    first_clean_lap_seconds: float


@dataclass
class StintPaceModel:
    """O PaceModel de um stint real específico, identificado pela sua
    posição cronológica na corrida (stint_number) — ver
    build_driver_stint_pace_models() para o porquê de não se fundir
    stints diferentes do mesmo composto."""

    stint_number: int
    compound: str
    pace: PaceModel | None


def compute_stint_pace(
    stint_laps: list[Lap],
    total_laps: int,
    fuel_config: FuelModelConfig = DEFAULT_FUEL_MODEL_CONFIG,
) -> PaceModel | None:
    """Estima o ritmo base e a degradação por volta de um stint (um
    piloto, um composto), a partir das voltas desse stint ordenadas por
    lap_number.

    A primeira volta do stint é sempre excluída do ajuste: em qualquer
    stint que não seja o inicial, é a volta de saída das boxes (mais lenta
    por causa do limite de velocidade na pit lane), e no stint inicial é a
    volta de arranque parado — ambas são estruturalmente mais lentas do
    que uma volta de corrida "normal", por isso incluí-las enviesaria o
    ritmo base e o declive de degradação para valores mais baixos do que
    deviam ser.

    Antes de ajustar a regressão, cada tempo de volta é corrigido do efeito
    do peso de combustível (ver fuel_model.py), usando o número de volta
    ABSOLUTO na corrida (`lap.lap_number`), não a posição dentro do stint —
    o nível de combustível depende de quanto da corrida já foi percorrida,
    não de quando foi a última paragem. Sem esta correção, a degradação
    medida misturaria "pneu a piorar" com "carro a ficar mais leve",
    subestimando a degradação real do pneu.

    Entre as voltas restantes (já corrigidas), qualquer volta cujo tempo
    seja um outlier estatístico do stint (ver OUTLIER_STD_DEV_THRESHOLD) é
    também excluída do ajuste — tipicamente voltas sob safety car / VSC,
    que não refletem o ritmo real do piloto nem a degradação do pneu.

    O ritmo base devolvido (base_pace_seconds) é o INTERCEPTO da reta
    ajustada por regressão às voltas já corrigidas de combustível — ou
    seja, representa o ritmo "puro" (só pneu) que o piloto teria no fim da
    corrida (combustível mínimo, ver fuel_model.fuel_correction_seconds),
    não o valor bruto da primeira volta nem o ritmo com combustível a
    bordo.

    Devolve None se sobrarem menos de MIN_VALID_LAPS_FOR_DEGRADATION
    voltas válidas depois de excluir a volta de saída e os outliers: uma
    reta ajustada a 1-2 pontos não é uma tendência real, e reportar um
    número mesmo assim seria inventá-lo em vez de medi-lo.
    """
    positioned_laps = positioned_clean_laps(stint_laps)

    if len(positioned_laps) < MIN_VALID_LAPS_FOR_DEGRADATION:
        return None

    positions_in_stint = [position for position, _ in positioned_laps]
    raw_lap_times = [lap.lap_time_seconds for _, lap in positioned_laps]
    fuel_corrected_lap_times = [
        lap.lap_time_seconds - fuel_correction_seconds(lap.lap_number, total_laps, fuel_config)
        for _, lap in positioned_laps
    ]

    filtered_positions, filtered_times = _exclude_outlier_laps(
        positions_in_stint, fuel_corrected_lap_times
    )

    if len(filtered_times) < MIN_VALID_LAPS_FOR_DEGRADATION:
        return None

    slope, intercept = _linear_regression(filtered_positions, filtered_times)

    return PaceModel(
        base_pace_seconds=intercept,
        degradation_seconds_per_lap=slope,
        laps_used=len(filtered_times),
        first_clean_lap_seconds=raw_lap_times[0],
    )


def positioned_clean_laps(stint_laps: list[Lap]) -> list[tuple[int, Lap]]:
    """Voltas do stint elegíveis para o ajuste de ritmo — todas exceto a
    primeira (ver compute_stint_pace) e as que não têm lap_time_seconds —
    emparelhadas com a sua posição 0-indexada dentro dessa lista elegível.

    Esta é a MESMA indexação usada pela regressão em compute_stint_pace,
    exposta aqui para que outras partes do motor (ver
    safety_car.calculate_safety_car_time_lost) consigam calcular "o ritmo
    esperado nesta volta" com base.base_pace_seconds + degradação×posição
    de forma consistente com o que foi realmente ajustado.
    """
    eligible_laps = [lap for lap in stint_laps[1:] if lap.lap_time_seconds is not None]
    return list(enumerate(eligible_laps))


def _exclude_outlier_laps(
    positions: list[int], lap_times: list[float]
) -> tuple[list[int], list[float]]:
    """Remove pares (posição, tempo) cujo tempo esteja a mais de
    OUTLIER_STD_DEV_THRESHOLD desvios-padrão da mediana do stint.

    As posições originais (não renumeradas) são preservadas nos pares que
    sobram: a posição representa a idade do pneu em voltas desde que foi
    montado, um facto físico que não muda por se ter removido uma volta
    anómala algures no meio do stint.
    """
    if len(lap_times) < 2:
        return positions, lap_times

    median_time = statistics.median(lap_times)
    std_dev = statistics.pstdev(lap_times)

    if std_dev == 0:
        return positions, lap_times

    filtered_pairs = [
        (position, time)
        for position, time in zip(positions, lap_times, strict=True)
        if abs(time - median_time) <= OUTLIER_STD_DEV_THRESHOLD * std_dev
    ]

    if not filtered_pairs:
        # Caso degenerado (nunca deve acontecer com o limiar de 2 desvios-
        # padrão, mas por segurança): não filtrar tudo, usar os dados tal
        # como vieram em vez de ficar sem nada para ajustar.
        return positions, lap_times

    filtered_positions, filtered_times = zip(*filtered_pairs, strict=True)
    return list(filtered_positions), list(filtered_times)


def build_driver_stint_pace_models(
    driver_laps: list[Lap],
    driver_stints: list[Stint],
    total_laps: int,
    fuel_config: FuelModelConfig = DEFAULT_FUEL_MODEL_CONFIG,
) -> list[StintPaceModel]:
    """Um StintPaceModel por stint real do piloto (por ordem cronológica),
    cada um com o seu próprio PaceModel ajustado de forma independente.

    Stints diferentes do mesmo composto NÃO são fundidos nem substituem-se
    um ao outro: são jogos de pneus fisicamente diferentes, montados em
    condições de pista diferentes, com ritmos que podem ser bem distintos
    (ex.: o mesmo composto usado numa 1ª stint em pista suja e numa 2ª
    stint mais tarde, com a pista mais evoluída). Ver engine.py para como
    esta lista é usada: stints da estratégia pedida que correspondam
    posicionalmente a um stint real (mesmo índice, mesmo composto) usam o
    PaceModel exato desse stint; caso contrário usa-se um fallback
    agregado (ver average_pace_model).

    `total_laps` é o total de voltas da CORRIDA (não do stint) — necessário
    para a correção de combustível em compute_stint_pace(). Deve ser o
    mesmo valor usado depois em engine.py para simular, e em
    safety_car.py para quantificar tempo perdido: ver fuel_model.py.
    """
    laps_by_number = {lap.lap_number: lap for lap in driver_laps}
    stint_pace_models: list[StintPaceModel] = []

    for stint in sorted(driver_stints, key=lambda s: s.stint_number):
        if stint.compound is None:
            continue

        stint_laps = [
            laps_by_number[lap_number]
            for lap_number in range(stint.start_lap, stint.end_lap + 1)
            if lap_number in laps_by_number
        ]
        stint_pace_models.append(
            StintPaceModel(
                stint_number=stint.stint_number,
                compound=stint.compound,
                pace=compute_stint_pace(stint_laps, total_laps, fuel_config),
            )
        )

    return stint_pace_models


def average_pace_model(pace_models: list[PaceModel | None]) -> PaceModel | None:
    """Fallback para um stint HIPOTÉTICO de um composto que não corresponde
    posicionalmente a nenhum stint real específico (ver
    build_driver_stint_pace_models): a média simples (não ponderada) do
    ritmo base e da degradação entre todos os stints reais fiáveis desse
    composto, nesta sessão.

    Escolha explícita para a V1: uma média não ponderada é o critério mais
    simples e defensável quando não há uma stint real específica a que
    associar o stint hipotético — ao contrário de "ficar com o mais
    recente" (o comportamento anterior, que era acidental, não uma
    decisão), não há ainda razão de peso para confiar mais nas condições
    de um stint real do que noutro. Pode vir a ser substituído por uma
    média ponderada (ex. por número de voltas) numa fase futura, se se
    verificar que a simples não é suficientemente representativa.
    """
    valid_models = [pace for pace in pace_models if pace is not None]

    if not valid_models:
        return None

    count = len(valid_models)
    return PaceModel(
        base_pace_seconds=sum(pace.base_pace_seconds for pace in valid_models) / count,
        degradation_seconds_per_lap=(
            sum(pace.degradation_seconds_per_lap for pace in valid_models) / count
        ),
        laps_used=sum(pace.laps_used for pace in valid_models),
        first_clean_lap_seconds=(
            sum(pace.first_clean_lap_seconds for pace in valid_models) / count
        ),
    )


def _linear_regression(xs: list[float], ys: list[float]) -> tuple[float, float]:
    """Declive e intercepto de y em função de x, por mínimos quadrados
    simples: devolve (declive, intercepto) tal que a reta ajustada é
    y = intercepto + declive * x."""
    n = len(xs)
    x_mean = sum(xs) / n
    y_mean = sum(ys) / n

    numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(xs, ys, strict=True))
    denominator = sum((x - x_mean) ** 2 for x in xs)

    if denominator == 0:
        return 0.0, y_mean

    slope = numerator / denominator
    intercept = y_mean - slope * x_mean
    return slope, intercept
