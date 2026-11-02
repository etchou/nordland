# Nordland — Beyond Explanation

A GitHub Pages-ready, mobile-friendly research website by Elaine Chou. The site is prebuilt using static HTML, CSS, and vanilla JavaScript. **No build server, paid hosting, API key, or JavaScript framework is required.**

## Pages

- `index.html`: welfare-state paradox, conceptual depth, research method, limitations, and scholarly foundations.
- `evaluation.html`: interactive five-dimension 0–4 scoring rubric, evaluator-only interpretive notes, three constructed essays with explained scores, and validity audit.
- `case.html`: **standalone neutral case record and broad essay assignment only**. Supply this page or `data/Nordland_Case_Record.md` directly to a model, without sending the evaluator page.

## Publish with GitHub Pages

1. Open GitHub and create a new repository (for example `nordland-research`). Set the repository **Public** if the website should be publicly viewable.
2. Open the repository's **Add file → Upload files**. Upload **the contents of this folder**, not the ZIP itself. `index.html` must sit at the root alongside `case.html`, `evaluation.html`, and the `assets` and `data` directories.
3. Commit the uploaded files.
4. Open **Settings → Pages → Build and deployment**. Choose **Deploy from a branch**; select the `main` branch and `/ (root)` folder; save.
5. Visit the public address GitHub displays in the Pages settings. Check all three pages, mobile layout, copy-record function, and JSON/CSV exports.

The site uses relative links and will also work when hosted under a repository subdirectory. HTML can be opened directly from a computer for inspection; secure-context browser restrictions may prevent clipboard copying when opened as a local `file://` page. The download links still work.

## Updating without changing document names

Edit the content in the stable filenames inside `data/`. To check the weighted office-table figures, run `python verify_case.py`. Then rebuild from the repository root:

```bash
python -m pip install -r requirements.txt
python build.py
```

Upload or commit the updated `data` files and generated `index.html`, `evaluation.html`, and `case.html`. No cross-document draft labels or numbered filenames need updating. Git itself retains the change history.

The content source files are:

- `data/Nordland_Case_Record.md`
- `data/Nordland_Methodology.md`
- `data/Nordland_Evaluator_Interpretations_and_Assessment_Criteria.md`
- `data/Nordland_Validity_Questions.md`

Styling is in `assets/styles.css` and browser interactions are in `assets/app.js`. The design requests Noto Serif via Google Fonts with a local serif fallback; no font files are bundled.

## Research and publication boundaries

The fictional record and broad prompt are separate from assessor notes. The public evaluator page is **not password protected**; do not provide it as context in a clean first-run model test. The three scored illustrations (4/20, 15/20, 20/20) are constructed calibration examples, not results of model testing. The website is a methodological demonstration, not evidence of validated general model capability.

Rubric scoring runs locally in the browser. The form does not contact a server and does not automatically save entries. Export JSON (full evaluator notes) or CSV (dimension scores) before closing the page. No automatic data collection or user tracking is included.
