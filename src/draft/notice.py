"""Draft s.138 demand notice: fixed template, visibly marked fact injection.

Safety architecture, in order of importance:

1. The template below is static, hand-written legal prose reviewed in
   git. There is no generation path; only named slots are filled.
2. Slots fill ONLY from the Phase 2 facts object, using the verbatim
   raw text of the extracted fact (never the inferred ISO form of an
   approximate date, never a reformatted number).
3. Every injected fact is visibly marked with the FROM YOUR COMPLAINT
   convention so it cannot melt into official-looking prose; every
   missing fact renders as a NOT FOUND placeholder the user must
   complete. The draft is honestly incomplete, never silently wrong.
4. The statutory payment window is referenced to the curated Section
   138 text accompanying the draft; the template deliberately contains
   no day counts or other numeric statutory claims of its own.
5. If none of the critical facts (drawer, amount, cheque identity) are
   present, no draft is produced at all.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Callable

from src.explain.explain import DISCLAIMER
from src.explain.pathways import SectionRef
from src.explain.statutes import get_section

DOC_TYPE = "s138_demand_notice"

FILLED_OPEN = "[FROM YOUR COMPLAINT: "
FILLED_CLOSE = " (verify)]"
MISSING_OPEN = "[NOT FOUND IN YOUR COMPLAINT: "
MISSING_CLOSE = "]"

DRAFT_WARNING = (
    "DRAFT ONLY. Review this document with a lawyer before sending or "
    "filing anything; it is not a finished notice and must not be sent "
    "as-is. Every value marked FROM YOUR COMPLAINT was automatically "
    "extracted from your own description and is unverified; every value "
    "marked NOT FOUND is missing and must be filled in. Verify all "
    "names, dates, amounts, and addresses against your documents."
)

INSUFFICIENT_FACTS_MESSAGE = (
    "There is not enough reliable information in your complaint to draft "
    "this notice safely: none of the critical facts (who wrote the "
    "cheque, the amount, and the cheque's date or number) could be "
    "extracted. A draft made only of blanks would not help you. Please "
    "take your documents to a qualified advocate, or approach your "
    "District Legal Services Authority (DLSA) or NALSA for free legal "
    "aid."
)

TEMPLATE = """DRAFT DEMAND NOTICE (DISHONOUR OF CHEQUE)

{draft_warning}

To: {drawer_name}
Address: {drawer_address}

From: {sender_name}
Address: {sender_address}

Subject: Demand notice for dishonour of cheque number {cheque_number} dated {cheque_date} for {amount}

Sir or Madam,

1. You issued a cheque bearing number {cheque_number}, dated {cheque_date}, for {amount}, drawn on {bank}, in favour of the undersigned, towards discharge of {debt_description}.

2. On presentation, the said cheque was returned unpaid, with the return recorded on {return_date}, and with the reason stated as {bounce_reason}.

3. The undersigned therefore calls upon you to pay the said amount within the period provided under Section 138 of the Negotiable Instruments Act, 1881, the text of which accompanies this draft, failing which the undersigned will be constrained to initiate proceedings under the said Act, entirely at your risk as to costs and consequences.

Place: {sender_place}
Date: {notice_date}

Signature: ________________________
{sender_name_sign}
"""

# Slot -> instruction shown inside the NOT FOUND placeholder.
SLOT_INSTRUCTIONS: dict[str, str] = {
    "drawer_name": "full name of the person or firm that wrote the cheque",
    "drawer_address": "current address of the cheque writer",
    "sender_name": "your full name",
    "sender_address": "your address",
    "cheque_number": "the cheque number, from the cheque or return memo",
    "cheque_date": "the date written on the cheque",
    "amount": "the cheque amount",
    "bank": "the bank and branch the cheque was drawn on",
    "debt_description": "what the cheque was payment for (goods, services, loan)",
    "return_date": "the date the bank returned the cheque, from the return memo",
    "bounce_reason": "the reason on the bank return memo",
    "sender_place": "the place of signing",
    "notice_date": "the date you send this notice",
    "sender_name_sign": "your full name, repeated under the signature",
}

CRITICAL_GROUPS: tuple[tuple[str, ...], ...] = (
    ("drawer_name",),
    ("amount",),
    ("cheque_number", "cheque_date"),
)


@dataclass(frozen=True)
class DraftDocument:
    """A rendered draft with full slot provenance."""

    status: str  # ok | insufficient_facts
    doc_type: str = DOC_TYPE
    title: str = "Draft demand notice (cheque dishonour)"
    body_text: str = ""
    slots_filled: dict[str, dict] = field(default_factory=dict)
    slots_missing: list[str] = field(default_factory=list)
    section_refs: list[SectionRef] = field(default_factory=list)
    caveats: list[str] = field(default_factory=list)
    message: str | None = None
    draft_warning: str = DRAFT_WARNING
    disclaimer: str = DISCLAIMER

    def to_dict(self) -> dict:
        return asdict(self)


def _slot_value(facts: dict, name: str) -> str | None:
    """Verbatim raw text of a Phase 2 slot, or None."""
    slot = facts.get("slots", {}).get(name)
    if isinstance(slot, dict) and slot.get("raw"):
        return str(slot["raw"])
    return None


def _drawer_display(facts: dict) -> str | None:
    """Drawer's name if extracted, else the verbatim mention."""
    slot = facts.get("slots", {}).get("drawer")
    if not isinstance(slot, dict) or not isinstance(slot.get("value"), int):
        return None
    parties = facts.get("parties", [])
    index = slot["value"]
    if not 0 <= index < len(parties):
        return None
    party = parties[index]
    return party.get("name") or party.get("mention")


def _first_bounce_raw(facts: dict) -> str | None:
    """Verbatim raw text of the first recorded bounce date, if any."""
    entries = facts.get("slots", {}).get("bounce_dates")
    if isinstance(entries, list) and entries and entries[0].get("raw"):
        return str(entries[0]["raw"])
    return None


_EXTRACTORS: dict[str, Callable[[dict], str | None]] = {
    "drawer_name": _drawer_display,
    "amount": lambda f: _slot_value(f, "cheque_amount"),
    "cheque_number": lambda f: _slot_value(f, "cheque_number"),
    "cheque_date": lambda f: _slot_value(f, "cheque_date"),
    "bank": lambda f: _slot_value(f, "bank"),
    "return_date": _first_bounce_raw,
    "bounce_reason": lambda f: _slot_value(f, "bounce_reason"),
}


def draft_s138_notice(facts: dict) -> DraftDocument:
    """Render the s.138 demand notice draft from a Phase 2 facts object.

    Extracted facts fill their slots verbatim inside the FROM YOUR
    COMPLAINT marker; everything else renders as a NOT FOUND placeholder.
    Abstains entirely when no critical fact group is filled.
    """
    filled: dict[str, dict] = {}
    missing: list[str] = []
    rendered: dict[str, str] = {"draft_warning": DRAFT_WARNING}
    for slot, instruction in SLOT_INSTRUCTIONS.items():
        extractor = _EXTRACTORS.get(slot)
        value = extractor(facts) if extractor else None
        if slot == "sender_name_sign":
            value = None  # always the user's to complete alongside the signature
        if value:
            filled[slot] = {"display": value, "source": f"facts:{slot}"}
            rendered[slot] = f"{FILLED_OPEN}{value}{FILLED_CLOSE}"
        else:
            missing.append(slot)
            rendered[slot] = f"{MISSING_OPEN}{instruction}{MISSING_CLOSE}"

    any_critical = any(
        any(slot in filled for slot in group) for group in CRITICAL_GROUPS
    )
    if not any_critical:
        return DraftDocument(status="insufficient_facts", message=INSUFFICIENT_FACTS_MESSAGE)

    record = get_section("ni_act_1881", "138")
    assert record is not None
    ref = SectionRef(act_id="ni_act_1881", section="138", act=record["act"], title=record["title"])
    caveats = [record["caveat"]] if record["caveat"] else []
    return DraftDocument(
        status="ok",
        body_text=TEMPLATE.format(**rendered),
        slots_filled=filled,
        slots_missing=missing,
        section_refs=[ref],
        caveats=caveats,
    )
