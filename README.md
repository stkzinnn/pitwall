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

Nesta primeira etapa existe apenas o scaffold do backend (FastAPI a correr,
sem lógica de F1 ainda).

## Stack

- **Backend:** Python 3.11+ / FastAPI
- **Simulação:** Python (dentro do backend, `app/simulation`)
- **Dados:** [FastF1](https://docs.fastf1.dev/) (timing oficial: voltas,
  pneus, pit stops, clima, race control) — ver justificação em
  [docs/architecture.md](docs/architecture.md#fontes-de-dados--análise)
- **Persistência:** PostgreSQL (a partir da Fase 2)
- **Frontend:** React + TypeScript (a partir da Fase 5)

## Desenvolvimento local

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS/Linux

pip install -r requirements-dev.txt
cp .env.example .env

uvicorn app.main:app --reload
```

A API fica disponível em `http://localhost:8000` e a documentação
interativa (Swagger) em `http://localhost:8000/docs`.

### Testes

```bash
cd backend
pytest
```

### Lint / type-check

```bash
cd backend
ruff check .
mypy app
```

## Estrutura do repositório

```
backend/    API + simulação (FastAPI, Python)
frontend/   UI (React/TS) — adicionado na Fase 5
infra/      Docker, CI/CD, Kubernetes — adicionado na Fase 6
docs/       Arquitetura e decisões técnicas
```
