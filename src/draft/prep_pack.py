"""Prep pack: compose existing outputs into a lawyer-visit preparation
object.

Same discipline as the explainers: no generation path. Document
checklists and lawyer-question lists are static, hand-written prose
reviewed in git, with no extracted facts injected and no law restated.
The fact timeline is the Phase 2 chronology shown back as-is (user
data, not generated), omitted gracefully when absent. Rights, pathways,
and limitation all come from the already-built 4a/4b outputs by
reference; nothing legal is rebuilt here.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

from src.explain.explain import DISCLAIMER, explain_rights
from src.explain.pathways import LimitationFlag, SectionRef, explain_pathways

NO_PREP_PACK_MESSAGE = (
    "No prep pack is available for this issue from the covered issue "
    "areas. The best preparation is still the same: gather every document "
    "connected to your problem, write down what happened in date order, "
    "and consult a qualified advocate, or approach your District Legal "
    "Services Authority (DLSA) or NALSA for free legal aid."
)

NO_TIMELINE_NOTE = (
    "No structured timeline is available for this complaint. Writing down "
    "what happened in date order before the consultation saves paid time."
)


@dataclass(frozen=True)
class PathwayRef:
    """Pointer to a 4b pathway by id and display name."""

    pathway_id: str
    name: str


@dataclass(frozen=True)
class PrepPack:
    """Everything a user should bring to and ask in the first consultation."""

    status: str  # ok | no_prep_pack
    issue_type: str
    documents_checklist: list[str] = field(default_factory=list)
    lawyer_questions: list[str] = field(default_factory=list)
    timeline: list[dict] = field(default_factory=list)
    timeline_note: str | None = None
    rights_refs: list[SectionRef] = field(default_factory=list)
    pathway_refs: list[PathwayRef] = field(default_factory=list)
    limitation_flags: list[LimitationFlag] = field(default_factory=list)
    # Act-level caveats from cited sections (for example the Model
    # Tenancy Act model-law warning), deduplicated, order-preserving.
    # Pack-level rather than per-ref so renderers cannot drop it with a
    # compact reference display.
    caveats: list[str] = field(default_factory=list)
    message: str | None = None
    disclaimer: str = DISCLAIMER

    def to_dict(self) -> dict:
        return asdict(self)


_DOCUMENTS: dict[str, tuple[str, ...]] = {
    "cheque": (
        "The original bounced cheque",
        "The bank's return memo or cheque return advice",
        "Proof of the underlying debt or transaction: invoice, agreement, "
        "delivery challan, or loan record",
        "The written demand notice you sent, with proof of dispatch and "
        "delivery (courier slip, tracking record, acknowledgment)",
        "Your bank statement showing when the cheque was presented",
        "Any reply or communication from the cheque writer, including "
        "messages admitting the debt or promising payment",
        "The cheque writer's full name and current address",
    ),
    "consumer": (
        "Purchase invoice, receipt, or booking confirmation",
        "Payment proof: card statement, UPI record, or cash receipt",
        "Warranty or guarantee card, if any",
        "Photos or video of the defect or deficiency",
        "Service records, complaint ticket numbers, and technician visit notes",
        "All correspondence with the seller or service provider",
        "Delivery documents or installation reports",
        "The written complaint you sent the business, with proof of delivery",
    ),
    "tenancy": (
        "The rent or tenancy agreement; if there is none in writing, "
        "whatever shows the arrangement (messages, receipts)",
        "Rent payment records: transfers, receipts, or a rent ledger",
        "Proof of the security deposit payment",
        "Move-in and move-out photos or inspection notes, if any",
        "All correspondence with the other side",
        "Utility bills or society records connecting you to the premises",
        "The written notice or demand you sent, with proof of delivery",
        "Names and contacts of any witnesses (neighbours, broker)",
    ),
}

_QUESTIONS: dict[str, tuple[str, ...]] = {
    "cheque": (
        "Looking at my dates, am I within the statutory windows, and "
        "which dates control my case?",
        "Criminal complaint, civil recovery, or both: which fits my "
        "facts, and in what order?",
        "What will this realistically cost and how long will it take?",
        "What evidence am I missing that I should secure now?",
        "Is a settlement worth exploring, and at what amount would you "
        "advise accepting?",
        "What happens if the cheque writer has no money or the company "
        "shuts down?",
    ),
    "consumer": (
        "Do I qualify as a consumer for this purchase, given how I "
        "bought and used it?",
        "Which level of consumer commission applies at the current "
        "monetary limits, and where would we file?",
        "What remedy is realistic here: refund, replacement, or "
        "compensation, and roughly how much?",
        "Am I within the limitation period, and from when does my clock "
        "run?",
        "What are the filing fee and the realistic timeline?",
        "Should we send one more formal notice first, or file now?",
    ),
    "tenancy": (
        "Which law applies in my state, and which forum should hear my "
        "dispute?",
        "Is my documentation enough to prove the tenancy and the "
        "deposit, and what would strengthen it?",
        "What would the forum route realistically cost and take, "
        "compared with negotiating?",
        "If I fear being locked out or dispossessed, what interim "
        "protection can we seek immediately?",
        "Until this resolves, what should I keep doing or stop doing "
        "about rent payments and communication?",
    ),
}


def build_prep_pack(issue_type: str, facts: dict | None = None) -> PrepPack:
    """Compose the prep pack for a classified issue.

    facts is the Phase 2 facts dict; only its timeline is used, shown
    back as-is. Checklists and questions are static per issue area.
    Rights, pathways, and limitation flags are pulled by reference from
    the 4a/4b explainers.
    """
    documents = _DOCUMENTS.get(issue_type)
    if documents is None:
        return PrepPack(
            status="no_prep_pack", issue_type=issue_type, message=NO_PREP_PACK_MESSAGE
        )

    rights = explain_rights(issue_type, facts)
    pathways = explain_pathways(issue_type, facts)
    timeline = list(facts.get("timeline", [])) if facts else []
    caveats: list[str] = []
    for caveat in [s.caveat for s in rights.sections] + list(pathways.caveats):
        if caveat and caveat not in caveats:
            caveats.append(caveat)
    return PrepPack(
        status="ok",
        issue_type=issue_type,
        documents_checklist=list(documents),
        lawyer_questions=list(_QUESTIONS[issue_type]),
        timeline=timeline,
        timeline_note=None if timeline else NO_TIMELINE_NOTE,
        rights_refs=[
            SectionRef(act_id=s.act_id, section=s.section, act=s.act, title=s.title)
            for s in rights.sections
        ],
        pathway_refs=[PathwayRef(pathway_id=p.pathway_id, name=p.name) for p in pathways.pathways],
        limitation_flags=list(pathways.limitation_flags),
        caveats=caveats,
    )
