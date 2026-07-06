"""Orchestrator: extract_facts(complaint, issue_type, anchor_date).

Combines the rule extractors (primary for amounts, dates, party roles)
with spaCy NER supplements (DATE, GPE, ORG, PERSON), assembles the
timeline, fills issue-conditioned slots, and reports everything that
could not be resolved. Fully deterministic; no generation anywhere.
"""

from __future__ import annotations

import datetime as dt

from src.extract.amounts import extract_amounts
from src.extract.dates import extract_dates
from src.extract.gazetteer import is_hinglish_noise
from src.extract.ner import analyze, extract_places
from src.extract.parties import extract_parties
from src.extract.schema import (
    ISSUE_SLOTS,
    FactsDocument,
    Meta,
    Unresolved,
)
from src.extract.slots import fill_cheque_slots, fill_consumer_slots, fill_tenancy_slots
from src.extract.timeline import build_timeline
from src.intake.data import normalize_text

_SLOT_FILLERS = {
    "cheque": fill_cheque_slots,
    "consumer": fill_consumer_slots,
    "tenancy": fill_tenancy_slots,
}

_MISSING_REASONS = {
    "notice_date": "notice not mentioned or not dated",
    "notice_served_date": "notice receipt not mentioned",
    "complainant_side": "signals absent or conflicting",
}


def extract_facts(
    complaint: str,
    issue_type: str,
    anchor_date: dt.date | str | None = None,
) -> FactsDocument:
    """Extract the structured facts object for one complaint.

    issue_type comes from the Phase 1 classifier (consumer, cheque,
    tenancy, or other) and selects which slots are attempted. anchor_date
    (date, ISO string, or None for today) anchors relative-date
    resolution.
    """
    if issue_type not in ISSUE_SLOTS:
        raise ValueError(f"unknown issue_type: {issue_type!r}")
    if anchor_date is None:
        anchor = dt.date.today()
    elif isinstance(anchor_date, str):
        anchor = dt.date.fromisoformat(anchor_date)
    else:
        anchor = anchor_date

    text = normalize_text(complaint)
    doc = analyze(text)

    amounts = extract_amounts(text)
    dates, date_fragments = extract_dates(text, anchor)
    places = extract_places(text, doc)
    parties = extract_parties(text, doc)
    timeline = build_timeline(doc, dates, amounts)

    unresolved: list[Unresolved] = [
        Unresolved(kind="fragment", raw=frag, reason="date fragment not resolvable")
        for frag in date_fragments
    ]

    # spaCy DATE spans the rules did not claim become explicit fragments,
    # so nothing silently disappears.
    claimed = [(d.span[0], d.span[1]) for d in dates]
    for ent in doc.ents:
        if ent.label_ != "DATE" or is_hinglish_noise(ent.text):
            continue
        if not any(s < ent.end_char and ent.start_char < e for s, e in claimed):
            unresolved.append(
                Unresolved(
                    kind="fragment",
                    raw=ent.text,
                    reason="date-like span not resolvable to a calendar date",
                )
            )

    filler = _SLOT_FILLERS.get(issue_type)
    slots: dict = {}
    if filler is not None:
        slots = filler(text, doc, parties, amounts, dates)
        for name in ISSUE_SLOTS[issue_type]:
            if slots.get(name) is None:
                reason = _MISSING_REASONS.get(name, "not mentioned in complaint")
                unresolved.append(Unresolved(kind="slot", field=name, reason=reason))

    return FactsDocument(
        meta=Meta(
            issue_type=issue_type,
            anchor_date=anchor.isoformat(),
            complaint_text=text,
        ),
        parties=parties,
        amounts=amounts,
        dates=dates,
        places=places,
        timeline=timeline,
        slots=slots,
        unresolved=unresolved,
    )
