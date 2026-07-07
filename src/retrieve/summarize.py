"""Extractive, grounded summaries of retrieved judgments.

No LLM anywhere: every summary component is either the dataset's outcome
label, sentences quoted verbatim from the judgment, or PredEx's
expert-annotated pivotal sentences. Each component carries its source
tag so traceability is checkable by construction.

Outcome phrasing rule: outcomes are stated as "the appeal was granted /
denied", never flattened to "the complainant won/lost". The appellant is
named only when determinable from the judgment text itself.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+")

WEAK_CAUTION = (
    "Weak match: this case is only loosely similar to your situation. "
    "Treat it with caution; it may involve a different fact pattern."
)

ABSTAIN_MESSAGE = (
    "Nothing sufficiently similar was retrieved from the case corpus for "
    "your situation. That does not mean your problem has no legal remedy; "
    "it means this tool could not find comparable appellate judgments to "
    "show you. Please consult a qualified advocate, or approach your "
    "District Legal Services Authority (DLSA) or NALSA for free legal aid."
)


@dataclass(frozen=True)
class SummaryPart:
    """One summary component with its provenance."""

    text: str
    source: str  # dataset_label | judgment_text | expert_annotation


def first_party(case_name: str) -> str | None:
    """The first-named party from a case caption, if parseable."""
    m = re.split(r"\s+vs?\.?\s+", case_name, maxsplit=1, flags=re.IGNORECASE)
    if len(m) == 2 and m[0].strip():
        return m[0].strip().title()
    return None


def appellant_if_determinable(case_name: str, judgment_text: str) -> str | None:
    """Name the appellant only if the judgment text itself supports it.

    Heuristic: the first-named party's lead word appears within 120
    characters of the word appellant/petitioner in the judgment.
    """
    party = first_party(case_name)
    if party is None:
        return None
    lead = party.split()[0].lower()
    if len(lead) < 4:
        return None
    for m in re.finditer(r"appellant|petitioner", judgment_text[:4000], re.IGNORECASE):
        window = judgment_text[max(0, m.start() - 120) : m.end() + 120].lower()
        if lead in window:
            return party
    return None


def outcome_part(label: int, case_name: str, judgment_text: str) -> SummaryPart:
    """Outcome sentence from the dataset label, appeal-framed."""
    verdict = "granted" if int(label) == 1 else "denied"
    appellant = appellant_if_determinable(case_name, judgment_text)
    if appellant:
        text = f"The appeal, brought by {appellant}, was {verdict} by the Supreme Court."
    else:
        text = f"The appeal was {verdict} by the Supreme Court."
    return SummaryPart(text=text, source="dataset_label")


def dispute_part(matched_chunk: str, max_sentences: int = 2) -> SummaryPart:
    """The opening sentences of the best-matching passage, verbatim."""
    sentences = _SENT_SPLIT.split(matched_chunk.strip())
    quoted = " ".join(sentences[:max_sentences]).strip()
    return SummaryPart(text=quoted, source="judgment_text")


def pivotal_part(expert_explanation: str, max_sentences: int = 2) -> SummaryPart | None:
    """Expert-annotated pivotal sentences, verbatim, when present."""
    if not expert_explanation or not expert_explanation.strip():
        return None
    sentences = _SENT_SPLIT.split(expert_explanation.strip())
    quoted = " ".join(sentences[:max_sentences]).strip()
    if not quoted:
        return None
    return SummaryPart(text=quoted, source="expert_annotation")


def build_summary(
    label: int, case_name: str, judgment_text: str, matched_chunk: str, expert_explanation: str
) -> list[SummaryPart]:
    """Assemble the grounded summary: outcome, dispute, pivotal sentences."""
    parts = [
        outcome_part(label, case_name, judgment_text),
        dispute_part(matched_chunk),
    ]
    pivotal = pivotal_part(expert_explanation)
    if pivotal is not None:
        parts.append(pivotal)
    return parts
