"""Group-aware stratified splitting at the seed-complaint level.

Splitting happens on original seed ids before any augmentation, so every
variant automatically lands on the same side as its parent. Test seeds are
never augmented at all; the test set contains hand-written originals only.
"""

from __future__ import annotations

import random

import pandas as pd

from src.intake.data import LABELS


def split_seed_ids(
    df: pd.DataFrame,
    train_frac: float = 0.70,
    val_frac: float = 0.15,
    seed: int = 42,
) -> dict[str, list[str]]:
    """Partition seed ids into train/val/test, stratified by label.

    The remainder after train_frac and val_frac goes to test. Shuffling is
    deterministic for a given seed.
    """
    if train_frac + val_frac >= 1.0:
        raise ValueError("train_frac + val_frac must be below 1.0")
    rng = random.Random(seed)
    splits: dict[str, list[str]] = {"train": [], "val": [], "test": []}
    for label in LABELS:
        ids = sorted(df.loc[df["label"] == label, "id"])
        rng.shuffle(ids)
        n = len(ids)
        n_train = round(n * train_frac)
        n_val = round(n * val_frac)
        splits["train"].extend(ids[:n_train])
        splits["val"].extend(ids[n_train : n_train + n_val])
        splits["test"].extend(ids[n_train + n_val :])
    return splits


def assign_split(df: pd.DataFrame, splits: dict[str, list[str]]) -> pd.DataFrame:
    """Return df with a split column derived from the id partition."""
    id_to_split = {i: name for name, ids in splits.items() for i in ids}
    unknown = set(df["id"]) - set(id_to_split)
    if unknown:
        raise ValueError(f"ids missing from split assignment: {sorted(unknown)}")
    out = df.copy()
    out["split"] = out["id"].map(id_to_split)
    return out
