# Pre-registration

Working title: What Falls and What Survives: A Census of Results Conditional on the Exponential Time Hypothesis

Authors: Muntaser Syed, Marius Silaghi (Florida Institute of Technology)

Version 0.1, drafted 2026-10-29. Status: DRAFT. This document is frozen by the git tag `prereg-v1`; until that tag exists, edits are made in place and listed in the revision log. After the tag, nothing here changes; deviations are recorded in `LOGBOOK.md` with date and reason and are reported in the paper.

Items marked TO CONFIRM are decisions the authors must take before the tag.

## 1. Research questions

- RQ1. How many published results are proved conditionally on the Exponential Time Hypothesis or on a hypothesis that implies it, and which hypothesis does each proof use?
- RQ2. For each such result, does a hypothesis that the October 2026 refutations leave standing suffice for the same bound (survives), for a weaker bound (survives weakened), or for nothing (falls), and does the refutation transfer a new algorithm to the problem (transfer)?
- RQ3. What share of the SETH-attributed fine-grained lower bounds route through Orthogonal Vectors and therefore keep a premise?
- RQ4. How reliable is codebook-based classification of such results by expert annotators, and by large language models measured against adjudicated expert labels?
- RQ5. Which tight conditional lower bounds have lost their support, ranked by citation impact, so that the problems they concern are open again?

## 2. Scope

The refuted family is {ETH, rETH, SETH, rSETH, nuETH, nuSETH, #ETH, #SETH, Gap-ETH, NSETH} as defined in `CODEBOOK.md` Section 2, with status fixed on the reference date 2026-10-29. The census does not adjudicate the correctness of the claimed algorithms; every statement of the form "falls" is conditional on their correctness, and the paper says so in the abstract.

The unit of analysis is a result (theorem, corollary, proposition or lemma stated as conditional on a named hypothesis), aggregated to papers by the rules of `CODEBOOK.md` Section 8.

## 3. Corpus construction (EXP-001)

### 3.1 Seed works

Core seeds define the corpus. A work is in the corpus if it cites at least one core seed record in OpenAlex or in Semantic Scholar.

| Seed | Hypothesis defined | OpenAlex records | Semantic Scholar paperId |
| --- | --- | --- | --- |
| Impagliazzo, Paturi, On the complexity of k-SAT (CCC 1999; JCSS 2001) | ETH, sk, s_infty | W1507717186, W1985572324 | 94ebc9130e780c017e6e851c8c3d24b7c61c727d |
| Impagliazzo, Paturi, Zane, Which problems have strongly exponential complexity? (FOCS 1998; JCSS 2001) | ETH, sparsification, SERF | W1684108869, W1995725694 | a3651caf1265328e3231fe2d261679b4d926d5b7 |
| Calabro, Impagliazzo, Paturi, The complexity of satisfiability of small depth circuits (IWPEC 2009) | SETH (named) | W1576180980 | b0fc4fffa1f9fa85ea82167ea48b9cee1406ebc1 |
| Dinur, Mildly exponential reduction from gap 3SAT to polynomial-gap label-cover (ECCC TR16-128) | Gap-ETH | W2576456765 | 1d409293c2cc9913295be8a6778127bbc29d2beb |
| Manurangsi, Raghavendra, A birthday repetition theorem and complexity of approximating dense CSPs (ICALP 2017; arXiv:1607.02986) | Gap-ETH (named) | W2461430093 | b1f811e3e29382fa1de591957804aafdef382fd6 |
| Dell, Husfeldt, Marx, Taslaman, Wahlen, Exponential time complexity of the permanent and the Tutte polynomial (TALG 2014; ICALP 2010) | #ETH | W2021372200, W1786652263 | 6c35958ed428d76cce9a20c28321e1432e3fd80c |
| Carmosino et al., Nondeterministic extensions of the Strong Exponential Time Hypothesis (ITCS 2016) | NSETH | W2294619171 | 318a0217242c181ebe66e15056bbc2901f1b47f7 |

Auxiliary seeds extend the corpus to papers that cite the hypotheses through surveys or through the Orthogonal Vectors connection rather than through the defining papers. They are collected separately and tagged by seed so that every statistic can be reported with and without them.

| Auxiliary seed | OpenAlex records | Semantic Scholar paperId |
| --- | --- | --- |
| Williams, A new algorithm for optimal 2-constraint satisfaction and its implications (TCS 2005; ICALP 2004) | W2084732238, W1571792361 | cde0d7cc93fc82fcf218db056d1e6a2053266af8 |
| Cygan et al., On problems as hard as CNF-SAT (TALG 2016; CCC 2012) | W2404960361, W2139087151 | aec7d7d5d81064942bc5cebf8455f150e8d7ac57 |
| Lokshtanov, Marx, Saurabh, Lower bounds based on the Exponential Time Hypothesis (BEATCS 2011), conflated in both indexes with chapter 14 of Parameterized Algorithms (2015) | W2249739104 | 77042a24ac267ba3d486c9dc53693e03626c9b80 |
| Vassilevska Williams, On some fine-grained questions in algorithms and complexity (ICM 2018) | W2972926935 | 7659e4632203e8af7b4c3907b6c851e2ebc93496 |

The book-level record of Parameterized Algorithms (W2914414140, about 2,000 citers, most unrelated to ETH) is excluded from the corpus and used only in the recall check of Section 3.5.

### 3.2 Sources and procedure

1. OpenAlex, primary: `GET /works?filter=cites:<ids joined by |>&per_page=100&cursor=*&api_key=KEY&select=...` with the field list recorded in `configs/base.yaml`; cursor pagination to exhaustion; `meta.count` recorded per seed group. Metadata are CC0 and are committed in full.
2. Semantic Scholar, secondary: `GET /paper/{id}/citations?fields=...&limit=1000` paged by offset, with citation `contexts` retained; identifiers and citation links are committed, abstracts are not.
3. Union and deduplication: match on DOI (case-folded), then arXiv identifier, then normalized title plus first-author surname plus year within one year. Conference and journal versions of one paper are merged into one corpus entry with both identifiers retained. Every merge decision is logged.
4. Counts at every stage (per source, per seed group, after union, after deduplication) are written to `experiments/EXP-001/results/counts.json`.
5. The snapshot is taken once, dated, hashed into `data/checksums.sha256`, and never overwritten.

### 3.3 Full-text acquisition

For each corpus entry, in order of preference: arXiv e-print LaTeX source; arXiv PDF; open-access PDF from `best_oa_location.pdf_url` or `openAccessPdf.url`; OpenAlex cached PDF; abstract only. The basis obtained is recorded as `text_basis` (LATEX, PDF, ABSTRACT). Requests obey the arXiv Terms of Use (one request per three seconds, single connection). Full texts are stored locally, verified by checksum, and never redistributed.

### 3.4 Inclusion and exclusion

Included: every deduplicated work citing at least one core seed, any document type, any language (non-English works flagged and annotated by abstract if no annotator reads the language). Excluded: works whose metadata cannot be resolved to a title (logged by identifier).

### 3.5 Recall check of the citation criterion

The citation criterion misses papers that use ETH without citing a seed (for example citing only the textbook or a survey not in the seed list). To estimate the miss rate, a sample of 100 works is drawn from an OpenAlex search for the hypothesis names ("exponential time hypothesis", "strong exponential time hypothesis", "Gap-ETH") restricted to works not in the corpus, annotated by the same codebook, and the share that is exposed is reported as the recall bound of the corpus definition. This sample is reported separately and is not pooled into corpus estimates.

## 4. Extraction (EXP-002)

The extractor (`ethcensus.extract`) produces, for each work, every theorem-like environment and every sentence within three sentences of a hypothesis mention, using the pattern list `configs/patterns.yaml` (frozen with the tag). Extraction coverage (works with at least one context, by text_basis) is reported. The extractor is validated on the development set (Section 5.2): the share of annotator-identified results that the extractor captured is reported as extractor recall.

## 5. Human annotation (EXP-003)

### 5.1 Sampling frame and strata

The frame is the set of corpus works with at least one extracted context, plus the works with text_basis ABSTRACT. Strata: text_basis (LATEX, PDF, ABSTRACT) crossed with publication period (up to 2010, 2011 to 2016, 2017 to 2021, 2022 to 2026) and with the seed group cited (ETH-defining only; SETH; Gap-ETH; #ETH; NSETH; auxiliary only). Allocation is proportional with a minimum of 20 works per non-empty stratum, so rare hypotheses are oversampled; sampling weights are recorded and used in every estimate.

### 5.2 Sample sizes (TO CONFIRM)

Two requirements set the size: a Wilson interval of half-width 0.05 at 95 percent on the exposed share needs 381 works at the worst case, and Krippendorff's sample-size rule for alpha at or above 0.80 with four to five codes and two coders needs about 139 double-coded works.

- Option A (recommended): gold set 400 works, of which 150 double-coded by MS and MSi (reliability subsample) and 250 single-coded, split equally; development set 40 further works, disjoint, used for the codebook pilot and prompt development and excluded from all statistics. Estimated effort at 30 minutes per work: about 300 person-hours.
- Option B: gold set 300 (half-width about 0.057), 100 double-coded; development set 40. About 220 person-hours.

The sample is drawn by `scripts/sample_gold.py` with master seed 20261029 before any annotation begins, and the drawn identifiers are committed.

### 5.3 Procedure

Annotators follow `CODEBOOK.md` at the version frozen with the tag. The pilot on the development set precedes the tag; codebook revisions after the pilot are listed in the codebook's revision log. Annotators work independently, in randomized order, without access to model outputs or to each other's records. Time per work is logged. Adjudication follows `CODEBOOK.md` Section 11; agreement is computed on pre-adjudication records.

### 5.4 Reliability gate

Krippendorff's alpha (nominal) on the five-class coarse label in the reliability subsample, with a 10,000-resample bootstrap interval, is the quality gate. If alpha is below 0.667, the classifier study (EXP-004) is not run on the full corpus and the paper reports the reliability result and the codebook as its findings. If alpha is between 0.667 and 0.800, the classifier study runs and all conclusions are labelled tentative. Cohen's kappa for the pair and per-class agreement are reported alongside.

## 6. Classifier study (EXP-004)

### 6.1 Models (TO CONFIRM)

- Primary: one Ollama cloud model, chosen on the development set before any test-set evaluation and recorded by name, tag, digest and run date. Candidate list from the Ollama cloud catalogue on 2026-10-29: deepseek-v4.1-flash, glm-5.3, kimi-k3, nemotron-3-ultra, mistral-large-4, gemma4:31b.
- Secondary: one open-weight model served locally on the RTX 4090 (16 GB VRAM), pinned by digest, for reproducibility without cloud access. Candidate: gemma4:12b.
- Both run; the primary is named before the test set is touched and is the one H3 refers to. The secondary is a sensitivity analysis, not an independent rater.

### 6.2 Inputs and prompt

Input per candidate result: the paper's title and abstract, the extracted context, the theorem environment if present, and the codebook sections 2, 4, 5 and 6. The prompt is developed on the development set only, then frozen by hash. Temperature 0. Three runs with different seeds; the label is the majority; no majority yields ABSTAIN. Output is structured JSON with the fields of `CODEBOOK.md` Section 3 and a free-text rationale. The model never emits bibliographic identifiers; every citation it refers to is resolved by the pipeline against the corpus manifest.

### 6.3 Evaluation

Against adjudicated gold on the 400-work gold set (development set excluded): per-class precision and recall, macro-F1, Cohen's kappa on the five-class and binary labels, the confusion matrix M used for correction, abstention rate, and run-to-run self-agreement. Reported following the CEE reporting guidance for AI in evidence synthesis (model identity, role, validation, prompts, human oversight).

## 7. Analysis plan (EXP-005)

### 7.1 Estimands

- E1: share of in-scope results, and of corpus papers, that are exposed (coarse label FALLS), overall and by seed group, period and field.
- E2: among in-scope results whose stated premises include SETH and whose result_type is FINE, the share with route R_OV.
- E3: number of exposed papers under the Anthropic criterion (`CODEBOOK.md` Section 8), with a 95 percent interval, compared with the figure "more than 800" stated in the Anthropic paper. No directional prediction; the comparison is pre-specified.
- E4: the list of results with tightness TIGHT and status F_NONE, ranked by the citing paper's OpenAlex cited_by_count (the reopened problems list).
- E5: the list of T_TRANSFER results.

### 7.2 Estimation

Corpus-level shares are estimated two ways, and both are reported:

1. Model-corrected: adjusted classify-and-count. The classifier's label distribution q on the corpus is corrected with the gold confusion matrix M by solving q = M p under p at or above 0 and sum p = 1 (constrained least squares); the binary case reduces to the Rogan-Gladen estimator. Intervals by stratified bootstrap with 10,000 resamples that resample the gold set within true class and the corpus labels within stratum, percentile interval, clipped to [0, 1].
2. Design-based: weighted estimate from the gold set alone (Horvitz-Thompson with the stratum weights of Section 5.1), with a Wilson interval.

If the two intervals do not overlap, the design-based estimate is the headline and the discrepancy is reported as a finding about the classifier.

### 7.3 Confirmatory hypotheses and decision rules

- H1 (Orthogonal Vectors routing): E2 is at least 0.50. Supported if the lower bound of the 95 percent interval exceeds 0.50; refuted if the upper bound is below 0.50; inconclusive otherwise.
- H2 (exposure): E1 at the result level is at least 0.30. Same decision rule.
- H3 (classifier reliability): the primary classifier's Cohen's kappa against adjudicated gold on the five-class label is at least 0.70 as a point estimate with a bootstrap 95 percent lower bound of at least 0.60.
- H4 (human reliability): Krippendorff's alpha on the reliability subsample is at least 0.80 (Section 5.4 states what happens below 0.667).

H1 to H3 form one family; where p-values are computed (bootstrap, one-sided), Holm-Bonferroni holds the family-wise error at 0.05. All four hypotheses were fixed before any corpus data were examined; the numbers 0.50, 0.30, 0.70 and 0.80 were chosen from the community discussion (Lampis, cstheory 57313), from the Anthropic paper's exclusion criterion, and from the inter-rater standards cited in `_ai` report 2 (McHugh 2012; Krippendorff 2004).

### 7.4 Pre-specified sensitivity analyses

1. Secondary model in place of the primary.
2. ABSTAIN treated as its own class versus assigned by a human.
3. Corpus with and without auxiliary seeds.
4. Corpus with and without ABSTRACT-only works.
5. Exposure under the Anthropic criterion versus under the full substitute search.
6. Unweighted versus weighted estimates.

### 7.5 Exploratory analyses (labelled as such in the paper)

Temporal trend of exposed results per year; distribution by field and venue; citation-weighted exposure; agreement between S2 citation contexts and the annotated premise; the inter-model agreement between primary and secondary classifiers.

## 8. Reproducibility commitments

- Every number in the paper traces to an `EXP-XXX` entry, a frozen config, an environment snapshot (`environment.json`), and a results file.
- Random seeds: master seed 20261029; per-script seeds derived and logged.
- Full-text inputs are verified by `data/checksums.sha256`; the fetch script reproduces the local store from the manifest.
- Released: code (MIT), annotations and derived statistics (CC BY 4.0), metadata (CC0), prompts, codebook, and the adjudication notes. Not released: full texts.
- All model runs record model name, tag, digest, prompt hash, temperature, seed and timestamp. Cloud models are additionally recorded with the run date because their weights are not under the authors' control.

## 9. Stopping rules and deviations

There is no time-based stopping rule. The work stops when EXP-005 is complete or when the reliability gate of Section 5.4 is failed. Any deviation from this document is logged with date and reason and reported in the paper's methods section.

## 10. Venue (TO CONFIRM)

Primary target: Journal of Artificial Intelligence Research. The manuscript is written at full length; a short announcement of the dataset may be submitted to FLAIRS-40 if the dataset exists by its deadline.

## Revision log

- 2026-10-29 v0.1: initial draft from the three background reports in `_ai/paper4/reports/`.
