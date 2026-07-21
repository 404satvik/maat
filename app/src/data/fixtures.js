// Transport mock: the UI reads pre-computed pipeline output committed under
// src/fixtures/. Each fixture is genuine output from the full pipeline
// (classifier, extractor, retrieval, explainers, prep pack, draft). Only the
// transport is mocked here; none of the pipeline logic is reimplemented.
import chequeBounce from '../fixtures/cheque-bounce.json'
import tenancyDeposit from '../fixtures/tenancy-deposit.json'
import unclearFamily from '../fixtures/unclear-family.json'

export const scenarios = [chequeBounce, tenancyDeposit, unclearFamily]

export const scenarioById = Object.fromEntries(
  scenarios.map((scenario) => [scenario.id, scenario]),
)

export const steps = [
  { key: 'describe', label: 'Describe your situation', kicker: 'Start' },
  { key: 'issue', label: 'Issue and fact timeline', kicker: 'Understand' },
  { key: 'cases', label: 'Cases like yours', kicker: 'Compare' },
  { key: 'rights', label: 'Your rights', kicker: 'Orient' },
  { key: 'pathways', label: 'Options and pathways', kicker: 'Orient' },
  { key: 'prep', label: 'Prep pack', kicker: 'Prepare' },
  { key: 'draft', label: 'Draft notice', kicker: 'Prepare' },
]

export const issueLabels = {
  cheque: 'Cheque bounce (Negotiable Instruments Act, s.138)',
  consumer: 'Consumer dispute (Consumer Protection Act, 2019)',
  tenancy: 'Tenancy or rent dispute',
  other: 'Outside the covered issue areas',
}
