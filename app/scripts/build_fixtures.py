"""Generate real-pipeline fixtures for the web UI preview build.

The first-pass UI mocks TRANSPORT only. Every fixture here is produced
by the actual pipeline (fine-tuned classifier checkpoint, extractor,
retrieval index, explainers, prep pack, draft renderer), so the data the
UI shows is genuine pipeline output for three sample complaints.

Run from the repo root with the project venv:

    .venv/bin/python app/scripts/build_fixtures.py
"""

from __future__ import annotations

import dataclasses
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.draft import build_prep_pack, draft_s138_notice
from src.explain import explain_pathways, explain_rights
from src.extract import extract_facts
from src.intake.infer import classify, load_classifier
from src.retrieve import retrieve_similar

OUT_DIR = Path("app/src/fixtures")
ANCHOR_DATE = "2026-07-08"

SCENARIOS: tuple[tuple[str, str, str], ...] = (
    (
        "cheque-bounce",
        "A customer's cheque bounced",
        "A customer gave me a cheque of Rs 1,20,000 for goods supplied to "
        "his shop. The bank returned it saying insufficient funds. He keeps "
        "promising to pay next week but nothing comes.",
    ),
    (
        "tenancy-deposit",
        "Landlord will not return the deposit",
        "I vacated my rented flat two months ago after giving proper "
        "notice. The landlord has not returned my security deposit of "
        "Rs 50,000 and now claims painting charges that were never "
        "mentioned in the agreement.",
    ),
    (
        "unclear-family",
        "A family matter, hard to describe",
        "There is a dispute in our family and it has become very ugly. "
        "Everyone has said things and done things. I do not even know "
        "where to start explaining. Can a lawyer just listen to everything "
        "first?",
    ),
)


def main() -> None:
    """Run the pipeline for each scenario and write one JSON per fixture."""
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    clf = load_classifier("inlegalbert")
    for scenario_id, title, complaint in SCENARIOS:
        label = classify(clf, complaint)[0]
        facts = extract_facts(complaint, label.label, ANCHOR_DATE).to_dict()
        retrieval = retrieve_similar(facts, label.label, k=5)
        rights = explain_rights(label.label, facts)
        pathways = explain_pathways(label.label, facts)
        prep_pack = build_prep_pack(label.label, facts)
        draft = draft_s138_notice(facts) if label.label == "cheque" else None
        payload = {
            "id": scenario_id,
            "title": title,
            "complaint": complaint,
            "anchor_date": ANCHOR_DATE,
            "classification": dataclasses.asdict(label),
            "facts": facts,
            "retrieval": retrieval.to_dict(),
            "rights": rights.to_dict(),
            "pathways": pathways.to_dict(),
            "prep_pack": prep_pack.to_dict(),
            "draft": draft.to_dict() if draft else None,
        }
        path = OUT_DIR / f"{scenario_id}.json"
        path.write_text(json.dumps(payload, indent=1, ensure_ascii=False), encoding="utf-8")
        print(
            f"{scenario_id}: label={label.label} ({label.score}), "
            f"retrieval={retrieval.query_confidence}, rights={rights.status}, "
            f"draft={'yes' if draft else 'none'} -> {path}"
        )


if __name__ == "__main__":
    main()
