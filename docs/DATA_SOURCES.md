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
| `opennyai` | Indian-legal NER + rhetorical-role segmentation; see compatibility note below |
| `spacy` + `en_core_web_sm` | General NER (DATE, GPE, ORG spans) supplementing the rule-based fact extractor |
| `sentence-transformers` | Embedding pipeline for retrieval |
| `faiss` / `chromadb` | Vector store over embedded cases and statutes |

### OpenNyAI compatibility note

The `opennyai` package does not install on Python 3.13 (it pins a spaCy
3.2-era stack whose C extensions fail to build), and its published NER
models (`opennyaiorg/en_legal_ner_sm` and `_trf` on HuggingFace) do not
deserialize under modern spaCy either. Fact extraction from user
complaints therefore uses spaCy `en_core_web_sm` plus a rule layer, which
fits the register anyway: OpenNyAI's entity types (JUDGE, COURT,
PETITIONER, STATUTE, and so on) target judgment prose, not complaints.

Where OpenNyAI remains relevant is extracting facts from retrieved
judgments in the retrieval phase, its native register. The option there
is a separate Python 3.10 sidecar venv running OpenNyAI as an offline
preprocessing step. That is a retrieval-phase decision, deferred until
that phase begins.

## Redaction note

Datasets already redact sexual-violence victim identities per IPC Section
228A. Maat must never attempt to reverse or surface these identities, and
must not re-identify or profile litigants, judges, or victims from any
retrieved source.
