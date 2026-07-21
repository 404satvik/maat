import { Callout, Kicker, SectionCard, Tag } from '../components/ui'

const SOURCE_LABELS = {
  dataset_label: 'Outcome (dataset label)',
  judgment_text: 'From the judgment',
  expert_annotation: 'Expert annotation',
}

// Verbatim excerpts can begin mid-sentence. Prepend a leading ellipsis for
// display so it reads as an intentional excerpt; the stored text is unchanged.
function displayExcerpt(text) {
  return /^\s*[a-z]/.test(text) ? `... ${text.trimStart()}` : text
}

// Step 3: retrieval. Confident, weak, and abstain must read differently.
// Abstain shows its routing message, never an empty list.
export default function CasesView({ scenario }) {
  const retrieval = scenario.retrieval
  const cases = retrieval.cases ?? []
  const framing = cases[0]?.framing

  return (
    <div className="max-w-3xl">
      <Kicker>Step 3</Kicker>
      <h2 className="mt-2 font-serif text-3xl tracking-tight">Cases like yours</h2>

      {retrieval.query_confidence === 'abstain' ? (
        <Callout tone="route" label="Nothing close enough was found" className="mt-6">
          {retrieval.message}
        </Callout>
      ) : (
        <>
          <div className="mt-4 flex flex-wrap items-center gap-2">
            {retrieval.query_confidence === 'weak' ? (
              <Tag tone="ochre">weak matches only</Tag>
            ) : (
              <Tag tone="lapis">confident matches</Tag>
            )}
            <span className="text-sm text-ink-muted">
              {cases.length} comparable {cases.length === 1 ? 'judgment' : 'judgments'}
            </span>
          </div>

          {framing ? (
            <Callout tone="neutral" label="How to read these" className="mt-4">
              {framing}
            </Callout>
          ) : null}

          <div className="mt-6 space-y-4">
            {cases.map((item) => {
              const weak = item.confidence === 'weak'
              return (
                <SectionCard
                  key={item.doc_id}
                  className={`border-l-2 p-5 ${weak ? 'border-l-ochre' : 'border-l-lapis'}`}
                >
                  <div className="flex flex-wrap items-baseline justify-between gap-2">
                    <h3 className="font-serif text-lg">{item.case_name}</h3>
                    <span className="font-mono text-xs text-ink-muted">
                      similarity {item.similarity.toFixed(2)}
                    </span>
                  </div>
                  <div className="mt-2 flex flex-wrap items-center gap-2">
                    <Tag tone={weak ? 'ochre' : 'lapis'}>{item.confidence}</Tag>
                    <Tag>{item.issue_area}</Tag>
                    <span className="font-mono text-xs text-ink-muted">{item.doc_id}</span>
                  </div>

                  {weak && item.caution ? (
                    <Callout tone="caution" label="Treat with caution" className="mt-3">
                      {item.caution}
                    </Callout>
                  ) : null}

                  <dl className="mt-4 space-y-3">
                    {item.summary.map((part, index) => (
                      <div key={index}>
                        <dt className="font-mono text-xs uppercase tracking-[0.12em] text-ink-muted">
                          {SOURCE_LABELS[part.source] ?? part.source}
                        </dt>
                        <dd className="mt-1 text-sm leading-relaxed text-ink">
                          {displayExcerpt(part.text)}
                        </dd>
                      </div>
                    ))}
                  </dl>
                </SectionCard>
              )
            })}
          </div>
        </>
      )}
    </div>
  )
}
