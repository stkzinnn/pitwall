# PitWall — Frontend

React + TypeScript + Vite. UI do PitWall Strategy Simulator.

## Stack e porquê

- **Vite** — dev server rápido, build simples, é o standard atual para SPAs React sem framework de SSR (não precisamos de SSR nesta V1).
- **React Router** — routing preparado desde já para os próximos ecrãs (construtor de estratégias, comparação) encaixarem sem reestruturar.
- **Tailwind CSS v4** (em vez de CSS Modules) — escolhido especificamente pela forma como o v4 trata *design tokens*: as cores/tipografia definidas em `src/index.css` (bloco `@theme`) tornam-se classes utilitárias automaticamente (`bg-surface`, `text-tyre-soft`, `font-mono`, ...). Isso mantém **um único sítio** para o tema (pedido explícito: "cores dos compostos... guardar como tokens/variáveis reutilizáveis, não hardcoded espalhados") em vez de repetir valores por CSS Modules em cada componente. Como o projeto vai ganhar vários ecrãs de telemetria com a mesma linguagem visual, isto compensa a curva de aprendizagem inicial do Tailwind.
- **Nenhuma lib de HTTP** — a API do backend é pequena e mesma-origem em espírito; um wrapper fino sobre `fetch` (`src/api/client.ts`) chega, sem trazer axios/react-query nesta fase.

## Tema — "Estação de Estratégia"

Direção visual (Fase 5): telemetria técnica (dados densos, mono nos números,
cor de composto como código visual) + tom editorial/cinematográfico
(tipografia display forte, drama nos momentos-chave — o herói P→P dos
resultados de simulação, o fundo 3D da página inicial). Base preta com tom
quente (não azulado), acento vermelho-corrida como identidade de marca.

Tokens centrais em [`src/index.css`](src/index.css) (`@theme`):

| Token | Uso |
|---|---|
| `--color-bg`, `--color-surface`, `--color-surface-raised` | Fundo da página, painéis, elementos elevados (preto quente) |
| `--color-border`, `--color-border-strong` | Contornos subtis / mais marcados |
| `--color-text`, `--color-text-muted`, `--color-text-dim` | Hierarquia de texto |
| `--color-accent`, `--color-accent-strong` | **Identidade de marca** (vermelho-corrida) — logo, ações primárias, títulos em destaque, foco, o fundo 3D. Nunca usado para significar "melhor" ou "pior". |
| `--color-success` | **Só** "melhor / mais rápido / subiu de posição / estratégia vencedora" — nunca um acento decorativo genérico |
| `--color-danger` | "pior / mais lento / desceu de posição" (e estados de erro genéricos) |
| `--color-warning` | Avisos (dados parciais, discrepância de voltas, safety car) |
| `--color-tyre-soft` (vermelho-rosa, distinto do vermelho de marca), `--color-tyre-medium` (amarelo), `--color-tyre-hard` (branco/cinza), `--color-tyre-intermediate`, `--color-tyre-wet` | Linguagem visual de composto de pneu — usar em todos os ecrãs que mostrem compostos |
| `--font-display` | Títulos/heróis (Archivo, 700–900) — grande, tight tracking |
| `--font-sans` | Corpo/prosa (Inter) |
| `--font-mono` | Todo número que seja "telemetria": tempos, deltas, posições, voltas (JetBrains Mono) |

Fontes carregadas via Google Fonts em [`index.html`](index.html). Qualquer
ecrã novo deve usar estas classes (`bg-surface`, `text-tyre-hard`,
`font-mono`, `font-display`, etc.) em vez de valores hex soltos.

### Fundo 3D (`RaceBackground.tsx`)

Um circuito estilizado em three.js (não `@react-three/fiber` — é uma cena
isolada e imperativa com o seu próprio loop de render, mais simples de
pausar/retomar fora do ciclo do React sem trazer um reconciler React→WebGL
inteiro). Usado **só** no hero da `RaceSelectionPage` (lazy-loaded — o
chunk de three.js só é pedido nessa página) e nunca nos ecrãs de trabalho,
que usam antes o `.ambient-backdrop` estático em CSS (ver `index.css`).
Pausa em `visibilitychange`, sai de cena via `IntersectionObserver`, e
respeita `prefers-reduced-motion` (não inicia WebGL nenhum, mostra 1 frame
estático).

### Cores de equipa e avatares de piloto — sem material protegido

`src/theme/teamColors.ts` mapeia nome de equipa → cor de identidade (só a cor,
como texto/hex — nunca logos nem imagens). `DriverAvatar` gera um círculo com
as iniciais do piloto sobre essa cor, em vez de usar fotos oficiais (material
protegido). Bandeiras de país (`src/lib/countryFlag.ts`) usam emoji Unicode
de bandeira — também texto, não imagem — nunca ícones/SVGs de bandeira.

## Estrutura

```
src/
  api/            cliente HTTP tipado (client.ts, types.ts espelham os schemas do backend, races.ts)
  components/     componentes reutilizáveis: AppLayout, Logo, RaceBackground (hero 3D),
                  LoadingState, ErrorState, RaceSummary, DriverCard/DriverAvatar (identidade de
                  piloto), TyreIcon/CompoundPicker (seletor de composto),
                  StintEditor/StrategyBar/StrategyEditor (construtor), ResultsRow (linha clicável
                  da classificação), StrategyResultCard (resultado de simulação)
  hooks/          useRaceSession — fetch + loading/erro partilhado por ecrãs que vivem numa
                  URL /races/:year/:round/... (resultados, construtor)
  lib/            helpers de apresentação (driverDisplay.ts, countryFlag.ts, strategyLabels.ts,
                  raceResults.ts, formatTime.ts)
  theme/          mapas de identidade visual fora do CSS (teamColors.ts, compoundColors.ts, color.ts)
  pages/          um componente por ecrã (RaceSelectionPage, ResultsPage, StrategyBuilderPage)
  routes/         tabela central de rotas (paths.ts) — novos ecrãs acrescentam aqui, não como strings soltas
  index.css       tokens de tema + estilos base
```

### Fluxo de navegação

`RaceSelectionPage` (`/`) → `ResultsPage` (`/races/:year/:round/results`, classificação
real, uma linha clicável por piloto) → `StrategyBuilderPage`
(`/races/:year/:round/drivers/:driver/strategy`). A grelha de cartões de piloto que
existia na seleção de corrida foi substituída por um único link "Ver classificação
da corrida": a classificação já mostra identidade do piloto (mesmo estilo de
avatar/cor de equipa) mais tempo, paragens e estratégia real — não fazia sentido
ter duas UIs diferentes para escolher piloto.

### Construtor de estratégias

`StrategyBuilderPage` gere o estado de uma ou mais `NamedStrategy` — o mesmo
formato (`{ label, strategy: StintPlan[] }`) que o backend espera em
`POST /api/v1/compare` (ver `backend/app/schemas/simulation.py`), para a
próxima etapa (ligar à API de simulação) não precisar de reestruturar nada,
só enviar este estado diretamente. Ainda não chama `/simulate` nem `/compare`.

A mesma `StrategyBar` usada no construtor (`stints planeados`) é reutilizada em
`ResultsPage` para mostrar a estratégia REAL de cada piloto (`lib/raceResults.ts`
converte `Stint[]` reais para o formato `StintPlan[]` que a barra já sabe
desenhar) — linguagem visual consistente entre "o que aconteceu" e "o que
podia ter acontecido".

## Desenvolvimento local

```bash
npm install
cp .env.example .env      # ajusta VITE_API_BASE_URL se o backend não estiver em localhost:8000
npm run dev
```

Abre em `http://localhost:5173`. Precisa do backend (`uvicorn app.main:app --reload`, porta 8000) e da base de dados (`docker compose up -d db`, na raiz do repo) a correr — ver [README.md](../README.md) na raiz.

```bash
npm run build     # build de produção (tsc -b && vite build) — falha se houver erros de tipos
npm run lint       # oxlint
npm run preview    # serve o build de produção localmente
```
