"""Party extraction: role words are primary, names supplement.

Role words (landlord, dealer, tenant, employer...) matter more than
names on this register. spaCy PERSON/ORG spans attach names to role
mentions or add organization parties. complainant_side inference lives
here; conflicts route to unresolved rather than defaulting.
"""

from __future__ import annotations

import re

from src.extract.gazetteer import ACRONYM_STOPLIST, BANKS, is_hinglish_noise
from src.extract.schema import Party, SlotValue

# Role words that name the counterparty when possessed by the complainant
# ("my landlord") or introduced as the actor ("the dealer says").
COUNTERPARTY_WORDS: tuple[str, ...] = (
    "landlord", "landlady", "tenant", "shopkeeper", "dealer", "seller",
    "builder", "employer", "customer", "client", "contractor", "supplier",
    "transporter", "buyer", "agent", "broker", "house owner", "flat owner",
    "owner", "neighbour", "neighbor", "friend", "colleague", "relative",
    "brother in law", "brother", "sister", "uncle", "cousin", "in laws",
    "husband", "wife", "moneylender", "lender", "organiser", "operator",
    "photographer", "caterer", "technician", "doctor", "hospital",
    "company", "firm", "bank", "shop", "store", "showroom", "school",
    "society", "institute", "agency", "platform", "insurer", "manufacturer",
    "distributor", "retailer", "courier", "salon", "gym", "hotel",
    "service centre", "partner", "trust", "college",
)

_ORG_WORDS = frozenset(
    {
        "company", "firm", "bank", "shop", "store", "showroom", "school",
        "society", "institute", "agency", "platform", "insurer", "hospital",
        "manufacturer", "distributor", "retailer", "courier", "salon",
        "gym", "hotel", "service centre", "trust", "college",
    }
)

# "my X" where X is an asset of the complainant, not a counterparty.
_SELF_ASSETS = frozenset(
    {"firm", "shop", "business", "unit", "agency", "store", "office"}
)

_EMPLOYMENT_CUES = ("salary", "salaries", "wages", "terminated", "resigned", "hr", "employer", "notice period", "gratuity", "pf")

_ROLE_RE = re.compile(
    r"\b(my|our|the|a|an|his|her|their)\s+((?:" + "|".join(re.escape(w) for w in COUNTERPARTY_WORDS) + r"))\b",
    re.IGNORECASE,
)

_FIRST_PERSON_RE = re.compile(r"\b(I|we|my|our)\b")


def _kind_for(word: str) -> str:
    return "organization" if word.lower() in _ORG_WORDS else "person"


def extract_parties(text: str, doc) -> list[Party]:
    """Extract parties from role-word rules, supplemented by NER spans."""
    parties: list[Party] = []
    by_key: dict[tuple[str, str], Party] = {}

    def upsert(role: str, kind: str, mention: str, role_word: str | None, start: int, end: int) -> Party:
        key = (role, (role_word or mention).lower())
        if key in by_key:
            by_key[key].spans.append([start, end])
            return by_key[key]
        party = Party(role=role, kind=kind, mention=mention, role_word=role_word, name=None, spans=[[start, end]])
        by_key[key] = party
        parties.append(party)
        return party

    first = _FIRST_PERSON_RE.search(text)
    if first is not None:
        upsert("complainant", "person", first.group(0), None, first.start(), first.end())

    for m in _ROLE_RE.finditer(text):
        determiner, word = m.group(1).lower(), m.group(2).lower()
        sentence = text[max(0, m.start() - 80) : m.end() + 80].lower()
        if determiner in ("my", "our") and word in _SELF_ASSETS:
            role = "complainant"
        elif word == "company" and determiner in ("my", "our"):
            role = "other_side" if any(c in sentence for c in _EMPLOYMENT_CUES) else "complainant"
        elif determiner in ("his", "her", "their"):
            role = "third_party"
        else:
            role = "other_side"
        upsert(role, _kind_for(word), m.group(0), word, m.start(), m.end())

    # Attach PERSON names adjacent to a role mention; otherwise add as
    # third_party person mentions.
    for ent in doc.ents:
        if ent.label_ != "PERSON" or is_hinglish_noise(ent.text):
            continue
        attached = False
        for party in parties:
            for start, end in party.spans:
                if 0 <= ent.start_char - end <= 2 and party.name is None:
                    party.name = ent.text
                    attached = True
                    break
            if attached:
                break
        if not attached:
            upsert("third_party", "person", ent.text, None, ent.start_char, ent.end_char)

    # ORG spans not overlapping existing mentions become organization parties.
    for ent in doc.ents:
        if ent.label_ != "ORG" or is_hinglish_noise(ent.text):
            continue
        if ent.text.lower().strip() in ACRONYM_STOPLIST:
            continue
        overlaps = any(
            s < ent.end_char and ent.start_char < e
            for party in parties
            for s, e in party.spans
        )
        if not overlaps:
            upsert("other_side", "organization", ent.text, None, ent.start_char, ent.end_char)

    return parties


def find_bank(text: str, doc) -> tuple[str, int, int] | None:
    """Find a named bank via the gazetteer or an ORG span containing Bank."""
    for bank in sorted(BANKS, key=len, reverse=True):
        m = re.search(rf"\b{re.escape(bank)}\b", text)
        if m:
            return bank, m.start(), m.end()
    for ent in doc.ents:
        if ent.label_ == "ORG" and "bank" in ent.text.lower() and not is_hinglish_noise(ent.text):
            return ent.text, ent.start_char, ent.end_char
    return None


_TENANT_SIGNALS = (
    r"\bmy landlord\b", r"\bour landlord\b", r"\bI vacated\b", r"\bwe vacated\b",
    r"\bI rent\b", r"\bwe rent\b", r"\bmy rented\b", r"\bour rented\b",
    r"\bthe (?:flat|house|room) I rent", r"\bwe have lived\b", r"\bmy deposit\b",
    r"\bmy pg\b",
)
_LANDLORD_SIGNALS = (
    r"\bmy tenant\b", r"\bour tenant\b", r"\bI (?:have )?rented (?:out|my)\b",
    r"\bgave my (?:flat|house|shop|property) on rent\b", r"\bI own\b",
    r"\bmy (?:flat|house|shop) which I rented\b", r"\bmy tenant's\b",
)
_PAYEE_SIGNALS = (
    r"\bgave me a cheque\b", r"\bgave (?:me|us) (?:a|the|his|her|their)? ?cheques?\b",
    r"\bI received a cheque\b", r"\b(?:his|her|their|the) cheques? .{0,30}bounc",
    r"\bsettled with a cheque\b", r"\bissued (?:me|us)\b", r"\bcheque (?:of|for) .{0,40} (?:from|by)\b",
    r"\bhold(?:s|ing)? a bounced cheque\b", r"\breceived .{0,30}cheque\b",
)
_DRAWER_SIGNALS = (
    r"\bmy cheque\b", r"\bcheque (?:I|we) (?:gave|issued|wrote)\b",
    r"\breceived a (?:court )?summons\b", r"\breceived a .{0,20}notice\b.{0,40}\bcheque\b",
    r"\bmy .{0,20}account\b.{0,30}\b(?:froze|frozen|closed)\b",
    r"\bsent me a notice\b", r"\bcase against me\b", r"\b138 .{0,20}against me\b",
)


def infer_side(text: str, issue_type: str) -> SlotValue | None:
    """Infer complainant_side from signal patterns; None means unresolved."""
    if issue_type == "tenancy":
        positive, negative, labels = _TENANT_SIGNALS, _LANDLORD_SIGNALS, ("tenant", "landlord")
    elif issue_type == "cheque":
        positive, negative, labels = _PAYEE_SIGNALS, _DRAWER_SIGNALS, ("payee", "drawer")
    else:
        return None
    pos_hits = [m for p in positive for m in re.finditer(p, text, re.IGNORECASE)]
    neg_hits = [m for p in negative for m in re.finditer(p, text, re.IGNORECASE)]
    if len(pos_hits) == len(neg_hits):
        return None
    winner = labels[0] if len(pos_hits) > len(neg_hits) else labels[1]
    hit = (pos_hits if len(pos_hits) > len(neg_hits) else neg_hits)[0]
    return SlotValue(value=winner, raw=hit.group(0), span=[hit.start(), hit.end()])
