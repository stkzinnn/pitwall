"""Corrige o efeito do peso de combustível no tempo de volta, para que
pace_model.py consiga medir a degradação "pura" do pneu (sem misturar o
efeito de "carro mais leve ao longo da corrida"), e engine.py consiga
reconstruir tempos de volta realistas a partir dessa degradação pura.

Sem esta correção, a degradação medida a partir das voltas reais mistura
dois efeitos com sinais opostos: o pneu a piorar (tempos sobem) e o carro
a ficar mais leve (tempos descem à medida que se queima combustível) — o
que subestima a degradação real do pneu, e torna as extrapolações para
stints de comprimento diferente do real pouco fiáveis (a "ajuda" do
combustível a ficar mais leve não existe da mesma forma num stint
simulado mais longo).
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class FuelModelConfig:
    """Parâmetros do modelo de combustível, centralizados aqui (em vez de
    soltos no código) para poderem ser afinados por circuito no futuro
    (ex.: consumo mais alto em Spa do que em Mónaco) sem tocar na lógica
    de correção em si — bastaria construir e passar uma FuelModelConfig
    diferente por circuito."""

    fuel_effect_seconds_per_kg: float = 0.03
    """Segundos de tempo de volta ganhos por cada kg de combustível a
    menos. ~0.03 s/kg corresponde à referência frequentemente citada no
    paddock/imprensa técnica de F1 de "~0.3s por cada 10kg" — uma
    aproximação de ordem de grandeza razoável para a V1 (varia na
    realidade por carro/circuito/downforce)."""

    fuel_burn_kg_per_lap: float = 1.8
    """Consumo médio aproximado de combustível por volta, em kg. Carros de
    F1 atuais arrancam com cerca de 100-110kg para corridas de ~55-70
    voltas — 1.8 kg/volta é uma média de referência para a V1 (o consumo
    real varia por volta: mais alto em voltas de ultrapassagem/perseguição,
    mais baixo em fuel-saving)."""


DEFAULT_FUEL_MODEL_CONFIG = FuelModelConfig()

# Configuração de conveniência para testes que querem isolar lógica de
# degradação/pace de pneu do efeito de combustível (correção sempre 0).
ZERO_FUEL_EFFECT_CONFIG = FuelModelConfig(fuel_effect_seconds_per_kg=0.0, fuel_burn_kg_per_lap=0.0)


def fuel_correction_seconds(
    lap_number_in_race: int,
    total_laps: int,
    config: FuelModelConfig = DEFAULT_FUEL_MODEL_CONFIG,
) -> float:
    """Quantos segundos esta volta foi mais lenta do que teria sido no fim
    da corrida, só por causa do combustível extra ainda a bordo.

    CONVENÇÃO (importante manter consistente em toda a base de código):
    a referência de "correção zero" é a ÚLTIMA volta da corrida — o ponto
    em que o carro está mais leve. Todas as voltas anteriores tiveram mais
    combustível a bordo, logo foram mais lentas só por esse motivo, e a
    correção devolvida é sempre >= 0.

    - Para MEDIR degradação "pura" (só pneu): subtrai-se esta correção ao
      tempo de volta real antes de ajustar a regressão — ver
      pace_model.compute_stint_pace. Isto traz todas as voltas para o
      mesmo referencial de combustível (fim de corrida), sobrando só a
      variação por degradação do pneu.
    - Para SIMULAR um tempo de volta realista a partir de um modelo de
      ritmo "puro": soma-se esta correção de volta ao valor previsto —
      ver engine.py. Aqui usa-se o número de volta ABSOLUTO na corrida
      simulada (contagem acumulada ao longo da estratégia), não a posição
      dentro do stint — o nível de combustível depende de quanto da
      corrida já foi percorrida, não de quando foi a última paragem.

    Se as duas metades (medir vs. simular) alguma vez usarem convenções
    diferentes, introduz-se um viés sistemático em vez de o eliminar — daí
    esta função ser o único sítio onde a fórmula existe.

    Assume queima de combustível linear ao longo da corrida — aproximação
    razoável para a V1; a queima real varia ligeiramente de volta para
    volta (mais alta em ultrapassagens/perseguições, mais baixa em
    fuel-saving), o que fica fora do âmbito desta versão.
    """
    laps_of_fuel_still_to_burn = max(total_laps - lap_number_in_race, 0)
    fuel_kg_relative_to_finish = laps_of_fuel_still_to_burn * config.fuel_burn_kg_per_lap
    return fuel_kg_relative_to_finish * config.fuel_effect_seconds_per_kg
