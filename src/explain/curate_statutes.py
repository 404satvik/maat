"""Curate the tracked statute set from official source PDFs.

Reads the PDFs downloaded from India Code and MoHUA (see SOURCES) out of
data/raw/statute_sources/ and slices the sections the explainer needs
into data/statutes/*.json. Cleaning is mechanical only: whitespace
collapsing and removal of footnote reference markers. No wording is
changed; PDF extraction artifacts (occasional missing spaces) are left
as-is rather than silently edited. Verify curated text against the
source PDFs before production use.

Run from the repo root:

    python -m src.explain.curate_statutes
"""

from __future__ import annotations

import datetime as dt
import json
import re
from pathlib import Path

RAW_DIR = Path("data/raw/statute_sources")
OUT_DIR = Path("data/statutes")

SOURCES = {
    "ni_act_1881": {
        "act": "The Negotiable Instruments Act, 1881",
        "pdf": "ni_act_1881.pdf",
        "url": "https://www.indiacode.nic.in/bitstream/123456789/15327/1/negotiable_instruments_act,_1881.pdf",
        "publisher": "India Code (official)",
        "caveat": None,
    },
    "cpa_2019": {
        "act": "The Consumer Protection Act, 2019",
        "pdf": "cpa_2019.pdf",
        "url": "https://www.indiacode.nic.in/bitstream/123456789/16939/1/a2019-35.pdf",
        "publisher": "India Code (official)",
        "caveat": None,
    },
    "mta_2021": {
        "act": "The Model Tenancy Act, 2021",
        "pdf": "model_tenancy_act_2021.pdf",
        "url": "https://mohua.gov.in/upload/uploadfiles/files/Model-Tenancy-Act-English-02_06_2021.pdf (retrieved via web.archive.org)",
        "publisher": "Ministry of Housing and Urban Affairs (official model law)",
        "caveat": (
            "The Model Tenancy Act is a central model law circulated to "
            "states; the rent or tenancy act of your own state governs "
            "your dispute. A lawyer can tell you which act applies where "
            "you live."
        ),
    },
}

# (act_id, section, title, start regex, end regex). The body occurrence
# is matched last, after any arrangement-of-sections listing.
SECTION_MARKERS: tuple[tuple[str, str, str, str, str], ...] = (
    (
        "ni_act_1881", "138",
        "Dishonour of cheque for insufficiency, etc., of funds in the account",
        r"138\.\s*Dishonour of cheque for insufficiency.*?—",
        r"139\.\s*Presumption in favour of holder",
    ),
    (
        "ni_act_1881", "139",
        "Presumption in favour of holder",
        r"139\.\s*Presumption in favour of holder\s*\.?\s*—",
        r"140\.\s*Defence which may not be allowed",
    ),
    (
        "ni_act_1881", "142",
        "Cognizance of offences",
        r"142\.[\s\S]{0,40}?Cognizance of offences\s*\.?\s*—?",
        r"142A\.|143\.\s",
    ),
    (
        "cpa_2019", "2(7)",
        "Definition: consumer",
        r"\(7\)\s*(?=[\"“]consumer[\"”]\s*means)",
        r"\(8\)\s*[\"“]",
    ),
    (
        "cpa_2019", "2(11)",
        "Definition: deficiency",
        r"\(11\)\s*(?=[\"“]deficiency[\"”]\s*means)",
        r"\(12\)\s*[\"“]",
    ),
    (
        "cpa_2019", "35",
        "Manner in which complaint shall be made",
        r"35\.\s*Manner in which complaint shall be made\s*\.?\s*—",
        r"36\.\s*Proceedings before District Commission",
    ),
    (
        "cpa_2019", "69",
        "Limitation period",
        r"69\.\s*Limitation period\s*\.?\s*—",
        r"70\.\s*Administrative control",
    ),
    (
        "mta_2021", "11",
        "Security deposit",
        r"\n11\.\s*(?=\(1\)\s*The security deposit)",
        r"CHAPTER\s+IV|\n12\.\s",
    ),
    (
        "mta_2021", "9",
        "Revision of rent",
        r"\n9\.\s*(?=\(1\)\s*The revision of rent)",
        r"\n10\.\s",
    ),
    (
        "mta_2021", "21",
        "Eviction and recovery of possession of premises by landlord",
        r"\n21\.\s*(?=\(1\)\s*A tenant shall not be evicted)",
        r"\n22\.\s",
    ),
)

_FOOTNOTE_MARK = re.compile(r"\d+\[")
_PAGE_MARK = re.compile(r"Page \d+(?: of \d+)?")
_TOC_TITLE = re.compile(r"^\s*\d{1,2}\.\s+([A-Z][^.\n]{3,90})\.\s*$", re.MULTILINE)

# Margin-note strings as they actually render in the MoHUA PDF body,
# where hyphenation differs from the arrangement listing (for example
# "sub-letting" in the margin versus "subletting" in the listing).
MTA_MARGIN_NOISE: tuple[str, ...] = (
    "Restriction on sub-letting",
    "Rent payable",
    "Revision of rent",
    "Rent Authority to determine the revised rent in case of dispute",
    "Security deposit",
    "Eviction and recovery of possession of premises by landlord",
    "Payment of rent during eviction proceedings",
    "Rights and obligations of successor in case of death",
)


def _margin_titles(full_text: str) -> list[str]:
    """Section titles from the arrangement-of-sections listing.

    The MoHUA PDF prints section titles in the page margins; pypdf
    interleaves them into body text. The same strings appear in the
    arrangement listing at the top of the act, so they can be collected
    and removed mechanically.
    """
    head = full_text[:6000]
    return [m.group(1).strip() for m in _TOC_TITLE.finditer(head)]


def _clean(text: str, noise: list[str] | None = None) -> str:
    """Mechanical cleanup: footnotes, page marks, margin titles, spacing.

    Whitespace is collapsed before noise removal so margin titles that
    the PDF wrapped across lines still match.
    """
    text = _FOOTNOTE_MARK.sub("", text)
    text = text.replace("]", "")
    text = re.sub(r"\s+", " ", text)
    text = _PAGE_MARK.sub(" ", text)
    for title in noise or []:
        text = text.replace(f"{title}.", " ")
    return re.sub(r"\s+", " ", text).strip()


def _extract_text(pdf_path: Path) -> str:
    from pypdf import PdfReader

    reader = PdfReader(str(pdf_path))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def _slice_section(full_text: str, start_pattern: str, end_pattern: str) -> str | None:
    """Text between the LAST start-pattern match and the next end match."""
    starts = list(re.finditer(start_pattern, full_text, re.IGNORECASE))
    if not starts:
        return None
    start = starts[-1].end()
    end_match = re.search(end_pattern, full_text[start:], re.IGNORECASE)
    if end_match is None:
        return None
    return full_text[start : start + end_match.start()]


def main() -> None:
    """Slice all configured sections and write the statute JSON files."""
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    texts = {act_id: _extract_text(RAW_DIR / spec["pdf"]) for act_id, spec in SOURCES.items()}
    acts: dict[str, dict] = {
        act_id: {
            "act": spec["act"],
            "source": {
                "publisher": spec["publisher"],
                "url": spec["url"],
                "downloaded": dt.date.today().isoformat(),
                "note": (
                    "Mechanically extracted from the official PDF; verify "
                    "against the source before production use."
                ),
            },
            "caveat": spec["caveat"],
            "sections": {},
        }
        for act_id, spec in SOURCES.items()
    }
    noise_by_act = {
        "mta_2021": list(MTA_MARGIN_NOISE) + _margin_titles(texts["mta_2021"])
    }
    for act_id, number, title, start_pattern, end_pattern in SECTION_MARKERS:
        raw = _slice_section(texts[act_id], start_pattern, end_pattern)
        if raw is None:
            raise RuntimeError(f"could not slice {act_id} section {number}")
        cleaned = _clean(raw, noise_by_act.get(act_id))
        acts[act_id]["sections"][number] = {"title": title, "text": cleaned}
        print(f"{act_id} s.{number}: {len(cleaned)} chars")
    for act_id, payload in acts.items():
        path = OUT_DIR / f"{act_id}.json"
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"wrote {path}")


if __name__ == "__main__":
    main()
