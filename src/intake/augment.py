"""Deterministic surface-level augmentation for training complaints.

Only surface edits are applied: amount and city substitution, label-neutral
synonym swaps, and filler phrases. A variant therefore cannot drift to a
different class, which keeps augmented labels trustworthy by construction.
"""

from __future__ import annotations

import random
import re

import pandas as pd

CITIES: tuple[str, ...] = (
    "Delhi", "Mumbai", "Pune", "Jaipur", "Lucknow", "Bhopal", "Indore",
    "Nagpur", "Kanpur", "Patna", "Ranchi", "Surat", "Vadodara", "Noida",
    "Ghaziabad", "Gurgaon", "Chandigarh", "Kolkata", "Chennai", "Hyderabad",
    "Bengaluru", "Bangalore", "Kochi", "Coimbatore", "Varanasi", "Agra",
    "Meerut", "Dehradun", "Guwahati", "Bhubaneswar", "Kerala",
)

LEXICON: dict[str, tuple[str, ...]] = {
    "shopkeeper": ("dealer", "seller", "shop owner"),
    "landlord": ("house owner", "flat owner", "owner of the house"),
    "refund": ("money back",),
    "bounced": ("was dishonoured", "came back unpaid"),
    "flat": ("apartment",),
    "phone": ("mobile",),
    "shop": ("store",),
    "vacate": ("move out",),
    "defective": ("faulty",),
    "company": ("firm",),
    "advance": ("upfront payment",),
    "complaint": ("grievance",),
}

FILLER_PREFIX: tuple[str, ...] = (
    "Sir, ",
    "Hello, ",
    "I need some guidance. ",
    "Please help me with this. ",
)

FILLER_SUFFIX: tuple[str, ...] = (
    " Please advise.",
    " What should I do now?",
    " Kindly guide me on the next steps.",
    " Is there any legal option for me?",
)

_AMOUNT_RES: tuple[re.Pattern[str], ...] = (
    re.compile(r"Rs\.?\s?([\d,]*\d{3,}|\d+\.\d+ lakhs?|\d+ lakhs?)"),
    re.compile(r"([\d,]*\d{3,})\s+(rupees|ka|ki|ke)"),
)

_FACTORS: tuple[float, ...] = (0.4, 0.6, 0.8, 1.5, 2.0, 2.5)


def _reformat_amount(value: int) -> str:
    """Round an amount to a plausible figure."""
    if value >= 10000:
        value = round(value / 1000) * 1000
    elif value >= 1000:
        value = round(value / 100) * 100
    else:
        value = max(100, round(value / 10) * 10)
    return f"{value:,}"


def swap_amount(text: str, rng: random.Random) -> str:
    """Scale the first plain-digit rupee amount found, if any."""
    for pattern in _AMOUNT_RES:
        match = pattern.search(text)
        if match is None:
            continue
        raw = match.group(1)
        if "lakh" in raw:
            continue
        value = int(raw.replace(",", ""))
        scaled = _reformat_amount(int(value * rng.choice(_FACTORS)))
        start, end = match.span(1)
        return text[:start] + scaled + text[end:]
    return text


def swap_city(text: str, rng: random.Random) -> str:
    """Replace the first known city name with a different one, if any."""
    for city in CITIES:
        pattern = re.compile(rf"\b{city}\b")
        if pattern.search(text):
            others = [c for c in CITIES if c != city and c != "Kerala"]
            return pattern.sub(rng.choice(others), text, count=1)
    return text


def swap_lexicon(text: str, rng: random.Random, max_swaps: int = 2) -> str:
    """Apply up to max_swaps label-neutral synonym substitutions."""
    keys = [k for k in LEXICON if re.search(rf"\b{k}\b", text)]
    rng.shuffle(keys)
    for key in keys[:max_swaps]:
        replacement = rng.choice(LEXICON[key])
        text = re.sub(rf"\b{key}\b", replacement, text, count=1)
    return text


def add_filler(text: str, rng: random.Random) -> str:
    """Attach a filler phrase at the start or end."""
    if rng.random() < 0.5:
        return rng.choice(FILLER_PREFIX) + text
    return text + rng.choice(FILLER_SUFFIX)


def make_variant(text: str, rng: random.Random) -> str:
    """Produce one surface variant of a complaint."""
    out = swap_amount(text, rng)
    out = swap_city(out, rng)
    out = swap_lexicon(out, rng)
    if rng.random() < 0.5 or out == text:
        out = add_filler(out, rng)
    return out


def augment_frame(df: pd.DataFrame, n_variants: int, seed: int) -> pd.DataFrame:
    """Return n_variants distinct surface variants per row of df.

    Output rows carry the parent id in group_id and is_augmented=True.
    Originals are not included in the returned frame.
    """
    rng = random.Random(seed)
    rows: list[dict[str, object]] = []
    for row in df.itertuples(index=False):
        seen: set[str] = {row.text}
        for i in range(1, n_variants + 1):
            variant = make_variant(row.text, rng)
            for _ in range(10):
                if variant not in seen:
                    break
                variant = make_variant(row.text, rng)
            seen.add(variant)
            rows.append(
                {
                    "id": f"{row.id}-v{i}",
                    "label": row.label,
                    "lang": row.lang,
                    "text": variant,
                    "group_id": row.id,
                    "is_augmented": True,
                }
            )
    return pd.DataFrame(rows)
