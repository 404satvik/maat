# Maat

A tool that helps people in India get ready to see a lawyer. You describe
your problem in plain English or Hindi, and it helps you work out what kind
of legal issue you actually have, lays your facts out as a timeline, shows
how similar disputes have played out in court, explains the law that
applies, and builds a prep pack (questions to ask, documents to carry, a
draft notice) so your first consultation isn't wasted figuring out basics.

Named after Ma'at, the Egyptian goddess who weighed hearts against her
feather of truth. The idea is the same: get your facts straight before you
seek justice.

Two things this will never do: predict how your case will end, or replace a
lawyer. Everything it produces is legal information, not legal advice, and
it always points you toward a real advocate or free legal aid (NALSA /
DLSA). Any law or case it cites comes from a local corpus of released
research datasets and public bare acts, never from a model making things up,
and never from scraping court websites.

For now it only covers three kinds of problems, because a narrow pipeline
that works end to end beats a broad one that doesn't:

- consumer disputes (defective goods or services, refunds)
- cheque bounce under s.138 of the Negotiable Instruments Act
- tenancy and rent disputes

## Layout

```
src/        pipeline modules (intake, extract, retrieve, explain, draft, route)
notebooks/  experiments
data/       corpora and statute text (raw data is not tracked)
app/        web UI (React + Vite + Tailwind)
docs/       notes on data sources
```

## Findings

On an 18-query retrieval eval, general-purpose MiniLM beat the Indian-legal
InLegalBERT on the primary config: hit@5 of 1.000 against 0.833 and hit@10
of 1.000 against 0.944, with precision pointing the same way (P@5 0.600
against 0.400) as directional support. The takeaway is that contrastive
training matters more than domain vocabulary for similarity retrieval.
InLegalBERT was in the experiment precisely as the comparison baseline, so
it earned its keep by losing cleanly. These numbers come from a small
keyword-predicate proxy eval, not human adjudication, so treat them as
directional rather than settled.

Still early: the repo is scaffolding only at this point, no models or data
yet.
