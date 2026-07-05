"""Inference entry point for the intake issue-triage classifier.

This is the module later phases import to classify a user's complaint:

    from src.intake.infer import load_classifier, classify

    clf = load_classifier("inlegalbert")
    result = classify(clf, "My landlord will not return my deposit.")[0]
    result.label, result.score

Torch and transformers are imported lazily, so loading a scikit-learn
model does not require the transformer stack to be installed.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Sequence

import numpy as np

from src.intake.data import normalize_text

ClassifierKind = Literal["logreg", "linearsvc", "inlegalbert"]

DEFAULT_PATHS: dict[str, Path] = {
    "logreg": Path("models/intake-baselines/tfidf_logreg.joblib"),
    "linearsvc": Path("models/intake-baselines/tfidf_linearsvc.joblib"),
    "inlegalbert": Path("models/inlegalbert-intake"),
}

_BATCH_SIZE = 32


@dataclass(frozen=True)
class Classification:
    """One classification result.

    score_type is "probability" for logreg and inlegalbert. For linearsvc
    it is "margin": softmax-normalized decision margins that rank classes
    correctly but are NOT calibrated probabilities.
    """

    label: str
    score: float
    score_type: str
    scores: dict[str, float]


@dataclass(frozen=True)
class LoadedClassifier:
    """A loaded classifier plus what classify() needs to run it."""

    kind: str
    model: object
    tokenizer: object | None = None


def load_classifier(kind: ClassifierKind, path: str | Path | None = None) -> LoadedClassifier:
    """Load a persisted intake classifier from models/.

    kind selects the backend; path overrides the default location for that
    kind. Raises FileNotFoundError if nothing is persisted at the path.
    """
    if kind not in DEFAULT_PATHS:
        raise ValueError(f"unknown classifier kind: {kind!r}")
    resolved = Path(path) if path is not None else DEFAULT_PATHS[kind]
    if not resolved.exists():
        raise FileNotFoundError(
            f"no persisted {kind} classifier at {resolved}; run the matching "
            "training script first"
        )
    if kind in ("logreg", "linearsvc"):
        import joblib

        return LoadedClassifier(kind=kind, model=joblib.load(resolved))
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    from src.intake.transformer import pick_device

    device = pick_device()
    model = AutoModelForSequenceClassification.from_pretrained(resolved).to(device)
    model.eval()
    tokenizer = AutoTokenizer.from_pretrained(resolved)
    return LoadedClassifier(kind=kind, model=model, tokenizer=tokenizer)


def _softmax(rows: np.ndarray) -> np.ndarray:
    """Row-wise stable softmax."""
    shifted = rows - rows.max(axis=1, keepdims=True)
    exp = np.exp(shifted)
    return exp / exp.sum(axis=1, keepdims=True)


def _bundle(rows: np.ndarray, classes: Sequence[str], score_type: str) -> list[Classification]:
    """Turn a score matrix (one row per text) into Classification results."""
    results: list[Classification] = []
    for row in rows:
        best = int(np.argmax(row))
        results.append(
            Classification(
                label=str(classes[best]),
                score=round(float(row[best]), 4),
                score_type=score_type,
                scores={str(c): round(float(v), 4) for c, v in zip(classes, row)},
            )
        )
    return results


def _transformer_scores(clf: LoadedClassifier, texts: list[str]) -> tuple[np.ndarray, list[str]]:
    """Softmax probabilities and label order for the transformer backend."""
    import torch

    from src.intake.transformer import MAX_LENGTH

    device = next(clf.model.parameters()).device
    chunks: list[np.ndarray] = []
    with torch.no_grad():
        for start in range(0, len(texts), _BATCH_SIZE):
            batch = clf.tokenizer(
                texts[start : start + _BATCH_SIZE],
                truncation=True,
                max_length=MAX_LENGTH,
                padding=True,
                return_tensors="pt",
            ).to(device)
            logits = clf.model(**batch).logits
            chunks.append(torch.softmax(logits, dim=-1).cpu().numpy())
    probs = np.vstack(chunks)
    id2label = clf.model.config.id2label
    classes = [id2label[i] for i in range(probs.shape[1])]
    return probs, classes


def classify(clf: LoadedClassifier, texts: str | Sequence[str]) -> list[Classification]:
    """Classify one complaint or a sequence of complaints.

    Always returns a list (length 1 for a single string). Text is
    normalized the same way as at training time. Scores are true
    probabilities for logreg and inlegalbert; for linearsvc they are
    softmax-normalized decision margins, not calibrated probabilities.
    """
    items = [texts] if isinstance(texts, str) else list(texts)
    items = [normalize_text(t) for t in items]
    if not items:
        return []
    if clf.kind == "logreg":
        return _bundle(clf.model.predict_proba(items), clf.model.classes_, "probability")
    if clf.kind == "linearsvc":
        margins = clf.model.decision_function(items)
        return _bundle(_softmax(np.asarray(margins)), clf.model.classes_, "margin")
    probs, classes = _transformer_scores(clf, items)
    return _bundle(probs, classes, "probability")


if __name__ == "__main__":
    examples = [
        "My landlord is refusing to return my security deposit of Rs 40,000.",
        "The cheque my client gave me for finished work came back unpaid twice.",
        "My cousin will not repay the cash I lent him last year.",
    ]
    for kind in ("logreg", "linearsvc", "inlegalbert"):
        try:
            clf = load_classifier(kind)
        except FileNotFoundError as err:
            print(f"{kind}: skipped ({err})")
            continue
        print(f"{kind}:")
        for text, result in zip(examples, classify(clf, examples)):
            print(f"  [{result.label} {result.score:.2f} {result.score_type}] {text}")
