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
- **Git commit:** to be recorded after `git init` and the first commit
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

### Addendum 2026-10-29 18:10
- `CODEBOOK.md` v0.1 and `PREREGISTRATION.md` v0.1 drafted from three background reports kept outside the repository (`_ai/paper4/reports/01` to `03`). Facts carried into the drafts: no public list of the 800+ dependent papers exists; Gap-ETH is refuted on paper only (no Lean statement in either repository); Orthogonal Vectors, k-Clique, Set Cover, unbounded-width CNF-SAT, pathwidth-SETH, PIH and Weak ETH (no 2^{n^{1-eps}}) are not refuted; OpenAlex and Semantic Scholar identifiers for the twelve seed records; direct citers of the two ETH-defining papers number about 2,600 distinct works in Semantic Scholar, about half with arXiv full text.
- Open decisions before the tag `prereg-v1`: gold-set option A or B, primary classifier model, venue.
