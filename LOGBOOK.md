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

---

## EXP-002: Extraction of hypothesis contexts from full texts

**Date:** 2026-10-29 17:10 (America/New_York)
**Researcher:** MS
**Type:** computational (deterministic text processing)
**Status:** planned

### Hypothesis
Pre-stated expectations: among entries with text basis LATEX, at least 80 percent yield at least one context (a hypothesis mention outside or inside a theorem-like environment); among those, at least 40 percent have at least one theorem-kind context. Lower figures mean the citation criterion admits many papers that cite a seed without using a hypothesis, which is itself a reportable number, not a failure. Extractor recall (the share of annotator-identified results that the extractor captured) is measured on the development set in EXP-003 and reported in the paper.

### Independent Variables
- Text basis: LATEX (flattened e-print), PDF (PyMuPDF text), ABSTRACT.
- Patterns file version (`configs/patterns.yaml`, hashed into the experiment config).

### Dependent Variables / Metrics
- Per text basis: entries, entries with at least one context, contexts, theorem-kind contexts. Per entry: number of contexts, hypothesis codes mentioned, whether a premise phrase matched.

### Control Conditions
- Deterministic; same inputs and patterns give identical outputs. Outputs are never overwritten.

### Protocol
1. `pytest tests -v` green (extractor tests in `tests/test_extract.py`).
2. Smoke: run on the OpenAlex-only smoke fetch: `python scripts/extract_contexts.py --status experiments/EXP-001/smoke/data/processed/fulltext_status_2026-10-29.csv --data-dir experiments/EXP-001/smoke/data --out experiments/EXP-002/smoke`; read a few contexts by eye and record what the patterns miss or over-match.
3. After EXP-001 completes: `python scripts/extract_contexts.py --status data/processed/fulltext_status_<date>.csv --out experiments/EXP-002`; commit `data/processed/contexts_<date>.jsonl` (short quotations with locators; the paper's scholarly-analysis basis for quotation) and the results files.

### Environment
- As EXP-001; git commit recorded at step 3.

### Results
To be filled.

### Observations
To be filled.

### Interpretation
To be filled.

### Artifacts
- `data/processed/contexts_<date>.jsonl`, `experiments/EXP-002/results/extract_counts_<date>.json`, `experiments/EXP-002/results/entry_summaries_<date>.json`, `experiments/EXP-002/config.yaml` (patterns hash), `experiments/EXP-002/environment.json`.

### Addendum 2026-10-29 17:35: protocol step 2 executed (smoke, OpenAlex-only fetch of ten arXiv entries), commit a45c57d
- Counts: 10 entries, 21 contexts. LATEX: 9 entries, 6 with at least one context, 20 contexts, 6 theorem-kind. PDF: 1 entry (E000079, arXiv 1111.1261), 1 context, theorem-kind. Against the pre-stated expectations: 67 percent of LATEX entries yield a context (expected at least 80 percent; ten entries give no precision, see the next point) and 4 of 6 entries with contexts have a theorem-kind context (expected at least 40 percent).
- Three LATEX entries yield no context: E000047 (arXiv cs/0602075), E000085 (arXiv 1010.1750), E000092 (arXiv 1208.2329). Whether they never name a hypothesis or spell it in a way the patterns miss (a macro such as `\eth`, a phrase such as "exponential-time hypotheses") is checked by grepping their flattened sources; the outcome is recorded in the next addendum before any pattern change.
- Defect 1 (misses, fixed): user macros kept their backslashes after de-TeXing, so `unless \ETH\ fails` (E000065, four theorem statements) was recognized as a mention but not as a premise phrase. De-TeXing now unescapes `\#`, `\&`, `\_` and the escaped space, and turns any remaining macro into its own name (`\ETH` becomes `ETH`, `\cnfsat` becomes `cnfsat`). Section, title and author commands keep their argument on its own line; `\thanks` is treated like `\footnote`; `\url` and `\href` keep their visible text; `\maketitle` and `\and` are dropped. A nested bracket in an environment's optional argument (`\begin{proof}[Proof of Theorem 2 of [cite]]`) no longer leaves a stray `]` (seen in E000066).
- Defect 2 (over-match, fixed): in PDF text, PyMuPDF puts no blank line between paragraphs, so the theorem block for E000079 (Theorem 4.2, Karp-Lipton) ran into the following paragraph, and the ETH mention in that paragraph was attributed to the theorem. A heading block now also ends at the next theorem-like heading, at a numbered section heading, or at `Proof`.
- Not defects, noted for the codebook: (a) E000065 states an equivalence ("ETH holds if and only if #d-SAT requires time exp(Omega(m))"), which the codebook routes as R_EQUIV; the extractor surfaces it mechanically. (b) The first window of E000076 reaches back into the author block because the title or abstract mentions the hypothesis; the window rule is unchanged, since the annotator sees the whole window. (c) Text before the first `\section` has an empty section field; the field is informative only.
- Decision: patterns.yaml is unchanged (version 0.1) until the grep of the three empty entries is in; the extractor change is code only and re-run on the same ten entries as the next step, with the before and after counts recorded here.

### Addendum 2026-10-29 17:55: the three zero-context entries, patterns 0.2, pre-registration v0.1b
- Grep of the three flattened sources for `\bS?ETH\b`, "exponential time hypothes", "Impagliazzo", "subexponential", then for unresolved `\input`/`\include`/`\subfile` commands and for 3-SAT, k-SAT, CNF, 2^{o(n)}, n^{o(k)} wording. All included files were resolved (only commented-out `\input` lines remain in E000047).
- E000085 (arXiv 1010.1750): one live use, line 541, "unless there is a subexponential-time quantum algorithm for 3-$\SAT$", with IP01 cited on a commented-out line 487; "ETH Zurich" on line 283 is the university and was correctly excluded. The paper uses ETH's content (a quantum variant) without its name. This is the paraphrase case.
- E000047 (arXiv cs/0602075) and E000092 (arXiv 1208.2329): no hypothesis name, no author name, no SAT or subexponential wording anywhere. They cite a seed for something other than a hypothesis, or the index's citation link is wrong; either way they are out of scope by CODEBOOK Section 8 and the extractor is right to return nothing.
- Change 1: patterns.yaml version 0.2 adds the extraction code ETH_PARA with three patterns for unnamed paraphrases ("subexponential(-time) [word] algorithm for ...SAT", "2^{o(n)}(-time) algorithm for ...SAT", "...SAT requires/cannot be solved/has ... 2^{o(n)} | 2^{Omega(n)} | 2^{(1-eps)n} | (2-eps)^n | subexponential"), matched on de-TeXed text. Probed on ten sentences before adoption (seven positives including the E000085 sentence, three negatives: "subexponential algorithms for planar graph problems", "the SAT solver", "Max-SAT is in APX"); all ten as intended; the probe is now `tests/test_extract.py::test_paraphrase_patterns_are_a_separate_code`. ETH_PARA is its own code so that its precision is reported apart from named mentions.
- Change 2: PREREGISTRATION.md v0.1b. The sampling frame of Section 5.1 had excluded zero-context works from the gold sample, which would have left the share of E000047-type works that do use a hypothesis unmeasured and would have made paper-level estimates shares of the frame rather than of the corpus. The frame is now the whole corpus with a zero-context stratum (60 works under Option A, 40 under Option B, single-coded), its in-scope share enters E1 and E3 design-based, and Section 4 names the paper-level miss rate as a reported quantity. CODEBOOK Section 9 revised to match (in place, before the tag).
- Expectation for the re-run on the same ten entries: E000085 gains at least one ETH_PARA context; E000065's four theorem statements gain premise_phrase True; E000079's theorem block no longer contains the paragraph after Theorem 4.2; E000047 and E000092 stay at zero.

### Addendum 2026-10-29 18:05: re-run under label 2026-10-29b, one prediction not met, PDF text extraction changed
- Met: E000065's three theorems and corollary with "unless ETH fails" now carry premise_phrase True (the equivalence theorem correctly stays False); E000085 gains one ETH_PARA context (section Results); E000047 and E000092 stay at zero.
- Not met: E000079's Theorem 4.2 block still runs into "Now how plausible is this assumption?". Cause: the following paragraph starts on the next line with no blank line and no heading, so no cut rule of the 17:35 fix applies. Plain-text mode of PyMuPDF discards the paragraph structure, so no rule on that text can be reliable. Fix at the source: `pdf_to_text` now uses PyMuPDF block mode, writes one line per paragraph block with a blank line between blocks (so a theorem statement ends with its paragraph and the existing blank-line cut applies), joins the lines of a block with end-of-line hyphenation removed ("Hy-/pothesis" reads "Hypothesis"), and applies NFKC normalization so that ligatures read as letters ("Satisﬁability" reads "Satisfiability"; the 2026-10-29b text of E000079 still contained the ligature). Verified on a synthetic two-paragraph, two-page PDF (`tests/test_fetch.py::test_pdf_to_text_keeps_paragraph_blocks_and_joins_hyphenated_lines`).
- Because processed PDF texts are now a different function of the raw downloads, `scripts/fetch_fulltext.py --reprocess` re-derives every processed text in a status file from the stored, checksummed raw files without network calls (`ethcensus.fetch.reprocess_row`, tested). Raw files, status rows and checksums are unchanged; the processed text's provenance is the raw checksum plus the code commit recorded in the extraction run's environment.json.
- Two small readability changes in de-TeXing: a macro glued to a word gets a space ("$x\in\Q$" reads "$x in Q$"); the named-hypothesis patterns accept "exponentialtime hypothesis" (version 0.2, `[- ]?`), which is what a line broken at "exponential-" produces after dehyphenation.
- Next: tests, `--reprocess` on the smoke status file, extraction re-run under label 2026-10-29c. Expectation: E000079's theorem context ends at "P/poly."; counts otherwise as in 2026-10-29b.

### Addendum 2026-10-30 01:45: run 2026-10-29c, predictions met
- 48 tests green. `--reprocess` re-derived 9 LATEX and 1 PDF processed texts. Extraction under patterns 0.2 (sha256 e68933ed1666...0e7cab719fb4903): 10 entries, 22 contexts; LATEX 9 entries, 7 with contexts, 21 contexts, 6 theorem-kind; PDF 1 entry, 1 context, 0 theorem-kind.
- E000079: with paragraph blocks restored, the Karp-Lipton theorem block ends at "P/poly." and contains no hypothesis mention, so it is no longer a context; the ETH mention in the following discussion paragraph is now a sentence window of its own ("The state of the art in satisfiability algorithms is far from half-exponential time ..."). This is the correct reading of the paper: the theorem is unconditional and ETH appears in the surrounding discussion. The 2026-10-29 and 2026-10-29b runs had attributed that mention to the theorem.
- Smoke summary against the pre-stated EXP-002 expectations: 7 of 9 LATEX entries (78 percent) yield a context, against an expectation of at least 80 percent; the two misses are confirmed cite-without-use entries, so the expectation was set too high for a corpus defined by citation alone, and the full-corpus figure will be read as a measurement of the citation criterion's over-inclusion, not as extractor failure. 4 of 7 LATEX entries with contexts have a theorem-kind context (57 percent), against an expectation of at least 40 percent.
- Commit of this state follows; the smoke artifacts stay git-ignored.

### Addendum 2026-10-30 02:05: committed as c9568d8; Semantic Scholar key received
- Commit c9568d8 also carries `experiments/EXP-001/config.yaml`, `environment.json`, `seed.json` and `results/counts_openalex_only.json` from the count-only run of 16:50, which had been left untracked at 4eabed8. The full pull overwrites the first three (the script freezes its configuration on every run); the count-only versions stay in the history at c9568d8.
- The Semantic Scholar key arrived with a limit of one request per second. `configs/base.yaml` now sets `min_interval_seconds: 1.1` and `limit: 1000` for the S2 client (the script read a hard-coded 1.0 before); the interval is above the limit so that timing jitter never trips it.
- EXP-001 protocol step 3 (smoke with both sources) can now run: one page per seed and source into the git-ignored smoke directory, snapshot label 2026-10-30-smoke. Expectation: the S2 page of IP01 and IPZ01 holds 1,000 items each (first page of about 2,600 distinct citers found in the pilot); the merged entry count exceeds the OpenAlex-only 733 and the share of entries with two sources is well below one half, since one page per source covers different subsets of the citers.

### Addendum 2026-10-30 15:35: protocol step 3 executed with both sources (smoke), run 15:29 to 15:30
- Key accepted. 11 OpenAlex list pages (100 records each, or all records for DIN16 45, MR17 54, DHMTW14 97) and 11 S2 first pages: IP01 1000, IPZ01 1000, CIP09 182, DIN16 116, MR17 129, DHMTW14 117, CGIMPS16 138, WIL05 565, CDLMNOPSW16 263, LMS11 396, VW18 278. 5,180 candidates merged into 2,744 entries (2,302 with DOI, 1,601 with arXiv identifier, 1,320 with an OA URL, 543 present in both sources, 50 with several OpenAlex records, 33 merged by title alone, 13 seed works). Expectations met: 1,000-item first pages for IP01 and IPZ01; 2,744 above 733; two-source share 20 percent.
- Pacing: three of eleven S2 requests received a 429 on the first attempt although at least 1.1 s (in two cases more than 7 s) had passed since the previous S2 request; each succeeded on the first or second retry (2 s and 4 s backoff). The 429s are therefore not caused by our interval; the retry policy absorbs them at a cost of a few seconds each, acceptable for the roughly 30 S2 requests of the full pull.
- Coverage: for every seed whose OpenAlex count is complete in one page, Semantic Scholar returns more citers (DIN16 45 against 116, MR17 54 against 129, DHMTW14 97 against 117), and the S2 first pages of the auxiliary seeds exceed the OpenAlex totals (WIL05 565 against 421, CDLMNOPSW16 263 against 187, LMS11 396 against 335, VW18 278 against 101). The union will therefore sit well above the OpenAlex-only 2,187 core citers; the pre-stated 3,000 to 5,000 expectation is re-checked at step 4. The coverage gap between the two indexes is reported in the paper as planned.
- Before step 4 (full pull), a spot check of the cross-source merge rule on this smoke snapshot: all 33 title-only merges, and a reproducible random sample of 20 of the 543 two-source entries (`scripts/inspect_merges.py`, seed 20261029). Verdicts recorded in the next addendum.

### Addendum 2026-10-30 16:10: merge spot check, one false merge found and fixed
- Title-only merges (33 entries, all read): 32 correct. They are conference and journal versions (E000189 ICALP 2012 and SIDMA; E000200 WADS 2013 and SIDMA; E000665 TU/e portal and Algorithmica; E000698 STOC 2018 and JACM; E001505 KR 2020 and AIJ; E001542 and E001914 PODS and the ACM Transactions versions; E001691 ISAAC 2021 and CGTA; E002178 LATIN 2024 and Algorithmica), repository or thesis copies (E000060, E000113, E000142, E000154, E000263), Semantic Scholar duplicates of one record (E000335 four copies, E001674 three), and SODA papers carrying two DOIs, `10.5555/...` in OpenAlex and `10.1145/...` or `10.1137/...` in Semantic Scholar (E000031, E000049, E000138, E000347), which only the title rule could unite.
- One false merge: E002744 fused ten Semantic Scholar records titled "UvA-DARE (Digital Academic Repository)", first author Yan-Lin Chen, no year, no DOI, five distinct paperIds each cited by two seeds. The title is repository boilerplate, and the rule treated two missing years as compatible. Fix in `merge_candidates`: the title rule is withheld when the normalized title has fewer than three words or matches repository or volume boilerplate (repository, front matter, table of contents, proceedings, editorial, preface, index, corrigendum, erratum, untitled), and when neither record carries a year; a pair with one dated record still merges. The number of withheld pairs is logged. Test `test_title_rule_withheld_for_generic_short_or_undated_titles`; two fixtures that used the two-word title "Treewidth bounds" for a legitimate title merge now use "Tight treewidth bounds".
- Cross-source sample (20 of 543, seed 20261029): 20 correct, all united by DOI or arXiv identifier. Observed quirks for later analysis: Semantic Scholar's `year` is often the preprint year while its DOI points to the journal version (E000843 2018 against 2023, E001614 2021 against 2024), and its venue strings are sometimes wrong ("Embedded Systems and Applications" for ESA in E001553, "Information Technology Convergence" for ITCS in E001618). Entry venue and type come from the OpenAlex record when one exists; venue analyses in the paper (exploratory) must normalize venues or use OpenAlex fields only. Entry year is the minimum over records, which reads as first appearance.
- Verification planned: tests, then the two-source smoke repeated under label 2026-10-30-smoke2. Expectation: `entries_total` rises from 2,744 to 2,748 (one entry becomes five), `entries_merged_by_title_only` falls from 33 to 32, `entries_by_seed` for CDLMNOPSW16 and VW18 rise by 4 each, other counts unchanged up to whatever the indexes added between the two runs; the log reports the withheld pairs.

### Addendum 2026-10-30 16:30: smoke2 result, the year tolerance was far too strict, rule revised (pre-registration v0.1c)
- 49 tests green. smoke2 (16:12): entries_total 2,749 (predicted 2,748), entries_merged_by_title_only 32, CDLMNOPSW16 267 and VW18 285 (both as predicted), entries_in_both_sources 542 (predicted 543); 38 candidate pairs withheld by the new rule, 9 of them the UvA group. The one extra separation is "Beyond Outerplanarity" (Chaplick et al., GD 2017 in S2, LNCS 2018 in OpenAlex), a correct merge lost to the three-word minimum. Accepted: a duplicate entry is the cheaper error and the annotator sees both; the minimum stays.
- `inspect_merges.py --mode split` on smoke2 listed 99 entries in 50 groups sharing normalized title and first-author surname without being merged. Five are the UvA entries, now correctly apart. The other 45 groups are all versions of one paper kept apart by the one-year tolerance I pre-stated: conference and journal versions two to eight years apart (Lokshtanov et al., SODA 2011 and TALG 2018; Marx and Pilipczuk, ESA 2015 and TALG 2022; Dell and van Melkebeek, STOC 2010 and JACM 2014; Williams, STOC 2010 and SICOMP 2013; Backurs and Indyk, STOC 2015 and SICOMP 2018; Abboud et al., SODA 2019 against its arXiv 2017 and TALG 2022 cluster; and so on), arXiv or repository copies against the published version (Chan, SODA 2015 and DSpace 2021; Haferkamp et al., arXiv 2018 and Refubium 2020), and two pairs lost to a metadata quirk: OpenAlex renders some author names with a trailing initial ("Maxime Crochemore A", "Virginia Vassilevska W"), so the surname key became a single letter.
- Revisions. (1) The title rule's year tolerance goes from one year to ten (`YEAR_TOLERANCE`), which covers every pair observed (largest gap 8 years, Lokshtanov et al. 2010 preprint against 2018 journal). The false-merge risk this adds is bounded by the identical normalized full title, the identical surname, the three-word minimum and the boilerplate screen. (2) `surname_key` ignores single-letter tokens when a longer token exists. (3) The two-word-title loss is accepted as stated. Tests: `test_title_and_surname_keys` gains the three quirk cases; the title-rule test gains a 2011 against 2018 pair that merges at the default tolerance and splits at tolerance one; one fixture year moves from 2019 to 2025 so the tolerance boundary is still exercised. PREREGISTRATION.md 3.2 step 3 revised (v0.1c).
- Why this matters for the paper: with the one-year rule roughly 45 of 2,749 entries (1.6 percent) in a one-page sample were duplicate versions; in the full corpus the share is higher because the smoke draws one page per source, and duplicates would inflate paper counts and split a paper's citations across two entries. The pre-stated rule was wrong in a way that the smoke was designed to reveal; the revision is logged before any full pull.
- Verification planned: tests, smoke3, `--mode split` again. Expectation: only the five UvA entries, the Chaplick pair, and any same-title pairs more than ten years apart remain in the split list; entries_total falls by about 45 relative to smoke2.

### Addendum 2026-10-30 16:35: smoke3 result, predictions met, merge rule final for the full pull
- 49 tests green. smoke3 (16:23): entries_total 2,700 (smoke2 2,749; predicted a fall of about 45, observed 49), entries_in_both_sources 553 (542), entries_merged_by_title_only 53 (32), 38 pairs withheld as before. `--mode split` lists 7 entries: the five UvA entries and the two-word "Beyond Outerplanarity" pair, exactly as predicted; no same-title pair more than ten years apart occurs in this sample.
- The three smoke snapshots (2026-10-30-smoke, smoke2, smoke3) stay in the git-ignored smoke directory as the record of the rule's development; the full pull uses the rule of smoke3 (DOI, arXiv, then title with surname within ten years, withheld for short or boilerplate titles and undated pairs). Commit follows, then protocol step 4.
