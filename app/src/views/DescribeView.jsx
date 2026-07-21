import { useEffect, useState } from 'react'
import { Button, Callout, Kicker } from '../components/ui'

// Step 1: intake. The textarea is prefilled with the selected sample so every
// state downstream is reachable, but it is editable to show the real entry
// point. Submitting runs the simulated analysis in the parent.
export default function DescribeView({ scenario, status, onAnalyze }) {
  const [text, setText] = useState(scenario.complaint)

  useEffect(() => {
    setText(scenario.complaint)
  }, [scenario.id, scenario.complaint])

  const busy = status === 'loading'

  return (
    <div className="max-w-2xl">
      <Kicker>Step 1</Kicker>
      <h2 className="mt-2 font-serif text-3xl tracking-tight">Describe your situation</h2>
      <p className="mt-3 max-w-prose text-ink-muted">
        Write what happened in plain English or Hindi. There are no wrong words.
        The more concrete the facts, dates, and amounts, the more this tool can
        help you organize them before you see a lawyer.
      </p>

      <form
        className="mt-6"
        onSubmit={(event) => {
          event.preventDefault()
          onAnalyze()
        }}
      >
        <label htmlFor="complaint" className="sr-only">
          Describe your situation
        </label>
        <textarea
          id="complaint"
          value={text}
          onChange={(event) => setText(event.target.value)}
          rows={7}
          disabled={busy}
          className="w-full resize-y rounded-md border border-border bg-paper-raised p-4 text-ink leading-relaxed focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-lapis disabled:opacity-60"
        />
        <div className="mt-4 flex flex-wrap items-center gap-3">
          <Button type="submit" disabled={busy || text.trim().length === 0}>
            {busy ? 'Analyzing your situation' : 'Analyze my situation'}
          </Button>
          <span className="font-mono text-xs text-ink-muted">
            Sample loaded: {scenario.title}
          </span>
        </div>
      </form>

      <Callout tone="neutral" label="About this preview" className="mt-8">
        This preview runs on pre-computed output from the analysis pipeline for
        three sample situations. Editing the text above still loads the sample
        it started from, so you can see every screen and every result state.
      </Callout>
    </div>
  )
}
