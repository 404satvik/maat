"""Rights and applicable-law explainer, grounded in the curated bare acts.

Grounding discipline, same standard as the case summaries: every cited
section is retrieved from data/statutes/ and rendered verbatim; the
plain-language glosses below are static, hand-written restatements of
their quoted section and nothing else, reviewed in git rather than
generated at runtime. There is no generation path in this module. If no
section maps to the issue, the output is an explicit no-statute state
routing to a lawyer or legal aid, never a fabricated section.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

from src.explain.statutes import get_section

DISCLAIMER = (
    "This is legal information, not legal advice. It does not predict any "
    "outcome and is not a substitute for a lawyer. Please consult a "
    "qualified advocate."
)

NO_STATUTE_MESSAGE = (
    "No applicable statute was retrieved from the bundled statute set for "
    "this issue. That does not mean no law applies to your situation; it "
    "means this tool does not have a curated act to show you. Please "
    "consult a qualified advocate, or approach your District Legal "
    "Services Authority (DLSA) or NALSA for free legal aid."
)

# Issue area -> ordered (act_id, section) citations. The mapping is the
# primary retrieval mechanism; keyword lookup in statutes.py is secondary.
ISSUE_SECTIONS: dict[str, tuple[tuple[str, str], ...]] = {
    "cheque": (("ni_act_1881", "138"), ("ni_act_1881", "139"), ("ni_act_1881", "142")),
    "consumer": (("cpa_2019", "2(7)"), ("cpa_2019", "2(11)"), ("cpa_2019", "35"), ("cpa_2019", "69")),
    "tenancy": (("mta_2021", "11"), ("mta_2021", "9"), ("mta_2021", "21")),
    "other": (),
}

# Tenancy dispute_object -> which sections matter most, in order.
_TENANCY_PRIORITY: dict[str, tuple[tuple[str, str], ...]] = {
    "deposit_refund": (("mta_2021", "11"), ("mta_2021", "21")),
    "rent_increase": (("mta_2021", "9"), ("mta_2021", "21")),
    "eviction": (("mta_2021", "21"), ("mta_2021", "11")),
    "harassment": (("mta_2021", "21"), ("mta_2021", "11")),
}

# Hand-written plain-language glosses. Each gloss restates ONLY the
# section quoted alongside it; any section number it mentions must be
# the cited section itself or a number appearing inside the quoted
# text. The grounding check in run_grounding.py enforces both rules.
GLOSSES: dict[tuple[str, str], str] = {
    ("ni_act_1881", "138"): (
        "Under the section quoted above, a bounced cheque can be a criminal "
        "offence. It applies when a cheque given for a debt or other "
        "liability comes back unpaid because the account had insufficient "
        "funds or the amount exceeded what the bank had agreed to pay. The "
        "section sets three conditions: the cheque must have been presented "
        "within six months of its date or within its validity period, "
        "whichever is earlier; the person who received the cheque must "
        "demand payment by a written notice to the person who wrote it, "
        "within thirty days of learning from the bank that it was returned "
        "unpaid; and the writer of the cheque must have failed to pay "
        "within fifteen days of receiving that notice. The punishment the "
        "section provides is imprisonment up to two years, or a fine up to "
        "twice the cheque amount, or both."
    ),
    ("ni_act_1881", "139"): (
        "The section quoted above says the law presumes, unless the "
        "contrary is proved, that a cheque you hold was received for the "
        "discharge of a debt or other liability. The burden of proving "
        "otherwise lies on the other side."
    ),
    ("ni_act_1881", "142"): (
        "The section quoted above governs who can complain and where. Only "
        "the payee or holder in due course of the cheque can file the "
        "complaint, it must be in writing, and it must be made within one "
        "month of the cause of action arising under section 138, though a "
        "court may accept a later complaint if you show sufficient cause "
        "for the delay. It also fixes the court: no court below a "
        "Metropolitan Magistrate or Judicial Magistrate of the first "
        "class, in the place connected to the bank branch the section "
        "describes."
    ),
    ("cpa_2019", "2(7)"): (
        "Under the definition quoted above, you count as a consumer if you "
        "bought goods or hired or availed a service for a consideration, "
        "paid or promised, including online transactions. The definition "
        "excludes anyone who obtained the goods or service for resale or a "
        "commercial purpose, but its own explanation says goods bought "
        "exclusively for earning your livelihood through self-employment "
        "do not count as a commercial purpose."
    ),
    ("cpa_2019", "2(11)"): (
        "The definition quoted above describes what counts as a deficiency "
        "in service: any fault, imperfection, shortcoming or inadequacy in "
        "the quality, nature or manner of performance that the law or a "
        "contract requires, including negligence causing loss or injury "
        "and the deliberate withholding of relevant information from the "
        "consumer."
    ),
    ("cpa_2019", "35"): (
        "The section quoted above says who can file a consumer complaint "
        "with a District Commission: the consumer themselves, a recognised "
        "consumer association even if the consumer is not a member, or a "
        "group of consumers with the same interest with the Commission's "
        "permission. It also says the complaint may be filed "
        "electronically, with the prescribed fee."
    ),
    ("cpa_2019", "69"): (
        "The section quoted above sets the time limit: a consumer "
        "complaint must be filed within two years from the date the cause "
        "of action arises. A later complaint can be admitted only if the "
        "Commission is satisfied there was sufficient cause for the delay "
        "and records its reasons for condoning it."
    ),
    ("mta_2021", "11"): (
        "Under the model provision quoted above, a security deposit for "
        "residential premises cannot exceed two months' rent (six months "
        "for non-residential premises), and it must be refunded to the "
        "tenant on the date the landlord takes back vacant possession, "
        "after deducting any liability of the tenant."
    ),
    ("mta_2021", "9"): (
        "The model provision quoted above says rent revision must follow "
        "the terms of the tenancy agreement. It allows a rent increase for "
        "improvements, additions or structural alterations only where the "
        "landlord agreed the work with the tenant in writing beforehand, "
        "and the increase takes effect one month after the work is "
        "completed."
    ),
    ("mta_2021", "21"): (
        "Under the model provision quoted above, a tenant cannot be "
        "evicted while the tenancy agreement runs except by written "
        "agreement or on the grounds the provision lists, on the "
        "landlord's application to the Rent Court: refusal to pay the "
        "agreed rent, arrears of two consecutive months not cleared within "
        "one month of a demand notice, parting with possession without the "
        "landlord's written consent, continued misuse of the premises "
        "after notice, or specified repair, rebuilding or land-use "
        "situations. It also says no eviction order for arrears shall be "
        "made if the tenant pays or deposits the arrears with interest "
        "within one month of the demand notice, a relief the tenant "
        "cannot claim again after failing to pay for two consecutive "
        "months in the same year."
    ),
}


@dataclass(frozen=True)
class SectionExplanation:
    """One cited section: verbatim text, source, and its static gloss."""

    act_id: str
    act: str
    section: str
    title: str
    verbatim_text: str
    source: dict
    gloss: str
    caveat: str | None = None


@dataclass(frozen=True)
class RightsExplanation:
    """Explainer output: cited sections or an explicit no-statute state."""

    status: str  # ok | no_statute
    issue_type: str
    sections: list[SectionExplanation] = field(default_factory=list)
    message: str | None = None
    disclaimer: str = DISCLAIMER

    def to_dict(self) -> dict:
        return asdict(self)


def _citations_for(issue_type: str, facts: dict | None) -> tuple[tuple[str, str], ...]:
    """Pick the citation list, letting tenancy facts reorder by dispute."""
    if issue_type == "tenancy" and facts is not None:
        slot = facts.get("slots", {}).get("dispute_object")
        if isinstance(slot, dict) and slot.get("value") in _TENANCY_PRIORITY:
            return _TENANCY_PRIORITY[slot["value"]]
    return ISSUE_SECTIONS.get(issue_type, ())


def explain_rights(issue_type: str, facts: dict | None = None) -> RightsExplanation:
    """Explain the law applicable to a classified issue, grounded in the
    curated statute set.

    issue_type comes from the Phase 1 classifier; facts (Phase 2 output)
    optionally reorders tenancy sections by dispute object. Unknown or
    unmapped issues return the explicit no-statute state.
    """
    citations = _citations_for(issue_type, facts)
    sections: list[SectionExplanation] = []
    for act_id, number in citations:
        record = get_section(act_id, number)
        if record is None:
            continue
        sections.append(
            SectionExplanation(
                act_id=act_id,
                act=record["act"],
                section=number,
                title=record["title"],
                verbatim_text=record["text"],
                source=record["source"],
                gloss=GLOSSES[(act_id, number)],
                caveat=record["caveat"],
            )
        )
    if not sections:
        return RightsExplanation(
            status="no_statute", issue_type=issue_type, message=NO_STATUTE_MESSAGE
        )
    return RightsExplanation(status="ok", issue_type=issue_type, sections=sections)
