"""Rule-based date extraction with anchor-relative resolution.

Explicit dates (DD/MM/YYYY read in Indian day-first convention, day-month
names, bare months), relative dates ("three months ago", "since last
week") resolved against a caller-supplied anchor date, and worst-case
date_range windows for anything approximate. The policy table lives in
docs/EXTRACTION_NOTES.md.
"""

from __future__ import annotations

import calendar
import datetime as dt
import re

from src.extract.schema import DateMention

_MONTHS = {
    name.lower(): i
    for i, name in enumerate(calendar.month_name)
    if name
} | {name.lower(): i for i, name in enumerate(calendar.month_abbr) if name}

_MONTH_RE = r"(?:january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|jun|jul|aug|sep|sept|oct|nov|dec)"

_WORD_NUMS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
    "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11,
    "twelve": 12, "a": 1, "an": 1, "couple of": 2, "few": 3,
}
_NUM_WORD_RE = r"(?:\d+|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|a|an|couple of|few)"

_HALF_WINDOW = {"day": 1, "week": 3, "month": 15, "year": 182}


def add_months(base: dt.date, months: int) -> dt.date:
    """Shift base by months, clamping the day to the target month length."""
    month_index = base.month - 1 + months
    year = base.year + month_index // 12
    month = month_index % 12 + 1
    day = min(base.day, calendar.monthrange(year, month)[1])
    return dt.date(year, month, day)


def _num(token: str) -> int | None:
    token = token.lower().strip()
    if token.isdigit():
        return int(token)
    return _WORD_NUMS.get(token)


def _month_span(year: int, month: int) -> list[str]:
    last = calendar.monthrange(year, month)[1]
    return [dt.date(year, month, 1).isoformat(), dt.date(year, month, last).isoformat()]


def _infer_year(month: int, day: int | None, anchor: dt.date) -> int:
    """Most recent occurrence of the month (and day) at or before anchor."""
    year = anchor.year
    probe = dt.date(year, month, min(day or 1, calendar.monthrange(year, month)[1]))
    if probe > anchor:
        year -= 1
    return year


def _mention(
    raw: str,
    span: tuple[int, int],
    iso: dt.date | None,
    resolution: str,
    approximate: bool,
    date_range: list[str] | None = None,
) -> DateMention:
    return DateMention(
        raw=raw.strip(),
        iso=iso.isoformat() if iso else None,
        approximate=approximate,
        resolution=resolution,
        span=[span[0], span[1]],
        date_range=date_range,
    )


def extract_dates(text: str, anchor: dt.date) -> tuple[list[DateMention], list[str]]:
    """Extract date mentions; also return raw fragments that failed to resolve."""
    mentions: list[DateMention] = []
    taken: list[tuple[int, int]] = []
    fragments: list[str] = []

    def claim(start: int, end: int) -> bool:
        if any(s < end and start < e for s, e in taken):
            return False
        taken.append((start, end))
        return True

    # 1. numeric day-first dates: 03/04/2026, 3-4-26
    for m in re.finditer(r"\b(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})\b", text):
        day, month, year = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if year < 100:
            year += 2000
        try:
            resolved = dt.date(year, month, day)
        except ValueError:
            fragments.append(m.group(0))
            continue
        if claim(*m.span()):
            mentions.append(_mention(m.group(0), m.span(), resolved, "explicit", False))

    # 2. day month (year?): 3rd April 2026, 15 March, 3rd of april
    for m in re.finditer(
        rf"\b(\d{{1,2}})(?:st|nd|rd|th)?\s+(?:of\s+)?({_MONTH_RE})\b(?:,?\s+(\d{{4}}))?",
        text,
        re.IGNORECASE,
    ):
        day, month = int(m.group(1)), _MONTHS[m.group(2).lower()]
        year_text = m.group(3)
        if not claim(*m.span()):
            continue
        if year_text:
            try:
                mentions.append(_mention(m.group(0), m.span(), dt.date(int(year_text), month, day), "explicit", False))
            except ValueError:
                fragments.append(m.group(0))
            continue
        year = _infer_year(month, day, anchor)
        try:
            mentions.append(_mention(m.group(0), m.span(), dt.date(year, month, day), "partial", True))
        except ValueError:
            fragments.append(m.group(0))

    # 3. month day (year?): March 3, 2026 / April 8th
    for m in re.finditer(
        rf"\b({_MONTH_RE})\s+(\d{{1,2}})(?:st|nd|rd|th)?\b(?:,?\s+(\d{{4}}))?",
        text,
        re.IGNORECASE,
    ):
        month, day = _MONTHS[m.group(1).lower()], int(m.group(2))
        year_text = m.group(3)
        if day > 31 or not claim(*m.span()):
            continue
        if year_text:
            try:
                mentions.append(_mention(m.group(0), m.span(), dt.date(int(year_text), month, day), "explicit", False))
            except ValueError:
                fragments.append(m.group(0))
        else:
            year = _infer_year(month, day, anchor)
            mentions.append(_mention(m.group(0), m.span(), dt.date(year, month, day), "partial", True))

    # 4. month year / bare month: January 2026 / in January
    for m in re.finditer(rf"\b({_MONTH_RE})\b(?:\s+(\d{{4}}))?", text, re.IGNORECASE):
        if not claim(*m.span()):
            continue
        month = _MONTHS[m.group(1).lower()]
        year = int(m.group(2)) if m.group(2) else _infer_year(month, None, anchor)
        mentions.append(
            _mention(m.group(0), m.span(), None, "partial", True, _month_span(year, month))
        )

    # 5. the Nth of this/last month
    for m in re.finditer(
        r"\bthe\s+(\d{1,2})(?:st|nd|rd|th)?\s+of\s+(this|last)\s+month\b", text, re.IGNORECASE
    ):
        if not claim(*m.span()):
            continue
        base = anchor if m.group(2).lower() == "this" else add_months(anchor, -1)
        try:
            resolved = dt.date(base.year, base.month, int(m.group(1)))
            mentions.append(_mention(m.group(0), m.span(), resolved, "relative_to_anchor", False))
        except ValueError:
            fragments.append(m.group(0))

    # 6. N units ago / since N units / for the last N units
    for m in re.finditer(
        rf"\b(?:since\s+|for\s+the\s+last\s+|for\s+)?({_NUM_WORD_RE})\s+(day|week|month|year)s?\s*(ago|back|earlier|over|now)?\b",
        text,
        re.IGNORECASE,
    ):
        matched = m.group(0).lower()
        has_since = matched.startswith("since") or "for the last" in matched
        suffix = (m.group(3) or "").lower()
        if not (suffix in ("ago", "back", "earlier") or has_since):
            continue
        n = _num(m.group(1))
        if n is None or not claim(*m.span()):
            continue
        unit = m.group(2).lower()
        if unit == "day":
            nominal = anchor - dt.timedelta(days=n)
        elif unit == "week":
            nominal = anchor - dt.timedelta(weeks=n)
        elif unit == "month":
            nominal = add_months(anchor, -n)
        else:
            nominal = add_months(anchor, -12 * n)
        half = dt.timedelta(days=_HALF_WINDOW[unit])
        date_range = [(nominal - half).isoformat(), (nominal + half).isoformat()]
        mentions.append(_mention(m.group(0), m.span(), nominal, "relative_to_anchor", True, date_range))

    # 7. last/next week/month/year, yesterday, today
    simple = {
        "yesterday": (anchor - dt.timedelta(days=1), False, None),
        "today": (anchor, False, None),
        "last week": (
            anchor - dt.timedelta(days=7),
            True,
            [(anchor - dt.timedelta(days=14)).isoformat(), (anchor - dt.timedelta(days=7)).isoformat()],
        ),
        "next week": (
            anchor + dt.timedelta(days=7),
            True,
            [(anchor + dt.timedelta(days=7)).isoformat(), (anchor + dt.timedelta(days=14)).isoformat()],
        ),
        "last month": (
            add_months(anchor, -1),
            True,
            _month_span(add_months(anchor, -1).year, add_months(anchor, -1).month),
        ),
        "last year": (add_months(anchor, -12), True, None),
    }
    for phrase, (nominal, approx, date_range) in simple.items():
        for m in re.finditer(rf"\b{phrase}\b", text, re.IGNORECASE):
            if claim(*m.span()):
                mentions.append(
                    _mention(m.group(0), m.span(), nominal, "relative_to_anchor", approx, date_range)
                )

    mentions.sort(key=lambda d: d.span[0])
    return mentions, fragments


def covered_spans(mentions: list[DateMention]) -> list[tuple[int, int]]:
    """Character spans already claimed by resolved date mentions."""
    return [(d.span[0], d.span[1]) for d in mentions]
