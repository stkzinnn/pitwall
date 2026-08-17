# PitWall

F1 Strategy Simulator — usa dados reais de Fórmula 1 para comparar a
**estratégia que realmente aconteceu** numa corrida com **estratégias
alternativas simuladas** (nº de pit stops, timing das paragens, composto de
pneus), e analisar o impacto de safety cars, clima, degradação e tráfego.

Este não é mais um "previsor da melhor estratégia" — o objetivo é permitir
explorar cenários contrafactuais ("e se tivesse parado 5 voltas mais cedo?")
sobre corridas históricas reais.

Ver [docs/architecture.md](docs/architecture.md) para a análise completa de
arquitetura, escolha de fontes de dados e roadmap.

## Estado atual

🚧 V1 em desenvolvimento incremental, por fases pequenas. Ver o roadmap em
[docs/architecture.md](docs/architecture.md#roadmap-fases-pequenas-uma-de-cada-vez).

Fases 1-4 (ingestão via FastF1, persistência em PostgreSQL, motor de
simulação, comparação de estratégias) já estão implementadas no backend.
Fase 5 (frontend) está a começar: o ecrã de seleção de corrida já liga ao
backend real.

## Stack

- **Backend:** Python 3.11+ / FastAPI
- **Simulação:** Python (dentro do backend, `app/simulation`)
- **Dados:** [FastF1](https://docs.fastf1.dev/) (timing oficial: voltas,
  pneus, pit stops, clima, race control) — ver justificação em
  [docs/architecture.md](docs/architecture.md#fontes-de-dados--análise)
- **Persistência:** PostgreSQL, via SQLAlchemy 2.x assíncrono (`asyncpg`) +
  Alembic para migrations
- **Frontend:** React + TypeScript + Vite, Tailwind v4 (tema escuro "pit
  wall" com tokens de cor de composto/acento — ver
  [frontend/README.md](frontend/README.md))

## Desenvolvimento local

```bash
# Base de dados (Postgres 16, porta 5433 — ver nota abaixo)
docker compose up -d db

cd backend
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS/Linux

pip install -r requirements-dev.txt
cp .env.example .env

alembic upgrade head            # aplica as migrations
uvicorn app.main:app --reload
```

> **Nota:** o `docker-compose.yml` mapeia o Postgres para o porto **5433**
> (não o 5432 por omissão), para não colidir com uma instalação local de
> PostgreSQL já existente na máquina. Se não tiveres esse conflito, podes
> alterar para 5432 no `docker-compose.yml` e no `.env`.

A API fica disponível em `http://localhost:8000` e a documentação
interativa (Swagger) em `http://localhost:8000/docs`.

### Migrations (Alembic)

```bash
cd backend
alembic revision --autogenerate -m "descrição da alteração"   # gerar
alembic upgrade head                                            # aplicar
```

O `alembic/env.py` lê sempre `DATABASE_URL` a partir de `app.core.config`
(logo do `.env`), nunca do `alembic.ini`, para nunca divergir da app.

### Testes

```bash
cd backend
pytest                     # tudo (marca `integration` exige FastF1 + `docker compose up -d db` + migrations aplicadas)
pytest -m "not integration"  # só testes unitários, offline, sem Postgres
```

### Lint / type-check

```bash
cd backend
ruff check .
mypy app
```

## Frontend

```bash
cd frontend
npm install
cp .env.example .env    # aponta para http://localhost:8000 por omissão
npm run dev
```

Fica disponível em `http://localhost:5173`. Precisa do backend (e da base
de dados) a correr — ver acima. Detalhes de stack, tokens de tema e
estrutura em [frontend/README.md](frontend/README.md).

## Estrutura do repositório

```
backend/    API + simulação (FastAPI, Python)
frontend/   UI (React/TS/Vite) — em desenvolvimento desde a Fase 5
infra/      Docker, CI/CD, Kubernetes — adicionado na Fase 6
docs/       Arquitetura e decisões técnicas
```
