import { Button, Callout, EmptyState, Kicker, SectionCard, Tag } from '../components/ui'

// Step 6: the prep pack, laid out like a considered printable worksheet.
export default function PrepPackView({ scenario }) {
  const pack = scenario.prep_pack

  if (pack.status !== 'ok') {
    return (
      <div className="max-w-3xl">
        <Kicker>Step 6</Kicker>
        <h2 className="mt-2 font-serif text-3xl tracking-tight">Prep pack</h2>
        <Callout tone="route" label="No prep pack for this issue" className="mt-6">
          {pack.message}
        </Callout>
      </div>
    )
  }

  return (
    <div className="max-w-3xl" id="prep-pack-worksheet">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <Kicker>Step 6</Kicker>
          <h2 className="mt-2 font-serif text-3xl tracking-tight">Prep pack</h2>
        </div>
        <Button variant="secondary" className="print:hidden" onClick={() => window.print()}>
          Print this worksheet
        </Button>
      </div>
      <p className="mt-3 max-w-prose text-ink-muted">
        Take this to your first consultation. It gathers what to bring, what to
        ask, and the timeline built from your own words, so paid time is spent
        on advice, not on catching up.
      </p>

      {pack.caveats.map((caveat) => (
        <Callout key={caveat.slice(0, 24)} tone="caution" label="Important caveat" className="mt-6">
          {caveat}
        </Callout>
      ))}

      <div className="mt-8 grid gap-6 md:grid-cols-2">
        <SectionCard className="p-5">
          <Kicker>Documents to gather</Kicker>
          <ul className="mt-3 space-y-2">
            {pack.documents_checklist.map((doc) => (
              <li key={doc} className="flex gap-3 text-sm text-ink">
                <span
                  aria-hidden="true"
                  className="mt-0.5 h-4 w-4 shrink-0 rounded-sm border border-ink-muted"
                />
                <span>{doc}</span>
              </li>
            ))}
          </ul>
        </SectionCard>

        <SectionCard className="p-5">
          <Kicker>Questions for your lawyer</Kicker>
          <ol className="mt-3 space-y-2">
            {pack.lawyer_questions.map((question, index) => (
              <li key={question} className="flex gap-3 text-sm text-ink">
                <span className="font-mono text-xs text-ink-muted">
                  {String(index + 1).padStart(2, '0')}
                </span>
                <span>{question}</span>
              </li>
            ))}
          </ol>
        </SectionCard>
      </div>

      <div className="mt-6">
        <SectionCard className="p-5">
          <Kicker>Your fact timeline</Kicker>
          {pack.timeline.length === 0 ? (
            <EmptyState title="No timeline yet">
              {pack.timeline_note}
            </EmptyState>
          ) : (
            <ol className="mt-3 space-y-2">
              {pack.timeline.map((event) => (
                <li key={event.order} className="flex gap-3 text-sm text-ink">
                  <span className="font-mono text-xs text-ink-muted">
                    {String(event.order).padStart(2, '0')}
                  </span>
                  <span>{event.description}</span>
                </li>
              ))}
            </ol>
          )}
        </SectionCard>
      </div>

      {(pack.rights_refs.length > 0 || pack.pathway_refs.length > 0) && (
        <div className="mt-6 flex flex-wrap gap-2">
          {pack.rights_refs.map((ref) => (
            <Tag key={`${ref.act_id}-${ref.section}`} tone="lapis">
              s.{ref.section} {ref.act}
            </Tag>
          ))}
          {pack.pathway_refs.map((ref) => (
            <Tag key={ref.pathway_id}>{ref.name}</Tag>
          ))}
        </div>
      )}
    </div>
  )
}
