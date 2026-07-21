import { steps } from '../data/fixtures'

// Left rail on desktop, horizontal stepper on mobile. Steps after the first
// unlock once the situation has been analyzed.
export default function StepRail({ current, unlocked, onSelect }) {
  return (
    <nav aria-label="Progress" className="lg:sticky lg:top-6">
      <ol className="flex gap-2 overflow-x-auto pb-2 lg:flex-col lg:gap-0 lg:overflow-visible lg:pb-0">
        {steps.map((step, index) => {
          const isCurrent = index === current
          const isDisabled = index > 0 && !unlocked
          return (
            <li key={step.key} className="shrink-0 lg:border-b lg:border-border lg:last:border-b-0">
              <button
                type="button"
                disabled={isDisabled}
                aria-current={isCurrent ? 'step' : undefined}
                onClick={() => onSelect(index)}
                className={`group flex w-full items-baseline gap-3 rounded-md px-3 py-2.5 text-left transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-lapis disabled:cursor-not-allowed disabled:opacity-40 lg:rounded-none ${
                  isCurrent ? 'bg-lapis-wash lg:bg-transparent' : 'hover:bg-paper-alt'
                }`}
              >
                <span
                  className={`font-mono text-xs ${isCurrent ? 'text-lapis' : 'text-ink-muted'}`}
                >
                  {String(index + 1).padStart(2, '0')}
                </span>
                <span className="min-w-0">
                  <span className="block font-mono text-[0.65rem] uppercase tracking-[0.14em] text-ink-muted">
                    {step.kicker}
                  </span>
                  <span
                    className={`block text-sm ${
                      isCurrent ? 'font-medium text-ink' : 'text-ink'
                    }`}
                  >
                    {step.label}
                  </span>
                </span>
              </button>
            </li>
          )
        })}
      </ol>
    </nav>
  )
}
