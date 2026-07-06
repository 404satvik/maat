"""Facts schema: the contract between extraction and later phases.

Every extracted item carries a span [start, end] into the normalized
complaint text stored in Meta. Slots that cannot be filled from the text
are None and appear in unresolved; nothing is ever invented.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

Span = list[int]

ISSUE_SLOTS: dict[str, tuple[str, ...]] = {
    "cheque": (
        "cheque_amount",
        "cheque_date",
        "bounce_dates",
        "bounce_reason",
        "drawer",
        "payee",
        "complainant_side",
        "notice_date",
        "notice_served_date",
        "cheque_number",
        "bank",
    ),
    "consumer": (
        "purchase_date",
        "item_or_service",
        "amount_paid",
        "seller",
        "defect_or_deficiency",
        "remedy_sought",
    ),
    "tenancy": (
        "monthly_rent",
        "deposit_amount",
        "agreement_start",
        "agreement_end_or_duration",
        "notice_given_date",
        "vacated_date",
        "landlord",
        "tenant",
        "complainant_side",
        "dispute_object",
    ),
    "other": (),
}

BOUNCE_REASONS: tuple[str, ...] = (
    "insufficient_funds",
    "stop_payment",
    "account_closed",
    "signature_mismatch",
    "exceeds_arrangement",
    "other",
)


@dataclass
class Meta:
    issue_type: str
    anchor_date: str
    complaint_text: str
    extractor_version: str = "0.1"


@dataclass
class Party:
    role: str  # complainant | other_side | third_party
    kind: str  # person | organization | unknown
    mention: str
    role_word: str | None
    name: str | None
    spans: list[Span]


@dataclass
class Amount:
    raw: str
    value: int
    currency: str
    purpose: str
    span: Span


@dataclass
class DateMention:
    raw: str
    iso: str | None
    approximate: bool
    resolution: str  # explicit | relative_to_anchor | partial | unresolved
    span: Span
    date_range: list[str] | None = None  # [earliest, latest] ISO for approximate dates


@dataclass
class Place:
    raw: str
    normalized: str
    validated_indian_place: bool
    span: Span


@dataclass
class TimelineEvent:
    order: int
    event_cue: str
    description: str  # the source sentence verbatim, never generated
    date_index: int | None
    amount_indices: list[int]
    date_basis: str  # resolved | narrative
    span: Span


@dataclass
class SlotValue:
    value: Any  # int, str, ISO date string, or index into parties
    raw: str
    span: Span
    qualifier: str | None = None  # e.g. date_kind for bounce_dates entries


@dataclass
class Unresolved:
    kind: str  # slot | fragment
    reason: str
    field: str | None = None
    raw: str | None = None


@dataclass
class FactsDocument:
    """The full facts object later phases consume."""

    meta: Meta
    parties: list[Party] = field(default_factory=list)
    amounts: list[Amount] = field(default_factory=list)
    dates: list[DateMention] = field(default_factory=list)
    places: list[Place] = field(default_factory=list)
    timeline: list[TimelineEvent] = field(default_factory=list)
    slots: dict[str, Any] = field(default_factory=dict)
    unresolved: list[Unresolved] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Serialize to plain JSON-compatible dicts."""
        return asdict(self)
