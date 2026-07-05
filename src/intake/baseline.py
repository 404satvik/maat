"""Scikit-learn baselines for the intake issue-triage classifier.

Three models: a majority-class floor, TF-IDF with logistic regression, and
TF-IDF with a linear SVM. Evaluation is either group-aware stratified CV
over the seed originals (augmentation applied inside each fold, to that
fold's training seeds only) or a single fixed-split run against the pinned
test and probe sets.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.dummy import DummyClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_recall_fscore_support,
    recall_score,
)
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.pipeline import Pipeline
from sklearn.svm import LinearSVC

from src.intake.augment import augment_frame
from src.intake.data import LABELS

RANDOM_SEED = 42
MODEL_NAMES: tuple[str, ...] = ("majority", "tfidf_logreg", "tfidf_linearsvc")


def build_model(name: str) -> Pipeline:
    """Return a fresh, unfitted pipeline for one of MODEL_NAMES."""
    if name == "majority":
        return Pipeline([("clf", DummyClassifier(strategy="most_frequent"))])
    vectorizer = TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True)
    if name == "tfidf_logreg":
        clf: LogisticRegression | LinearSVC = LogisticRegression(
            max_iter=2000, random_state=RANDOM_SEED
        )
    elif name == "tfidf_linearsvc":
        clf = LinearSVC(dual="auto", random_state=RANDOM_SEED)
    else:
        raise ValueError(f"unknown model name: {name}")
    return Pipeline([("tfidf", vectorizer), ("clf", clf)])


def evaluate(y_true: list[str], y_pred: list[str]) -> dict:
    """Compute accuracy, macro PRF, per-class PRF, confusion matrix, other recall."""
    prec, rec, f1, support = precision_recall_fscore_support(
        y_true, y_pred, labels=list(LABELS), zero_division=0
    )
    per_class = {
        label: {
            "precision": round(float(p), 4),
            "recall": round(float(r), 4),
            "f1": round(float(f), 4),
            "support": int(s),
        }
        for label, p, r, f, s in zip(LABELS, prec, rec, f1, support)
    }
    return {
        "accuracy": round(float(accuracy_score(y_true, y_pred)), 4),
        "macro_precision": round(float(prec.mean()), 4),
        "macro_recall": round(float(rec.mean()), 4),
        "macro_f1": round(float(f1.mean()), 4),
        "other_recall": per_class["other"]["recall"],
        "per_class": per_class,
        "labels": list(LABELS),
        "confusion_matrix": confusion_matrix(y_true, y_pred, labels=list(LABELS)).tolist(),
    }


def cross_validate_originals(
    originals: pd.DataFrame,
    model_name: str,
    n_splits: int = 5,
    n_variants: int = 3,
    seed: int = RANDOM_SEED,
) -> dict:
    """Group-aware stratified k-fold CV over the seed originals.

    Folds are formed on the originals only, keyed on seed id, stratified by
    label. Inside each fold the training seeds are augmented with n_variants
    surface variants; the held-out fold stays originals-only, so no variant
    of a held-out seed is ever seen in training.
    """
    splitter = StratifiedGroupKFold(n_splits=n_splits, shuffle=True, random_state=seed)
    y = originals["label"].to_numpy()
    groups = originals["id"].to_numpy()
    fold_macro_f1: list[float] = []
    fold_other_recall: list[float] = []
    for train_idx, held_idx in splitter.split(originals, y, groups):
        train_orig = originals.iloc[train_idx]
        held_out = originals.iloc[held_idx]
        variants = augment_frame(train_orig, n_variants, seed)
        train_all = pd.concat(
            [train_orig[["text", "label"]], variants[["text", "label"]]],
            ignore_index=True,
        )
        model = build_model(model_name)
        model.fit(train_all["text"].tolist(), train_all["label"].tolist())
        pred = model.predict(held_out["text"].tolist())
        fold_macro_f1.append(float(f1_score(held_out["label"], pred, average="macro")))
        fold_other_recall.append(
            float(
                recall_score(
                    held_out["label"], pred, labels=["other"], average=None, zero_division=0
                )[0]
            )
        )
    return {
        "n_splits": n_splits,
        "macro_f1_mean": round(float(np.mean(fold_macro_f1)), 4),
        "macro_f1_std": round(float(np.std(fold_macro_f1)), 4),
        "other_recall_mean": round(float(np.mean(fold_other_recall)), 4),
        "other_recall_std": round(float(np.std(fold_other_recall)), 4),
        "fold_macro_f1": [round(v, 4) for v in fold_macro_f1],
        "fold_other_recall": [round(v, 4) for v in fold_other_recall],
    }


def fixed_split_eval(
    train: pd.DataFrame,
    eval_sets: dict[str, pd.DataFrame],
    model_name: str,
) -> dict[str, dict]:
    """Train once on the pinned train split and evaluate on each eval set."""
    model = build_model(model_name)
    model.fit(train["text"].tolist(), train["label"].tolist())
    results: dict[str, dict] = {}
    for name, frame in eval_sets.items():
        pred = model.predict(frame["text"].tolist())
        results[name] = evaluate(frame["label"].tolist(), list(pred))
    return results
