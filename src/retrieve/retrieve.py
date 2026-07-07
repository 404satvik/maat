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
from src.retrieve.summarize import ABSTAIN_MESSAGE, WEAK_CAUTION, SummaryPart, build_summary

INDEX_DIR = Path("index")
FRAMING = (
    "Illustrative of how comparable disputes have played out in appellate "
    "courts. Not a prediction of your outcome. These are Supreme Court "
    "appeal judgments; consumer-forum and rent-court level outcomes are "
    "not in this corpus."
)

# Abstention thresholds, anchored to the score distributions in
# results/abstention.md (provisional; fit on 18 proxy-labelled queries).
# SIM_FLOOR sits just above the median top-1 similarity of out-of-scope
# queries (0.435); SIM_CONFIDENT sits just above their maximum (0.532).
SIM_FLOOR = 0.44
SIM_CONFIDENT = 0.54
MIN_QUERY_WORDS = 5

_STRIP_PATTERNS = (
    re.compile(r"(?:Rs\.?|rupees)\s*[\d,]+(?:\.\d+)?(?:\s*(?:lakhs?|crores?))?", re.IGNORECASE),
    re.compile(r"\b[\d,]{4,}\b"),
)

_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+")


def _strip_literals(text: str) -> str:
    """Remove amounts and long numbers; collapse whitespace."""
    for pattern in _STRIP_PATTERNS:
        text = pattern.sub(" ", text)
    return re.sub(r"\s+", " ", text).strip()


@dataclass(frozen=True)
class RetrievedCase:
    """One real retrieved judgment with its grounded summary."""

    doc_id: str
    case_name: str
    issue_area: str
    similarity: float
    matched_passage: str
    summary: list[SummaryPart]
    confidence: str = "confident"  # confident | weak
    caution: str | None = None  # WEAK_CAUTION for weak matches
    framing: str = FRAMING

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class RetrievalResponse:
    """Query-level retrieval outcome: cases plus a confidence verdict.

    query_confidence is confident, weak, or abstain. On abstain, cases is
    empty and message carries the explicit nothing-relevant-retrieved
    text with routing to legal aid; no low-quality case list is shown.
    """

    query_confidence: str
    cases: list[RetrievedCase]
    message: str | None = None
    abstain_reason: str | None = None

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

    Two deliberate design decisions live here; do not revert either
    without re-running the abstention analysis (results/abstention.md):

    1. Content-only, no issue-keyword prepend. An earlier version
       prepended fixed issue keywords ("cheque dishonoured section 138
       ...") to every query. That boilerplate dominated similarity for
       off-topic input: a domestic-violence complaint (oth-003) scored
       0.777 against the cheque corpus on keywords alone, destroying the
       in-scope versus out-of-scope score separation the abstention
       floor depends on. The issue area is enforced by the corpus
       filter, so the prepend added nothing for on-topic queries.

    2. Raw-text fallback when extracted content is sparse. The primary
       query is built from timeline sentences and filled slots, but
       timeline extraction drops question sentences and needs an
       event-cue verb, so concrete complaints can synthesize to almost
       nothing: chq-077 (a real s.138 matter phrased mostly as
       questions) became a 1-word query, and terse complaints like
       "landlord kept my deposit" or "seller refuses refund" died
       pre-scoring because "kept" is not a cue verb. When the primary
       query falls under MIN_QUERY_WORDS, the complaint's non-question
       sentences (amounts stripped, same as always) are appended, so
       the similarity floor judges real content and the content-abstain
       trigger only catches genuinely contentless input. Queries built
       this way are capped at weak confidence by retrieve_similar:
       without the cap, a vague-but-wordy complaint (oth-076, "confused
       about a legal matter concerning my family and property") scored
       0.557 against the tenancy corpus and presented as confident.
    """
    query, _ = synthesize_query_with_provenance(facts, issue_type)
    return query


def synthesize_query_with_provenance(facts: dict, issue_type: str) -> tuple[str, bool]:
    """synthesize_query plus whether the raw-text fallback was used.

    See synthesize_query for the design rationale.
    """
    pieces: list[str] = []
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
    query = _strip_literals(" ".join(p for p in pieces if p))

    used_fallback = False
    if len(query.split()) < MIN_QUERY_WORDS:
        complaint_text = str(facts.get("meta", {}).get("complaint_text", ""))
        statements = [
            s for s in _SENT_SPLIT.split(complaint_text)
            if s.strip() and not s.rstrip().endswith("?")
        ]
        fallback = _strip_literals(" ".join([query, *statements]))
        if len(fallback.split()) > len(query.split()):
            query = fallback
            used_fallback = True
    return query, used_fallback


def retrieve_similar(
    facts_or_query: dict | str,
    issue_type: str,
    k: int = 5,
    embedder: str = "minilm",
    candidate_chunks: int = 400,
    max_chunk_pos: int | None = None,
    apply_floor: bool = True,
) -> RetrievalResponse:
    """Retrieve similar real judgments with a query-level confidence.

    facts_or_query is a Phase 2 facts dict (query synthesized from it) or
    a raw query string. Results are filtered to the issue area, ranked by
    max chunk similarity, deduplicated by caption, and summarized
    extractively. Three outcomes: confident, weak (results carry a
    caution), or abstain (no cases; explicit message instead).
    apply_floor=False disables abstention and confidence filtering for
    evaluation continuity. max_chunk_pos, if set, restricts matching to
    the first N chunks of each judgment.
    """
    used_fallback = False
    if isinstance(facts_or_query, dict):
        query, used_fallback = synthesize_query_with_provenance(facts_or_query, issue_type)
        if apply_floor and len(query.split()) < MIN_QUERY_WORDS:
            return RetrievalResponse(
                query_confidence="abstain",
                cases=[],
                message=ABSTAIN_MESSAGE,
                abstain_reason="insufficient extractable detail to search meaningfully",
            )
    else:
        query = str(facts_or_query)
    if not query.strip():
        return RetrievalResponse(
            query_confidence="abstain",
            cases=[],
            message=ABSTAIN_MESSAGE,
            abstain_reason="empty query",
        )

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
        if apply_floor and score < SIM_FLOOR:
            continue
        doc = docs.loc[doc_id]
        name_key = str(doc["case_name"]).strip().lower()
        if name_key in seen_names:
            continue
        seen_names.add(name_key)
        # Fallback-built queries never earned structured extraction, so
        # they are capped at weak (see synthesize_query rationale).
        confidence = "confident" if score >= SIM_CONFIDENT and not used_fallback else "weak"
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
                confidence=confidence,
                caution=WEAK_CAUTION if confidence == "weak" else None,
            )
        )

    if not results:
        return RetrievalResponse(
            query_confidence="abstain",
            cases=[],
            message=ABSTAIN_MESSAGE,
            abstain_reason="no judgment scored above the similarity floor",
        )
    top = results[0].similarity
    if used_fallback:
        query_confidence = "weak"
    elif apply_floor:
        query_confidence = "confident" if top >= SIM_CONFIDENT else "weak"
    else:
        query_confidence = "confident" if top >= SIM_CONFIDENT else ("weak" if top >= SIM_FLOOR else "abstain")
    return RetrievalResponse(query_confidence=query_confidence, cases=results)
