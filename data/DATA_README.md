# Data provenance

This directory holds manifests, checksums and annotations. It never holds full texts.

## What is committed

- `raw/corpus_snapshot_<date>.jsonl.gz`: bibliographic records of every work in the corpus as returned by the source APIs on the snapshot date (OpenAlex records are CC0; Semantic Scholar records are stored without abstracts, with identifiers, metadata and citation contexts). The snapshot is committed gzip-compressed because the plain file exceeds GitHub's 50 MiB warning threshold; the plain `.jsonl` is written by `scripts/collect_corpus.py`, kept locally and ignored by git. `checksums.sha256` records both the plain and the compressed file, so a reproduction decompresses and verifies either. Every script that reads a snapshot accepts both forms.
- `raw/manifest_<date>.csv`: one row per work with the entry identifier, DOI, arXiv identifier, source identifiers, title, year, first author, venue, type, seeds cited, open-access URL, citation count, sources, number of citation contexts, seed flag and the merge keys that united its records.
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
