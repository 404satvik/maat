# Data sources

Notes on the datasets and models planned for Maat. Nothing here is
downloaded yet; this is a reference for Phase 1 onward. Guardrail for all of
it: only released research datasets and public statutes, no scraping of
Indian Kanoon, eCourts, or court sites.

## Case corpus (retrieval: "cases like yours")

| Source | What | Use | Where |
|---|---|---|---|
| ILDC | ~35k Supreme Court of India cases | Retrieval corpus | `law-ai` / Exploration-Lab, HuggingFace + GitHub |
| PredEx | 15k+ expert-annotated cases (Nigam et al., 2024) | Retrieval + better summaries | HuggingFace |
| NyayaAnumana | Largest Indian legal judgment prediction dataset | Scale-up later | Law-AI Lab, IIT Kharagpur |

## Statute corpus (rights / applicable-law explainer)

Curated bare-act text for the chosen issue areas, stored as clean text under
`data/statutes/`. Bare acts are government works and freely reproducible.
Planned coverage:

- Consumer Protection Act, 2019
- Negotiable Instruments Act, 1881 (Section 138 and surrounding provisions)
- The relevant state/central rent or tenancy act for the tenancy issue area

## Models and libraries

| Name | Use |
|---|---|
| `law-ai/InLegalBERT` (HuggingFace) | Indian-legal BERT; intake classifier fine-tuning and case/statute embeddings |
| `opennyai` | Indian-legal NER + rhetorical-role segmentation; fact/entity extraction and pulling the Facts section out of retrieved judgments |
| `sentence-transformers` | Embedding pipeline for retrieval |
| `faiss` / `chromadb` | Vector store over embedded cases and statutes |

## Redaction note

Datasets already redact sexual-violence victim identities per IPC Section
228A. Maat must never attempt to reverse or surface these identities, and
must not re-identify or profile litigants, judges, or victims from any
retrieved source.
