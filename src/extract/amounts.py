"""Rule-based extraction of Indian-format monetary amounts.

Rules are primary here (spaCy tags these as CARDINAL and drops the
currency marker). Handles Rs / rupees markers, Indian digit grouping
(1,20,000), lakh / crore multipliers including number words, and bare
digit amounts when they are not year-like.
"""

from __future__ import annotations

import re

from src.extract.schema import Amount

LAKH = 100_000
CRORE = 10_000_000

_NUMBER_WORDS: dict[str, int] = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
    "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11,
    "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15,
    "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19,
    "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60,
    "seventy": 70, "eighty": 80, "ninety": 90, "a": 1, "an": 1, "half": 0,
}

_WORD = r"(?:one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety|a|an)"

# Ordered patterns; earlier wins on overlap.
_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    # Rs 2.2 lakhs / rupees 1.5 crore / 2 lakh rupees / forty lakhs
    (
        "scaled",
        re.compile(
            rf"(?:Rs\.?|rupees|rs\.?)?\s*((?:\d+(?:\.\d+)?|{_WORD}(?:\s+{_WORD})?))\s*(lakhs?|lacs?|crores?)(?:\s*(?:rupees|rs\.?))?",
            re.IGNORECASE,
        ),
    ),
    # Rs 1,20,000 / Rs. 5000 / rs 3899
    (
        "marked",
        re.compile(r"(?:Rs\.?|rupees|rs\.?)\s*([\d,]*\d)", re.IGNORECASE),
    ),
    # 5,000 rupees / 21000 rs / 590rs
    (
        "marked_after",
        re.compile(r"([\d,]*\d)\s*(?:rupees|rupaye|rs\.?)(?![a-z])", re.IGNORECASE),
    ),
    # bare digits with grouping or 4+ digits (filtered below for year-likeness)
    (
        "bare",
        re.compile(r"(?<![\d,.])(\d{1,2}(?:,\d{2,3})+|\d{4,8})(?![\d,%])"),
    ),
)

_PURPOSE_KEYWORDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("cheque_amount", ("cheque", "cheques", "dishonoured", "bounced")),
    ("deposit", ("deposit", "security deposit", "token", "advance")),
    ("rent", ("rent", "monthly", "maintenance")),
    ("loan", ("loan", "lent", "borrowed", "udhaar", "hand loan", "repay")),
    ("fee", ("fee", "fees", "charges", "charged", "membership", "subscription")),
    ("compensation", ("compensation", "damages", "claim", "settlement")),
    ("price_paid", ("paid", "bought", "ordered", "purchased", "cost", "costing", "price", "worth", "bill", "for")),
)


def _words_to_number(text: str) -> float | None:
    """Parse 'forty' or 'forty five' style small number words."""
    total = 0
    for token in text.lower().split():
        if token not in _NUMBER_WORDS:
            return None
        total += _NUMBER_WORDS[token]
    return float(total) if total else None


def _is_year_like(value: int, raw: str) -> bool:
    """True for bare 4-digit numbers that read as years (1900-2099)."""
    return "," not in raw and 1900 <= value <= 2099


def classify_purpose(text: str, span_start: int, span_end: int, window: int = 60) -> str:
    """Assign an amount purpose from keywords in a window around the span."""
    lo = max(0, span_start - window)
    context = text[lo : span_end + window].lower()
    best: tuple[int, str] | None = None
    for purpose, keywords in _PURPOSE_KEYWORDS:
        for kw in keywords:
            pos = context.find(kw)
            if pos < 0:
                continue
            distance = abs((lo + pos) - span_start)
            if best is None or distance < best[0]:
                best = (distance, purpose)
    return best[1] if best else "unknown"


def extract_amounts(text: str) -> list[Amount]:
    """Extract all monetary amounts with normalized integer values."""
    found: list[Amount] = []
    taken: list[tuple[int, int]] = []
    for kind, pattern in _PATTERNS:
        for match in pattern.finditer(text):
            start, end = match.span()
            if any(s < end and start < e for s, e in taken):
                continue
            raw_num = match.group(1)
            if kind == "scaled":
                unit = match.group(2).lower()
                multiplier = CRORE if unit.startswith("crore") else LAKH
                base = (
                    float(raw_num.replace(",", ""))
                    if raw_num[0].isdigit()
                    else _words_to_number(raw_num)
                )
                if base is None:
                    continue
                value = int(round(base * multiplier))
            else:
                value = int(raw_num.replace(",", ""))
                if kind == "bare" and (_is_year_like(value, raw_num) or value < 1000 or len(raw_num.replace(",", "")) > 8):
                    continue
            if value <= 0:
                continue
            taken.append((start, end))
            found.append(
                Amount(
                    raw=text[start:end].strip(),
                    value=value,
                    currency="INR",
                    purpose=classify_purpose(text, start, end),
                    span=[start, end],
                )
            )
    found.sort(key=lambda a: a.span[0])
    return found
