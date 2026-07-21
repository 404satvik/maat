import { useState } from 'react'
import { Button, Callout, Kicker, SectionCard, Tag } from '../components/ui'

// Step 4: applicable-law explainer. Verbatim section text plus a plain-language
// gloss, each section's source shown. Any act-level caveat must render.
export default function RightsView({ scenario }) {
  const rights = scenario.rights

  if (rights.status !== 'ok') {
    return (
      <div className="max-w-3xl">
        <Kicker>Step 4</Kicker>
        <h2 className="mt-2 font-serif text-3xl tracking-tight">Your rights</h2>
        <Callout tone="route" label="No applicable statute found" className="mt-6">
          {rights.message}
        </Callout>
      </div>
    )
  }

  const caveats = scenario.pathways?.caveats ?? scenario.prep_pack?.caveats ?? []

  return (
    <div className="max-w-3xl">
      <Kicker>Step 4</Kicker>
      <h2 className="mt-2 font-serif text-3xl tracking-tight">Your rights</h2>
      <p className="mt-3 max-w-prose text-ink-muted">
        The law that applies to your issue, quoted from the bare act and
        explained in plain language. The quoted text is the source; the
        explanation restates only that text.
      </p>

      {caveats.map((caveat) => (
        <Callout key={caveat.slice(0, 24)} tone="caution" label="Important caveat" className="mt-6">
          {caveat}
        </Callout>
      ))}

      <div className="mt-6 space-y-5">
        {rights.sections.map((section) => (
          <RightsSection key={`${section.act_id}-${section.section}`} section={section} />
        ))}
      </div>
    </div>
  )
}

function RightsSection({ section }) {
  const [open, setOpen] = useState(false)
  return (
    <SectionCard className="p-5">
      <div className="flex flex-wrap items-baseline gap-2">
        <Tag tone="lapis">Section {section.section}</Tag>
        <h3 className="font-serif text-lg">{section.title}</h3>
      </div>
      <p className="mt-1 font-mono text-xs text-ink-muted">{section.act}</p>

      <p className="mt-4 leading-relaxed text-ink">{section.gloss}</p>

      <div className="mt-4">
        <Button
          variant="ghost"
          aria-expanded={open}
          onClick={() => setOpen((value) => !value)}
        >
          {open ? 'Hide the exact section text' : 'Read the exact section text'}
        </Button>
        {open ? (
          <blockquote className="mt-3 border-l-2 border-border bg-paper-alt p-4 font-serif text-sm leading-relaxed text-ink">
            {section.verbatim_text}
            <footer className="mt-3 font-mono text-xs not-italic text-ink-muted">
              Source: {section.source?.publisher}
              {section.source?.url ? ` — ${section.source.url}` : ''}
            </footer>
          </blockquote>
        ) : null}
      </div>

      {section.caveat ? (
        <Callout tone="caution" label="Section caveat" className="mt-4">
          {section.caveat}
        </Callout>
      ) : null}
    </SectionCard>
  )
}
