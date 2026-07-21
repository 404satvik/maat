import { Callout, EmptyState, Kicker, SectionCard, Tag } from '../components/ui'
import { parseDraftBody } from '../lib/draftMarkers'

// Step 7: the draft notice. Injected facts and missing-fact placeholders must
// read as visibly distinct from the static template prose, and the draft-only
// warning must be prominent.
export default function DraftView({ scenario }) {
  const draft = scenario.draft

  if (!draft) {
    return (
      <div className="max-w-3xl">
        <Kicker>Step 7</Kicker>
        <h2 className="mt-2 font-serif text-3xl tracking-tight">Draft notice</h2>
        <EmptyState title="No draft for this issue type">
          A draft document is generated only for issues with a standard notice,
          such as a cheque-bounce demand notice. For this situation, the prep
          pack and the pathways above are the place to start.
        </EmptyState>
      </div>
    )
  }

  if (draft.status !== 'ok') {
    return (
      <div className="max-w-3xl">
        <Kicker>Step 7</Kicker>
        <h2 className="mt-2 font-serif text-3xl tracking-tight">Draft notice</h2>
        <Callout tone="route" label="Not enough to draft safely" className="mt-6">
          {draft.message}
        </Callout>
      </div>
    )
  }

  const segments = parseDraftBody(draft.body_text)

  return (
    <div className="max-w-3xl">
      <Kicker>Step 7</Kicker>
      <h2 className="mt-2 font-serif text-3xl tracking-tight">Draft notice</h2>

      <Callout tone="route" label="Draft only, not reviewed by a lawyer" className="mt-6">
        {draft.draft_warning} This template has had no lawyer review. It is a
        starting scaffold to take to a lawyer, not a document to send as it is.
      </Callout>

      <div className="mt-6 flex flex-wrap items-center gap-3">
        <span className="inline-flex items-center gap-2 text-sm">
          <span className="h-3 w-3 rounded-sm border border-lapis/40 bg-lapis-wash" aria-hidden="true" />
          <span className="text-ink-muted">From your complaint (verify)</span>
        </span>
        <span className="inline-flex items-center gap-2 text-sm">
          <span className="h-3 w-3 rounded-sm border border-brick/40 bg-brick-wash" aria-hidden="true" />
          <span className="text-ink-muted">Missing, you must fill in</span>
        </span>
        <span className="font-mono text-xs text-ink-muted">
          {Object.keys(draft.slots_filled).length} filled, {draft.slots_missing.length} to complete
        </span>
      </div>

      <SectionCard className="mt-4 p-5">
        <p className="whitespace-pre-wrap font-sans text-sm leading-relaxed text-ink">
          {segments.map((segment, index) => {
            if (segment.type === 'filled') {
              return (
                <mark
                  key={index}
                  className="rounded-sm border border-lapis/40 bg-lapis-wash px-1 text-ink"
                  title="From your complaint, verify before sending"
                >
                  {segment.value}
                </mark>
              )
            }
            if (segment.type === 'missing') {
              return (
                <mark
                  key={index}
                  className="rounded-sm border border-brick/40 bg-brick-wash px-1 text-brick"
                  title="Not found in your complaint, fill this in"
                >
                  {segment.value}
                </mark>
              )
            }
            return <span key={index}>{segment.value}</span>
          })}
        </p>
      </SectionCard>

      {draft.section_refs?.length > 0 ? (
        <div className="mt-4 flex flex-wrap items-center gap-2">
          <span className="font-mono text-xs text-ink-muted">Statutory basis:</span>
          {draft.section_refs.map((ref) => (
            <Tag key={`${ref.act_id}-${ref.section}`} tone="lapis">
              s.{ref.section} {ref.act}
            </Tag>
          ))}
        </div>
      ) : null}

      {draft.caveats?.map((caveat) => (
        <Callout key={caveat.slice(0, 24)} tone="caution" label="Caveat" className="mt-4">
          {caveat}
        </Callout>
      ))}
    </div>
  )
}
