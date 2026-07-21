// Small shared primitives. Interaction states (hover, focus-visible, active,
// disabled) live here so every view inherits them consistently.

export function Button({ variant = 'primary', className = '', ...props }) {
  const base =
    'inline-flex items-center justify-center gap-2 rounded-md px-4 py-2 text-sm font-medium transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-lapis disabled:cursor-not-allowed disabled:opacity-45'
  const variants = {
    primary:
      'border border-lapis bg-lapis text-paper hover:bg-lapis-hover active:bg-lapis-hover',
    secondary:
      'border border-border bg-paper text-ink hover:bg-paper-alt active:bg-border/40',
    ghost:
      'border border-transparent bg-transparent text-lapis hover:bg-lapis-wash active:bg-lapis-wash',
  }
  return <button className={`${base} ${variants[variant]} ${className}`} {...props} />
}

export function Kicker({ children, className = '' }) {
  return (
    <p
      className={`font-mono text-xs uppercase tracking-[0.14em] text-ink-muted ${className}`}
    >
      {children}
    </p>
  )
}

export function SectionCard({ children, className = '' }) {
  return (
    <div
      className={`rounded-md border border-border bg-paper-raised ${className}`}
    >
      {children}
    </div>
  )
}

// tone: neutral | note | caution | route  (paper-and-ink tints, no shadows)
export function Callout({ tone = 'note', label, children, className = '' }) {
  const tones = {
    neutral: 'border-border bg-paper-alt',
    note: 'border-lapis/30 bg-lapis-wash',
    caution: 'border-ochre/45 bg-ochre-wash',
    route: 'border-brick/40 bg-brick-wash',
  }
  const labelTones = {
    neutral: 'text-ink-muted',
    note: 'text-lapis',
    caution: 'text-ochre-deep',
    route: 'text-brick',
  }
  return (
    <div className={`rounded-md border-l-2 border ${tones[tone]} p-4 ${className}`}>
      {label ? (
        <p className={`mb-1 font-mono text-xs uppercase tracking-[0.12em] ${labelTones[tone]}`}>
          {label}
        </p>
      ) : null}
      <div className="text-sm leading-relaxed text-ink">{children}</div>
    </div>
  )
}

export function Tag({ children, tone = 'neutral', className = '' }) {
  const tones = {
    neutral: 'border-border text-ink-muted',
    lapis: 'border-lapis/40 text-lapis',
    ochre: 'border-ochre/50 text-ochre-deep',
    brick: 'border-brick/40 text-brick',
  }
  return (
    <span
      className={`inline-flex items-center rounded-sm border px-2 py-0.5 font-mono text-xs tracking-wide ${tones[tone]} ${className}`}
    >
      {children}
    </span>
  )
}

export function LoadingState({ label = 'Working' }) {
  return (
    <div
      className="flex items-center gap-3 rounded-md border border-border bg-paper-raised p-6"
      role="status"
      aria-live="polite"
    >
      <span className="h-4 w-4 animate-spin rounded-full border-2 border-border border-t-lapis" />
      <span className="text-sm text-ink-muted">{label}</span>
    </div>
  )
}

export function EmptyState({ title, children }) {
  return (
    <div className="rounded-md border border-dashed border-border p-6">
      <p className="font-medium text-ink">{title}</p>
      {children ? <p className="mt-1 text-sm text-ink-muted">{children}</p> : null}
    </div>
  )
}

export function ErrorState({ message, onRetry }) {
  return (
    <div className="rounded-md border-l-2 border border-brick/40 bg-brick-wash p-6" role="alert">
      <p className="font-mono text-xs uppercase tracking-[0.12em] text-brick">Could not load</p>
      <p className="mt-1 text-sm text-ink">{message}</p>
      {onRetry ? (
        <Button variant="secondary" className="mt-3" onClick={onRetry}>
          Try again
        </Button>
      ) : null}
    </div>
  )
}
