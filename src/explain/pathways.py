"""Options and pathways per issue area, grounded by reference.

Same discipline as the 4a explainer: no generation path. Every pathway
description is static, hand-written, and reviewed in git. Where a
pathway involves a statutory fact curated in 4a (who can file, forum,
limitation), it carries a section_refs pointer to the curated section
instead of restating the law in fresh prose that can drift. Pathway
prose deliberately contains no numeric thresholds, fees, or timelines;
anything numeric lives only in the limitation flags, which cite their
curated section.

Limitation flagging is a separate, deliberately careful piece: it
states the statutory period by citing the 4a section and never computes
"days left" from user facts, by design.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

from src.explain.explain import DISCLAIMER
from src.explain.statutes import get_section

NO_PATHWAY_MESSAGE = (
    "No pathway guidance is available for this issue from the covered "
    "issue areas. That does not mean you have no options; it means this "
    "tool cannot responsibly lay them out. Please consult a qualified "
    "advocate, or approach your District Legal Services Authority (DLSA) "
    "or NALSA for free legal aid."
)

LIMITATION_CAVEAT = (
    "When a limitation period starts, whether it has expired, and whether "
    "a delay can be condoned are fact-dependent questions that this tool "
    "does not and will not compute. Treat every period here as a reason "
    "to act early, and confirm limitation with a lawyer as soon as "
    "possible."
)


@dataclass(frozen=True)
class SectionRef:
    """Pointer to a curated 4a section, resolved for display."""

    act_id: str
    section: str
    act: str
    title: str


@dataclass(frozen=True)
class Pathway:
    """One realistic route: static description plus curated references."""

    pathway_id: str
    name: str
    what_it_is: str
    when_it_makes_sense: str
    pros: list[str]
    cons: list[str]
    section_refs: list[SectionRef] = field(default_factory=list)


@dataclass(frozen=True)
class LimitationFlag:
    """A statutory time limit, stated by citing its curated section."""

    statement: str
    section_ref: SectionRef | None
    caveat: str = LIMITATION_CAVEAT


@dataclass(frozen=True)
class PathwaysExplanation:
    """Pathways output: ordered options or an explicit no-pathway state."""

    status: str  # ok | no_pathways
    issue_type: str
    pathways: list[Pathway] = field(default_factory=list)
    limitation_flags: list[LimitationFlag] = field(default_factory=list)
    # Act-level caveats from referenced sections (for example the Model
    # Tenancy Act model-law warning), deduplicated, order-preserving.
    # Structural guarantee; the tenancy pathway prose restates the point
    # as human-readable reinforcement, not as the mechanism.
    caveats: list[str] = field(default_factory=list)
    message: str | None = None
    disclaimer: str = DISCLAIMER

    def to_dict(self) -> dict:
        return asdict(self)


# (pathway_id, name, what, when, pros, cons, refs as (act_id, section))
_RAW_PATHWAYS: dict[str, tuple[tuple, ...]] = {
    "cheque": (
        (
            "demand_notice",
            "Written demand notice to the cheque writer",
            "A formal written demand for the cheque amount, sent to the "
            "person who wrote the bounced cheque. It is the statutory "
            "first step that keeps the criminal route open; the notice and "
            "payment windows are fixed by the cited section.",
            "Almost always the first step, as soon as possible after the "
            "bank returns the cheque unpaid.",
            [
                "Inexpensive and quick to send",
                "Often produces payment without any court case",
                "Preserves the criminal remedy under the cited section",
            ],
            [
                "The statutory windows are strict; delay can close the criminal route",
                "Needs proof of sending and delivery",
                "The other side may respond with a defence instead of payment",
            ],
            (("ni_act_1881", "138"),),
        ),
        (
            "s138_complaint",
            "Criminal complaint for cheque dishonour",
            "A criminal complaint before a Magistrate for the offence of "
            "cheque dishonour. Who may file, the time limit, and which "
            "court are all fixed by the cited sections.",
            "When the demand notice produced no payment, and only after "
            "the drawer's payment window in the cited section has fully "
            "passed; filing before it expires is premature.",
            [
                "Real pressure on the drawer, since conviction carries "
                "imprisonment or fine as per the cited section",
                "A very well-trodden route in Indian courts",
                "The law presumes the cheque was for a debt or liability "
                "(see the cited presumption section)",
            ],
            [
                "Court proceedings can run for years",
                "The statutory preconditions must be met exactly",
                "Requires attending hearings, personally or through a lawyer",
            ],
            (("ni_act_1881", "138"), ("ni_act_1881", "139"), ("ni_act_1881", "142")),
        ),
        (
            "civil_recovery",
            "Civil suit to recover the money",
            "A civil case asking the court to order repayment of the debt "
            "itself, with interest, independent of the criminal route.",
            "When the criminal route's preconditions were missed, or when "
            "recovering the money matters more than punishing the drawer.",
            [
                "Targets the money directly",
                "Available even if the notice windows were missed",
            ],
            [
                "Court fees and timelines vary; confirm with a lawyer",
                "Generally slower than the pressure a criminal complaint creates",
            ],
            (),
        ),
        (
            "mediation_lok_adalat",
            "Settlement, mediation, or Lok Adalat",
            "A negotiated settlement, including through court-annexed "
            "mediation or a Lok Adalat, where cheque disputes are commonly "
            "resolved.",
            "When the other side is willing to talk and a certain, quick "
            "outcome is worth more than a maximal one.",
            [
                "Fast and inexpensive compared to litigation",
                "Ends the dispute consensually and finally",
            ],
            [
                "Needs both sides willing",
                "The settled amount may be less than the full claim",
            ],
            (),
        ),
    ),
    "consumer": (
        (
            "written_complaint",
            "Written complaint to the seller or service provider",
            "A clear written grievance to the business, describing the "
            "defect or deficiency and the remedy you want, keeping copies "
            "and proof of delivery.",
            "First, in almost every consumer dispute; it is cheap and "
            "builds the paper trail every later step uses.",
            [
                "Costs nothing beyond time",
                "Often resolves the matter",
                "Creates the record a Commission complaint will rely on",
            ],
            ["No compulsion; the business can ignore it"],
            (),
        ),
        (
            "consumer_commission",
            "Complaint before the Consumer Commission",
            "A complaint to the consumer dispute redressal forum. Whether "
            "you count as a consumer, what counts as deficiency, who may "
            "file and how (including electronically) are set by the cited "
            "sections.",
            "When the business has not resolved a genuine defect or "
            "deficiency after a written complaint.",
            [
                "A forum designed for consumers, simpler than civil court",
                "Electronic filing is provided for by the cited section",
                "Consumer associations can file even for non-members",
            ],
            [
                "Proceedings still take real time in practice",
                "Which level of commission depends on the claim value; the "
                "current monetary limits change by notification, so confirm "
                "them with a lawyer",
            ],
            (("cpa_2019", "2(7)"), ("cpa_2019", "2(11)"), ("cpa_2019", "35")),
        ),
        (
            "mediation",
            "Mediation",
            "A settlement discussion assisted by a neutral mediator, "
            "including references to mediation made by consumer forums.",
            "When the business engages but the two sides are stuck.",
            ["Faster and cheaper than fighting the complaint through", "Preserves the relationship where that matters"],
            ["Needs both sides willing", "Availability and procedure vary; confirm locally"],
            (),
        ),
        (
            "civil_suit",
            "Civil suit",
            "An ordinary civil case for damages or specific relief instead "
            "of the consumer forum.",
            "Occasionally, for large or legally complex claims where a "
            "lawyer advises it over the consumer route.",
            ["Full civil remedies and procedure"],
            [
                "Slower and costlier than the consumer forum",
                "Court fees scale with the claim; confirm with a lawyer",
            ],
            (),
        ),
    ),
    "tenancy": (
        (
            "written_notice",
            "Written demand or notice to the other side",
            "A dated, written statement of what you demand (deposit "
            "refund, repairs, vacating, arrears) sent with proof of "
            "delivery.",
            "First, in nearly every tenancy dispute; most later forums "
            "expect to see it.",
            [
                "Cheap, quick, and creates the record",
                "Often enough to unlock a deposit or start a negotiation",
            ],
            ["No compulsion by itself"],
            (),
        ),
        (
            "rent_authority",
            "Rent Authority or Rent Court under your state's law",
            "The specialised forum for tenancy disputes where your state "
            "has one. The cited model-law provisions show how such forums "
            "handle deposits and eviction, but your state's own rent law "
            "governs; the caveat on the cited sections applies fully.",
            "When notice failed and the dispute is squarely about deposit, "
            "rent, or eviction.",
            [
                "A forum built for exactly these disputes where it exists",
                "The cited model provisions show the shape of the protections",
            ],
            [
                "Whether a Rent Authority or Rent Court exists, and its "
                "procedure, varies by state; confirm locally",
            ],
            (("mta_2021", "11"), ("mta_2021", "21")),
        ),
        (
            "civil_suit",
            "Civil suit",
            "An ordinary civil case, for example to recover a deposit as a "
            "money claim or to protect possession.",
            "When no specialised forum applies, or a lawyer advises it for "
            "the specific claim.",
            ["Available everywhere", "Full civil remedies"],
            [
                "Slower and costlier than a specialised forum",
                "Court fees and timelines vary; confirm with a lawyer",
            ],
            (),
        ),
        (
            "police_complaint",
            "Police complaint, for genuine criminality only",
            "A complaint to the police where there is actual criminal "
            "conduct, such as forcible lockout, threats, or violence. "
            "Police treat ordinary rent and deposit disputes as civil "
            "matters and generally will not intervene in them.",
            "When safety is at risk or you are being forcibly dispossessed, "
            "alongside, not instead of, the civil routes.",
            ["The right route where there are threats or force"],
            [
                "Not a recovery mechanism for money or possession",
                "Expect to be told it is a civil matter unless real "
                "criminality is shown",
            ],
            (),
        ),
        (
            "mediation_lok_adalat",
            "Settlement, mediation, or Lok Adalat",
            "A negotiated resolution, including through court-annexed "
            "mediation or a Lok Adalat.",
            "When the relationship or speed matters more than winning "
            "every point.",
            ["Fast, cheap, consensual"],
            ["Needs both sides willing"],
            (),
        ),
    ),
}

# Limitation flags per issue. Statements restate ONLY the cited curated
# section; tenancy has no curated limitation provision and says so.
_RAW_LIMITATION: dict[str, tuple[tuple[str, tuple[str, str] | None], ...]] = {
    "cheque": (
        (
            "The criminal route runs on strict statutory windows fixed by "
            "the cited section: the written demand notice must go within "
            "thirty days of learning from the bank that the cheque was "
            "returned unpaid, and the drawer then has fifteen days from "
            "receiving the notice to pay.",
            ("ni_act_1881", "138"),
        ),
        (
            "The complaint itself must be made within one month of the "
            "cause of action arising, and the cited section also lets a "
            "court take a later complaint if sufficient cause is shown.",
            ("ni_act_1881", "142"),
        ),
    ),
    "consumer": (
        (
            "A consumer complaint must be filed within two years from the "
            "date the cause of action arises; the cited section also "
            "allows a later complaint where the Commission is satisfied "
            "there was sufficient cause and records its reasons.",
            ("cpa_2019", "69"),
        ),
    ),
    "tenancy": (
        (
            "No general limitation period applies from the bundled statute "
            "set; time limits for tenancy claims depend on your state's "
            "rent law and the kind of claim.",
            None,
        ),
    ),
}


def _resolve_ref(act_id: str, section: str) -> SectionRef:
    """Resolve a curated section pointer; raises if it does not exist."""
    record = get_section(act_id, section)
    if record is None:
        raise KeyError(f"pathway references missing section {act_id} s.{section}")
    return SectionRef(act_id=act_id, section=section, act=record["act"], title=record["title"])


def explain_pathways(issue_type: str, facts: dict | None = None) -> PathwaysExplanation:
    """Lay out the realistic pathways for a classified issue.

    facts is accepted for interface symmetry with explain_rights but is
    deliberately never used for limitation: periods are stated by citing
    the curated section, and no deadline is ever computed from user
    facts.
    """
    del facts
    raw = _RAW_PATHWAYS.get(issue_type)
    if not raw:
        return PathwaysExplanation(
            status="no_pathways", issue_type=issue_type, message=NO_PATHWAY_MESSAGE
        )
    pathways = [
        Pathway(
            pathway_id=pid,
            name=name,
            what_it_is=what,
            when_it_makes_sense=when,
            pros=list(pros),
            cons=list(cons),
            section_refs=[_resolve_ref(a, s) for a, s in refs],
        )
        for pid, name, what, when, pros, cons, refs in raw
    ]
    flags = [
        LimitationFlag(
            statement=statement,
            section_ref=_resolve_ref(*ref) if ref else None,
        )
        for statement, ref in _RAW_LIMITATION.get(issue_type, ())
    ]
    caveats: list[str] = []
    referenced = [ref for p in pathways for ref in p.section_refs] + [
        f.section_ref for f in flags if f.section_ref is not None
    ]
    for ref in referenced:
        record = get_section(ref.act_id, ref.section)
        if record and record["caveat"] and record["caveat"] not in caveats:
            caveats.append(record["caveat"])
    return PathwaysExplanation(
        status="ok",
        issue_type=issue_type,
        pathways=pathways,
        limitation_flags=flags,
        caveats=caveats,
    )
