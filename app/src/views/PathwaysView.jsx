import { Callout, Kicker, SectionCard, Tag } from '../components/ui'

// Step 5: realistic routes with pros and cons, plus limitation flags. Each flag
// carries its hard caveat; deadlines are never computed from user facts.
export default function PathwaysView({ scenario }) {
  const pathways = scenario.pathways

  if (pathways.status !== 'ok') {
    return (
      <div className="max-w-3xl">
        <Kicker>Step 5</Kicker>
        <h2 className="mt-2 font-serif text-3xl tracking-tight">Options and pathways</h2>
        <Callout tone="route" label="No pathway guidance available" className="mt-6">
          {pathways.message}
        </Callout>
      </div>
    )
  }

  return (
    <div className="max-w-3xl">
      <Kicker>Step 5</Kicker>
      <h2 className="mt-2 font-serif text-3xl tracking-tight">Options and pathways</h2>
      <p className="mt-3 max-w-prose text-ink-muted">
        Realistic routes for this kind of dispute, with rough trade-offs. Which
        one fits, and in what order, is a decision to make with a lawyer.
      </p>

      <ol className="mt-6 space-y-4">
        {pathways.pathways.map((pathway, index) => (
          <SectionCard key={pathway.pathway_id} className="p-5">
            <div className="flex items-baseline gap-3">
              <span className="font-mono text-sm text-ink-muted">
                {String(index + 1).padStart(2, '0')}
              </span>
              <h3 className="font-serif text-lg">{pathway.name}</h3>
            </div>
            <p className="mt-2 leading-relaxed text-ink">{pathway.what_it_is}</p>
            <p className="mt-2 text-sm text-ink-muted">
              <span className="font-medium text-ink">When it makes sense: </span>
              {pathway.when_it_makes_sense}
            </p>

            <div className="mt-4 grid gap-4 sm:grid-cols-2">
              <div>
                <Kicker>Pros</Kicker>
                <ul className="mt-2 space-y-1">
                  {pathway.pros.map((pro) => (
                    <li key={pro} className="flex gap-2 text-sm text-ink">
                      <span aria-hidden="true" className="text-lapis">+</span>
                      <span>{pro}</span>
                    </li>
                  ))}
                </ul>
              </div>
              <div>
                <Kicker>Cons</Kicker>
                <ul className="mt-2 space-y-1">
                  {pathway.cons.map((con) => (
                    <li key={con} className="flex gap-2 text-sm text-ink">
                      <span aria-hidden="true" className="text-brick">-</span>
                      <span>{con}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>

            {pathway.section_refs.length > 0 ? (
              <div className="mt-4 flex flex-wrap items-center gap-2">
                <span className="font-mono text-xs text-ink-muted">Refers to:</span>
                {pathway.section_refs.map((ref) => (
                  <Tag key={`${ref.act_id}-${ref.section}`} tone="lapis">
                    s.{ref.section} {ref.act}
                  </Tag>
                ))}
              </div>
            ) : null}
          </SectionCard>
        ))}
      </ol>

      <div className="mt-8">
        <Kicker>Deadlines and limitation</Kicker>
        <h3 className="mt-1 font-serif text-2xl">Time limits to confirm early</h3>
        <div className="mt-4 space-y-4">
          {pathways.limitation_flags.map((flag, index) => (
            <Callout key={index} tone="caution" label="Limitation">
              <p>{flag.statement}</p>
              {flag.section_ref ? (
                <p className="mt-2 font-mono text-xs text-ochre-deep">
                  From s.{flag.section_ref.section}, {flag.section_ref.act}
                </p>
              ) : null}
              <p className="mt-2 text-sm text-ink-muted">{flag.caveat}</p>
            </Callout>
          ))}
        </div>
      </div>
    </div>
  )
}
