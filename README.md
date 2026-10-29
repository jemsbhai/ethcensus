# What Falls and What Survives: A Census of Results Conditional on the Exponential Time Hypothesis

Working repository for a census of published results that are proved conditionally on the Exponential Time Hypothesis (ETH) or on a hypothesis that implies it (SETH, Gap-ETH, #ETH, #SETH, NSETH, non-uniform variants), prompted by the claimed refutations of ETH released by OpenAI on 26 October 2026 and by Anthropic on 27 October 2026.

The census answers, for each conditional result, which hypothesis its proof actually uses, whether a weaker hypothesis that is not refuted (for example the Orthogonal Vectors conjecture) suffices, and whether the result is therefore unsupported, still supported, or turned into a new algorithm by the refutation. The pipeline combines deterministic extraction of hypothesis-mention contexts from paper sources, human expert annotation of a gold set, and classification of the full corpus with large language models, with classifier error corrected in the prevalence estimates.

Status: scaffolded, pre-registration in preparation. Nothing in this repository is a result until it is recorded in `LOGBOOK.md` under an experiment identifier and summarized in `findings.md`.

## Authors

Muntaser Syed and Marius Silaghi, Florida Institute of Technology.

## Repository layout

```
paper4/
  README.md             this file
  LOGBOOK.md            append-only experimental logbook (plan before run, results after)
  findings.md           curated summary plus append-only raw findings log
  PREREGISTRATION.md    frozen hypotheses, sampling plan and analysis plan (tagged before data collection)
  CODEBOOK.md           annotation codebook for hypothesis labels, dependency routes and survival status
  CHANGELOG.md
  requirements.txt      direct dependencies; requirements.lock.txt is the pip freeze used for the reported runs
  pyproject.toml        the ethcensus package (src layout)
  configs/              experiment configurations; frozen copies live with each experiment
  data/                 manifests, checksums, annotations and DATA_README.md (full texts are never committed)
  src/ethcensus/        collection, extraction, annotation, classification and analysis code
  scripts/              entry points, one per pipeline stage
  experiments/          one directory per EXP-XXX with frozen config, environment snapshot, seeds, results, figures
  tests/                pytest suite
  paper/                LaTeX source
```

## Setup

Python 3.12 on Windows, no virtual environment (the project convention).

```powershell
cd E:\data\code\claudecode\ethpapers\paper4
pip install -r requirements.txt
pip install -e .
Copy-Item .env.example .env   # then fill in the keys
pytest tests -v
```

Keys: OpenAlex (free, https://openalex.org/settings/api) and Semantic Scholar (free, request form linked from https://www.semanticscholar.org/product/api). Without an OpenAlex key, requests share a $0.10 per day budget with every other keyless user on the same IP address, which is not enough for a corpus crawl.

## Reproduction

Every reported number traces to an `EXP-XXX` entry in `LOGBOOK.md`, a frozen config in `experiments/EXP-XXX/config.yaml`, an environment snapshot, and a results file. The pipeline stages and the scripts that run them are listed in `LOGBOOK.md` as they are added. Full texts are fetched by script from the original sources and verified against `data/checksums.sha256`; they are not redistributed.

## Licensing

Code: MIT (see `LICENSE`). Released annotations and derived statistics: CC BY 4.0. OpenAlex metadata: CC0. Full texts of studied papers: not redistributed.
