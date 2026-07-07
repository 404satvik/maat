# Retrieval eval

Corpus: L-NLProc/PredEx (official), 2170 filtered docs, 68415 chunks. Per area: {'tenancy': 1661, 'consumer': 301, 'cheque': 208}.

Relevance is a keyword-predicate proxy (stated in the eval file), not
human adjudication; numbers are directional.

| embedder | query mode | chunks | P@5 | P@10 | hit@5 | hit@10 |
|---|---|---|---|---|---|---|
| minilm | facts | full | 0.567 | 0.533 | 0.889 | 1.000 |
| minilm | raw | full | 0.567 | 0.533 | 0.833 | 1.000 |
| inlegalbert | facts | full | 0.433 | 0.406 | 0.833 | 0.944 |
| inlegalbert | raw | full | 0.433 | 0.350 | 0.833 | 0.889 |
| minilm | facts | first10 | 0.511 | 0.494 | 0.889 | 1.000 |
| minilm | raw | first10 | 0.544 | 0.533 | 0.889 | 0.944 |

Grounding check: 1080 results checked, 0 violations. All summaries verbatim-traceable to their sources.
