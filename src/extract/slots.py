"""Issue-conditioned slot filling from extracted primitives.

Slots record what the user said; legal significance (deadlines,
limitation) is later phases' job. Unfillable slots return None and are
reported in unresolved by the orchestrator.
"""

from __future__ import annotations

import re

from src.extract.parties import find_bank, infer_side
from src.extract.schema import Amount, DateMention, Party, SlotValue

_BOUNCE_REASONS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("insufficient_funds", ("insufficient fund", "funds insufficient", "insufficient balance")),
    ("stop_payment", ("stop payment", "payment stopped", "stopped by drawer")),
    ("account_closed", ("account closed", "account is closed", "account shows closed", "closed account")),
    ("signature_mismatch", ("signature mismatch", "signature does not match", "signature differs", "signature mismatch")),
    ("exceeds_arrangement", ("exceeds arrangement",)),
    ("other", ("refer to drawer", "account dormant", "account frozen", "kyc")),
)

_BOUNCE_CUES = ("bounce", "bounced", "dishonour", "dishonoured", "returned unpaid", "came back unpaid", "return")
_REMEDY_LEXICON: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("refund", ("refund", "money back", "return request", "return the amount", "paise wapas")),
    ("replacement", ("replace", "replacement", "exchange")),
    ("repair", ("repair", "fix", "service it")),
    ("compensation", ("compensation", "damages", "compensate")),
)
_DEFECT_CUES = (
    "defective", "faulty", "not working", "stopped working", "stopped charging",
    "broken", "damaged", "leaks", "leaking", "failed", "fake", "wrong", "used",
    "stale", "expired", "shrunk", "burned", "burnt", "kharab", "cooling issue",
    "does not work", "seized", "sagged", "scratches", "spoiled", "torn",
    "cracked", "blur", "adulterated", "contaminated", "different colour",
    "display piece", "second hand",
)
_DISPUTE_OBJECTS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("deposit_refund", ("deposit", "token advance")),
    (
        "eviction",
        ("evict", "vacate the", "asked to vacate", "to vacate", "demanding i vacate",
         "leave within", "days to leave", "khali karwa", "wants the house", "makaan khali"),
    ),
    ("repairs", ("repair", "leakage", "leaking", "unsafe", "maintenance")),
    ("rent_increase", ("rent increase", "increase in rent", "rent hike", "doubled the rent", "badhane")),
    ("harassment", ("harass", "threat", "locked", "cut off", "dhamki", "pareshan")),
)


def _sentence_of(text: str, span: list[int]) -> str:
    """The rough sentence containing span, for cue checks."""
    start = text.rfind(".", 0, span[0]) + 1
    end = text.find(".", span[1])
    return text[start : end if end >= 0 else len(text)].lower()


def _amount_slot(amounts: list[Amount], purposes: tuple[str, ...]) -> SlotValue | None:
    """Amount whose purpose matches; else a lone amount as fallback."""
    matched = [a for a in amounts if a.purpose in purposes]
    if matched:
        best = matched[0]
        return SlotValue(value=best.value, raw=best.raw, span=best.span)
    if len(amounts) == 1:
        lone = amounts[0]
        return SlotValue(value=lone.value, raw=lone.raw, span=lone.span)
    return None


def _date_slot(
    text: str, dates: list[DateMention], include: tuple[str, ...], exclude: tuple[str, ...] = ()
) -> SlotValue | None:
    """First date whose sentence contains an include cue and no exclude cue."""
    for date in dates:
        sentence = _sentence_of(text, date.span)
        if any(cue in sentence for cue in include) and not any(cue in sentence for cue in exclude):
            return SlotValue(value=date.iso or date.raw, raw=date.raw, span=date.span)
    return None


def _party_slot(parties: list[Party], role: str, words: tuple[str, ...]) -> SlotValue | None:
    """Index of the first party matching role words (or role as fallback).

    The fallback prefers parties with a role word over bare pronoun
    mentions, so "my firm" beats "my" for the complainant side.
    """
    for i, party in enumerate(parties):
        if party.role_word and any(w in party.role_word for w in words):
            return SlotValue(value=i, raw=party.mention, span=party.spans[0])
    candidates = [(i, p) for i, p in enumerate(parties) if p.role == role]
    candidates.sort(key=lambda item: item[1].role_word is None)
    if candidates:
        i, party = candidates[0]
        return SlotValue(value=i, raw=party.mention, span=party.spans[0])
    return None


def _keyword_slot(
    text: str, lexicon: tuple[tuple[str, tuple[str, ...]], ...]
) -> SlotValue | None:
    """First lexicon entry whose keyword appears; value is the entry label."""
    lowered = text.lower()
    best: tuple[int, str, str] | None = None
    for label, keywords in lexicon:
        for kw in keywords:
            pos = lowered.find(kw)
            if pos >= 0 and (best is None or pos < best[0]):
                best = (pos, label, kw)
    if best is None:
        return None
    pos, label, kw = best
    return SlotValue(value=label, raw=text[pos : pos + len(kw)], span=[pos, pos + len(kw)])


def fill_cheque_slots(
    text: str, doc, parties: list[Party], amounts: list[Amount], dates: list[DateMention]
) -> dict:
    """Fill the cheque issue slots. bounce_dates is a list of tagged entries."""
    slots: dict = {}
    slots["cheque_amount"] = _amount_slot(amounts, ("cheque_amount",))
    slots["cheque_date"] = _date_slot(text, dates, ("post dated", "cheque dated", "dated the cheque"), _BOUNCE_CUES)

    bounce_dates: list[SlotValue] = []
    for date in dates:
        sentence = _sentence_of(text, date.span)
        has_memo = "memo" in sentence
        has_bounce = any(cue in sentence for cue in _BOUNCE_CUES)
        if not (has_memo or has_bounce):
            continue
        if has_memo and has_bounce:
            kind = "unclear"
        elif has_memo:
            kind = "memo"
        else:
            kind = "actual_bounce"
        bounce_dates.append(
            SlotValue(value=date.iso or date.raw, raw=date.raw, span=date.span, qualifier=kind)
        )
    slots["bounce_dates"] = bounce_dates or None

    slots["bounce_reason"] = _keyword_slot(text, _BOUNCE_REASONS)
    slots["drawer"] = None
    slots["payee"] = None
    side = infer_side(text, "cheque")
    slots["complainant_side"] = side
    if side is not None:
        counter = _party_slot(parties, "other_side", ())
        me = _party_slot(parties, "complainant", ())
        if side.value == "payee":
            slots["payee"], slots["drawer"] = me, counter
        else:
            slots["drawer"], slots["payee"] = me, counter
    slots["notice_date"] = _date_slot(text, dates, ("notice sent", "sent a legal notice", "sent the notice", "notice through", "issued a notice"))
    slots["notice_served_date"] = _date_slot(text, dates, ("notice received", "received the notice", "notice was served", "notice delivered", "served on"))

    number = re.search(r"cheque\s+(?:no\.?|number)\s*[:#]?\s*(\d{6})", text, re.IGNORECASE)
    slots["cheque_number"] = (
        SlotValue(value=number.group(1), raw=number.group(0), span=[number.start(), number.end()])
        if number
        else None
    )
    bank = find_bank(text, doc)
    slots["bank"] = (
        SlotValue(value=bank[0], raw=text[bank[1] : bank[2]], span=[bank[1], bank[2]]) if bank else None
    )
    return slots


def fill_consumer_slots(
    text: str, doc, parties: list[Party], amounts: list[Amount], dates: list[DateMention]
) -> dict:
    """Fill the consumer issue slots."""
    slots: dict = {}
    slots["purchase_date"] = _date_slot(
        text, dates, ("bought", "ordered", "purchased", "booked", "paid")
    )
    slots["item_or_service"] = _item_or_service(doc)
    slots["amount_paid"] = _amount_slot(amounts, ("price_paid", "fee"))
    slots["seller"] = _party_slot(
        parties, "other_side",
        ("seller", "dealer", "shopkeeper", "shop", "store", "showroom", "company", "builder", "courier", "salon", "gym", "hotel", "agency", "institute", "platform", "insurer", "hospital"),
    )
    slots["defect_or_deficiency"] = _defect_clause(doc)
    slots["remedy_sought"] = _keyword_slot(text, _REMEDY_LEXICON)
    return slots


def _item_or_service(doc) -> SlotValue | None:
    """Direct object noun chunk of a purchase verb, verbatim."""
    purchase_lemmas = {"buy", "order", "purchase", "book", "hire"}
    for token in doc:
        if token.lemma_.lower() in purchase_lemmas and token.pos_ == "VERB":
            for chunk in doc.noun_chunks:
                if chunk.root.head == token and chunk.root.dep_ in ("dobj", "obj"):
                    return SlotValue(
                        value=chunk.text, raw=chunk.text, span=[chunk.start_char, chunk.end_char]
                    )
    return None


def _defect_clause(doc) -> SlotValue | None:
    """The first sentence containing a defect cue, verbatim."""
    for sent in doc.sents:
        lowered = sent.text.lower()
        if any(cue in lowered for cue in _DEFECT_CUES):
            return SlotValue(
                value=sent.text.strip(), raw=sent.text.strip(), span=[sent.start_char, sent.end_char]
            )
    return None


def fill_tenancy_slots(
    text: str, doc, parties: list[Party], amounts: list[Amount], dates: list[DateMention]
) -> dict:
    """Fill the tenancy issue slots."""
    slots: dict = {}
    slots["monthly_rent"] = _amount_slot(amounts, ("rent",)) if any(a.purpose == "rent" for a in amounts) else None
    slots["deposit_amount"] = _amount_slot(amounts, ("deposit",)) if any(a.purpose == "deposit" for a in amounts) else None
    slots["agreement_start"] = _date_slot(text, dates, ("agreement from", "agreement started", "lease from", "since"))
    slots["agreement_end_or_duration"] = _date_slot(text, dates, ("agreement till", "agreement ends", "agreement expired", "lease till", "remaining"))
    slots["notice_given_date"] = _date_slot(
        text, dates, ("gave notice on", "notice given", "notice in", "notice on"),
        exclude=("vacated", "moved out"),
    )
    slots["vacated_date"] = _date_slot(text, dates, ("vacated", "moved out", "left the flat", "khali"))
    slots["landlord"] = _party_slot(parties, "other_side", ("landlord", "landlady", "house owner", "flat owner", "owner"))
    side = infer_side(text, "tenancy")
    slots["complainant_side"] = side
    tenant_party = _party_slot(parties, "", ("tenant",))
    if tenant_party is None and side is not None and side.value == "tenant":
        tenant_party = _party_slot(parties, "complainant", ())
    slots["tenant"] = tenant_party
    slots["dispute_object"] = _keyword_slot(text, _DISPUTE_OBJECTS)
    return slots
