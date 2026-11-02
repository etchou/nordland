# Beyond Explanation — the Nordland study

A static research website by Elaine Chou, published with GitHub Pages. Nordland is a fictional welfare state whose universal benefit system sharply reduces poverty, yet minority-background residents face higher initial benefit denials and report a weaker sense of belonging. The study asks how that paradox should be understood and, inseparably, how well AI models can work it out for themselves.

No server, framework, API key or tracking is involved. The HTML is prebuilt and committed.

## Site structure

| Page | Section | Audience |
|---|---|---|
| `index.html` | Home: research questions, the paradox in the record, six-section index, study status | Public |
| `case-record.html` | 01 Case Record: the neutral record and essay prompt only | **Model-facing** |
| `methodology.html` | 02 Methodology: research questions, conceptual reasoning evaluation, study design, validity questions | Public |
| `rubric.html` | 03 Evaluation Rubric: five dimensions, 0–4 anchors, guardrails, protocol, reference analysis, calibration essays | **Evaluator-only** |
| `responses.html` | 04 Model Responses: unedited outputs with provenance | Public |
| `evaluations.html` | 05 Evaluations: score profiles, rationales, scoring instrument | Evaluator |
| `findings.html` | 06 Findings: comparative patterns, limitations, implications | Public |

`case.html` and `evaluation.html` redirect to their new locations so older links keep working.

## Repository layout

```
data/                     research content (edit these)
  Nordland_Case_Record.md
  Nordland_Methodology.md
  Nordland_Validity_Questions.md
  Nordland_Evaluator_Interpretations_and_Assessment_Criteria.md
  responses.json          model outputs + provenance (empty until collection)
  evaluations.json        dimension-level scores (empty until scoring)
  Nordland_Findings.md    optional; create when findings are written
assets/css/site.css       shared design system
assets/js/site.js         copy/print, contents highlighting, chart tooltips, scoring form
build.py                  generates every HTML page from data/
verify_case.py            arithmetic check of the Table A1 office figures
```

## Updating content

```bash
python -m pip install -r requirements.txt
python verify_case.py
python build.py
```

Commit the changed `data/` files together with the regenerated HTML.

- **Adding a model response:** append an object to `responses` in `data/responses.json` using the field names in `_template`. Paste the model's output, unedited, into `output_markdown`.
- **Adding an evaluation:** score the response with the instrument on `evaluations.html` and choose **Export JSON**. Paste the exported record into `evaluations` in `data/evaluations.json`.
- **Writing findings:** create `data/Nordland_Findings.md`. Until that file exists, the Findings page shows a labelled placeholder.

The build checks that every line of the case record appears in the rendered page, and that the homepage figure's numbers still match the case record text. If either check fails, the build stops.

## Publishing with GitHub Pages

Go to **Settings → Pages → Deploy from a branch**, then choose `main` / `(root)`. All links are relative, so the site works under a project path such as `https://<user>.github.io/nordland/`. A `.nojekyll` file disables Jekyll processing.

## Research and publication boundaries

- Supply only `case-record.html` (or `data/Nordland_Case_Record.md`) to a model. The evaluator pages are public for transparency but not access-controlled.
- The three scored essays on the Rubric page are **constructed calibration examples**, not model outputs or experimental results.
- No model responses, evaluations or findings have been published yet. Those pages show clearly marked placeholders until real data is added.
- The scoring form runs entirely in the browser and saves nothing automatically.
