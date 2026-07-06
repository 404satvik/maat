"""spaCy wrapper: supplemental NER with Hinglish-noise defenses.

Rules are primary for amounts and party roles; spaCy supplies DATE, GPE,
ORG, and PERSON spans. GPE spans are only trusted if validated against
the Indian place gazetteer; a direct gazetteer scan also catches
lowercase place names spaCy misses.
"""

from __future__ import annotations

import re
from functools import lru_cache

from src.extract.gazetteer import is_hinglish_noise, lookup_indian_place
from src.extract.schema import Place


@lru_cache(maxsize=1)
def get_nlp():
    """Load en_core_web_sm once."""
    import spacy

    return spacy.load("en_core_web_sm")


def analyze(text: str):
    """Run the spaCy pipeline on text."""
    return get_nlp()(text)


def clean_entities(doc, labels: tuple[str, ...]) -> list:
    """spaCy entities of the given labels, minus Hinglish noise."""
    return [
        ent
        for ent in doc.ents
        if ent.label_ in labels and not is_hinglish_noise(ent.text)
    ]


def extract_places(text: str, doc) -> list[Place]:
    """Gazetteer-validated places from GPE spans plus a raw text scan."""
    places: list[Place] = []
    seen_spans: list[tuple[int, int]] = []

    def add(raw: str, normalized: str, start: int, end: int) -> None:
        if any(s < end and start < e for s, e in seen_spans):
            return
        seen_spans.append((start, end))
        places.append(
            Place(raw=raw, normalized=normalized, validated_indian_place=True, span=[start, end])
        )

    for ent in clean_entities(doc, ("GPE", "LOC")):
        normalized = lookup_indian_place(ent.text)
        if normalized is not None:
            add(ent.text, normalized, ent.start_char, ent.end_char)

    lowered = text.lower()
    from src.extract.gazetteer import HINGLISH_STOPLIST, _PLACE_LOOKUP

    for key, canonical in _PLACE_LOOKUP.items():
        for m in re.finditer(rf"\b{re.escape(key)}\b", lowered):
            raw = text[m.start() : m.end()]
            if key in HINGLISH_STOPLIST and not raw.istitle():
                continue
            add(raw, canonical, m.start(), m.end())

    places.sort(key=lambda p: p.span[0])
    return places
