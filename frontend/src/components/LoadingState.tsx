interface LoadingStateProps {
  message: string
  hint?: string
}

export function LoadingState({ message, hint }: LoadingStateProps) {
  return (
    <div className="flex flex-col items-center gap-3 rounded-lg border border-border bg-surface px-6 py-12 text-center">
      <span
        className="h-8 w-8 animate-spin rounded-full border-2 border-border-strong border-t-accent"
        role="status"
        aria-label="A carregar"
      />
      <p className="font-medium text-text">{message}</p>
      {hint && <p className="max-w-sm text-sm text-text-muted">{hint}</p>}
    </div>
  )
}
