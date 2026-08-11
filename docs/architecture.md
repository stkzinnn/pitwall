# PitWall — Arquitetura (V1)

## Objetivo

Comparar a **estratégia real** de uma corrida de F1 com **estratégias simuladas**
alternativas (número de pit stops, timing das paragens, composto de pneus),
respondendo a perguntas contrafactuais ("e se...") em vez de apenas prever a
estratégia ótima.

## Fluxo de dados (V1)

```
FastF1 (dados oficiais de timing) ──┐
                                     ├──▶ Data Ingestion Layer ──▶ PostgreSQL
Jolpica-F1 (Ergast-compatible) ─────┘         (backend/app/data_sources)
                                                       │
                                                       ▼
                                          Simulation Engine (backend/app/simulation)
                                                       │
                                                       ▼
                                     Comparação: estratégia real vs. simulada
                                                       │
                                                       ▼
                                        API (FastAPI) ──▶ Frontend (React)
```

## Fontes de dados — análise

| Critério | **FastF1** (escolhida) | OpenF1 | Jolpica-F1 (sucessor do Ergast) |
|---|---|---|---|
| Natureza | Biblioteca Python que agrega o live-timing oficial da F1 + Ergast/Jolpica | API REST pública | API REST pública, compatível com Ergast |
| Cobertura histórica | 2018–presente (timing oficial completo) | 2023–presente | 1950–presente (resultados/standings), mas sem laps/tyres/telemetria |
| Voltas (lap times) | ✅ completo, por piloto | ✅ | ⚠️ apenas fastest lap por corrida |
| Pit stops | ✅ (duração, volta) | ✅ | ✅ (desde 2012, duração e volta) |
| Pneus / stints | ✅ composto, idade, stint | ✅ | ❌ |
| Clima | ✅ por sessão, alta resolução | ✅ | ❌ |
| Race control (safety car, flags) | ✅ track status + mensagens | ✅ | ❌ |
| Resultados/classificação | ✅ | ✅ | ✅ (histórico completo) |
| Autenticação / rate limit | Nenhuma; cache local em disco (`.fastf1_cache`) | Nenhuma; 3 req/s (free) | Nenhuma; ~200 req/h |
| Facilidade de uso | Alta — devolve DataFrames já estruturados por sessão | Média — chamadas REST manuais, paginação | Alta — mas schema mínimo |

**Decisão:** usar **FastF1** como fonte principal para a V1. É a única fonte
que junta, numa só chamada por sessão, exatamente os dados de que a
simulação precisa (voltas, stints/pneus, pit stops, clima, track status) já
alinhados por volta e piloto, com cache local automático — o que evita lidar
com múltiplas APIs REST e problemas de rate limit logo na V1. O **Jolpica-F1**
fica reservado como fonte complementar futura (ex.: standings de campeonato,
corridas anteriores a 2018). O **OpenF1** é uma alternativa válida (dados
desde 2023, boa granularidade), mas não traz vantagem sobre o FastF1 para
corridas históricas e implicaria implementar nós próprios a normalização que
o FastF1 já faz.

Fontes: [openf1.org](https://openf1.org/), [github.com/jolpica/jolpica-f1](https://github.com/jolpica/jolpica-f1), [github.com/theOehrly/Fast-F1](https://github.com/theOehrly/Fast-F1), [docs.fastf1.dev](https://docs.fastf1.dev/).

## Stack (V1)

- **Backend:** Python 3.11+ / FastAPI — assíncrono, tipado, boa integração com
  Pydantic para validar os dados que entram das APIs externas.
- **Simulação:** Python puro dentro do backend (`app/simulation`) — sem
  necessidade de um serviço separado nesta fase; o modelo de simulação é
  determinístico (baseado em pace/degradação observados), não requer treino
  de ML na V1.
- **Persistência:** PostgreSQL — guardar os dados já normalizados de cada
  corrida (evita reprocessar/redescarregar do FastF1 a cada pedido) e os
  resultados de simulações para comparação futura.
- **Frontend:** React + TypeScript — adequado para um seletor de
  corrida/estratégia interativo e visualizações (gráficos de posição/tempo
  por volta). Só será implementado a partir da fase em que houver API estável
  para consumir.

## Estrutura de pastas

```
PitWall/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app entrypoint (lifespan liga a cache do FastF1)
│   │   ├── core/                # configuração (env vars, settings)
│   │   ├── api/v1/               # routers HTTP
│   │   ├── data_sources/         # integração com FastF1 / Jolpica-F1
│   │   ├── db/                   # engine/sessão SQLAlchemy assíncrona
│   │   ├── models/               # modelos SQLAlchemy (RaceSession, Lap, PitStop, Stint)
│   │   ├── repositories/         # save_session / get_session (DB <-> SessionData)
│   │   ├── schemas/              # schemas Pydantic (request/response)
│   │   └── simulation/           # motor de simulação de estratégias
│   ├── alembic/                  # migrations (template async)
│   ├── tests/
│   ├── requirements.txt
│   ├── requirements-dev.txt
│   ├── pyproject.toml            # config ruff/mypy/pytest
│   └── .env.example
├── frontend/                     # placeholder — React/TS (fase futura)
├── infra/                        # placeholder — K8s/CI (fase futura)
├── docs/
│   └── architecture.md
├── docker-compose.yml            # Postgres 16 para desenvolvimento local
└── README.md
```

Preparado para, sem reestruturar, adicionar mais tarde: `infra/k8s/`
(manifests), `.github/workflows/` (CI/CD), Dockerfile da própria app, e um
serviço de observabilidade (logging estruturado + métricas).

## Roadmap (fases pequenas, uma de cada vez)

1. ✅ **Fase 0 — Scaffold:** estrutura de pastas, FastAPI mínimo,
   testes, configuração por env vars, README, git. *(sem lógica de F1 ainda)*
2. ✅ **Fase 1 — Ingestão de dados:** wrapper sobre FastF1 para carregar uma
   sessão de corrida (laps, stints, pit stops, clima, track status) e
   endpoint `GET /races/{year}/{round}` que devolve esses dados normalizados.
3. ✅ **Fase 2 — Persistência:** modelos SQLAlchemy assíncronos + Alembic;
   `GET /races/{year}/{round}` lê primeiro da base de dados (PostgreSQL via
   `asyncpg`) e só recorre ao FastF1 — gravando o resultado — se a corrida
   ainda não tiver sido ingerida. Postgres local via `docker-compose.yml`.
4. **Fase 3 — Motor de simulação (v1 simples):** dado um conjunto de voltas
   reais (pace por piloto/composto), simular uma estratégia alternativa
   (nº de paragens, volta da paragem, composto) e devolver tempo total
   estimado + posição estimada.
5. **Fase 4 — Comparação:** endpoint que compara a estratégia real extraída
   dos dados vs. uma ou mais estratégias simuladas, incluindo o impacto de
   safety cars / clima já observados na corrida.
6. **Fase 5 — Frontend:** seleção de corrida, visualização da estratégia real
   vs. simulada (gráfico de posição/tempo, tabela de stints).
7. **Fase 6 — Produção:** Docker, docker-compose (backend + db), CI (lint +
   testes), e só depois Kubernetes/cloud/monitoring.

Cada fase só arranca quando a anterior estiver validada e o utilizador pedir
para avançar.
