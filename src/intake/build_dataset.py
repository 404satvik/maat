"""Build the processed intake dataset from the tracked seed files.

Reads data/seed/, splits the originals stratified by label at the seed
level, augments only the train and val seeds, and writes train/val/test/
probe CSVs plus a split manifest to data/processed/.

Run from the repo root:

    python -m src.intake.build_dataset
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from src.intake.augment import augment_frame
from src.intake.data import LABELS, load_probe, load_seed
from src.intake.split import assign_split, split_seed_ids

SEED_DIR = Path("data/seed")
PROCESSED_DIR = Path("data/processed")
RANDOM_SEED = 42
N_VARIANTS = 3
TRAIN_FRAC = 0.70
VAL_FRAC = 0.15


def build(
    seed_dir: Path = SEED_DIR,
    n_variants: int = N_VARIANTS,
    random_seed: int = RANDOM_SEED,
) -> dict[str, pd.DataFrame]:
    """Assemble the train/val/test/probe frames without writing anything."""
    seed_df = load_seed(seed_dir)
    seed_df["group_id"] = seed_df["id"]
    seed_df["is_augmented"] = False

    splits = split_seed_ids(seed_df, TRAIN_FRAC, VAL_FRAC, random_seed)
    seed_df = assign_split(seed_df, splits)

    frames: dict[str, pd.DataFrame] = {}
    for name in ("train", "val"):
        originals = seed_df[seed_df["split"] == name].drop(columns=["split"])
        variants = augment_frame(originals, n_variants, random_seed)
        frames[name] = (
            pd.concat([originals, variants], ignore_index=True)
            .sort_values("id")
            .reset_index(drop=True)
        )
    frames["test"] = (
        seed_df[seed_df["split"] == "test"]
        .drop(columns=["split"])
        .sort_values("id")
        .reset_index(drop=True)
    )

    probe = load_probe(seed_dir)
    probe["group_id"] = probe["id"]
    probe["is_augmented"] = False
    frames["probe"] = probe
    return frames


def write_outputs(frames: dict[str, pd.DataFrame], out_dir: Path = PROCESSED_DIR) -> None:
    """Write the split CSVs and a manifest pinning the split configuration."""
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, frame in frames.items():
        frame.to_csv(out_dir / f"{name}.csv", index=False)
    manifest = {
        "random_seed": RANDOM_SEED,
        "n_variants": N_VARIANTS,
        "train_frac": TRAIN_FRAC,
        "val_frac": VAL_FRAC,
        "seed_ids": {
            name: sorted(frames[name].loc[~frames[name]["is_augmented"], "id"])
            for name in ("train", "val", "test")
        },
    }
    with open(out_dir / "split_manifest.json", "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2)


def summarize(frames: dict[str, pd.DataFrame]) -> str:
    """Return a class-balance table across splits as printable text."""
    lines = [f"{'split':<8}{'rows':>6}  " + "".join(f"{lbl:>10}" for lbl in LABELS) + f"{'augmented':>12}"]
    for name in ("train", "val", "test", "probe"):
        frame = frames[name]
        counts = frame["label"].value_counts()
        lines.append(
            f"{name:<8}{len(frame):>6}  "
            + "".join(f"{counts.get(lbl, 0):>10}" for lbl in LABELS)
            + f"{int(frame['is_augmented'].sum()):>12}"
        )
    return "\n".join(lines)


def main() -> None:
    """Build the dataset, write it to data/processed/, and print a summary."""
    frames = build()
    write_outputs(frames)
    print("Class balance by split:")
    print(summarize(frames))
    print("\nExample rows (one per class, from train):")
    train = frames["train"]
    for label in LABELS:
        row = train[(train["label"] == label) & (~train["is_augmented"])].iloc[0]
        print(f"\n[{row['id']}] ({row['label']}, {row['lang']})")
        print(f"  {row['text']}")
    example = train[train["is_augmented"]].iloc[0]
    parent = train[train["id"] == example["group_id"]].iloc[0]
    print(f"\nAugmentation example:\n  original [{parent['id']}]: {parent['text']}")
    print(f"  variant  [{example['id']}]: {example['text']}")
    print(f"\nWrote train/val/test/probe CSVs and split_manifest.json to {PROCESSED_DIR}/")


if __name__ == "__main__":
    main()
