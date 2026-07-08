# Statute explainer grounding check

Automated checks run: 214 across 27 explainer outputs.
Violations: 0.

## What these checks cover

Every cited section exists in data/statutes/; every rendered
verbatim text and source matches the statute file exactly; glosses
reference no section number absent from their quoted text and no
act other than the one cited; unmapped issues return the explicit
no-statute state with the disclaimer.

## What a human must still verify

1. Gloss faithfulness: the glosses are static hand-written
   restatements; automation checks their citations, not their
   meaning. Read each gloss beside its section once per change.
2. Curation fidelity: data/statutes/ text is mechanically extracted
   from the official PDFs recorded in each file's source field.
   Spot-check the curated text against those PDFs; known artifacts
   are minor spacing errors inherited from PDF extraction. Known
   source quirk, preserved verbatim per source-fidelity: the India
   Code PDF itself prints "debt of other liability" in the s.138
   Explanation (page 28; confirmed in two extraction modes of the
   digitally typeset text layer).
3. The Model Tenancy Act caveat: it is a model law and the user's
   state rent act governs; the caveat field carries this on every
   tenancy citation and must remain user-visible downstream.
4. Pathway accuracy and currency: the pathway descriptions and
   pros/cons are static hand-written procedural prose. Automation
   verifies their citations, the absence of fabricated section
   numbers, and that no deadline is computed; whether the
   procedure described is legally accurate and current needs a
   one-time human review, same as the glosses.
5. Prep pack completeness: the document checklists and lawyer
   question lists are static hand-written prose. Automation
   verifies their references resolve and that they state no law;
   whether they are sensible and reasonably complete for each
   issue area needs the same one-time human review.
