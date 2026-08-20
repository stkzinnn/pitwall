import { Link, useParams } from 'react-router-dom'
import type { SessionData } from '../api/types'
import { ErrorState } from '../components/ErrorState'
import { LoadingState } from '../components/LoadingState'
import { ResultsRow } from '../components/ResultsRow'
import { useRaceSession } from '../hooks/useRaceSession'
import { getOrderedResults } from '../lib/raceResults'
import { ROUTES } from '../routes/paths'

export function ResultsPage() {
  const params = useParams<{ year: string; round: string }>()
  const year = Number(params.year)
  const round = Number(params.round)

  const { status, session, errorMessage } = useRaceSession(year, round)

  return (
    <div className="flex flex-col gap-8">
      <Link
        to={ROUTES.raceSelection}
        className="inline-flex w-fit items-center gap-1.5 text-sm text-text-muted transition-colors hover:text-accent"
      >
        ← Voltar à seleção de corrida
      </Link>

      {status === 'loading' && (
        <LoadingState message="A carregar classificação…" hint="Um instante." />
      )}

      {status === 'error' && <ErrorState message={errorMessage} />}

      {status === 'success' && session && <ResultsContent session={session} />}
    </div>
  )
}

function ResultsContent({ session }: { session: SessionData }) {
  const orderedResults = getOrderedResults(session)

  return (
    <div className="flex flex-col gap-6">
      <div>
        <p className="font-mono text-sm tracking-widest text-text-dim uppercase">
          {session.year} · Ronda {session.round}
          {session.total_laps !== null && ` · ${session.total_laps} voltas`}
        </p>
        <h1 className="mt-1 font-display text-3xl font-extrabold tracking-tight text-text sm:text-4xl">
          {session.event_name ?? 'Corrida'}
        </h1>
        <p className="mt-2 text-text-muted">
          Classificação final — clica num piloto para montar uma estratégia alternativa a partir
          daqui.
        </p>
      </div>

      {orderedResults.length > 0 ? (
        <div className="animate-fade-rise-in overflow-x-auto rounded-xl border border-border bg-surface/90 backdrop-blur-sm">
          <table className="w-full min-w-[640px] border-collapse">
            <thead>
              <tr className="border-b border-border text-left text-xs tracking-wide text-text-dim uppercase">
                <th className="px-4 py-3 font-medium">Pos</th>
                <th className="px-4 py-3 font-medium">Piloto</th>
                <th className="px-4 py-3 text-right font-medium">Tempo / Gap</th>
                <th className="px-4 py-3 text-center font-medium">Paragens</th>
                <th className="px-4 py-3 font-medium">Estratégia real</th>
              </tr>
            </thead>
            <tbody>
              {orderedResults.map((result) => (
                <ResultsRow key={result.code} session={session} result={result} />
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <p className="rounded-lg border border-dashed border-border p-6 text-center text-sm text-text-dim">
          Sem classificação disponível para esta sessão.
        </p>
      )}
    </div>
  )
}
