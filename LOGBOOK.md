# Experimental Logbook

Append-only. Corrections are dated addenda that reference the original entry. Every experiment gets its plan written here before it runs and its results after it completes. Experiment identifiers are EXP-000 onward.

Conventions: timestamps are local time, America/New_York. Researcher names: MS (Muntaser Syed), MSi (Marius Silaghi). Commit SHAs are recorded in full once the repository is initialized.

---

## EXP-000: Project initiation and pre-registration setup

**Date:** 2026-10-29 15:45 (America/New_York)
**Researcher:** MS
**Type:** computational (scientometric corpus construction, human annotation, LLM-assisted classification)
**Status:** planned

### Hypothesis
Not applicable. This entry records the project decisions taken before any data collection, so that later entries can reference them.

### Independent Variables
Not applicable.

### Dependent Variables / Metrics
Not applicable.

### Control Conditions
Not applicable.

### Protocol
1. Scaffold the repository (this commit).
2. Obtain API keys for OpenAlex and Semantic Scholar; store them in `.env` only.
3. Write `CODEBOOK.md` v0.1 and `PREREGISTRATION.md` v0.1.
4. Pilot the codebook on a small development set that is disjoint from every later gold or test set, revise the codebook, and record each revision as a dated addendum.
5. Freeze the pre-registration in a tagged commit (`prereg-v1`) before the corpus snapshot is taken. No corpus-level statistic is computed before that tag exists.
6. Proceed to EXP-001 (corpus construction).

### Decisions recorded at initiation
- D1. Working title: "What Falls and What Survives: A Census of Results Conditional on the Exponential Time Hypothesis".
- D2. Target venue: to be fixed in the pre-registration; the draft is written venue-agnostic at full length and trimmed later.
- D3. AI workflow material (continuation prompts, agent reports, task lists) lives outside this repository in `E:\data\code\claudecode\ethpapers\_ai\paper4\`. This repository holds only publishable and reproducible material.
- D4. Annotators for the gold set: MS and MSi. A double-coded reliability subsample is used to estimate inter-annotator agreement.
- D5. Classification engines: an open-weight model served locally by Ollama on the RTX 4090 (16 GB VRAM) and an Ollama cloud model. Which one is primary is fixed in the pre-registration before any test-set evaluation. Every model is recorded by name, tag and digest, with the date of the run, because cloud-served weights can change.
- D6. Python 3.12, no virtual environment, dependencies in `requirements.txt` with the exact resolved versions committed in `requirements.lock.txt` (`pip freeze`).
- D7. The repository is public from the first commit. Pre-registration therefore carries a public timestamp.
- D8. Package name: `ethcensus` (PyPI name availability confirmed on 2026-10-29 via the pypi.org JSON endpoint returning 404).
- D9. Licensing: code MIT, released annotations CC BY 4.0, OpenAlex metadata CC0, full texts never redistributed.

### Environment
- **Hardware:** Windows 11 laptop, Intel i9-14900HX, 64 GB RAM, NVIDIA RTX 4090 Laptop GPU (16 GB VRAM)
- **Software:** Python 3.12; package versions to be recorded in `requirements.lock.txt`
- **Git commit:** 164f38644845964f8688501efb2f23597733e587 (root commit, 2026-10-29; public repository https://github.com/jemsbhai/ethcensus)
- **Config file:** `configs/base.yaml`
- **Seeds:** master seed 20261029, recorded in `configs/base.yaml`

### Results
Not applicable.

### Observations
- The sandbox used for drafting could reach api.openalex.org, api.semanticscholar.org and export.arxiv.org. OpenAlex returned a notice that keyless requests share a $0.10 per day budget per IP address and that a free key provides $1 per day. Semantic Scholar returned HTTP 429 to a keyless request. Both keys are therefore required before EXP-001.

### Interpretation
Not applicable.

### Artifacts
- This file, `README.md`, `.gitignore`, `.env.example`, `LICENSE`, `pyproject.toml`, `requirements.txt`, `configs/base.yaml`, `data/DATA_README.md`, `src/ethcensus/__init__.py`, `tests/test_smoke.py`.

### Addendum 2026-10-29 16:00
- `CODEBOOK.md` v0.1 and `PREREGISTRATION.md` v0.1 drafted from three background reports kept outside the repository (`_ai/paper4/reports/01` to `03`). Facts carried into the drafts: no public list of the 800+ dependent papers exists; Gap-ETH is refuted on paper only (no Lean statement in either repository); Orthogonal Vectors, k-Clique, Set Cover, unbounded-width CNF-SAT, pathwidth-SETH, PIH and Weak ETH (no 2^{n^{1-eps}}) are not refuted; OpenAlex and Semantic Scholar identifiers for the twelve seed records; direct citers of the two ETH-defining papers number about 2,600 distinct works in Semantic Scholar, about half with arXiv full text.
- Open decisions before the tag `prereg-v1`: gold-set option A or B, primary classifier model, venue.

### Addendum 2026-10-29 16:45
- D10 (supersedes D5): classification uses Ollama cloud models only, called directly at https://ollama.com/api/chat with the account key; no model is hosted locally. Primary and secondary classifiers are two different cloud models, each recorded by name, tag, digest and run date. Because cloud weights are outside the authors' control, every raw model response is committed so that the analysis is reproducible from the recorded outputs even if a model is later changed or withdrawn.

---

## EXP-001: Corpus construction from the citation graphs of the seed works

**Date:** 2026-10-29 16:30 (America/New_York)
**Researcher:** MS
**Type:** computational (API data collection)
**Status:** planned

### Hypothesis
Descriptive experiment with pre-stated expectations, from the Semantic Scholar pilot numbers in `_ai/paper4/reports/01` (2,596 distinct citers of IP01 and IPZ01 in S2 on 2026-10-29, 51 percent with arXiv identifiers): the union of citers of the seven core seeds, deduplicated across OpenAlex and Semantic Scholar, will contain between 3,000 and 5,000 entries, with at least 45 percent carrying an arXiv identifier and at least 60 percent a DOI. A count outside 2,000 to 7,000 triggers a check of the seed identifiers before anything else is done.

### Independent Variables
- Seed group: core (IP01, IPZ01, CIP09, DIN16, MR17, DHMTW14, CGIMPS16) and aux (WIL05, CDLMNOPSW16, LMS11, VW18), tagged per entry so every later statistic can be reported with and without aux.
- Source: OpenAlex (filter `cites:`, cursor paging) and Semantic Scholar (`/paper/{id}/citations`, offset paging, with citation contexts).

### Dependent Variables / Metrics
- Counts at every stage: candidates per seed and source, `meta.count` versus fetched per seed (OpenAlex), entries after merging, entries with DOI, with arXiv identifier, with an OA PDF URL, present in both sources, merged by title match.

### Control Conditions
- Deterministic given the API state; the snapshot is dated and never overwritten. The collection runs once; a rerun produces a new dated snapshot and is a new logbook entry.

### Protocol
1. Confirm the keys are in `.env` and that `pytest tests -v` passes (21 tests).
2. Cheap check of keys and identifiers: `python scripts/collect_corpus.py --out experiments/EXP-001 --count-only`. Record the printed counts here.
3. Smoke run of one page per seed and source into a scratch data directory that git ignores: `python scripts/collect_corpus.py --out experiments/EXP-001 --max-pages 1 --data-dir experiments/EXP-001/smoke`. Inspect `experiments/EXP-001/smoke/raw/manifest_<date>.csv`.
4. Commit the clean tree, then run the full collection: `python scripts/collect_corpus.py --out experiments/EXP-001`. Expected duration: OpenAlex about 60 list calls at 30 per second; Semantic Scholar about 12 pages at 1 request per second; under five minutes if no 429 backoff is needed.
5. Record the commit SHA, `experiments/EXP-001/results/counts.json`, and the snapshot file name in the Results section; commit the snapshot, manifest and checksums.

### Environment
- **Hardware:** Windows 11 laptop, Intel i9-14900HX, 64 GB RAM
- **Software:** Python 3.12; versions in `requirements.lock.txt`; `experiments/EXP-001/environment.json` written by the script
- **Git commit:** to be recorded at step 4
- **Config file:** `configs/base.yaml` and `configs/seeds.yaml`, frozen into `experiments/EXP-001/config.yaml`
- **Seeds:** master seed 20261029 (no randomness in this experiment)

### Results
To be filled.

### Observations
To be filled.

### Interpretation
To be filled.

### Artifacts
- `data/raw/corpus_snapshot_<date>.jsonl`, `data/raw/manifest_<date>.csv`, `data/checksums.sha256`, `experiments/EXP-001/results/counts.json`, `experiments/EXP-001/config.yaml`, `experiments/EXP-001/environment.json`.

### Addendum 2026-10-29 16:40: stage 2, full-text acquisition
- Protocol continues after step 5: (6) smoke run `python scripts/fetch_fulltext.py --snapshot data/raw/corpus_snapshot_<date>.jsonl --out experiments/EXP-001 --limit 5`, inspect `data/processed/fulltext/E*/` and the status file; (7) full run without `--limit`; the run is resumable and obeys the arXiv limit of one request per three seconds, so about 2,000 arXiv entries take at least two hours (two calls when the e-print is not usable); (8) record `experiments/EXP-001/results/fulltext_counts_<date>.json` (entries by text basis and by source) in Results.
- Expectation: text_basis LATEX for at least 40 percent of core entries and LATEX or PDF for at least 60 percent, from the S2 pilot numbers (51 percent with arXiv identifiers, 42 percent with an OA PDF URL).
- The OpenAlex cached-PDF fallback (`--use-openalex-content`, $0.01 per download) is not used in the first full run; its use for the remaining entries is decided after step 8 and logged as its own addendum.
- Additional artifacts: `data/processed/fulltext_status_<date>.csv` (committed), checksum lines for every downloaded file (committed), the downloads themselves (git-ignored, never redistributed).

### Addendum 2026-10-29 16:50: protocol step 2 executed (count-only), commit 4eabed8
- OpenAlex citer counts per seed: IP01 1146, IPZ01 1442, CIP09 124, DIN16 45, MR17 54, DHMTW14 97, CGIMPS16 101, WIL05 421, CDLMNOPSW16 187, LMS11 335, VW18 101; union of core seeds 2187 distinct works. Budget after twelve calls: $0.9989 of the daily $1.
- Check against the pre-stated expectation (3,000 to 5,000 for the deduplicated union of both sources): OpenAlex alone gives 2,187, inside the 2,000 to 7,000 tripwire band, below the expected range. The S2 pilot found 2,596 distinct citers of IP01 and IPZ01 alone, so the two sources differ in coverage by roughly 20 to 30 percent; the expectation is re-checked when the S2 key arrives and the union is built. Whichever way it falls, the difference in coverage between the two databases is itself reported in the paper.
- The Semantic Scholar key has been requested; steps 3 and 4 (smoke run, full pull) wait for it so that the snapshot carries both sources at once. A smoke run with OpenAlex only is permitted in the meantime because it writes to a git-ignored scratch directory.

### Addendum 2026-10-29 16:50: protocol step 3 executed with OpenAlex only (smoke), commit a3fd428
- One page per seed (996 candidates) merged into 733 entries: 712 with DOI, 183 with arXiv identifier, 480 with an OA URL, 32 with two or more OpenAlex records, 20 merged by title alone, 10 flagged is_seed (seed records citing other seeds).
- Spot check of all 32 multi-record entries by title, first author and year: every one is a conference, journal or preprint version of the same paper (examples: Patrascu and Williams, SODA 2010; Abboud, Vassilevska Williams and Wang, 2015; Gao, Impagliazzo, Kolokolova and Williams, 2017, three records). No false merge found; the title rule (normalized title, first-author surname, years within one) is kept for the full pull.
- Known OpenAlex quirk confirmed in the data: the CCC 1999 record of IP01 carries publication_year 2003.
- Process note: commit a3fd428 was made while one test (a fixture with identical default titles that the merge rule correctly unified) was failing; the fixture is corrected in the following commit. The code under test was not at fault.
