# Changelog

All notable changes to this repository are documented here. The format follows Keep a Changelog, and the package follows semantic versioning.

## [Unreleased]

### Added
- Repository scaffold: logbook (EXP-000), findings skeleton, package skeleton `ethcensus` 0.0.1, base configuration, data README, smoke test.
- `CODEBOOK.md` v0.1 and `PREREGISTRATION.md` v0.1 (drafts, not yet frozen).
- `configs/seeds.yaml` (verified seed identifiers) and `configs/patterns.yaml` (hypothesis-mention patterns).
- `ethcensus.collect`: OpenAlex and Semantic Scholar clients with retry and throttling, candidate normalization, cross-source merging, dated snapshots, checksums, environment snapshot; 19 tests.
- `scripts/collect_corpus.py`: EXP-001 entry point with count-only and smoke modes.
- `is_seed` flag on corpus entries (seed works citing other seeds are kept but excluded from sampling); manifest carries `is_seed` and `merge_keys`; stage counts report entries with several OpenAlex ids and entries merged by title alone.
- `ethcensus.extract`: hypothesis-context extraction from LaTeX (comment stripping with offsets kept, custom theorem environments via newtheorem and declaretheorem, section tracking, de-TeXing, sentence windows outside environments) and from PDF text or abstracts (heading blocks plus windows); 9 tests. `scripts/extract_contexts.py` entry point (EXP-002). ETH patterns no longer match inside SETH, Gap-ETH or #ETH.
- `ethcensus.fetch`: full-text acquisition (arXiv e-print with LaTeX flattening, arXiv PDF, OA PDF, optional OpenAlex cached PDF, abstract fallback), arXiv-compliant throttling, resumable status file, PDF text via PyMuPDF; 13 tests. `scripts/fetch_fulltext.py` entry point.
- `configs/patterns.yaml` 0.2: extraction code `ETH_PARA` for unnamed paraphrases of ETH and SETH; named-hypothesis patterns tolerate "exponentialtime" produced by dehyphenation.
- `scripts/fetch_fulltext.py --reprocess` and `ethcensus.fetch.reprocess_row`: re-derive processed texts from stored raw files after a change to the text processing, without network calls.
- `PREREGISTRATION.md` v0.1b: the sampling frame is the whole corpus; zero-context works form their own gold stratum; paper-level extractor miss rate is a reported quantity. `CODEBOOK.md` Section 9 revised to match.
- `scripts/inspect_merges.py`: prints the records behind merged corpus entries (title-only, cross-source, all) and the same-title pairs the title rule declined to unite (split), for logged spot checks.
- `configs/base.yaml`: Semantic Scholar request interval (1.1 s) and page size (1000) are configuration, read by `collect_corpus.py`.
- `PREREGISTRATION.md` v0.1c: deduplication rule as revised after the two-source smoke.

### Changed
- `ethcensus.extract.detex`: user macros become their own names (`\ETH` reads `ETH`), escaped characters and spaces are unescaped, section, title and author arguments stay on their own line, `\thanks`, `\url` and `\href` keep their visible text; premise phrases written with macros are now recognized.
- `ethcensus.extract.extract_plain`: a PDF theorem block also ends at the next theorem-like heading, numbered section heading or proof.
- `ethcensus.fetch.pdf_to_text`: PyMuPDF block mode (one line per paragraph, blank line between paragraphs), end-of-line hyphenation joined, NFKC normalization of ligatures. Processed PDF texts produced before this change are re-derived with `--reprocess`.
- `ethcensus.collect.merge_candidates`: the title rule's year tolerance is ten years instead of one (conference and journal versions of theory papers are typically two to eight years apart), and the rule is withheld for titles under three words, repository or volume boilerplate titles, and pairs with no year on either record; `surname_key` ignores single-letter tokens (OpenAlex sometimes appends a stray initial to author names).
