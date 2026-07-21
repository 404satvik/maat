import { Callout, EmptyState, Kicker, SectionCard, Tag } from '../components/ui'
import { issueLabels } from '../data/fixtures'

// Step 2: the classified issue and the extracted chronology. The timeline is
// the hero interaction: a clean vertical chronology of the extracted events.
export default function IssueTimelineView({ scenario }) {
  const { classification, facts } = scenario
  const timeline = facts.timeline ?? []
  const amounts = facts.amounts ?? []
  const confidencePct = Math.round((classification.score ?? 0) * 100)

  return (
    <div className="max-w-3xl">
      <Kicker>Step 2</Kicker>
      <h2 className="mt-2 font-serif text-3xl tracking-tight">Issue and fact timeline</h2>

      <SectionCard className="mt-6 p-5">
        <Kicker>Identified issue area</Kicker>
        <p className="mt-2 font-serif text-xl">{issueLabels[classification.label]}</p>
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <Tag tone="lapis">{classification.label}</Tag>
          <span className="font-mono text-xs text-ink-muted">
            model confidence {confidencePct}%
          </span>
        </div>
        <p className="mt-3 text-sm text-ink-muted">
          This is a starting classification, not a decision about your case. If
          it looks wrong, your own description is what a lawyer will read.
        </p>
      </SectionCard>

      <div className="mt-8">
        <Kicker>Fact timeline</Kicker>
        <h3 className="mt-1 font-serif text-2xl">What happened, in order</h3>

        {timeline.length === 0 ? (
          <EmptyState title="No structured events were extracted">
            The description did not contain concrete dated events to lay out.
            Writing what happened in date order before your consultation still
            saves paid time.
          </EmptyState>
        ) : (
          <ol className="mt-5 border-l border-border pl-6">
            {timeline.map((event) => {
              const linked = event.amount_indices?.map((i) => amounts[i]).filter(Boolean) ?? []
              return (
                <li key={event.order} className="relative pb-7 last:pb-0">
                  <span
                    className="absolute -left-[27px] mt-1 h-2.5 w-2.5 rounded-full border border-lapis bg-paper"
                    aria-hidden="true"
                  />
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-mono text-xs text-ink-muted">
                      {String(event.order).padStart(2, '0')}
                    </span>
                    <Tag>{event.event_cue}</Tag>
                    <Tag tone={event.date_basis === 'resolved' ? 'lapis' : 'neutral'}>
                      {event.date_basis === 'resolved' ? 'dated' : 'narrative order'}
                    </Tag>
                  </div>
                  <p className="mt-2 leading-relaxed text-ink">{event.description}</p>
                  {linked.length > 0 ? (
                    <div className="mt-2 flex flex-wrap gap-2">
                      {linked.map((amount) => (
                        <Tag key={amount.span?.join('-') ?? amount.raw} tone="ochre">
                          {amount.raw}
                        </Tag>
                      ))}
                    </div>
                  ) : null}
                </li>
              )
            })}
          </ol>
        )}
      </div>

      <Callout tone="neutral" label="Shown back to you" className="mt-8">
        This timeline is built only from what you wrote. Nothing here is added or
        assumed. Correct anything that is off before relying on it.
      </Callout>
    </div>
  )
}
