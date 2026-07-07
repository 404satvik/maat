"""Similar-case retrieval: the Phase 3 entry point.

retrieve_similar takes a Phase 2 facts object (or a raw query string),
synthesizes a query, searches the chunk index, aggregates to documents,
and returns real retrieved cases with grounded extractive summaries.
Every result carries its real source and the fixed illustrative framing.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from functools import lru_cache
from pathlib import Path

import faiss
import numpy as np
import pandas as pd

from src.retrieve.embed import EMBEDDERS
from src.retrieve.summarize import SummaryPart, build_summary

INDEX_DIR = Path("index")
FRAMING = (
    "Illustrative of how comparable disputes have played out in appellate "
    "courts. Not a prediction of your outcome. These are Supreme Court "
    "appeal judgments; consumer-forum and rent-court level outcomes are "
    "not in this corpus."
)

_ISSUE_KEYWORDS = {
    "cheque": "cheque dishonoured section 138 negotiable instruments",
    "consumer": "consumer deficiency in service goods refund",
    "tenancy": "landlord tenant rent eviction premises",
}

_STRIP_PATTERNS = (
    re.compile(r"(?:Rs\.?|rupees)\s*[\d,]+(?:\.\d+)?(?:\s*(?:lakhs?|crores?))?", re.IGNORECASE),
    re.compile(r"\b[\d,]{4,}\b"),
)


@dataclass(frozen=True)
class RetrievedCase:
    """One real retrieved judgment with its grounded summary."""

    doc_id: str
    case_name: str
    issue_area: str
    similarity: float
    matched_passage: str
    summary: list[SummaryPart]
    framing: str = FRAMING

    def to_dict(self) -> dict:
        return asdict(self)


@lru_cache(maxsize=2)
def _load_store(embedder: str) -> tuple[faiss.Index, pd.DataFrame, pd.DataFrame]:
    index = faiss.read_index(str(INDEX_DIR / f"{embedder}.faiss"))
    chunks = pd.read_parquet(INDEX_DIR / "chunks.parquet")
    docs = pd.read_parquet(INDEX_DIR / "docs.parquet").set_index("doc_id")
    return index, chunks, docs


def synthesize_query(facts: dict, issue_type: str) -> str:
    """Deterministic query text from a Phase 2 facts object.

    Keeps semantic dispute content (timeline sentences, dispute_object,
    defect, bounce_reason, item_or_service); strips literal amounts and
    other long numbers, which do not transfer between cases.
    """
    pieces: list[str] = [_ISSUE_KEYWORDS.get(issue_type, "")]
    slots = facts.get("slots", {})
    for name in ("dispute_object", "bounce_reason", "remedy_sought", "complainant_side"):
        slot = slots.get(name)
        if isinstance(slot, dict) and slot.get("value") is not None:
            pieces.append(str(slot["value"]).replace("_", " "))
    for name in ("item_or_service", "defect_or_deficiency"):
        slot = slots.get(name)
        if isinstance(slot, dict) and slot.get("value"):
            pieces.append(str(slot["value"]))
    pieces.extend(event["description"] for event in facts.get("timeline", []))
    query = " ".join(p for p in pieces if p)
    for pattern in _STRIP_PATTERNS:
        query = pattern.sub(" ", query)
    return re.sub(r"\s+", " ", query).strip()


def retrieve_similar(
    facts_or_query: dict | str,
    issue_type: str,
    k: int = 5,
    embedder: str = "minilm",
    candidate_chunks: int = 400,
    max_chunk_pos: int | None = None,
) -> list[RetrievedCase]:
    """Retrieve the k most similar real judgments for the issue type.

    facts_or_query is a Phase 2 facts dict (query synthesized from it) or
    a raw query string. Results are filtered to the issue area, ranked by
    max chunk similarity, and summarized extractively. max_chunk_pos, if
    set, restricts matching to the first N chunks of each judgment (the
    facts of a case usually appear early).
    """
    if isinstance(facts_or_query, dict):
        query = synthesize_query(facts_or_query, issue_type)
    else:
        query = str(facts_or_query)
    if not query.strip():
        return []

    index, chunks, docs = _load_store(embedder)
    vector = EMBEDDERS[embedder]([query])
    scores, ids = index.search(vector, min(candidate_chunks, index.ntotal))

    best: dict[str, tuple[float, str]] = {}
    for score, chunk_idx in zip(scores[0], ids[0]):
        if chunk_idx < 0:
            continue
        chunk = chunks.iloc[int(chunk_idx)]
        if max_chunk_pos is not None and chunk["chunk_pos"] >= max_chunk_pos:
            continue
        doc_id = chunk["doc_id"]
        if docs.loc[doc_id, "issue_area"] != issue_type:
            continue
        if doc_id not in best or score > best[doc_id][0]:
            best[doc_id] = (float(score), chunk["text"])

    ranked = sorted(best.items(), key=lambda item: -item[1][0])
    results: list[RetrievedCase] = []
    seen_names: set[str] = set()
    for doc_id, (score, passage) in ranked:
        if len(results) >= k:
            break
        doc = docs.loc[doc_id]
        name_key = str(doc["case_name"]).strip().lower()
        if name_key in seen_names:
            continue
        seen_names.add(name_key)
        results.append(
            RetrievedCase(
                doc_id=doc_id,
                case_name=doc["case_name"],
                issue_area=doc["issue_area"],
                similarity=round(score, 4),
                matched_passage=passage,
                summary=build_summary(
                    int(doc["label"]), doc["case_name"], doc["text"], passage, doc["expert_explanation"]
                ),
            )
        )
    return results
