# Annotation Codebook

Version 0.1 (draft, 2026-10-29). Status: not frozen. Revisions before the pre-registration tag are made in place with a dated entry in the revision log at the end of this file; after the tag, every change is a new version and the logbook records which version each annotation used.

## 1. Purpose and unit of analysis

The census records, for every published result whose proof depends on the Exponential Time Hypothesis or on a hypothesis that implies it, which hypothesis the proof actually uses and what the claimed refutations of ETH (OpenAI, 26 October 2026; Anthropic, 27 October 2026) do to it.

The unit of annotation is a **result**: a theorem, corollary, proposition or lemma, stated in a paper, that is conditional on a named hardness hypothesis. A paper contributes zero or more results. Paper-level labels are derived from result-level labels by the rules in Section 8.

Three facts drive the design and must be kept apart by annotators:

1. A conditional theorem of the form "if H then X" remains true when H is refuted. What changes is that it no longer provides evidence for X. The census records evidential status, not truth.
2. Many lower bounds attributed to SETH are proved by a reduction from Orthogonal Vectors and cite SETH only because SETH implies the Orthogonal Vectors hypothesis. Neither refutation touches the Orthogonal Vectors hypothesis, so those bounds keep a premise, though one of that premise's two supports (the implication from SETH) is gone.
3. The refutations give algorithms running in time 2^{O(n log log n / sqrt(log n))} for fixed clause width. Hypotheses asserting that 3-SAT needs 2^{n^{1-eps}} time (Weak ETH) or that unbounded-width CNF-SAT needs 2^{(1-eps)n} time are not refuted, so some ETH-based bounds survive in a quantitatively weaker form.

## 2. Hypotheses and their status on the reference date

Status is fixed as of the reference date 2026-10-29 and is recorded with every annotation. "Refuted" means refuted if the claimed algorithms are correct; the census does not adjudicate the proofs. "Formal" means a Lean statement of the refutation exists in the named repository; "paper" means the refutation is asserted in the paper text only.

| Code | Hypothesis | Status on reference date | Basis |
| --- | --- | --- | --- |
| ETH | 3-SAT has no 2^{o(n)} algorithm (s_3 > 0) | refuted | formal: Anthropic MainResults.ethIsFalse; OpenAI exact_count_and_sat gives the algorithm, ETH not named in its Lean |
| rETH | randomized ETH | refuted | formal: Anthropic allZeroRandomized |
| SETH | s_infty = 1 | refuted | formal: Anthropic eth_and_seth_false; complexitylib not_seth |
| rSETH | randomized SETH | refuted | formal: Anthropic allZeroRandomized |
| nuETH, nuSETH | non-uniform variants | refuted | immediate: a uniform deterministic algorithm is a non-uniform algorithm |
| #ETH | counting ETH (Dell et al. 2014) | refuted | formal: Anthropic countingCorollary |
| #SETH | counting SETH | refuted | immediate from the counting algorithm |
| Gap-ETH | no 2^{o(n)} algorithm distinguishes satisfiable 3-CNFs from (1-eps)-satisfiable ones | refuted | paper: OpenAI p. 4; immediate, since an exact 2^{o(n)} algorithm distinguishes; no Lean statement in either repository |
| NSETH | nondeterministic SETH (Carmosino et al. 2016) | refuted | formal: Anthropic nsethFalse (verifier form) |
| OVH | Orthogonal Vectors hypothesis (Williams 2005), including k-OV | not refuted | both papers state this; the k-SAT-to-OV instances are now easy but OVH stands |
| MaxIP, BCP | Max Inner Product, bichromatic closest pair and similar SETH-implied polynomial hypotheses | not refuted | same reasoning as OVH; record the exact hypothesis named |
| kClique | k-Clique hypothesis (n^{omega k/3 - o(1)}) | not refuted | independent conjecture; implies no f(k) n^{o(k)} algorithm |
| SCC | Set Cover Conjecture (Cygan et al. 2016) | not refuted | not implied by SETH |
| CNFSAT | unbounded-width CNF-SAT with poly(n) clauses needs 2^{(1-eps)n} | not refuted | the new algorithms are for fixed width; OpenAI p. 6 names this hypothesis as possibly surviving |
| WeakETH | 3-SAT has no 2^{n^{1-eps}} algorithm for any eps > 0 | not refuted | consistent with 2^{n/sqrt(log n)}; proposed as the salvage hypothesis in the community discussion (Lampis, cstheory 57313, 27 October 2026) |
| pwSETH | pathwidth-SETH family (Lampis, SODA 2025, SODA 2026) | not refuted | per the same discussion; annotators record the exact statement used |
| PIH | Parameterized Inapproximability Hypothesis | not refuted | proved under ETH by Guruswami, Lin, Ren, Sun, Wu (STOC 2024); reverts to an independent hypothesis |
| APSP, 3SUM, HS | all-pairs shortest paths, 3SUM, Hitting Set conjectures | not refuted | unrelated to ETH |
| UGC, PNP, NPpoly | Unique Games, P != NP, NP not in P/poly | not refuted | unrelated to ETH |
| W1 | FPT != W[1] | not refuted | implied by ETH; refuting ETH says nothing about it |
| OTHER | any other named hypothesis | recorded verbatim | annotator writes the statement |

The **refuted family** is {ETH, rETH, SETH, rSETH, nuETH, nuSETH, #ETH, #SETH, Gap-ETH, NSETH}. A result is **in scope** when at least one hypothesis in the refuted family appears among its stated premises.

W[1]-hardness and NP-hardness results are unconditional reductions and are not results in the sense of this codebook. A sentence such as "the problem is W[1]-hard, and admits no f(k) n^{o(k)} algorithm unless ETH fails" contains one in-scope result (the n^{o(k)} bound), not two.

## 3. Fields of an annotation record

One record per result. Required unless marked optional.

| Field | Values | Notes |
| --- | --- | --- |
| paper_id | corpus identifier | from the manifest |
| result_id | paper_id plus running integer | |
| locator | section, theorem number, page | as printed in the version annotated |
| statement | at most 60 words quoted from the paper | the conditional claim, verbatim |
| hypotheses_stated | list of codes from Section 2 | every premise the statement names; OTHER with text |
| route | one code from Section 4 | how the proof uses the premise |
| substitute | one code from Section 2 or NONE | weakest surviving hypothesis from which the same or a weakened bound follows, per Section 5 |
| substitute_evidence | PAPER, CITED, DERIVED, NONE | PAPER: the paper itself proves the result under the substitute; CITED: a cited work does; DERIVED: the annotator re-derives it, with the argument in evidence_note; NONE: no substitute found |
| weakened_form | free text, optional | the bound that follows from the substitute when it is weaker than the stated one |
| status | one code from Section 6 | derived by the rules of Section 6; annotators record it, the pipeline recomputes it from route and substitute and flags disagreements |
| result_type | EXP, PARAM, FINE, APPROX, EQUIV, OTHER | Section 7 |
| tightness | TIGHT, NOT_TIGHT, UNKNOWN | TIGHT when the paper or a cited work gives a matching upper bound up to lower-order terms in the exponent |
| field | one of the topic codes in Section 7 | |
| confidence | 1 to 5 | 5: proof read and route certain; 3: proof sketch read; 1: inferred from the statement alone |
| evidence_note | free text | what was read; the reduction's source problem; the blow-up of the reduction if used for WeakETH |
| annotator | MS, MSi, or model identifier | |
| timestamp | ISO 8601 | |
| minutes | integer | time spent on the record |
| text_basis | LATEX, PDF, ABSTRACT | what text was available |

Model annotations add: model_name, model_tag, model_digest, prompt_hash, temperature, seed, abstain (true or false), rationale (verbatim model output).

## 4. Route: how the proof uses the premise

Choose the single route that the proof of the stated result actually takes. If a result has several proofs, annotate the one the paper presents as primary.

| Code | Route | Typical premise | Default status |
| --- | --- | --- | --- |
| R_SAT | reduction from k-SAT or bounded-width CNF-SAT, possibly after sparsification | ETH, SETH | FALLS unless a substitute is found |
| R_OV | reduction from OV, k-OV, Max-IP, bichromatic closest pair, or another polynomial-time problem whose hardness is itself a named hypothesis implied by SETH | SETH, cited only to justify the intermediate | SURVIVES with substitute OVH (or the named hypothesis) |
| R_INT | reduction from an intermediate NP-hard or parameterized problem whose conditional hardness is cited from prior work (k-Clique n^{o(k)}, Grid Tiling, 3-Coloring, CSP by treewidth, Subgraph Isomorphism, and so on) | ETH through the cited bound | FALLS unless the intermediate has a surviving independent hypothesis (kClique for n^{o(k)} bounds) or the chain re-derives under WeakETH |
| R_GAP | reduction from Gap-3SAT, Label Cover or a PCP-based gap problem | Gap-ETH, or ETH through PIH | FALLS unless the result follows from PIH alone |
| R_COUNT | reduction from #3-SAT or a counting hypothesis | #ETH, #SETH | FALLS |
| R_NONDET | argument using NSETH or a non-uniform variant | NSETH, nuSETH | FALLS |
| R_BLACKBOX | the premise is used as a black box in a non-reduction argument (an algorithm-to-lower-bound connection, a structural collapse, a conditional separation) | any | annotate case by case; status by Section 6 |
| R_EQUIV | the result is an equivalence between the premise and another statement, or a reduction into k-SAT with subexponential blow-up | any | TRANSFER when the refutation yields a new algorithm; otherwise annotate the direction that remains informative |
| R_NONE | the hypothesis is mentioned in motivation, related work or discussion and is not a premise of any stated result | any | MENTION |
| R_UNKNOWN | text insufficient to determine the route | any | UNCLEAR |

When a proof chains several steps (for instance SETH, then OV, then the paper's own gadget), the route is the first step that the paper itself performs or cites as the source of hardness, and the substitute is the weakest named hypothesis at or after that step that is not refuted.

## 5. Finding the substitute

Apply the following in order and stop at the first that applies. Record the step number in evidence_note.

1. The paper proves the same result under a hypothesis outside the refuted family (for example "under SETH or OVH"). Substitute is that hypothesis; substitute_evidence PAPER.
2. The reduction starts from OV, k-OV, Max-IP, BCP or another SETH-implied polynomial-time hypothesis. Substitute is that hypothesis; substitute_evidence CITED (cite the work that states the hypothesis, usually Williams 2005 for OV).
3. The reduction starts from a bound on k-Clique of the form f(k) n^{o(k)} or n^{Omega(k)}. Substitute kClique; substitute_evidence DERIVED, with the observation that the k-Clique hypothesis implies the cited bound.
4. The reduction starts from a gap problem obtained through PIH, or the result is stated for parameterized inapproximability. Substitute PIH; substitute_evidence DERIVED.
5. The result is stated for unbounded-width CNF-SAT, Hitting Set, Set Splitting, NAE-SAT or another problem that Cygan et al. 2016 tie to CNF-SAT of unbounded width, and the proof does not use bounded width. Substitute CNFSAT; substitute_evidence CITED.
6. The proof is a reduction from 3-SAT in which the hardness parameter p of the target instance satisfies p = Theta(n^c polylog(n)) for an explicit c >= 1, and the stated bound is of the form "no 2^{o(p^{1/c})}" or "no 2^{o(p)}" for c = 1. Then WeakETH yields "no 2^{p^{(1-eps)/c}}" for every eps > 0. Substitute WeakETH; substitute_evidence DERIVED; write the weakened form in weakened_form. Do not apply this step to bounds whose form is f(k) n^{o(k)}, 2^{o(k log k)}, n^{o(k)} or any bound in which the exponent depends on a free parameter other than the instance size, because WeakETH does not control those; record NONE instead.
7. Otherwise substitute NONE.

Steps 3 to 6 are annotator derivations and must be checked by the second annotator in the reliability subsample. A derivation that either annotator cannot reproduce is downgraded to NONE at adjudication.

## 6. Status codes

| Code | Definition |
| --- | --- |
| F_NONE | in scope; premise in the refuted family; substitute NONE. The result no longer has evidential support. |
| F_WEAK | in scope; substitute is WeakETH or pwSETH and the surviving bound is strictly weaker than the stated one (weakened_form filled). |
| S_SUBST | in scope; the same bound follows from a surviving substitute (steps 1 to 5 of Section 5). |
| S_UNAFFECTED | not in scope; no premise in the refuted family (for example a result stated only under OVH, SCC or APSP). Recorded so that the corpus coverage of surviving hypotheses is measured. |
| T_TRANSFER | the refutation yields a new upper bound for the paper's problem through an equivalence or a reduction into k-SAT (route R_EQUIV). |
| M_MENTION | route R_NONE. |
| U_UNCLEAR | route R_UNKNOWN, or text_basis ABSTRACT with a conditional claim whose route cannot be read. |

Coarse label for agreement statistics (five classes): FALLS = {F_NONE, F_WEAK}; SURVIVES = {S_SUBST, S_UNAFFECTED}; TRANSFER; MENTION; UNCLEAR. Binary label: EXPOSED = FALLS versus everything else.

## 7. Result type and field

result_type: EXP (exponential-time lower bound for an NP-hard problem, for example no 2^{o(n)} or no 2^{o(sqrt n)}); PARAM (parameterized bound: f(k) n^{o(k)}, 2^{o(k)} n^{O(1)}, 2^{o(k log k)}, treewidth or pathwidth bases); FINE (polynomial-time bound: no n^{2-eps}, no n^{omega-eps}); APPROX (hardness of approximation or parameterized inapproximability); EQUIV (equivalence, collapse, or algorithm-to-lower-bound connection); OTHER.

field: PARAM_COMPLEXITY, FINE_GRAINED, APPROXIMATION, GRAPH_ALGORITHMS, STRINGS, GEOMETRY, DATABASES_CSP, LOGIC_AUTOMATA, COMPUTATIONAL_BIOLOGY, ML_THEORY, CRYPTOGRAPHY, SCHEDULING_OPTIMIZATION, COUNTING, OTHER. Assign by the problem studied, not by the venue.

## 8. Paper-level derivation

From a paper's result records:

- exposed: at least one result with coarse label FALLS.
- shielded: at least one in-scope result and none with coarse label FALLS.
- transfer: at least one T_TRANSFER.
- mention_only: every record is M_MENTION.
- out_of_scope: every record is S_UNAFFECTED or M_MENTION and none is in scope.
- unclear: no in-scope determination possible and at least one U_UNCLEAR.

The Anthropic paper's criterion ("prove at least one result of their own only under ETH or under a hypothesis that implies it ... we did not count results that are also proved under a hypothesis that we do not refute") corresponds to exposed when substitute_evidence PAPER is the only exclusion applied. The census reports both counts: exposed under the full substitute search of Section 5, and exposed under the Anthropic criterion, so the two are comparable.

## 9. Extraction of candidate results

The pipeline extracts, from LaTeX source when available and from PDF text otherwise, every theorem-like environment and every sentence within a window of three sentences of a hypothesis mention. Hypothesis mentions are matched by a fixed pattern list stored in `configs/patterns.yaml` (names, abbreviations, and phrasings such as "unless ETH fails", "assuming SETH", "under the Strong Exponential Time Hypothesis", "Orthogonal Vectors"). Unnamed paraphrases of ETH or SETH ("no subexponential-time algorithm for 3-SAT", "k-SAT cannot be solved in 2^{o(n)} time", "CNF-SAT requires 2^{(1-eps)n} time") are matched under the separate extraction code ETH_PARA, so that their precision is reported apart from the named mentions; the annotator records the hypothesis the paraphrase denotes in hypotheses_stated. Each extracted context is a candidate result. Annotators may merge candidates that refer to the same stated result and may add results the extractor missed; both actions are recorded.

A paper that cites a seed but yields no context is not excluded from the census. Such papers form their own stratum of the gold sample (PREREGISTRATION.md), so that the share of them that use a hypothesis in wording the patterns miss is estimated and reported as the extractor's paper-level miss rate; the rest are out_of_scope by the rules of Section 8.

## 10. Annotation procedure

1. Read the abstract and the introduction's contribution list.
2. For each candidate context, locate the stated result and copy its statement (statement field).
3. Read the proof or proof sketch far enough to identify the source problem of the reduction (route).
4. Apply Section 5 to find the substitute; record the step number and the evidence.
5. Record status by Section 6, result_type and field by Section 7, tightness, confidence and minutes.
6. If the available text is the abstract only, record what the abstract supports and set text_basis ABSTRACT; do not infer a route.

Time guidance: a typical paper takes 15 to 40 minutes. Annotators stop and flag a paper after 60 minutes rather than guess.

## 11. Adjudication

Records in the reliability subsample are annotated independently by MS and MSi, then compared. Disagreements on status, route or substitute are discussed and resolved into an adjudicated record with a note stating the reason for the final value. The adjudicated record is the gold label. Agreement statistics are computed on the pre-adjudication records.

## 12. Known limitations to state in the paper

- Status reflects the state of knowledge on the reference date and the correctness of the claimed algorithms, which are under examination.
- A surviving substitute keeps the result conditional; it does not restore the evidential weight the result had when two independent hypotheses supported it.
- Substitutes found by annotator derivation (steps 3 to 6) are claims of this census, not of the original authors, and are published with their derivations so that others can check them.

## Revision log

- 2026-10-29 v0.1: initial draft.
- 2026-10-29 v0.1 (in place, before the tag): Section 9 names the ETH_PARA paraphrase code (patterns.yaml 0.2) and the zero-context stratum, after the EXP-002 smoke run found one of ten papers using ETH's content without its name and two citing a seed without any hypothesis wording.
