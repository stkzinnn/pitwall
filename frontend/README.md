# PitWall — Frontend

React + TypeScript + Vite. UI do PitWall Strategy Simulator.

## Stack e porquê

- **Vite** — dev server rápido, build simples, é o standard atual para SPAs React sem framework de SSR (não precisamos de SSR nesta V1).
- **React Router** — routing preparado desde já para os próximos ecrãs (construtor de estratégias, comparação) encaixarem sem reestruturar.
- **Tailwind CSS v4** (em vez de CSS Modules) — escolhido especificamente pela forma como o v4 trata *design tokens*: as cores/tipografia definidas em `src/index.css` (bloco `@theme`) tornam-se classes utilitárias automaticamente (`bg-surface`, `text-tyre-soft`, `font-mono`, ...). Isso mantém **um único sítio** para o tema (pedido explícito: "cores dos compostos... guardar como tokens/variáveis reutilizáveis, não hardcoded espalhados") em vez de repetir valores por CSS Modules em cada componente. Como o projeto vai ganhar vários ecrãs de telemetria com a mesma linguagem visual, isto compensa a curva de aprendizagem inicial do Tailwind.
- **Nenhuma lib de HTTP** — a API do backend é pequena e mesma-origem em espírito; um wrapper fino sobre `fetch` (`src/api/client.ts`) chega, sem trazer axios/react-query nesta fase.

## Tema — "pit wall"

Tokens centrais em [`src/index.css`](src/index.css) (`@theme`):

| Token | Uso |
|---|---|
| `--color-bg`, `--color-surface`, `--color-surface-raised` | Fundo da página, painéis, elementos elevados (escala de escuro) |
| `--color-border`, `--color-border-strong` | Contornos subtis / mais marcados |
| `--color-text`, `--color-text-muted`, `--color-text-dim` | Hierarquia de texto |
| `--color-accent`, `--color-accent-strong` | Ações/destaques — usar com moderação |
| `--color-success`, `--color-danger`, `--color-warning` | Estado da aplicação (distintos dos tokens de composto, mesmo com tons próximos) |
| `--color-tyre-soft` (vermelho), `--color-tyre-medium` (amarelo), `--color-tyre-hard` (branco/cinza), `--color-tyre-intermediate`, `--color-tyre-wet` | Linguagem visual de composto de pneu — usar em todos os ecrãs que mostrem compostos |
| `--font-sans`, `--font-mono` | Mono para tudo o que for numérico/telemetria (tempos, deltas), sans para o resto |

Qualquer ecrã novo deve usar estas classes (`bg-surface`, `text-tyre-hard`, `font-mono`, etc.) em vez de valores hex soltos.

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
  components/     componentes reutilizáveis (AppLayout, LoadingState, ErrorState, RaceSummary, DriverCard, DriverAvatar)
  lib/            helpers de apresentação (driverDisplay.ts, countryFlag.ts)
  theme/          mapas de identidade visual fora do CSS (teamColors.ts)
  pages/          um componente por ecrã (RaceSelectionPage)
  routes/         tabela central de rotas (paths.ts) — novos ecrãs acrescentam aqui, não como strings soltas
  index.css       tokens de tema + estilos base
```

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
