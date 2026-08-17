interface ErrorStateProps {
  message: string
}

export function ErrorState({ message }: ErrorStateProps) {
  return (
    <div
      role="alert"
      className="flex items-start gap-3 rounded-lg border border-danger/40 bg-danger/10 px-5 py-4"
    >
      <span className="mt-0.5 font-mono text-danger" aria-hidden="true">
        ✕
      </span>
      <p className="text-text">{message}</p>
    </div>
  )
}
