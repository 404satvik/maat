# Extraction notes: policies and tie-breaks

Companion to the facts schema in `src/extract/schema.py`. These are the
judgment calls the extractor applies consistently. The grounding rule
throughout: record what the user said, never invent; legal significance
of any fact is later phases' job.

## complainant_side inference

Inferred from role words plus first-person context. Conflicting or absent
signals route the slot to `unresolved`; the extractor never defaults to
the majority side.

| Signal | Side |
|---|---|
| "my landlord", "I vacated", "I rent", "my rented flat", "we have lived here" | tenant |
| "my tenant", "I rented out my flat", "gave my flat on rent", "my PG" as operator | landlord |
| "gave me a cheque", "his cheque bounced", "I received a cheque", "settled with a cheque" (received) | payee |
| "my cheque bounced", "cheque I gave", "I have received a notice / summons" (s.138) | drawer |
| Both directions present (for example complainant received one cheque and issued another) | unresolved |

## Date resolution policy

All resolution is against the caller-supplied anchor date. `approximate`
is true whenever any component (day, month, or year) was inferred rather
than stated. `date_range` gives the worst-case window for approximate
dates so deadline logic never trusts a fabricated exact day.

| Pattern | iso | range |
|---|---|---|
| Explicit day-month-year ("3 March 2026", "03/04/2026" read as DD/MM) | exact | none |
| Day and month, year inferred ("3rd April") | most recent occurrence at or before anchor | none, approximate=true |
| Month only ("in January") | none | whole inferred month |
| "N days ago / since N days" | anchor - N days | plus or minus 1 day |
| "N weeks ago" | anchor - 7N days | plus or minus 3 days |
| "N months ago" | anchor - N months | plus or minus 15 days |
| "N years ago" | anchor - N years | plus or minus 182 days |
| "last week" | anchor - 7 days | [anchor - 14, anchor - 7] |
| "last month" | same day previous month | whole previous month |
| "yesterday" / "today" | exact | none |
| "the 3rd of this month" | that day in anchor month | none |
| Bare day-of-month ("on the 8th") | unresolved fragment | not guessed |

## Amount parsing

Rules are primary. `Rs`, `rupees`, `lakh`, `crore` markers; Indian digit
grouping ("1,20,000") normalized to integers; number words for lakh and
crore multiples ("forty lakhs"). Bare numbers of four or more digits are
accepted as amounts only when they are not year-like, since real
complaints often drop the currency marker ("I gave 34000 to a laptop
shop"). Purpose comes from a keyword window around the amount; no
keyword means purpose "unknown", never a guess.

## Slot assignment pragmatics

- `cheque_amount` (and `amount_paid`, similarly): an amount whose purpose
  matched wins; otherwise, if the complaint contains exactly one amount,
  that amount is assigned. More than one unmatched amount goes to
  `unresolved` as ambiguous.
- `bounce_dates` is a list; each entry carries `date_kind`
  (memo / actual_bounce / unclear) so a memo date and an actual bounce
  date are never merged. "The memo is dated X" gives kind memo; a date in
  a sentence with a bounce verb gives actual_bounce; both cues in one
  sentence give unclear.
- `notice_date` is when a demand notice was written or sent;
  `notice_served_date` is when it was received or delivered. Both usually
  null; captured when stated.

## NER noise defenses

- Hinglish stoplist: known romanized-Hindi function words (hai, ka, ki,
  ke, nahi, and so on) are never accepted as entities.
- Places: raw GPE spans are validated against an Indian state and city
  gazetteer; unvalidated spans are dropped from `places`. A gazetteer
  scan of the raw text also catches lowercase place names spaCy misses.
- "my company" is ambiguous (asset versus employer): treated as the
  employer (other side) only when salary or employment cues appear in the
  same sentence, else as the complainant's organization.
