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

## Tudo containerizado (Docker Compose)

Alternativa ao desenvolvimento local acima: sobe a base de dados, o backend
e o frontend, todos em containers, com um único comando. Útil para testar o
"pacote" completo tal como vai correr num servidor, sem instalar Python/Node
na tua máquina.

```bash
docker compose up --build
```

- Frontend: http://localhost:8080
- Backend / Swagger: http://localhost:8000/docs
- Postgres (se quiseres ligar um cliente de BD): `localhost:5433`

O que acontece ao correr isto:

1. **`db`** — mesmo serviço Postgres 16 de sempre.
2. **`backend`** (`backend/Dockerfile`) — instala as dependências Python,
   copia o código, e no arranque (`backend/docker-entrypoint.sh`) aplica as
   migrations Alembic (`alembic upgrade head`) antes de arrancar o uvicorn.
   Liga-se ao Postgres pela rede interna do Docker (`db:5432`), não por
   `localhost` — dentro de containers, cada serviço só é acessível pelo
   nome definido no `docker-compose.yml`.
3. **`frontend`** (`frontend/Dockerfile`, multi-stage) — um stage Node faz
   `npm ci` + `npm run build`; o resultado (ficheiros estáticos) é copiado
   para uma imagem nginx muito mais pequena, que os serve. O nginx está
   configurado (`frontend/nginx.conf`) para devolver sempre `index.html` em
   rotas desconhecidas, para o react-router funcionar ao recarregar a
   página.

Detalhe importante sobre `VITE_API_BASE_URL`: o Vite grava esse valor
*dentro* dos ficheiros estáticos no momento do `npm run build` (não é lido
em runtime como as variáveis do backend). Por isso é passado como *build
arg* no `docker-compose.yml`, apontando para `localhost:<porta do
backend>` — é o browser do utilizador que faz os pedidos à API, não o
container do frontend, por isso tem de ser um endereço que o browser
consiga resolver, e não o nome interno `backend`.

As portas e credenciais são configuráveis via um `.env` na raiz do
repositório (ver `.env.example`); sem esse ficheiro, os valores por
omissão no `docker-compose.yml` já funcionam.

Para parar tudo: `docker compose down` (os dados do Postgres e a cache do
FastF1 ficam guardados em volumes nomeados; junta `-v` para os apagar
também).

> Este fluxo não substitui o desenvolvimento local acima — sem
> hot-reload, cada alteração de código exige um novo `--build`. Usa-o para
> validar que a app funciona "empacotada", ou como base para o deploy
> (fase seguinte do roadmap de DevOps).

## Estrutura do repositório

```
backend/    API + simulação (FastAPI, Python)
frontend/   UI (React/TS/Vite) — em desenvolvimento desde a Fase 5
infra/      Docker, CI/CD, Kubernetes — adicionado na Fase 6
docs/       Arquitetura e decisões técnicas
```
