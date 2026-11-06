# Beyond Explanation — the Nordland study

A static research website by Elaine Chou, published with GitHub Pages. Nordland is a fictional welfare state whose universal benefit system sharply reduces poverty, yet minority-background residents face higher initial benefit denials and report a weaker sense of belonging. The study asks how that paradox should be understood and, inseparably, how well AI models can work it out for themselves.

No server, framework, API key or tracking is involved. The HTML is prebuilt and committed.

## Site structure

| Page | Section | Material |
|---|---|---|
| `index.html` | Home: research questions, the paradox in the record, six-section index, separation of materials, source documents, study status | Overview |
| `case-record.html` | 01 Case Record: the complete case record and essay prompt, and nothing else | **Case evidence (model-facing)** |
| `methodology.html` | 02 Methodology: the full methodology paper | Methodology and interpretation |
| `validity.html` | 02 Methodology: validity questions and next research steps | Methodology and interpretation |
| `rubric.html` | 03 Evaluation Rubric: the five dimensions and exact anchors, guardrails, protocol, scoring record, reference analysis, Appendix A | **Evaluator-only** scoring criteria, interpretation, illustrative examples |
| `responses.html` | 04 Model Responses: unedited outputs with provenance | Observations |
| `evaluations.html` | 05 Evaluations: score profiles, rationales, scoring instrument | Findings and criteria |
| `findings.html` | 06 Findings: comparative patterns, limitations, implications | Findings |

`case.html` and `evaluation.html` redirect to their new locations so older links keep working.

## Repository layout

```
documents/                authoritative PDFs (stable names, linked by the site)
  archive/                versioned originals, kept for archival tracking
  manifest.json           titles, stable and versioned filenames, SHA-256
  README.md               sources, transcription checks, documented omissions
content/                  web transcriptions of the PDFs (rendered by build.py)
data/
  responses.json          model outputs + provenance (empty until collection)
  evaluations.json        dimension-level scores (empty until scoring)
  Nordland_Findings.md    optional; create when findings are written
assets/css/site.css       shared design system
assets/js/site.js         copy/print, contents highlighting, chart tooltips, scoring form
build.py                  generates every HTML page
verify_sources.py         checks PDFs against the manifest and transcriptions against the PDFs
verify_case.py            arithmetic check of the Table A1 office figures
```

## Updating content

```bash
python -m pip install -r requirements.txt
python verify_sources.py
python verify_case.py
python build.py
```

Commit the changed source files together with the regenerated HTML.

- **Adopting a new version of a research document:** follow `documents/README.md`. Never overwrite a file in `documents/archive/`.
- **Adding a model response:** append an object to `responses` in `data/responses.json` using the field names in `_template`. Paste the model's output, unedited, into `output_markdown`.
- **Adding an evaluation:** score the response with the instrument on `evaluations.html` and choose **Export JSON**. Paste the exported record into `evaluations` in `data/evaluations.json`.
- **Writing findings:** create `data/Nordland_Findings.md`. Until that file exists, the Findings page shows a labelled placeholder.

The build stops if a PDF no longer matches the manifest, if any line of a source document is missing from its rendered page, if the Case Record page links to any document other than the case record, if a homepage quotation or chart figure no longer matches its source, or if a version number or draft label appears in a page.

## Publishing with GitHub Pages

Go to **Settings → Pages → Deploy from a branch**, then choose `main` / `(root)`. All links are relative, so the site works under a project path such as `https://<user>.github.io/nordland/`. A `.nojekyll` file disables Jekyll processing.

## Research and publication boundaries

- Supply only `case-record.html` (or `documents/Nordland_Case_Record.pdf`) to a model. The evaluator pages are public for transparency but not access-controlled.
- The three scored essays in Appendix A of the rubric document, and the methodology's illustrative anchors, are **constructed calibration examples**, not model outputs or experimental results.
- No model responses, evaluations or findings have been published yet. Those pages show clearly marked placeholders until real data is added.
- The scoring form runs entirely in the browser and saves nothing automatically.
