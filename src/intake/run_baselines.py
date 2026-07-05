"""Run the intake baselines and write metrics to results/.

Produces results/baseline_metrics.json and results/baseline_metrics.md.
Reproducible end to end with the fixed seed; no tuning against test or
probe is performed anywhere in this script.

Run from the repo root:

    python -m src.intake.run_baselines
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from src.intake.baseline import (
    MODEL_NAMES,
    RANDOM_SEED,
    cross_validate_originals,
    fixed_split_eval,
)
from src.intake.data import LABELS, load_seed

SEED_DIR = Path("data/seed")
PROCESSED_DIR = Path("data/processed")
RESULTS_DIR = Path("results")
MODELS_DIR = Path("models/intake-baselines")
N_SPLITS = 5
N_VARIANTS = 3


def format_confusion(matrix: list[list[int]]) -> str:
    """Render a confusion matrix with true labels as rows."""
    width = max(len(lbl) for lbl in LABELS) + 2
    header = " " * width + "".join(f"{lbl:>{width}}" for lbl in LABELS)
    lines = [header]
    for label, row in zip(LABELS, matrix):
        lines.append(f"{label:<{width}}" + "".join(f"{n:>{width}}" for n in row))
    return "\n".join(lines)


def build_report(cv: dict, fixed: dict) -> str:
    """Render all metrics as a markdown report."""
    lines = [
        "# Intake baseline metrics",
        "",
        f"Seed {RANDOM_SEED}, {N_SPLITS}-fold group-aware stratified CV over the 320",
        f"seed originals with {N_VARIANTS} augmentation variants applied inside each",
        "fold to training seeds only. Fixed-split rows train on the pinned train",
        "split and evaluate on the authored test set (n=48) and the real-world",
        "probe set (n=48). Probe numbers are directional at this sample size;",
        "the authored-versus-probe gap is the insight, not small model deltas.",
        "",
        "## Cross-validation (held-out originals)",
        "",
        "| model | macro-F1 | other recall |",
        "|---|---|---|",
    ]
    for name in MODEL_NAMES:
        r = cv[name]
        lines.append(
            f"| {name} | {r['macro_f1_mean']:.3f} +/- {r['macro_f1_std']:.3f} "
            f"| {r['other_recall_mean']:.3f} +/- {r['other_recall_std']:.3f} |"
        )
    lines += ["", "## Fixed split (train on pinned train split)", ""]
    lines += ["| model | eval set | accuracy | macro-P | macro-R | macro-F1 | other recall |", "|---|---|---|---|---|---|---|"]
    for name in MODEL_NAMES:
        for eval_name in ("test", "probe"):
            r = fixed[name][eval_name]
            lines.append(
                f"| {name} | {eval_name} | {r['accuracy']:.3f} | {r['macro_precision']:.3f} "
                f"| {r['macro_recall']:.3f} | {r['macro_f1']:.3f} | {r['other_recall']:.3f} |"
            )
    for name in MODEL_NAMES:
        if name == "majority":
            continue
        for eval_name in ("test", "probe"):
            r = fixed[name][eval_name]
            lines += [
                "",
                f"### Confusion matrix: {name} on {eval_name}",
                "",
                "```",
                format_confusion(r["confusion_matrix"]),
                "```",
            ]
    lines += ["", "### Per-class metrics (fixed split)", ""]
    lines += ["| model | eval set | class | precision | recall | F1 | support |", "|---|---|---|---|---|---|---|"]
    for name in MODEL_NAMES:
        if name == "majority":
            continue
        for eval_name in ("test", "probe"):
            for label in LABELS:
                c = fixed[name][eval_name]["per_class"][label]
                lines.append(
                    f"| {name} | {eval_name} | {label} | {c['precision']:.3f} "
                    f"| {c['recall']:.3f} | {c['f1']:.3f} | {c['support']} |"
                )
    return "\n".join(lines) + "\n"


def main() -> None:
    """Run CV and fixed-split evaluation for all models and save results."""
    originals = load_seed(SEED_DIR)
    train = pd.read_csv(PROCESSED_DIR / "train.csv", dtype=str)
    eval_sets = {
        "test": pd.read_csv(PROCESSED_DIR / "test.csv", dtype=str),
        "probe": pd.read_csv(PROCESSED_DIR / "probe.csv", dtype=str),
    }

    cv = {name: cross_validate_originals(originals, name, N_SPLITS, N_VARIANTS) for name in MODEL_NAMES}
    fixed = {
        name: fixed_split_eval(
            train,
            eval_sets,
            name,
            save_path=None if name == "majority" else MODELS_DIR / f"{name}.joblib",
        )
        for name in MODEL_NAMES
    }

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "config": {
            "random_seed": RANDOM_SEED,
            "n_splits": N_SPLITS,
            "n_variants": N_VARIANTS,
            "vectorizer": "TfidfVectorizer(ngram_range=(1,2), min_df=2, sublinear_tf=True)",
            "models": {
                "majority": "DummyClassifier(strategy='most_frequent')",
                "tfidf_logreg": "LogisticRegression(max_iter=2000)",
                "tfidf_linearsvc": "LinearSVC(dual='auto')",
            },
        },
        "cv": cv,
        "fixed_split": fixed,
    }
    with open(RESULTS_DIR / "baseline_metrics.json", "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)
    report = build_report(cv, fixed)
    (RESULTS_DIR / "baseline_metrics.md").write_text(report, encoding="utf-8")
    print(report)
    print(f"Wrote {RESULTS_DIR}/baseline_metrics.json and {RESULTS_DIR}/baseline_metrics.md")


if __name__ == "__main__":
    main()
