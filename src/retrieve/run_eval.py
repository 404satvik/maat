"""Retrieval quality eval plus the no-fabrication grounding check.

Configs: embedder (minilm, inlegalbert) x query mode (facts-synthesis,
raw complaint), plus a first-10-chunks variant for the best config.
Metrics per config: precision@5/@10 and hit@5/@10 under each query's
relevance predicate (a stated keyword proxy, not human adjudication).

The grounding check verifies, for every produced result: the matched
passage is verbatim from the stored judgment (modulo whitespace), every
judgment_text summary part is verbatim from the matched passage, every
expert_annotation part is verbatim from the PredEx annotation, the
outcome wording matches the dataset label, and any named appellant
appears in the case caption.

Run from the repo root:

    python -m src.retrieve.run_eval
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd

from src.extract import extract_facts
from src.retrieve.retrieve import RetrievedCase, retrieve_similar

EVAL_PATH = Path("data/eval/retrieval_eval.json")
SEED_DIR = Path("data/seed")
INDEX_DIR = Path("index")
RESULTS_DIR = Path("results")
K_VALUES = (5, 10)


def load_texts() -> dict[str, str]:
    """Map complaint id to text across seed and probe files."""
    frames = [
        pd.read_csv(SEED_DIR / name, dtype=str)
        for name in ("consumer.csv", "cheque.csv", "tenancy.csv", "other.csv", "probe.csv")
    ]
    combined = pd.concat(frames, ignore_index=True)
    return dict(zip(combined["id"], combined["text"]))


def _norm(text: str) -> str:
    """Whitespace-normalized text for verbatim containment checks."""
    return re.sub(r"\s+", " ", text).strip().lower()


def grounding_check(result: RetrievedCase, docs: pd.DataFrame) -> list[str]:
    """Return a list of grounding violations for one result (empty = clean)."""
    violations: list[str] = []
    doc = docs.loc[result.doc_id]
    doc_text = _norm(str(doc["text"]))
    if _norm(result.matched_passage) not in doc_text:
        violations.append("matched_passage not verbatim in judgment")
    for part in result.summary:
        if part.source == "judgment_text":
            if _norm(part.text) not in _norm(result.matched_passage):
                violations.append("judgment_text part not verbatim in matched passage")
        elif part.source == "expert_annotation":
            if _norm(part.text) not in _norm(str(doc["expert_explanation"])):
                violations.append("expert_annotation part not verbatim in annotation")
        elif part.source == "dataset_label":
            verdict = "granted" if int(doc["label"]) == 1 else "denied"
            if verdict not in part.text:
                violations.append("outcome wording contradicts dataset label")
            m = re.search(r"brought by (.+?),", part.text)
            if m and m.group(1).split()[0].lower() not in str(doc["case_name"]).lower():
                violations.append("named appellant not in case caption")
        else:
            violations.append(f"unknown summary source {part.source}")
    return violations


def run_config(
    queries: list[dict],
    texts: dict[str, str],
    anchor: str,
    embedder: str,
    query_mode: str,
    docs: pd.DataFrame,
    max_chunk_pos: int | None = None,
) -> tuple[dict, list[RetrievedCase]]:
    """Metrics for one embedder x query-mode config; returns all results too."""
    per_query: list[dict] = []
    produced: list[RetrievedCase] = []
    for q in queries:
        text = texts[q["id"]]
        if query_mode == "facts":
            facts = extract_facts(text, q["issue_type"], anchor).to_dict()
            payload: dict | str = facts
        else:
            payload = text
        results = retrieve_similar(
            payload, q["issue_type"], k=max(K_VALUES), embedder=embedder, max_chunk_pos=max_chunk_pos
        )
        produced.extend(results)
        pattern = re.compile(q["relevance_regex"], re.IGNORECASE)
        relevant = [bool(pattern.search(str(docs.loc[r.doc_id, "text"]))) for r in results]
        entry = {"id": q["id"], "subtopic": q["subtopic"]}
        for k in K_VALUES:
            top = relevant[:k]
            entry[f"p_at_{k}"] = round(sum(top) / k, 3)
            entry[f"hit_at_{k}"] = int(any(top))
        per_query.append(entry)
    variant = f"first{max_chunk_pos}" if max_chunk_pos else "full"
    summary = {
        "embedder": embedder,
        "query_mode": query_mode,
        "chunks": variant,
        "n_queries": len(queries),
    }
    for k in K_VALUES:
        summary[f"p_at_{k}"] = round(sum(e[f"p_at_{k}"] for e in per_query) / len(per_query), 3)
        summary[f"hit_at_{k}"] = round(sum(e[f"hit_at_{k}"] for e in per_query) / len(per_query), 3)
    summary["per_query"] = per_query
    return summary, produced


def main() -> None:
    """Run all configs, the grounding check, and write results."""
    spec = json.loads(EVAL_PATH.read_text(encoding="utf-8"))
    texts = load_texts()
    docs = pd.read_parquet(INDEX_DIR / "docs.parquet").set_index("doc_id")
    manifest = json.loads((INDEX_DIR / "manifest.json").read_text(encoding="utf-8"))

    runs: list[tuple[str, str, int | None]] = [
        ("minilm", "facts", None),
        ("minilm", "raw", None),
        ("inlegalbert", "facts", None),
        ("inlegalbert", "raw", None),
        ("minilm", "facts", 10),
        ("minilm", "raw", 10),
    ]
    configs: list[dict] = []
    all_results: list[RetrievedCase] = []
    for embedder, query_mode, max_pos in runs:
        summary, produced = run_config(
            spec["queries"], texts, spec["anchor_date"], embedder, query_mode, docs, max_pos
        )
        configs.append(summary)
        all_results.extend(produced)
        print(
            f"{embedder}/{query_mode}/{summary['chunks']}: P@5 {summary['p_at_5']:.3f} "
            f"P@10 {summary['p_at_10']:.3f} hit@5 {summary['hit_at_5']:.3f} "
            f"hit@10 {summary['hit_at_10']:.3f}"
        )

    checked = 0
    violations: list[dict] = []
    for result in all_results:
        problems = grounding_check(result, docs)
        checked += 1
        if problems:
            violations.append({"doc_id": result.doc_id, "problems": problems})

    payload = {
        "corpus": {k: manifest[k] for k in ("corpus", "n_docs", "n_chunks", "per_area", "coverage_note")},
        "relevance_note": spec["description"],
        "configs": [{k: v for k, v in c.items() if k != "per_query"} for c in configs],
        "per_query": {
            f"{c['embedder']}/{c['query_mode']}/{c['chunks']}": c["per_query"] for c in configs
        },
        "grounding_check": {
            "results_checked": checked,
            "violations": violations,
            "clean": not violations,
        },
    }
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(RESULTS_DIR / "retrieval_metrics.json", "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)

    lines = [
        "# Retrieval eval",
        "",
        f"Corpus: {manifest['corpus']}, {manifest['n_docs']} filtered docs, "
        f"{manifest['n_chunks']} chunks. Per area: {manifest['per_area']}.",
        "",
        "Relevance is a keyword-predicate proxy (stated in the eval file), not",
        "human adjudication; numbers are directional.",
        "",
        "| embedder | query mode | chunks | P@5 | P@10 | hit@5 | hit@10 |",
        "|---|---|---|---|---|---|---|",
    ]
    for c in configs:
        lines.append(
            f"| {c['embedder']} | {c['query_mode']} | {c['chunks']} | {c['p_at_5']:.3f} "
            f"| {c['p_at_10']:.3f} | {c['hit_at_5']:.3f} | {c['hit_at_10']:.3f} |"
        )
    lines += [
        "",
        f"Grounding check: {checked} results checked, "
        f"{len(violations)} violations."
        + (" All summaries verbatim-traceable to their sources." if not violations else ""),
    ]
    report = "\n".join(lines) + "\n"
    (RESULTS_DIR / "retrieval_metrics.md").write_text(report, encoding="utf-8")
    print(report)


if __name__ == "__main__":
    main()
