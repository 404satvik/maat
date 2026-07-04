"""Loading and validation for the intake seed dataset."""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path

import pandas as pd

LABELS: tuple[str, ...] = ("consumer", "cheque", "tenancy", "other")
SEED_FILES: tuple[str, ...] = ("consumer.csv", "cheque.csv", "tenancy.csv", "other.csv")
REQUIRED_COLUMNS: tuple[str, ...] = ("id", "label", "lang", "text")

_WHITESPACE_RE = re.compile(r"\s+")


def normalize_text(text: str) -> str:
    """Return text in NFC form with whitespace collapsed and stripped.

    Casing and punctuation are preserved; lowercasing is left to the
    downstream vectorizer or tokenizer.
    """
    text = unicodedata.normalize("NFC", text)
    return _WHITESPACE_RE.sub(" ", text).strip()


def _read_csv(path: Path) -> pd.DataFrame:
    """Read one complaint CSV and check its columns."""
    df = pd.read_csv(path, dtype=str)
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"{path.name}: missing columns {missing}")
    return df[list(REQUIRED_COLUMNS)]


def _validate(df: pd.DataFrame, source: str) -> pd.DataFrame:
    """Validate ids, labels, and texts; normalize the text column."""
    dupes = df.loc[df["id"].duplicated(), "id"].tolist()
    if dupes:
        raise ValueError(f"{source}: duplicate ids {dupes}")
    bad_labels = sorted(set(df["label"]) - set(LABELS))
    if bad_labels:
        raise ValueError(f"{source}: unknown labels {bad_labels}")
    if df["text"].isna().any():
        raise ValueError(f"{source}: missing text values")
    df = df.copy()
    df["text"] = df["text"].map(normalize_text)
    empty = df.loc[df["text"].str.len() == 0, "id"].tolist()
    if empty:
        raise ValueError(f"{source}: empty text for ids {empty}")
    return df


def load_seed(seed_dir: Path) -> pd.DataFrame:
    """Load the hand-written seed complaints from the four per-class files."""
    frames = [_read_csv(seed_dir / name) for name in SEED_FILES]
    df = pd.concat(frames, ignore_index=True)
    return _validate(df, "seed")


def load_probe(seed_dir: Path) -> pd.DataFrame:
    """Load the real-world probe set (evaluation only, never training)."""
    return _validate(_read_csv(seed_dir / "probe.csv"), "probe")
