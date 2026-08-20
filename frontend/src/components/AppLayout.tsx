import { Link, Outlet } from 'react-router-dom'
import { Logo } from './Logo'
import { ROUTES } from '../routes/paths'

/** Shell shared by every screen: the "pit wall" header + a centered
 * content column, over the static ambient backdrop (see index.css
 * `.ambient-backdrop`) — the ONE 3D hero background lives inside
 * RaceSelectionPage itself, not here, so it only ever renders where it's
 * meant to be the protagonist. Screens render inside via <Outlet />. */
export function AppLayout() {
  return (
    <div className="flex min-h-screen flex-col text-text">
      <div className="ambient-backdrop" />

      <header className="sticky top-0 z-20 border-b border-border bg-surface/75 backdrop-blur-md">
        <div className="mx-auto flex max-w-6xl items-center gap-3 px-6 py-3.5">
          <Link to={ROUTES.raceSelection} className="flex items-center gap-3 focus-visible:outline-none">
            <Logo size={30} />
            <span className="font-display text-lg font-extrabold tracking-tight text-text">
              PIT<span className="text-accent">WALL</span>
            </span>
          </Link>
        </div>
      </header>

      <main className="mx-auto w-full max-w-6xl flex-1 px-6 py-10">
        <Outlet />
      </main>

      <footer className="border-t border-border px-6 py-5">
        <p className="mx-auto max-w-6xl font-mono text-xs text-text-dim">
          PitWall — dados de F1 via{' '}
          <a
            href="https://docs.fastf1.dev/"
            target="_blank"
            rel="noreferrer"
            className="underline decoration-border-strong underline-offset-2 hover:text-text-muted"
          >
            FastF1
          </a>
        </p>
      </footer>
    </div>
  )
}
