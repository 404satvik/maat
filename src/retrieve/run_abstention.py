"""Abstention analysis: score distributions, threshold effects, rates.

Reuses the existing 18-query eval and its keyword-predicate relevance
proxy (no new eval). Also probes out-of-scope behavior by forcing
other-class complaints through each issue area, which is what a Phase 1
misclassification would produce. Writes results/abstention.md so the
threshold choice is auditable.

Run from the repo root:

    python -m src.retrieve.run_abstention
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

from src.extract import extract_facts
from src.retrieve.retrieve import (
    MIN_QUERY_WORDS,
    SIM_CONFIDENT,
    SIM_FLOOR,
    retrieve_similar,
    synthesize_query,
)

EVAL_PATH = Path("data/eval/retrieval_eval.json")
SEED_DIR = Path("data/seed")
INDEX_DIR = Path("index")
RESULTS_DIR = Path("results")

# Other-class complaints used as out-of-scope probes (a Phase 1
# misclassification is the only path by which they reach retrieval).
OOS_IDS = (
    "oth-003", "oth-006", "oth-015", "oth-021", "oth-034",
    "oth-046", "oth-053", "oth-059", "oth-070", "oth-076",
)
WEAK_SPOT_IDS = ("chq-003", "probe-chq-010", "ten-001", "ten-060")


def load_texts() -> dict[str, str]:
    """Map complaint id to text across seed and probe files."""
    frames = [
        pd.read_csv(SEED_DIR / name, dtype=str)
        for name in ("consumer.csv", "cheque.csv", "tenancy.csv", "other.csv", "probe.csv")
    ]
    combined = pd.concat(frames, ignore_index=True)
    return dict(zip(combined["id"], combined["text"]))


def _stats(values: list[float]) -> dict:
    a = np.array(values)
    return {
        "n": int(len(a)),
        "min": round(float(a.min()), 3),
        "p25": round(float(np.percentile(a, 25)), 3),
        "median": round(float(np.median(a)), 3),
        "p75": round(float(np.percentile(a, 75)), 3),
        "max": round(float(a.max()), 3),
    }


def main() -> None:
    """Compute distributions and threshold effects; write abstention.md."""
    spec = json.loads(EVAL_PATH.read_text(encoding="utf-8"))
    texts = load_texts()
    docs = pd.read_parquet(INDEX_DIR / "docs.parquet").set_index("doc_id")
    anchor = spec["anchor_date"]

    relevant_scores: list[float] = []
    irrelevant_scores: list[float] = []
    in_scope_top: list[float] = []
    in_scope_states: dict[str, str] = {}
    weak_spot_effect: list[dict] = []

    for q in spec["queries"]:
        facts = extract_facts(texts[q["id"]], q["issue_type"], anchor).to_dict()
        unfloored = retrieve_similar(facts, q["issue_type"], k=10, apply_floor=False)
        pattern = re.compile(q["relevance_regex"], re.IGNORECASE)
        rels = []
        for case in unfloored.cases:
            rel = bool(pattern.search(str(docs.loc[case.doc_id, "text"])))
            rels.append((case.similarity, rel))
            (relevant_scores if rel else irrelevant_scores).append(case.similarity)
        top = unfloored.cases[0].similarity if unfloored.cases else 0.0
        in_scope_top.append(top)

        floored = retrieve_similar(facts, q["issue_type"], k=10, apply_floor=True)
        in_scope_states[q["id"]] = floored.query_confidence
        if q["id"] in WEAK_SPOT_IDS:
            retained = [(s, r) for s, r in rels if s >= SIM_FLOOR]
            weak_spot_effect.append(
                {
                    "id": q["id"],
                    "subtopic": q["subtopic"],
                    "state": floored.query_confidence,
                    "p_at_10_unfloored": round(sum(r for _, r in rels) / max(len(rels), 1), 3),
                    "retained": len(retained),
                    "p_retained": round(
                        sum(r for _, r in retained) / max(len(retained), 1), 3
                    ),
                }
            )

    oos_states: list[str] = []
    oos_top: list[float] = []
    for oid in OOS_IDS:
        for area in ("cheque", "consumer", "tenancy"):
            facts = extract_facts(texts[oid], area, anchor).to_dict()
            response = retrieve_similar(facts, area, k=10, apply_floor=True)
            oos_states.append(response.query_confidence)
            if response.query_confidence != "abstain":
                oos_top.append(response.cases[0].similarity)
            else:
                query = synthesize_query(facts, area)
                if len(query.split()) >= MIN_QUERY_WORDS:
                    unfloored = retrieve_similar(facts, area, k=1, apply_floor=False)
                    if unfloored.cases:
                        oos_top.append(unfloored.cases[0].similarity)

    def rate(states: list[str] | dict, value: str) -> float:
        values = list(states.values()) if isinstance(states, dict) else states
        return round(values.count(value) / len(values), 3)

    payload = {
        "thresholds": {
            "sim_floor": SIM_FLOOR,
            "sim_confident": SIM_CONFIDENT,
            "min_query_words": MIN_QUERY_WORDS,
        },
        "distributions": {
            "retrieved_relevant": _stats(relevant_scores),
            "retrieved_irrelevant": _stats(irrelevant_scores),
            "in_scope_top1": _stats(in_scope_top),
            "out_of_scope_top1": _stats(oos_top),
        },
        "in_scope_states": in_scope_states,
        "rates": {
            "in_scope": {s: rate(in_scope_states, s) for s in ("confident", "weak", "abstain")},
            "out_of_scope": {s: rate(oos_states, s) for s in ("confident", "weak", "abstain")},
        },
        "weak_spot_effect": weak_spot_effect,
    }
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(RESULTS_DIR / "abstention.json", "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)

    d = payload["distributions"]
    lines = [
        "# Retrieval abstention thresholds",
        "",
        "PROVISIONAL: these thresholds are fit on the existing 18",
        "proxy-labelled eval queries plus 30 forced out-of-scope probes.",
        "They are not human-calibrated and this is not calibration; they are",
        "a first, auditable cut at refusing to show weak results.",
        "",
        "## Score distributions (minilm / facts-synthesized / full chunks)",
        "",
        "| distribution | n | min | p25 | median | p75 | max |",
        "|---|---|---|---|---|---|---|",
    ]
    for name, key in (
        ("retrieved, proxy-relevant", "retrieved_relevant"),
        ("retrieved, proxy-irrelevant", "retrieved_irrelevant"),
        ("in-scope query top-1", "in_scope_top1"),
        ("out-of-scope query top-1", "out_of_scope_top1"),
    ):
        s = d[key]
        lines.append(
            f"| {name} | {s['n']} | {s['min']} | {s['p25']} | {s['median']} | {s['p75']} | {s['max']} |"
        )
    lines += [
        "",
        "The relevant and irrelevant distributions among retrieved results",
        "overlap almost completely, so a similarity threshold CANNOT improve",
        "precision within retrieved results and is not claimed to. What",
        "separates cleanly is in-scope versus out-of-scope query top-1",
        "similarity, once queries are content-only (issue-keyword boilerplate",
        "removed after it was measured to inflate off-topic scores).",
        "",
        "## Thresholds and their anchors",
        "",
        f"- Similarity floor {SIM_FLOOR}: just above the out-of-scope median",
        f"  top-1 ({d['out_of_scope_top1']['median']}). Below the floor nothing is shown.",
        f"- Confidence level {SIM_CONFIDENT}: just above the out-of-scope maximum",
        f"  top-1 ({d['out_of_scope_top1']['max']}). No out-of-scope probe can present",
        "  as confident.",
        f"- Minimum query content: {MIN_QUERY_WORDS} words of extractable dispute",
        "  content. Below that, the query falls back to the complaint's",
        "  non-question sentences (amounts stripped); only text still under the",
        "  minimum after fallback abstains outright.",
        "- Fallback cap: queries built from raw-text fallback are capped at",
        "  weak confidence. Fallback text never earned structured extraction,",
        "  and without the cap a vague-but-wordy probe (oth-076) scored 0.557",
        "  against the tenancy corpus and presented as confident.",
        "",
        "## Resulting rates",
        "",
        f"- In-scope (18 eval queries): {payload['rates']['in_scope']}",
        f"- Out-of-scope (30 forced probes): {payload['rates']['out_of_scope']}",
        "",
        "In-scope abstentions are thin-coverage fact patterns (for example a",
        "defective-appliance complaint against a Supreme Court appeals corpus)",
        "where declining to show cases is more honest than showing loose ones.",
        "",
        "## Effect on known weak spots",
        "",
        "| query | subtopic | state | P@10 unfloored | retained | P among retained |",
        "|---|---|---|---|---|---|",
    ]
    for w in weak_spot_effect:
        lines.append(
            f"| {w['id']} | {w['subtopic']} | {w['state']} | {w['p_at_10_unfloored']} "
            f"| {w['retained']} | {w['p_retained']} |"
        )
    lines += [
        "",
        "The floor mostly does not rescue precision on these (the overlap",
        "finding above predicts exactly that); its value is the abstain and",
        "weak states, not reranking.",
    ]
    report = "\n".join(lines) + "\n"
    (RESULTS_DIR / "abstention.md").write_text(report, encoding="utf-8")
    print(report)


if __name__ == "__main__":
    main()
