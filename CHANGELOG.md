# Changelog

All notable changes to this repository are documented here. The format follows Keep a Changelog, and the package follows semantic versioning.

## [Unreleased]

### Added
- Repository scaffold: logbook (EXP-000), findings skeleton, package skeleton `ethcensus` 0.0.1, base configuration, data README, smoke test.
- `CODEBOOK.md` v0.1 and `PREREGISTRATION.md` v0.1 (drafts, not yet frozen).
- `configs/seeds.yaml` (verified seed identifiers) and `configs/patterns.yaml` (hypothesis-mention patterns).
- `ethcensus.collect`: OpenAlex and Semantic Scholar clients with retry and throttling, candidate normalization, cross-source merging, dated snapshots, checksums, environment snapshot; 19 tests.
- `scripts/collect_corpus.py`: EXP-001 entry point with count-only and smoke modes.
