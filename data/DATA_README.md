# Data provenance

This directory holds manifests, checksums and annotations. It never holds full texts.

## What is committed

- `raw/corpus_snapshot_<date>.jsonl`: bibliographic records of every work in the corpus as returned by the source APIs on the snapshot date (OpenAlex records are CC0; Semantic Scholar records are stored only as identifiers and citation links).
- `raw/manifest.csv`: one row per work with the canonical identifier, DOI, arXiv identifier, open-access URL, and the source(s) that returned it.
- `checksums.sha256`: SHA-256 of every file under `raw/` and `processed/`, including the full texts fetched locally, so that a reproduction can verify that it obtained the same inputs.
- `processed/contexts/`: extracted hypothesis-mention contexts and theorem environments (short excerpts; quotation for the purpose of scholarly analysis).
- `processed/annotations/`: human annotation records (annotator, timestamp, label, confidence, free-text justification) and adjudication decisions.
- `processed/classifications/`: model outputs with model name, tag, digest, prompt hash, temperature, seed and timestamp.

## What is not committed

- Full-text PDFs and LaTeX sources under `raw/fulltext/`, `raw/pdf/`, `raw/latex/`. They are fetched by `scripts/fetch_fulltext.py` from arXiv or the open-access location in the manifest and verified against `checksums.sha256`.
- API response caches under `raw/api_cache/`.

## Snapshot discipline

Each corpus snapshot is taken once, dated, hashed and never overwritten. Later snapshots are new files. The pre-registration names the snapshot that the confirmatory analysis uses.

## Collection method

To be recorded in `LOGBOOK.md` under EXP-001 (corpus construction): seed works, API queries, pagination, deduplication rules, and counts at every stage.
