function FeatherMark({ className }) {
  return (
    <svg
      viewBox="0 0 24 24"
      className={className}
      fill="none"
      stroke="currentColor"
      strokeWidth="1.4"
      strokeLinecap="round"
      strokeLinejoin="round"
      role="img"
      aria-label="Maat"
    >
      <path d="M12 2c-4 3-7 8-7 13a5 5 0 0 0 5 5c1.8-3 3.2-6 4-9" />
      <path d="M12 2c4 3 7 8 7 13a5 5 0 0 1-5 5c-1.8-3-3.2-6-4-9" />
      <path d="M12 2v18" />
    </svg>
  )
}

function App() {
  return (
    <div className="min-h-svh flex flex-col bg-paper text-ink">
      <div className="border-b border-border bg-paper-alt">
        <p className="mx-auto max-w-5xl px-6 py-2 text-sm text-ink-muted">
          This is legal information, not legal advice. It does not predict any
          outcome and is not a substitute for a lawyer. Please consult a
          qualified advocate.
        </p>
      </div>

      <header className="border-b border-border">
        <div className="mx-auto flex max-w-5xl items-baseline gap-3 px-6 py-6">
          <FeatherMark className="h-6 w-6 shrink-0 text-lapis" />
          <h1 className="text-2xl font-medium">Maat</h1>
          <p className="font-mono text-xs uppercase tracking-wide text-ink-muted">
            Prep before you see a lawyer
          </p>
        </div>
      </header>

      <main className="mx-auto w-full max-w-5xl flex-1 px-6 py-16">
        <p className="max-w-prose text-ink-muted">
          This is the application shell for Maat. Feature views (issue
          intake, fact timeline, similar cases, rights and options, and the
          lawyer prep pack) are built out in later phases.
        </p>
      </main>

      <footer className="border-t border-border">
        <p className="mx-auto max-w-5xl px-6 py-4 text-xs text-ink-muted">
          Maat is an access-to-justice tool. It does not replace a lawyer.
        </p>
      </footer>
    </div>
  )
}

export default App
