"""Check the website's research texts against the authoritative PDF documents.

1. Integrity: every PDF listed in documents/manifest.json (the stable file the site links to and
   the designated current versioned original in documents/archive/) matches its recorded SHA-256.
2. Fidelity: the words of each web transcription in content/ match the words of its PDF.
   Running headers, footers and page numbers are removed; differences in line breaks, hyphenation
   at line ends, punctuation spacing and table-cell order are ignored. Any remaining word that
   appears in one source but not the other is reported, except the documented omissions below.

Run: python verify_sources.py      (exit status 1 on any failure)
Requires: pypdf (see requirements.txt)
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parent
MANIFEST = json.loads((ROOT / "documents" / "manifest.json").read_text(encoding="utf-8"))

# Running heads and footers printed on every PDF page, and page numbers.
RUNNING_PHRASES = [
    "BEYOND EXPLANATION / NORDLAND RESEARCH", "ELAINE CHOU • NORDLAND RESEARCH", "NORDLAND · CASE RECORD",
    "NORDLAND / EVALUATOR-ONLY REFERENCE", "RESTRICTED ASSESSOR MATERIAL • 1 NOV 2026",
    "NORDLAND / RESEARCH VALIDITY AUDIT", "NORDLAND · VALIDITY QUESTIONS",
]
RUNNING_TEXT = re.compile(
    "|".join(r"\s+".join(re.escape(w) for w in phrase.split()) for phrase in RUNNING_PHRASES)
    + r"|\|\s*\d+(\s*/\s*\d+)?[ \t]*$",
    re.MULTILINE,
)

# Text present in a PDF that the website deliberately does not display (internal date stamps and
# draft-status notes). Each entry is removed from the PDF text before comparison.
DOCUMENTED_OMISSIONS = {
    "evaluator-criteria": ["1 November 2026"],
    "validity": ["1 November 2026", "November 6 is a presentable prototype milestone, not final completion."],
}

# Repeated table header on page 2 of the case record (the web table shows its header once).
# Table headers that the PDFs repeat at the top of a continuation page (the web tables show each once).
REPEATED_TABLE_HEADER = {
    "case-record": ["Office Discretionary interviews Claims Minority share of claims Denial: minority Denial: other Incomplete at filing"],
    "evaluator-criteria": ["Dimension Score Explanation", "Dimension Score Explanation"],
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pdf_text(path: Path) -> str:
    return "\n".join(page.extract_text() or "" for page in PdfReader(str(path)).pages)


def words(text: str) -> list[str]:
    """Lower-case word tokens with markup, punctuation and hyphenation removed."""
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)          # Markdown links → text
    text = re.sub(r"(?m)^\s*\|?\s*-{3,}.*$", " ", text)            # table rules
    text = re.sub(r"[*_#>|`]", " ", text)                          # Markdown markup
    text = text.replace("­", "")                               # soft hyphens
    text = re.sub(r"[-‐‑](\s*\n\s*)", "", text)                     # hyphen at a line end
    text = re.sub(r"[-‐‑]", "", text)                               # hyphens in compounds
    text = re.sub(r"[—–/]", " ", text)                               # dashes and slashes separate words
    text = re.sub(r"([≈≥])", r" \1 ", text)
    text = re.sub(r"[^\w%≈≥.\s]", " ", text)
    text = re.sub(r"(?<!\d)\.|\.(?!\d)", " ", text)                 # keep decimal points only
    return [w for w in text.lower().split() if w]


def strip_once(text: str, phrase: str) -> tuple[str, bool]:
    pattern = r"\s+".join(re.escape(p) for p in phrase.split())
    new, n = re.subn(pattern, " ", text, count=1)
    return new, bool(n)


def check() -> int:
    failures = 0
    for doc in MANIFEST["documents"]:
        key = doc["key"]
        print(f"\n{doc['title']}")
        for label in ("pdf", "current_archive_file"):
            path = ROOT / doc[label]
            if not path.exists():
                print(f"  FAIL  missing {doc[label]}")
                failures += 1
            elif sha256(path) != doc["sha256"]:
                print(f"  FAIL  {doc[label]} does not match the recorded SHA-256")
                failures += 1
            else:
                print(f"  ok    {doc[label]} (SHA-256 matches)")

        raw = RUNNING_TEXT.sub(" ", pdf_text(ROOT / doc["pdf"]))
        for phrase in DOCUMENTED_OMISSIONS.get(key, []):
            raw, found = strip_once(raw, phrase)
            print(f"  note  omitted on the website by design: “{phrase}”" + ("" if found else "  (not found in PDF)"))
        for phrase in REPEATED_TABLE_HEADER.get(key, []):
            raw, _ = strip_once(raw, phrase)

        web = (ROOT / doc["web_source"]).read_text(encoding="utf-8")
        missing = Counter(words(raw)) - Counter(words(web))
        extra = Counter(words(web)) - Counter(words(raw))
        if missing or extra:
            failures += 1
            print(f"  FAIL  {doc['web_source']} differs from the PDF")
            if missing:
                print("        in PDF, not on website:", dict(missing.most_common(25)))
            if extra:
                print("        on website, not in PDF:", dict(extra.most_common(25)))
        else:
            print(f"  ok    {doc['web_source']} has the same words as the PDF ({sum(Counter(words(web)).values())} words)")
    print("\nAll source checks passed." if not failures else f"\n{failures} check(s) failed.")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(check())
