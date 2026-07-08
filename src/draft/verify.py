"""Safety verification for rendered drafts.

verify_draft is the machine-checkable half of the fact-injection safety
rules: every marked value must trace to a string actually present in
the input facts object, no facts-derived string may appear outside a
marker (the melt check), every missing slot must render its placeholder,
and both disclaimers must be present. The grounding runner additionally
proves these checks have teeth by tampering a draft and requiring a
violation.
"""

from __future__ import annotations

import re

from src.draft.notice import (
    DRAFT_WARNING,
    FILLED_CLOSE,
    FILLED_OPEN,
    MISSING_CLOSE,
    MISSING_OPEN,
    SLOT_INSTRUCTIONS,
    DraftDocument,
)

_FILLED_RE = re.compile(
    re.escape(FILLED_OPEN) + r"(.+?)" + re.escape(FILLED_CLOSE), re.DOTALL
)
_MIN_MELT_LENGTH = 4


def collect_fact_strings(facts: dict) -> set[str]:
    """Every verbatim string a draft could legitimately have taken from
    the facts object: party mentions and names, raw amounts, raw dates,
    and slot raw values including tagged bounce entries."""
    strings: set[str] = set()
    for party in facts.get("parties", []):
        for key in ("mention", "name"):
            if party.get(key):
                strings.add(str(party[key]))
    for amount in facts.get("amounts", []):
        if amount.get("raw"):
            strings.add(str(amount["raw"]))
    for date in facts.get("dates", []):
        if date.get("raw"):
            strings.add(str(date["raw"]))
    for slot in facts.get("slots", {}).values():
        if isinstance(slot, dict) and slot.get("raw"):
            strings.add(str(slot["raw"]))
        elif isinstance(slot, list):
            for entry in slot:
                if isinstance(entry, dict) and entry.get("raw"):
                    strings.add(str(entry["raw"]))
    return strings


def _marker_spans(body: str) -> list[tuple[int, int]]:
    """Character spans of every marker (filled or missing) in the body."""
    spans: list[tuple[int, int]] = []
    for open_mark, close_mark in ((FILLED_OPEN, FILLED_CLOSE), (MISSING_OPEN, MISSING_CLOSE)):
        pattern = re.compile(re.escape(open_mark) + r".+?" + re.escape(close_mark), re.DOTALL)
        spans.extend(m.span() for m in pattern.finditer(body))
    return spans


def verify_draft(draft: DraftDocument, facts: dict) -> list[str]:
    """Return violations of the fact-injection safety rules (empty = clean)."""
    violations: list[str] = []
    if draft.status == "insufficient_facts":
        if draft.body_text:
            violations.append("abstained draft still carries body text")
        if not draft.message:
            violations.append("abstained draft missing the routing message")
        return violations

    body = draft.body_text
    fact_strings = collect_fact_strings(facts)

    # 1. Traceability: every marked value must be a string from the facts.
    for match in _FILLED_RE.finditer(body):
        value = match.group(1)
        if value not in fact_strings:
            violations.append(f"marked value not traceable to facts: {value!r}")

    # 2. Melt check: no facts string may appear outside a marker.
    spans = _marker_spans(body)
    for value in fact_strings:
        if len(value) < _MIN_MELT_LENGTH:
            continue
        for m in re.finditer(re.escape(value), body):
            inside = any(s <= m.start() and m.end() <= e for s, e in spans)
            if not inside:
                violations.append(f"facts string appears unmarked in draft: {value!r}")
                break

    # 3. Every missing slot renders its placeholder.
    for slot in draft.slots_missing:
        placeholder = f"{MISSING_OPEN}{SLOT_INSTRUCTIONS[slot]}{MISSING_CLOSE}"
        if placeholder not in body:
            violations.append(f"missing slot {slot} has no visible placeholder")

    # 4. Both disclaimers, prominently.
    if DRAFT_WARNING not in body or draft.draft_warning != DRAFT_WARNING:
        violations.append("draft warning header absent or altered")
    if not draft.disclaimer:
        violations.append("standard disclaimer missing")

    # 5. Filled slots recorded in provenance must all appear marked.
    marked_values = {m.group(1) for m in _FILLED_RE.finditer(body)}
    for slot, info in draft.slots_filled.items():
        if info["display"] not in marked_values:
            violations.append(f"filled slot {slot} not rendered inside a marker")
    return violations
