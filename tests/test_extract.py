from pathlib import Path

import pytest

from ethcensus import extract as X

PATTERNS = Path(__file__).resolve().parents[1] / "configs" / "patterns.yaml"

TEX = r"""
\documentclass{article}
\newtheorem{thm}{Theorem}[section]
\newtheorem{lem}[thm]{Lemma}
\newtheorem{mainthm}{Main Theorem}
\newtheorem{hyp}{Hypothesis}
\begin{document}
\section{Introduction}
We work at ETH Zurich. % ETH here is a university, not the hypothesis
Many results rely on the Exponential Time Hypothesis (ETH) \cite{IP01}.
Our bound is tight. It matches the algorithm of \cite{X}. See e.g. Section 3. Filler one. Filler two. Filler three. Filler four.
\section{Results}
\begin{thm}[Main result]\label{thm:main}
Unless SETH fails, no algorithm solves \textsc{Edit Distance} in $O(n^{2-\epsilon})$ time.
\end{thm}
\begin{lem}
Every graph has a vertex.
\end{lem}
\begin{proof}
Trivial. This proof mentions no hypothesis.
\end{proof}
Filler five. Filler six. Filler seven. The reduction from Orthogonal Vectors follows \cite{W05}. Filler eight.
\end{document}
"""


@pytest.fixture(scope="module")
def patterns():
    return X.Patterns.load(PATTERNS)


def test_patterns_load_and_match(patterns):
    codes, premise = patterns.match("Assuming the Strong Exponential Time Hypothesis (SETH), nothing is fast.")
    assert "SETH" in codes and "ETH" not in codes and premise
    codes, premise = patterns.match("We thank ETH Zurich for hosting us.")
    assert codes == [] and not premise
    codes, _ = patterns.match("Under Gap-ETH the problem has no FPT approximation; this also uses #ETH and NSETH.")
    assert {"GAP_ETH", "SHARP_ETH", "NSETH"} <= set(codes)
    codes, _ = patterns.match("The Orthogonal Vectors conjecture and the k-Clique conjecture survive.")
    assert "OVH" in codes and "KCLIQUE" in codes


def test_paraphrase_patterns_are_a_separate_code(patterns):
    hits = ["unless there is a subexponential-time quantum algorithm for 3-$SAT$, then a constant exists",
            "3-SAT cannot be solved in time 2^{o(n)}", "$k$-SAT requires time $2^{Omega(n)}$ for every k",
            "CNF-SAT cannot be solved in $O(2^{(1-\\epsilon)n})$ time"]
    for s in hits:
        codes, _ = patterns.match(s)
        assert codes == ["ETH_PARA"], s
    for s in ["subexponential algorithms for planar graph problems are known", "the SAT solver is fast", "Max-SAT is in APX"]:
        assert patterns.match(s)[0] == [], s


def test_strip_comments_preserves_offsets():
    tex = "a % comment\nb \\% not a comment"
    out = X.strip_comments(tex)
    assert len(out) == len(tex)
    assert out.startswith("a ") and "comment\nb" not in out and "\\% not a comment" in out


def test_theorem_environments_maps_custom_names():
    env = X.theorem_environments(TEX)
    assert env["thm"] == "theorem" and env["lem"] == "lemma"
    assert env["mainthm"] == "theorem" and env["hyp"] == "hypothesis"
    assert env["theorem"] == "theorem"
    env2 = X.theorem_environments(r"\declaretheorem[name=Key Lemma,numberwithin=section]{keylem} \begin{cor} \end{cor}")
    assert env2["keylem"] == "lemma" and env2["cor"] == "corollary"


def test_detex_drops_citations_and_formatting():
    s = X.detex(r"Unless \textbf{SETH} fails \cite{A,B}, see \Cref{thm:main}\label{x}. Let $n$ be large.")
    assert s == 'Unless SETH fails [cite], see [ref]. Let $n$ be large.'


def test_detex_turns_macros_into_their_names(patterns):
    s = X.detex(r"\IS\ requires time $\exp(\Omega(n))$ unless \ETH\ fails; see \#$d$-SAT and \fast{}.")
    assert s == "IS requires time $exp(Omega(n))$ unless ETH fails; see #$d$-SAT and fast."
    codes, premise = patterns.match(s)
    assert codes == ["ETH"] and premise
    s = X.detex(r"\subsection{Lower bound} \begin{proof}[Proof of Theorem 2 of [cite]] Suppose not. \end{proof}")
    assert s == "Lower bound\n Suppose not."
    s = X.detex(r"\title{A result}\author{A. Author\thanks{Funded.} \and B. Author}\maketitle See \url{http://x.org}.")
    assert s == "A result\n\nA. Author (footnote: Funded.) B. Author\n See http://x.org."
    assert X.detex(r"$x\in\Q$ and $n\log n$ and $2^{\Omega(n)}$") == "$x in Q$ and $n log n$ and $2^{Omega(n)}$"


def test_split_sentences_protects_abbreviations():
    text = "See e.g. Section 3. Filler one. Results by et al. hold. Done."
    spans = X.split_sentences(text)
    sentences = [text[a:b] for a, b in spans]
    assert sentences == ["See e.g. Section 3.", "Filler one.", "Results by et al. hold.", "Done."]


def test_extract_latex_theorem_and_sentence_contexts(patterns):
    ctx = X.extract_latex("E000001", TEX, patterns)
    kinds = [(c.kind, c.env_kind) for c in ctx]
    assert ("theorem", "theorem") in kinds
    thm = next(c for c in ctx if c.kind == "theorem")
    assert thm.hypotheses == ["SETH"] and thm.premise_phrase
    assert thm.label == "thm:main" and thm.title == "Main result" and thm.ordinal == 1
    assert thm.section == "Results" and "Edit Distance" in thm.text and "\\textsc" not in thm.text
    assert "\\begin{thm}" in thm.raw
    sent = [c for c in ctx if c.kind == "sentence"]
    assert len(sent) == 2
    intro = sent[0]
    assert intro.hypotheses == ["ETH"] and intro.section == "Introduction"
    assert "Exponential Time Hypothesis" in intro.text and "Zurich" not in intro.hypotheses
    assert "Our bound is tight" in intro.text            # window extends three sentences after
    assert "documentclass" not in intro.text and "newtheorem" not in intro.text
    ov = sent[1]
    assert ov.hypotheses == ["OVH"] and ov.section == "Results"
    assert [c.context_id for c in ctx] == ["E000001-C001", "E000001-C002", "E000001-C003"]
    assert all(c.text_basis == "LATEX" for c in ctx)


def test_extract_latex_ignores_lemma_without_mention(patterns):
    ctx = X.extract_latex("E1", TEX, patterns)
    assert not any(c.env_kind == "lemma" for c in ctx)


def test_extract_plain_pdf_headings_and_windows(patterns):
    text = ("1 Introduction\nThe problem is hard. We assume ETH throughout. Filler.\n\n"
            "Theorem 3.1. Unless the ETH fails, k-Clique has no f(k) n^{o(k)} algorithm.\n"
            "Proof. By [12].\n\nLemma 2. Every graph has a vertex.\n\nConclusion. Nothing else.\n"
            "Theorem 4.2 (Karp-Lipton) If Circuit SAT is in half-exponential time, then EXP is not in P/poly.\n"
            "5 Discussion\nUnder ETH this paragraph must not be glued to Theorem 4.2.")
    ctx = X.extract_plain("E2", text, patterns, text_basis="PDF")
    thm = [c for c in ctx if c.kind == "theorem"]
    assert len(thm) == 1 and thm[0].label == "3.1" and thm[0].hypotheses == ["ETH"] and thm[0].premise_phrase
    assert "Proof." not in thm[0].text
    assert not any("Karp-Lipton" in c.text and "glued" in c.text for c in ctx)
    sent = [c for c in ctx if c.kind == "sentence"]
    assert len(sent) == 1 and sent[0].hypotheses == ["ETH"]
    abstract = X.extract_plain("E3", "We prove hardness under SETH. Nothing more.", patterns, text_basis="ABSTRACT")
    assert len(abstract) == 1 and abstract[0].kind == "sentence" and abstract[0].text_basis == "ABSTRACT"


def test_summarize_and_write(tmp_path: Path, patterns):
    ctx = X.extract_latex("E000001", TEX, patterns)
    summary = X.summarize(ctx)
    assert summary["E000001"]["n_contexts"] == 3 and summary["E000001"]["n_theorem"] == 1
    assert summary["E000001"]["hypotheses"] == ["ETH", "OVH", "SETH"] and summary["E000001"]["premise"]
    out = tmp_path / "contexts.jsonl"
    assert X.write_contexts(ctx, out) == 3
    assert len(out.read_text(encoding="utf-8").splitlines()) == 3
