# Source documents

The four PDFs in this folder are the authoritative research documents. The website reproduces each one in full from a web transcription in `content/`, and links only to the stable filenames below.

| Document | Stable file (linked by the site) | Current versioned original (archive) | Web transcription | Audience |
|---|---|---|---|---|
| Nordland Case Record | `Nordland_Case_Record.pdf` | `archive/Nordland_Case_Record_v1_4.pdf` | `content/Nordland_Case_Record.md` | Model-facing |
| Beyond Explanation: Evaluating Conceptual Reasoning in AI Through the Nordland Welfare-State Paradox | `Beyond_Explanation_Methodology.pdf` | `archive/Nordland_Beyond_Explanation_Methodology_v1_8.pdf` | `content/Beyond_Explanation_Methodology.md` | Methodology |
| Nordland: Evaluator Interpretations and Assessment Criteria | `Nordland_Evaluator_Interpretations_and_Assessment_Criteria.pdf` | `archive/Nordland_Evaluator_Interpretations_and_Assessment_Criteria_v1_2.pdf` | `content/Nordland_Evaluator_Interpretations_and_Assessment_Criteria.md` | Evaluator-only |
| Nordland: Validity Questions and Next Research Steps | `Nordland_Validity_Questions_and_Next_Research_Steps.pdf` | `archive/Nordland_Validity_Questions_and_Next_Research_Steps_v1_1.pdf` | `content/Nordland_Validity_Questions_and_Next_Research_Steps.md` | Methodology |

Each stable file is a byte-identical copy of its versioned original. `manifest.json` records the SHA-256 of both; `build.py` and `verify_sources.py` refuse to run if either file changes without the manifest being updated.

## Adopting a new version of a document

1. Add the new versioned PDF to `archive/` (do not overwrite or delete earlier versions).
2. Copy it over the stable filename in this folder.
3. Update that entry's `current_archive_file`, `sha256` and `pages` in `manifest.json`.
4. Update the web transcription in `content/` to match the new PDF.
5. Run `python verify_sources.py`, then `python build.py`.

## How the transcriptions were checked

`verify_sources.py` extracts the text of each PDF and compares it word for word with the web transcription, ignoring running headers and footers, page numbers, line-end hyphenation and table-cell order. All four documents pass. `build.py` then checks that every line and table cell of each transcription appears on its rendered page.

Text in the PDFs that the website deliberately does not display (internal date stamps and draft-status notes):

- Evaluator Interpretations and Assessment Criteria: the date "1 November 2026" in the subtitle and in every page footer.
- Validity Questions and Next Research Steps: the date "1 November 2026" in the subtitle, and the sentence "November 6 is a presentable prototype milestone, not final completion."

## Earlier web transcriptions

`archive/earlier-web-transcriptions/` holds the Markdown files the website used before these PDFs were adopted, unchanged. They are superseded and not linked from the site. The earlier Case Record transcription was already identical in wording to the current PDF and is now `content/Nordland_Case_Record.md`.
