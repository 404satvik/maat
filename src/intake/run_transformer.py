"""Fine-tune InLegalBERT across multiple seeds and build the combined
baseline-versus-transformer comparison.

Reads the pinned splits from data/processed/ (identical to the baseline
runs, no re-splitting), fine-tunes once per seed, evaluates every run on
the authored test set and the real-world probe set, and writes:

    results/transformer_metrics.json   per-run and aggregate metrics
    results/intake_comparison.md       combined table plus honest writeup

The saved checkpoint in models/inlegalbert-intake/ is the run with the
best VAL macro-F1 (never selected on test or probe).

Runs on a free Colab or Kaggle GPU: upload the repo, pip install the
pinned requirements, then from the repo root:

    python -m src.intake.run_transformer
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from src.intake.baseline import evaluate
from src.intake.data import LABELS
from src.intake.run_baselines import format_confusion
from src.intake.transformer import (
    FinetuneConfig,
    count_truncated,
    finetune,
    pick_device,
    predict,
)

PROCESSED_DIR = Path("data/processed")
RESULTS_DIR = Path("results")
MODELS_DIR = Path("models/inlegalbert-intake")
SEEDS: tuple[int, ...] = (42, 43, 44, 45, 46)


def aggregate_runs(run_metrics: list[dict], eval_name: str) -> dict:
    """Mean and std of the headline metrics across runs for one eval set."""
    out: dict[str, float] = {}
    for key in ("accuracy", "macro_f1", "other_recall"):
        values = [r[eval_name][key] for r in run_metrics]
        out[f"{key}_mean"] = round(float(np.mean(values)), 4)
        out[f"{key}_std"] = round(float(np.std(values)), 4)
    return out


def pooled_eval(y_true: list[str], preds_by_run: list[list[str]]) -> dict:
    """Full metric bundle over predictions pooled across all runs."""
    pooled_true = y_true * len(preds_by_run)
    pooled_pred = [p for preds in preds_by_run for p in preds]
    return evaluate(pooled_true, pooled_pred)


def comparison_verdict(delta: float, cv_std: float) -> str:
    """Describe a test-set delta relative to the baseline CV fold std."""
    if delta > cv_std:
        return "clearly ahead (more than one CV std)"
    if delta < -cv_std:
        return "clearly behind (more than one CV std)"
    return "within noise (less than one CV std)"


def build_writeup(agg: dict, baseline_fixed: dict, baseline_cv: dict) -> str:
    """Data-driven honest paragraph comparing InLegalBERT to LogReg."""
    logreg_test = baseline_fixed["tfidf_logreg"]["test"]["macro_f1"]
    logreg_probe = baseline_fixed["tfidf_logreg"]["probe"]["macro_f1"]
    cv_std = baseline_cv["tfidf_logreg"]["macro_f1_std"]
    d_test = agg["test"]["macro_f1_mean"] - logreg_test
    d_probe = agg["probe"]["macro_f1_mean"] - logreg_probe
    lines = [
        "## Honest comparison writeup",
        "",
        f"Against the linear reference (TF-IDF + LogReg, the better CV other-class",
        f"recall of the two baselines), InLegalBERT lands at macro-F1"
        f" {agg['test']['macro_f1_mean']:.3f} +/- {agg['test']['macro_f1_std']:.3f} on the authored"
        f" test set versus {logreg_test:.3f} for LogReg (delta {d_test:+.3f}),"
        f" and {agg['probe']['macro_f1_mean']:.3f} +/- {agg['probe']['macro_f1_std']:.3f} on the"
        f" probe set versus {logreg_probe:.3f} (delta {d_probe:+.3f}).",
        f"Measured against the baseline CV fold std of {cv_std:.3f}, the test-set"
        f" difference is {comparison_verdict(d_test, cv_std)} and the probe"
        f" difference is {comparison_verdict(d_probe, cv_std)}.",
        "",
        "Reading either way: complaints are short and keyword-dense, which is",
        "close to the best case for a TF-IDF linear model, while InLegalBERT is",
        "pretrained on formal judgment prose (a register mismatch with colloquial",
        "and Hinglish complaint text) and fine-tuned here on only about 224",
        "original seeds per class plus surface-level variants. A transformer win",
        "would need to come from reading context rather than keywords, for",
        "example separating a bounced rent cheque from a plain deposit dispute,",
        "or catching vague other-class texts that share no vocabulary with",
        "training. Sample sizes are small (n=48 per eval set, about 12 per",
        "class), so probe numbers are directional and only differences well",
        "beyond one CV std should be taken as real.",
    ]
    if d_test > cv_std and abs(d_probe) <= cv_std:
        lines += [
            "",
            "That is the pattern observed here: the transformer pulls clearly",
            "ahead on the authored test set, which deliberately concentrates",
            "boundary cases and vaguer phrasings, while on the keyword-dense",
            "probe set the linear model already captures most of the signal",
            "and the difference stays within noise.",
        ]
    return "\n".join(lines)


def build_report(
    agg: dict,
    pooled: dict,
    runs: list[dict],
    baseline_fixed: dict,
    baseline_cv: dict,
    config: FinetuneConfig,
    truncated: dict[str, int],
) -> str:
    """Render the combined comparison as markdown."""
    lines = [
        "# Intake classifier: baselines versus InLegalBERT",
        "",
        f"InLegalBERT ({config.model_name}) fine-tuned for 4-class sequence",
        f"classification on the pinned train split, {len(runs)} runs with seeds",
        f"{[r['info']['seed'] for r in runs]}. Checkpoint selection per run: best val macro-F1",
        f"(epochs={config.epochs}, batch={config.batch_size}, lr={config.lr},",
        f"weight_decay={config.weight_decay}, warmup={config.warmup_frac},",
        f"max_length={config.max_length}, truncation only, no tuning against test",
        "or probe). Texts exceeding max_length before truncation:",
        f"train {truncated['train']}, val {truncated['val']}, test {truncated['test']},"
        f" probe {truncated['probe']}.",
        "",
        "Baseline rows are single fixed-split runs (deterministic given the",
        "seed); InLegalBERT rows are mean +/- std across the fine-tune seeds.",
        "",
        "## Combined comparison (fixed split)",
        "",
        "| model | eval set | accuracy | macro-F1 | other recall |",
        "|---|---|---|---|---|",
    ]
    for name in ("majority", "tfidf_logreg", "tfidf_linearsvc"):
        for eval_name in ("test", "probe"):
            r = baseline_fixed[name][eval_name]
            lines.append(
                f"| {name} | {eval_name} | {r['accuracy']:.3f} "
                f"| {r['macro_f1']:.3f} | {r['other_recall']:.3f} |"
            )
    for eval_name in ("test", "probe"):
        a = agg[eval_name]
        lines.append(
            f"| inlegalbert | {eval_name} | {a['accuracy_mean']:.3f} +/- {a['accuracy_std']:.3f} "
            f"| {a['macro_f1_mean']:.3f} +/- {a['macro_f1_std']:.3f} "
            f"| {a['other_recall_mean']:.3f} +/- {a['other_recall_std']:.3f} |"
        )
    for eval_name in ("test", "probe"):
        lines += [
            "",
            f"## InLegalBERT on {eval_name}: pooled over {len(runs)} runs",
            "",
            "Confusion matrix (counts summed across runs):",
            "",
            "```",
            format_confusion(pooled[eval_name]["confusion_matrix"]),
            "```",
            "",
            "| class | precision | recall | F1 | support |",
            "|---|---|---|---|---|",
        ]
        for label in LABELS:
            c = pooled[eval_name]["per_class"][label]
            lines.append(
                f"| {label} | {c['precision']:.3f} | {c['recall']:.3f} "
                f"| {c['f1']:.3f} | {c['support']} |"
            )
    lines += ["", build_writeup(agg, baseline_fixed, baseline_cv), ""]
    return "\n".join(lines)


def main() -> None:
    """Run the multi-seed fine-tune experiment and write all results."""
    train = pd.read_csv(PROCESSED_DIR / "train.csv", dtype=str)
    val = pd.read_csv(PROCESSED_DIR / "val.csv", dtype=str)
    eval_sets = {
        "test": pd.read_csv(PROCESSED_DIR / "test.csv", dtype=str),
        "probe": pd.read_csv(PROCESSED_DIR / "probe.csv", dtype=str),
    }
    config = FinetuneConfig()
    device = pick_device()
    print(f"Device: {device}")

    runs: list[dict] = []
    preds_by_run: dict[str, list[list[str]]] = {"test": [], "probe": []}
    best_val = -1.0
    for seed in SEEDS:
        model, tokenizer, info = finetune(train, val, seed, config)
        metrics: dict = {"info": info}
        for name, frame in eval_sets.items():
            pred = predict(model, tokenizer, frame["text"].tolist(), device)
            metrics[name] = evaluate(frame["label"].tolist(), pred)
            preds_by_run[name].append(pred)
        runs.append(metrics)
        print(
            f"seed {seed}: best epoch {info['best_epoch']} "
            f"(val {info['best_val_macro_f1']:.3f}), "
            f"test macro-F1 {metrics['test']['macro_f1']:.3f}, "
            f"probe macro-F1 {metrics['probe']['macro_f1']:.3f}"
        )
        if info["best_val_macro_f1"] > best_val:
            best_val = info["best_val_macro_f1"]
            MODELS_DIR.mkdir(parents=True, exist_ok=True)
            model.save_pretrained(MODELS_DIR)
            tokenizer.save_pretrained(MODELS_DIR)

    tokenizer_for_stats = tokenizer
    truncated = {
        name: count_truncated(frame["text"].tolist(), tokenizer_for_stats, config.max_length)
        for name, frame in {"train": train, "val": val, **eval_sets}.items()
    }

    agg = {name: aggregate_runs(runs, name) for name in ("test", "probe")}
    pooled = {
        name: pooled_eval(eval_sets[name]["label"].tolist(), preds_by_run[name])
        for name in ("test", "probe")
    }

    with open(RESULTS_DIR / "baseline_metrics.json", encoding="utf-8") as fh:
        baseline = json.load(fh)

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "config": {
            "model_name": config.model_name,
            "seeds": list(SEEDS),
            "epochs": config.epochs,
            "batch_size": config.batch_size,
            "lr": config.lr,
            "weight_decay": config.weight_decay,
            "warmup_frac": config.warmup_frac,
            "max_length": config.max_length,
            "checkpoint_selection": "best val macro-F1 per run; saved run chosen by val only",
            "device": str(device),
        },
        "truncated_counts": truncated,
        "runs": runs,
        "aggregate": agg,
        "pooled": pooled,
    }
    with open(RESULTS_DIR / "transformer_metrics.json", "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)

    report = build_report(
        agg, pooled, runs, baseline["fixed_split"], baseline["cv"], config, truncated
    )
    (RESULTS_DIR / "intake_comparison.md").write_text(report, encoding="utf-8")
    print()
    print(report)
    print(
        f"Wrote {RESULTS_DIR}/transformer_metrics.json, "
        f"{RESULTS_DIR}/intake_comparison.md, checkpoint in {MODELS_DIR}/"
    )


if __name__ == "__main__":
    main()
