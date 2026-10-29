"""ethcensus: a census pipeline for results conditional on the Exponential Time Hypothesis.

Stages (each a submodule, added as the corresponding experiment is planned in LOGBOOK.md):
    collect    corpus construction from OpenAlex and Semantic Scholar citation graphs
    fetch      full-text acquisition from arXiv and open-access locations, with checksums
    extract    deterministic extraction of hypothesis-mention contexts and theorem environments
    annotate   gold-set sampling, annotation records, agreement statistics
    classify   LLM classification against the codebook, with abstention
    analyze    error-corrected prevalence estimation, confidence intervals, figures
"""

__version__ = "0.0.1"
