import { useState } from 'react'
import StepRail from './components/StepRail'
import { Button, ErrorState, LoadingState } from './components/ui'
import { scenarioById, scenarios, steps } from './data/fixtures'
import { runAnalysis } from './lib/analyze'
import DescribeView from './views/DescribeView'
import IssueTimelineView from './views/IssueTimelineView'
import CasesView from './views/CasesView'
import RightsView from './views/RightsView'
import PathwaysView from './views/PathwaysView'
import PrepPackView from './views/PrepPackView'
import DraftView from './views/DraftView'

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

export default function App() {
  const [scenarioId, setScenarioId] = useState(scenarios[0].id)
  const [stepIndex, setStepIndex] = useState(0)
  const [status, setStatus] = useState('idle') // idle | loading | ready | error
  const [error, setError] = useState(null)

  const scenario = scenarioById[scenarioId]
  const unlocked = status === 'ready'

  async function analyze() {
    setStatus('loading')
    setError(null)
    try {
      await runAnalysis(scenarioId)
      setStatus('ready')
      setStepIndex(1)
    } catch (err) {
      setError(err.message)
      setStatus('error')
    }
  }

  function selectScenario(id) {
    setScenarioId(id)
    if (status !== 'ready') {
      setStepIndex(0)
    }
  }

  const view = renderStep(steps[stepIndex].key, scenario, { status, error, analyze })

  return (
    <div className="min-h-svh bg-paper text-ink">
      <div className="border-b border-border bg-paper-alt">
        <p className="mx-auto max-w-6xl px-6 py-2 text-sm text-ink-muted">
          This is legal information, not legal advice. It does not predict any
          outcome and is not a substitute for a lawyer. Please consult a
          qualified advocate.
        </p>
      </div>

      <header className="border-b border-border">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-4 px-6 py-5">
          <div className="flex items-baseline gap-3">
            <FeatherMark className="h-6 w-6 shrink-0 self-center text-lapis" />
            <h1 className="font-serif text-2xl">Maat</h1>
            <p className="font-mono text-xs uppercase tracking-[0.14em] text-ink-muted">
              Prep before you see a lawyer
            </p>
          </div>
          <div className="flex items-center gap-2" role="group" aria-label="Sample situation">
            <span className="font-mono text-xs text-ink-muted">Sample:</span>
            {scenarios.map((item) => (
              <Button
                key={item.id}
                variant={item.id === scenarioId ? 'primary' : 'secondary'}
                className="px-3 py-1.5"
                aria-pressed={item.id === scenarioId}
                onClick={() => selectScenario(item.id)}
              >
                {item.title}
              </Button>
            ))}
          </div>
        </div>
      </header>

      <div className="mx-auto grid max-w-6xl gap-8 px-6 py-8 lg:grid-cols-[15rem_1fr]">
        <aside>
          <StepRail current={stepIndex} unlocked={unlocked} onSelect={setStepIndex} />
        </aside>

        <main className="min-w-0">
          {status === 'loading' && stepIndex === 0 ? (
            <div className="max-w-2xl space-y-6">
              <DescribeView scenario={scenario} status={status} onAnalyze={analyze} />
              <LoadingState label="Reading your situation, extracting facts, finding comparable cases" />
            </div>
          ) : status === 'error' ? (
            <ErrorState message={error} onRetry={analyze} />
          ) : (
            view
          )}

          {unlocked ? (
            <div className="mt-10 flex items-center justify-between border-t border-border pt-5">
              <Button
                variant="secondary"
                disabled={stepIndex === 0}
                onClick={() => setStepIndex((i) => Math.max(0, i - 1))}
              >
                Previous
              </Button>
              <span className="font-mono text-xs text-ink-muted">
                {stepIndex + 1} of {steps.length}
              </span>
              <Button
                disabled={stepIndex === steps.length - 1}
                onClick={() => setStepIndex((i) => Math.min(steps.length - 1, i + 1))}
              >
                Next
              </Button>
            </div>
          ) : null}
        </main>
      </div>

      <footer className="border-t border-border">
        <p className="mx-auto max-w-6xl px-6 py-4 text-xs text-ink-muted">
          Maat is an access-to-justice tool. It provides legal information and
          preparation help, and points you toward a qualified advocate or free
          legal aid (NALSA and the District Legal Services Authority). It does
          not replace a lawyer.
        </p>
      </footer>
    </div>
  )
}

function renderStep(key, scenario, flow) {
  switch (key) {
    case 'describe':
      return (
        <DescribeView scenario={scenario} status={flow.status} onAnalyze={flow.analyze} />
      )
    case 'issue':
      return <IssueTimelineView scenario={scenario} />
    case 'cases':
      return <CasesView scenario={scenario} />
    case 'rights':
      return <RightsView scenario={scenario} />
    case 'pathways':
      return <PathwaysView scenario={scenario} />
    case 'prep':
      return <PrepPackView scenario={scenario} />
    case 'draft':
      return <DraftView scenario={scenario} />
    default:
      return null
  }
}
