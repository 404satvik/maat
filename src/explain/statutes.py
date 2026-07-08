"""Loading and lookup for the curated statute set in data/statutes/.

This is a deliberately separate, tiny retrieval layer: a handful of
cleanly sectioned bare acts, looked up by issue-area mapping and by
section number or keyword. It does not touch the case-corpus FAISS
index; semantic search is unnecessary at this scale.
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

STATUTES_DIR = Path("data/statutes")
ACT_IDS: tuple[str, ...] = ("ni_act_1881", "cpa_2019", "mta_2021")


@lru_cache(maxsize=1)
def load_acts() -> dict[str, dict]:
    """Load every curated act JSON, keyed by act id."""
    acts: dict[str, dict] = {}
    for act_id in ACT_IDS:
        path = STATUTES_DIR / f"{act_id}.json"
        acts[act_id] = json.loads(path.read_text(encoding="utf-8"))
    return acts


def get_section(act_id: str, number: str) -> dict | None:
    """Return {act, title, text, source, caveat} for one section, or None."""
    act = load_acts().get(act_id)
    if act is None:
        return None
    section = act["sections"].get(number)
    if section is None:
        return None
    return {
        "act_id": act_id,
        "act": act["act"],
        "section": number,
        "title": section["title"],
        "text": section["text"],
        "source": act["source"],
        "caveat": act.get("caveat"),
    }


def find_sections(query: str, act_id: str | None = None) -> list[dict]:
    """Section-number or keyword lookup within the curated set.

    A bare number ("138") matches section numbers; other terms match
    against section titles and text, case-insensitively. Secondary to
    the issue-area mapping in explain.py.
    """
    acts = load_acts()
    targets = [act_id] if act_id else list(acts)
    query = query.strip()
    results: list[dict] = []
    for aid in targets:
        for number in acts[aid]["sections"]:
            section = get_section(aid, number)
            assert section is not None
            if re.fullmatch(r"\d+[A-Za-z]?(?:\(\d+\))?", query):
                if number == query or number.startswith(f"{query}("):
                    results.append(section)
            elif re.search(re.escape(query), f"{section['title']} {section['text']}", re.IGNORECASE):
                results.append(section)
    return results
