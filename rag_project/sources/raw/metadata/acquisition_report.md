# Badminton RAG Literature Acquisition Report

Generated: 2026-06-08

## Summary

- Source manifest: `rag_project/manifests/badminton_sources.csv`
- Download results: `rag_project/sources/raw/metadata/download_results.csv`
- File inventory: `rag_project/sources/raw/metadata/download_inventory.csv`
- Supplemental downloads: `rag_project/sources/raw/metadata/supplemental_downloads.csv`
- Original source entries: 37
- Entries with at least one local artifact: 37
- Valid PDF files: 11
- Saved HTML pages: 30
- Invalid PDF files after verification: 0

## What Can Go Into RAG Immediately

The following local artifacts are suitable for first-pass ingestion:

- Valid PDFs under `rag_project/sources/raw/pdf/`
- Full open-access article HTML pages under `rag_project/sources/raw/html/`, especially PMC, Nature Scientific Reports, Frontiers, arXiv abstract page, and conference-proceedings pages.

PMC PDF downloads returned an intermediate "Preparing to download" HTML page during automated access, so those invalid files were removed. The PMC full article HTML pages are still saved and can be parsed for RAG.

## Important Caveats

- Commercial textbooks were not downloaded as full books. `BOOK_GRICE.html` and `BOOK_BRAHMS.html` are product/preview pages only.
- Airiti, Taiwan thesis, and some Chinese journal pages were saved as metadata or article landing pages. They should not be treated as full text unless the HTML clearly includes the article body.
- BWF official coach and Shuttle Time pages were saved as HTML. BWF Coach Manual Level 1 was additionally downloaded from a public federation mirror. BWF Level 2 and Shuttle Time PDF manuals still need manual download or an authenticated source if you require the actual PDFs.
- MDPI article pages returned 403 to scripted access, but their static PDF resources were downloaded and validated.
- Retos PDF required disabling local certificate-chain verification. The saved file has a valid PDF header, but this source is explicitly tracked in `supplemental_downloads.csv`.

## Recommended Next Step

Before vectorization, run a source classifier that labels each artifact as one of:

- `full_text_pdf`
- `full_text_html`
- `abstract_or_metadata_only`
- `book_preview_or_product_page`
- `manual_or_official_training_material`

Then only chunk `full_text_pdf`, `full_text_html`, and `manual_or_official_training_material` by default. Keep metadata-only and preview pages in a separate bibliographic index.
