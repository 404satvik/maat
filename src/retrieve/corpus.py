"""PredEx corpus loading and issue-area filtering.

Corpus: L-NLProc/PredEx (official release; Nigam et al. 2024), Supreme
Court of India judgments with appeal outcome labels and expert-annotated
explanations. Coverage note carried into every downstream surface: these
are APPELLATE judgments; consumer-forum and rent-court level outcomes do
not appear in this corpus.
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

RAW_DIR = Path("data/raw/predex")
DATASET_ID = "L-NLProc/PredEx"

# Signal patterns per issue area. A document is assigned to the area with
# the highest signal count, subject to the per-area minimum. Tenancy
# demands two or more signals because landlord/tenant words appear
# incidentally in property and contract matters.
_AREA_PATTERNS: dict[str, tuple[re.Pattern[str], int]] = {
    "cheque": (
        re.compile(
            r"section 138|negotiable instruments act|dishonou?r of (?:the )?cheque|cheque (?:was |were )?dishonou?red|cheque bounce",
            re.IGNORECASE,
        ),
        1,
    ),
    "consumer": (
        re.compile(
            r"consumer protection act|deficiency in service|national consumer disputes|ncdrc|district consumer|consumer forum|consumer commission",
            re.IGNORECASE,
        ),
        1,
    ),
    "tenancy": (
        re.compile(
            r"rent control act|rent act|eviction|ejectment|landlord|tenant|tenancy|bona fide requirement|standard rent",
            re.IGNORECASE,
        ),
        2,
    ),
}


def load_predex(raw_dir: Path = RAW_DIR) -> pd.DataFrame:
    """Load PredEx from the local snapshot, downloading it if absent.

    Returns one row per case: doc_id, case_name, text, label,
    expert_explanation.
    """
    parquet = raw_dir / "predex.parquet"
    if parquet.exists():
        return pd.read_parquet(parquet)
    from datasets import load_dataset

    dataset = load_dataset(DATASET_ID)
    frames = []
    for split in dataset:
        df = dataset[split].to_pandas()
        df["doc_id"] = [f"predex-{split}-{i}" for i in range(len(df))]
        frames.append(df)
    combined = pd.concat(frames, ignore_index=True)
    # PredEx ships a "text" column holding an instruction-tuning prompt
    # wrapper around Input; drop it so the judgment text is the only text.
    combined = combined.drop(columns=[c for c in ("text",) if c in combined.columns])
    combined = combined.rename(
        columns={"Case Name": "case_name", "Input": "text", "Label": "label", "Output": "raw_output"}
    )[["doc_id", "case_name", "text", "label", "raw_output"]]
    combined["expert_explanation"] = combined["raw_output"].map(parse_explanation)
    combined = combined.drop(columns=["raw_output"])
    raw_dir.mkdir(parents=True, exist_ok=True)
    combined.to_parquet(parquet, index=False)
    return combined


def parse_explanation(raw: str | None) -> str:
    """Extract the expert explanation text from PredEx's Output field.

    The field packs the label and pivotal sentences with [ds] separators;
    everything after the leading label digits is annotation text.
    """
    if not isinstance(raw, str):
        return ""
    parts = [p.strip() for p in raw.split("[ds]") if p.strip()]
    if parts and re.fullmatch(r"\d+", parts[0]):
        parts = parts[1:]
    return " ".join(parts)


def assign_issue_area(text: str) -> str | None:
    """Assign an issue area by strongest signal count, or None."""
    scores: dict[str, int] = {}
    for area, (pattern, minimum) in _AREA_PATTERNS.items():
        count = len(pattern.findall(text))
        if count >= minimum:
            scores[area] = count
    if not scores:
        return None
    return max(scores, key=lambda a: scores[a])


def build_filtered_corpus(raw_dir: Path = RAW_DIR) -> pd.DataFrame:
    """PredEx rows relevant to the covered issue areas, with area labels.

    PredEx carries the same judgment more than once: full text in one
    split and a 1000-word segment of the same judgment in another.
    Deduplication groups by normalized case caption and keeps the
    longest copy, so area assignment and retrieval always see the
    fullest text of each judgment exactly once.
    """
    corpus = load_predex(raw_dir)
    corpus = corpus[corpus["text"].str.len() > 200].copy()
    corpus["_name_key"] = corpus["case_name"].str.strip().str.lower()
    corpus = (
        corpus.sort_values("text", key=lambda s: s.str.len(), ascending=False)
        .drop_duplicates("_name_key")
        .drop(columns=["_name_key"])
        .sort_index()
    )
    corpus["issue_area"] = corpus["text"].map(assign_issue_area)
    filtered = corpus.dropna(subset=["issue_area"]).reset_index(drop=True)
    return filtered
