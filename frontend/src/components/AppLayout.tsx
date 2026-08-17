import { Outlet } from 'react-router-dom'

/** Shell shared by every screen: the "pit wall" header + a centered
 * content column. Screens render inside via <Outlet />. */
export function AppLayout() {
  return (
    <div className="flex min-h-screen flex-col bg-bg text-text">
      <header className="border-b border-border bg-surface">
        <div className="mx-auto flex max-w-6xl items-center gap-3 px-6 py-4">
          <span
            className="h-2.5 w-2.5 rounded-full bg-accent"
            style={{ boxShadow: '0 0 10px var(--color-accent)' }}
            aria-hidden="true"
          />
          <span className="font-mono text-lg font-semibold tracking-[0.2em] text-text">
            PIT<span className="text-accent">WALL</span>
          </span>
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
