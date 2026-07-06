"""Evaluate the fact extractor against the hand-annotated eval set.

Measures precision/recall/F1 per field type (amounts, dates, parties,
places), role accuracy on matched parties, and timeline-event recall.
Writes results/extraction_metrics.json and .md. Fully deterministic.

Run from the repo root:

    python -m src.extract.run_eval
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from src.extract.facts import extract_facts

EVAL_PATH = Path("data/eval/extraction_eval.json")
SEED_DIR = Path("data/seed")
RESULTS_DIR = Path("results")

SEED_FILES = ("consumer.csv", "cheque.csv", "tenancy.csv", "other.csv", "probe.csv")


def load_texts() -> dict[str, str]:
    """Map complaint id to text across all seed and probe files."""
    frames = [pd.read_csv(SEED_DIR / name, dtype=str) for name in SEED_FILES]
    combined = pd.concat(frames, ignore_index=True)
    return dict(zip(combined["id"], combined["text"]))


def prf(tp: int, fp: int, fn: int) -> dict[str, float]:
    """Precision, recall, F1 from counts."""
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "tp": tp, "fp": fp, "fn": fn,
        "precision": round(precision, 3),
        "recall": round(recall, 3),
        "f1": round(f1, 3),
    }


def match_amounts(gold: list[int], extracted: list[int]) -> tuple[int, int, int]:
    """Multiset match on normalized integer values."""
    remaining = list(extracted)
    tp = 0
    for value in gold:
        if value in remaining:
            remaining.remove(value)
            tp += 1
    return tp, len(remaining), len(gold) - tp


def match_dates(gold: list[dict], extracted: list[dict]) -> tuple[int, int, int]:
    """Greedy match: ISO equality first, then raw equality, then containment."""
    remaining = list(range(len(extracted)))
    tp = 0
    for phase in ("iso", "raw", "contains"):
        for g in list(gold):
            hit = None
            for i in remaining:
                ext = extracted[i]
                if phase == "iso" and g["iso"] and ext["iso"] == g["iso"]:
                    hit = i
                elif phase == "raw" and ext["raw"].lower() == g["raw"].lower():
                    hit = i
                elif phase == "contains" and (
                    g["raw"].lower() in ext["raw"].lower() or ext["raw"].lower() in g["raw"].lower()
                ):
                    hit = i
                if hit is not None:
                    break
            if hit is not None:
                remaining.remove(hit)
                gold = [x for x in gold if x is not g]
                tp += 1
    return tp, len(remaining), len(gold)


def match_parties(gold: list[dict], extracted: list[dict]) -> tuple[int, int, int, int, int]:
    """Match by word against role_word/mention/name; role scored separately.

    Only non-complainant extracted parties are scored; complainant
    detection is trivial first-person matching and not measured.
    Returns tp, fp, fn, role_correct, role_total.
    """
    candidates = [p for p in extracted if p["role"] != "complainant"]
    remaining = list(range(len(candidates)))
    tp = fn = role_correct = role_total = 0
    for g in gold:
        word = g["word"].lower()
        hit = None
        for i in remaining:
            party = candidates[i]
            haystacks = [party["role_word"] or "", party["mention"], party["name"] or ""]
            if any(word in h.lower() for h in haystacks):
                hit = i
                break
        if hit is None:
            fn += 1
            continue
        remaining.remove(hit)
        tp += 1
        role_total += 1
        if candidates[hit]["role"] == g["role"]:
            role_correct += 1
    return tp, len(remaining), fn, role_correct, role_total


def match_places(gold: list[str], extracted: list[str]) -> tuple[int, int, int]:
    """Set match on normalized place names."""
    gold_set = {g.lower() for g in gold}
    ext_set = {e.lower() for e in extracted}
    tp = len(gold_set & ext_set)
    return tp, len(ext_set - gold_set), len(gold_set - ext_set)


def event_recall(gold: list[str], descriptions: list[str]) -> tuple[int, int]:
    """Gold events covered by some extracted timeline description."""
    lowered = [d.lower() for d in descriptions]
    covered = sum(1 for g in gold if any(g.lower() in d for d in lowered))
    return covered, len(gold)


def main() -> None:
    """Run the eval and write metrics."""
    spec = json.loads(EVAL_PATH.read_text(encoding="utf-8"))
    texts = load_texts()
    anchor = spec["anchor_date"]

    counts = {name: [0, 0, 0] for name in ("amounts", "dates", "parties", "places")}
    role_correct = role_total = events_covered = events_total = 0
    per_item: list[dict] = []

    for item in spec["items"]:
        text = texts[item["id"]]
        facts = extract_facts(text, item["issue_type"], anchor).to_dict()
        gold = item["gold"]

        a = match_amounts(gold["amounts"], [x["value"] for x in facts["amounts"]])
        d = match_dates(gold["dates"], facts["dates"])
        p = match_parties(gold["parties"], facts["parties"])
        g = match_places(gold["places"], [x["normalized"] for x in facts["places"]])
        e = event_recall(gold["events"], [x["description"] for x in facts["timeline"]])

        for name, res in (("amounts", a), ("dates", d), ("parties", p[:3]), ("places", g)):
            for j in range(3):
                counts[name][j] += res[j]
        role_correct += p[3]
        role_total += p[4]
        events_covered += e[0]
        events_total += e[1]
        per_item.append(
            {
                "id": item["id"],
                "amounts": a, "dates": d, "parties": p[:3], "places": g,
                "events_covered": e[0], "events_total": e[1],
            }
        )

    metrics = {name: prf(*counts[name]) for name in counts}
    summary = {
        "anchor_date": anchor,
        "n_items": len(spec["items"]),
        "fields": metrics,
        "party_role_accuracy": round(role_correct / role_total, 3) if role_total else None,
        "timeline_event_recall": round(events_covered / events_total, 3),
        "timeline_events_covered": events_covered,
        "timeline_events_total": events_total,
        "per_item": per_item,
    }

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(RESULTS_DIR / "extraction_metrics.json", "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2)

    lines = [
        "# Extraction eval (25 hand-annotated complaints)",
        "",
        f"Anchor date {anchor}. Gold includes known-hard items (Hindi relative",
        "dates, sub-1000 amounts, Hinglish role words), so these numbers reflect",
        "real weaknesses, not a friendly subset.",
        "",
        "| field | precision | recall | F1 | tp | fp | fn |",
        "|---|---|---|---|---|---|---|",
    ]
    for name, m in metrics.items():
        lines.append(
            f"| {name} | {m['precision']:.3f} | {m['recall']:.3f} | {m['f1']:.3f} "
            f"| {m['tp']} | {m['fp']} | {m['fn']} |"
        )
    lines += [
        "",
        f"Party role accuracy on matched parties: {summary['party_role_accuracy']}",
        f"Timeline event recall: {summary['timeline_event_recall']} "
        f"({events_covered}/{events_total})",
    ]
    report = "\n".join(lines) + "\n"
    (RESULTS_DIR / "extraction_metrics.md").write_text(report, encoding="utf-8")
    print(report)
    worst = sorted(per_item, key=lambda x: x["events_covered"] - x["events_total"])[:5]
    print("Hardest items by missed events:", [(w["id"], f"{w['events_covered']}/{w['events_total']}") for w in worst])


if __name__ == "__main__":
    main()
