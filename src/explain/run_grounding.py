"""Grounding check for the statute explainer, analogous to Phase 3's.

Automated checks:
  1. Every citation in ISSUE_SECTIONS and every gloss key resolves to a
     section that exists in data/statutes/.
  2. Every verbatim_text rendered by explain_rights matches the statute
     file byte for byte, and the source metadata matches the file.
  3. Gloss lint: every section number a gloss mentions is either the
     cited section itself or a number appearing inside the quoted text;
     every act name a gloss could name is the cited act.
  4. Unmapped issues ("other", unknown) return the explicit no-statute
     state with no sections.

What automation cannot verify, stated plainly: that a gloss is a
faithful paraphrase of its section (a human must read both side by
side), and that the curated section text matches the official PDF (the
curation is mechanical, but a human should spot-check data/statutes/
against the source PDFs recorded in each file's source field).

Run from the repo root:

    python -m src.explain.run_grounding
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import dataclasses

from src.draft.notice import TEMPLATE, draft_s138_notice
from src.draft.prep_pack import build_prep_pack
from src.draft.verify import verify_draft
from src.explain.explain import GLOSSES, ISSUE_SECTIONS, explain_rights
from src.explain.pathways import explain_pathways
from src.explain.statutes import get_section, load_acts

RESULTS_DIR = Path("results")

_SECTION_REF = re.compile(r"section\s+(\d+[A-Za-z]?(?:\(\d+\))?)", re.IGNORECASE)
_ACT_NAMES = (
    "Negotiable Instruments Act",
    "Consumer Protection Act",
    "Model Tenancy Act",
    "Transfer of Property Act",
    "Code of Criminal Procedure",
)


def check() -> tuple[int, list[str], int]:
    """Run all automated checks; return (checks_run, violations, n_outputs)."""
    violations: list[str] = []
    checks = 0

    for issue, citations in ISSUE_SECTIONS.items():
        for act_id, number in citations:
            checks += 1
            if get_section(act_id, number) is None:
                violations.append(f"{issue}: cited {act_id} s.{number} missing from data/statutes")
    for act_id, number in GLOSSES:
        checks += 1
        if get_section(act_id, number) is None:
            violations.append(f"gloss key {act_id} s.{number} missing from data/statutes")

    acts = load_acts()
    outputs = 0
    fact_variants: list[dict | None] = [
        None,
        {"slots": {"dispute_object": {"value": "deposit_refund"}}},
        {"slots": {"dispute_object": {"value": "eviction"}}},
        {"slots": {"dispute_object": {"value": "rent_increase"}}},
    ]
    for issue in ("cheque", "consumer", "tenancy"):
        for facts in fact_variants:
            result = explain_rights(issue, facts)
            outputs += 1
            for section in result.sections:
                checks += 3
                stored = acts[section.act_id]["sections"][section.section]
                if section.verbatim_text != stored["text"]:
                    violations.append(f"{section.act_id} s.{section.section}: rendered text differs from source file")
                if section.source != acts[section.act_id]["source"]:
                    violations.append(f"{section.act_id} s.{section.section}: source metadata differs")
                allowed_numbers = {section.section} | set(_SECTION_REF.findall(section.verbatim_text))
                for ref in _SECTION_REF.findall(section.gloss):
                    if ref not in allowed_numbers:
                        violations.append(
                            f"{section.act_id} s.{section.section}: gloss cites section {ref} "
                            "not present in the quoted text"
                        )
                for name in _ACT_NAMES:
                    if name.lower() in section.gloss.lower() and name.lower() not in section.act.lower():
                        checks += 1
                        if name.lower() not in section.verbatim_text.lower():
                            violations.append(
                                f"{section.act_id} s.{section.section}: gloss names {name}, "
                                "absent from cited act and quoted text"
                            )

    for issue in ("other", "something_unknown"):
        checks += 1
        outputs += 1
        result = explain_rights(issue)
        if result.status != "no_statute" or result.sections or not result.message:
            violations.append(f"{issue}: expected explicit no-statute state")
        if not result.disclaimer:
            violations.append(f"{issue}: missing disclaimer")

    # Phase 4b: pathways. Every section reference resolves (resolution
    # itself raises on dangling pointers); no prose cites a section
    # number outside its own reference list; nothing computes days left;
    # unmapped issues route out.
    days_left = re.compile(r"\d+\s*days?\s+(?:left|remaining)", re.IGNORECASE)
    for issue in ("cheque", "consumer", "tenancy"):
        outputs += 1
        response = explain_pathways(issue)
        if not response.disclaimer:
            violations.append(f"pathways {issue}: missing disclaimer")
        for pathway in response.pathways:
            checks += 2
            allowed = {ref.section for ref in pathway.section_refs}
            prose = " ".join(
                [pathway.what_it_is, pathway.when_it_makes_sense, *pathway.pros, *pathway.cons]
            )
            for ref in _SECTION_REF.findall(prose):
                if ref not in allowed:
                    violations.append(
                        f"pathways {issue}/{pathway.pathway_id}: prose cites section {ref} "
                        "outside its reference list"
                    )
            if days_left.search(prose):
                violations.append(
                    f"pathways {issue}/{pathway.pathway_id}: prose computes days left"
                )
        # Caveat visibility, same teeth as the prep pack check: any
        # referenced section whose act carries a non-null caveat must
        # have that caveat text present in the serialized output.
        serialized_pathways = json.dumps(response.to_dict())
        for pathway in response.pathways:
            for ref in pathway.section_refs:
                act_caveat = acts[ref.act_id].get("caveat")
                if act_caveat:
                    checks += 1
                    if act_caveat not in serialized_pathways:
                        violations.append(
                            f"pathways {issue}/{pathway.pathway_id}: caveat of "
                            f"{ref.act_id} s.{ref.section} is dropped from the output"
                        )
        for flag in response.limitation_flags:
            checks += 2
            if flag.section_ref is not None and get_section(flag.section_ref.act_id, flag.section_ref.section) is None:
                violations.append(f"pathways {issue}: limitation flag cites missing section")
            if days_left.search(flag.statement):
                violations.append(f"pathways {issue}: limitation statement computes days left")
            if not flag.caveat:
                violations.append(f"pathways {issue}: limitation flag missing caveat")

    for issue in ("other", "something_unknown"):
        checks += 1
        outputs += 1
        response = explain_pathways(issue)
        if response.status != "no_pathways" or response.pathways or not response.message:
            violations.append(f"pathways {issue}: expected explicit no-pathway state")

    # Phase 5a: prep pack. Every reference resolves to a real built
    # output; checklists and questions cite no section numbers at all
    # (they must not state law); the timeline is a pure passthrough;
    # unmapped issues route out with the disclaimer.
    sample_facts = {
        "timeline": [
            {"order": 1, "event_cue": "pay", "description": "sample event", "span": [0, 12]}
        ]
    }
    for issue in ("cheque", "consumer", "tenancy"):
        outputs += 2
        pack = build_prep_pack(issue, sample_facts)
        rights = explain_rights(issue)
        valid_sections = {(s.act_id, s.section) for s in rights.sections}
        valid_pathways = {p.pathway_id for p in explain_pathways(issue).pathways}
        for ref in pack.rights_refs:
            checks += 1
            if (ref.act_id, ref.section) not in valid_sections or get_section(ref.act_id, ref.section) is None:
                violations.append(f"prep {issue}: rights ref {ref.act_id} s.{ref.section} does not resolve")
        for pref in pack.pathway_refs:
            checks += 1
            if pref.pathway_id not in valid_pathways:
                violations.append(f"prep {issue}: pathway ref {pref.pathway_id} does not resolve")
        # Caveat visibility: if any cited section's act carries a
        # non-null caveat in data/statutes (the MTA model-law warning),
        # that caveat text must be present somewhere in the prep pack
        # output. Searched against the serialized pack so the check is
        # representation-agnostic and fails if the caveat is dropped.
        serialized = json.dumps(pack.to_dict())
        for ref in pack.rights_refs:
            act_caveat = acts[ref.act_id].get("caveat")
            if act_caveat:
                checks += 1
                if act_caveat not in serialized:
                    violations.append(
                        f"prep {issue}: caveat of {ref.act_id} s.{ref.section} "
                        "is dropped from the prep pack output"
                    )
        checks += 4
        if len(pack.caveats) != len(set(pack.caveats)):
            violations.append(f"prep {issue}: duplicate entries in pack caveats")
        static_prose = " ".join([*pack.documents_checklist, *pack.lawyer_questions])
        if _SECTION_REF.findall(static_prose):
            violations.append(f"prep {issue}: checklist or question prose cites a section number")
        if pack.timeline != sample_facts["timeline"]:
            violations.append(f"prep {issue}: timeline is not a pure passthrough")
        if not pack.disclaimer:
            violations.append(f"prep {issue}: missing disclaimer")
        empty = build_prep_pack(issue, None)
        checks += 1
        if empty.timeline or not empty.timeline_note:
            violations.append(f"prep {issue}: missing graceful empty timeline state")

    for issue in ("other", "something_unknown"):
        checks += 1
        outputs += 1
        pack = build_prep_pack(issue)
        if pack.status != "no_prep_pack" or pack.documents_checklist or not pack.message:
            violations.append(f"prep {issue}: expected explicit no-prep-pack state")
        if not pack.disclaimer:
            violations.append(f"prep {issue}: missing disclaimer")

    # Phase 5b: the s.138 demand notice draft.
    # Template lint: no numeric statutory claims (day counts) in the
    # static template; every section number it cites resolves.
    checks += 2
    if re.search(r"\d+\s*days?", TEMPLATE):
        violations.append("notice template states a day count instead of referencing s.138")
    for ref in _SECTION_REF.findall(TEMPLATE):
        if get_section("ni_act_1881", ref) is None:
            violations.append(f"notice template cites unresolvable section {ref}")

    sample_facts = {
        "parties": [
            {"role": "complainant", "kind": "person", "mention": "I", "role_word": None, "name": None},
            {"role": "other_side", "kind": "person", "mention": "A customer", "role_word": "customer", "name": None},
        ],
        "amounts": [{"raw": "Rs 1,20,000", "value": 120000, "currency": "INR", "purpose": "cheque_amount", "span": [30, 41]}],
        "dates": [],
        "timeline": [],
        "slots": {
            "cheque_amount": {"value": 120000, "raw": "Rs 1,20,000", "span": [30, 41], "qualifier": None},
            "drawer": {"value": 1, "raw": "A customer", "span": [2, 12], "qualifier": None},
            "bounce_reason": {"value": "insufficient_funds", "raw": "insufficient funds", "span": [60, 78], "qualifier": None},
            "bounce_dates": [{"value": "2026-07-03", "raw": "the 3rd of this month", "span": [80, 101], "qualifier": "memo"}],
            "cheque_date": {"value": "2026-05-01", "raw": "post dated", "span": [110, 120], "qualifier": None},
            "cheque_number": None,
            "bank": None,
        },
    }
    outputs += 1
    draft = draft_s138_notice(sample_facts)
    draft_violations = verify_draft(draft, sample_facts)
    checks += 8
    violations.extend(f"notice draft: {v}" for v in draft_violations)
    if draft.status != "ok":
        violations.append("notice draft: expected a rendered draft from sample facts")
    if "cheque_number" not in draft.slots_missing:
        violations.append("notice draft: cheque_number should be a missing placeholder")

    # Teeth check, run every time: tamper one marked value with a fact
    # that is NOT in the facts object; the verifier MUST flag it. If it
    # does not, the traceability check has lost its teeth.
    checks += 1
    tampered = dataclasses.replace(
        draft, body_text=draft.body_text.replace("Rs 1,20,000", "Rs 9,99,999")
    )
    if not any("not traceable" in v for v in verify_draft(tampered, sample_facts)):
        violations.append("notice draft: TEETH FAILURE, tampered value not caught")

    # Abstain when no critical fact group is present.
    checks += 1
    outputs += 1
    empty = draft_s138_notice({"parties": [], "amounts": [], "dates": [], "timeline": [], "slots": {}})
    if empty.status != "insufficient_facts" or empty.body_text or not empty.message:
        violations.append("notice draft: expected insufficient_facts abstention")
    violations.extend(f"notice abstain: {v}" for v in verify_draft(empty, {"slots": {}}))

    return checks, violations, outputs


def main() -> None:
    """Run the checks and write results/explain_grounding.md."""
    checks, violations, outputs = check()
    lines = [
        "# Statute explainer grounding check",
        "",
        f"Automated checks run: {checks} across {outputs} explainer outputs.",
        f"Violations: {len(violations)}.",
        "",
    ]
    if violations:
        lines += ["## Violations", ""] + [f"- {v}" for v in violations] + [""]
    lines += [
        "## What these checks cover",
        "",
        "Every cited section exists in data/statutes/; every rendered",
        "verbatim text and source matches the statute file exactly; glosses",
        "reference no section number absent from their quoted text and no",
        "act other than the one cited; unmapped issues return the explicit",
        "no-statute state with the disclaimer.",
        "",
        "## What a human must still verify",
        "",
        "1. Gloss faithfulness: the glosses are static hand-written",
        "   restatements; automation checks their citations, not their",
        "   meaning. Read each gloss beside its section once per change.",
        "2. Curation fidelity: data/statutes/ text is mechanically extracted",
        "   from the official PDFs recorded in each file's source field.",
        "   Spot-check the curated text against those PDFs; known artifacts",
        "   are minor spacing errors inherited from PDF extraction. Known",
        "   source quirk, preserved verbatim per source-fidelity: the India",
        "   Code PDF itself prints \"debt of other liability\" in the s.138",
        "   Explanation (page 28; confirmed in two extraction modes of the",
        "   digitally typeset text layer).",
        "3. The Model Tenancy Act caveat: it is a model law and the user's",
        "   state rent act governs; the caveat field carries this on every",
        "   tenancy citation and must remain user-visible downstream.",
        "4. Pathway accuracy and currency: the pathway descriptions and",
        "   pros/cons are static hand-written procedural prose. Automation",
        "   verifies their citations, the absence of fabricated section",
        "   numbers, and that no deadline is computed; whether the",
        "   procedure described is legally accurate and current needs a",
        "   one-time human review, same as the glosses.",
        "5. Prep pack completeness: the document checklists and lawyer",
        "   question lists are static hand-written prose. Automation",
        "   verifies their references resolve and that they state no law;",
        "   whether they are sensible and reasonably complete for each",
        "   issue area needs the same one-time human review.",
        "6. Notice template quality: the demand notice template is static",
        "   hand-written legal prose. Automation verifies slot",
        "   traceability, marking, placeholders, abstention, and that no",
        "   statutory day count is stated in the template; whether the",
        "   notice wording is legally adequate for sending needs a",
        "   lawyer's review, which the draft warning itself demands.",
    ]
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    report = "\n".join(lines) + "\n"
    (RESULTS_DIR / "explain_grounding.md").write_text(report, encoding="utf-8")
    print(report)


if __name__ == "__main__":
    main()
