"""Hypothesis-context extraction (EXP-002; CODEBOOK.md Section 9).

From a paper's text the extractor produces candidate contexts of two kinds:

* ``theorem``: a theorem-like LaTeX environment (or, in PDF text, a heading such
  as "Theorem 3.1.") whose statement mentions a hypothesis;
* ``sentence``: a window of sentences around a hypothesis mention that lies
  outside such environments.

Patterns, exclusions and premise phrases come from ``configs/patterns.yaml``.
Every context records the matched hypothesis codes, whether a premise phrase
matched, the nearest preceding section title, the raw slice and a lightly
de-TeXed version of it.
"""
from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable, Mapping, Sequence

import yaml

CANONICAL_KINDS = ("theorem", "lemma", "corollary", "proposition", "claim", "observation", "conjecture", "hypothesis")
ABBREVIATIONS = {"thm": "theorem", "theo": "theorem", "lem": "lemma", "lemma": "lemma", "cor": "corollary",
                 "corr": "corollary", "prop": "proposition", "prp": "proposition", "clm": "claim", "claim": "claim",
                 "obs": "observation", "conj": "conjecture", "hyp": "hypothesis"}


# ---------------------------------------------------------------------------
# Patterns
# ---------------------------------------------------------------------------

@dataclass
class Patterns:
    version: str
    window: int
    kinds: tuple[str, ...]
    hypothesis: dict[str, list[re.Pattern]]
    exclusions: list[re.Pattern]
    premise: list[re.Pattern]

    @classmethod
    def load(cls, path: Path | str) -> "Patterns":
        cfg = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
        return cls.from_config(cfg)

    @classmethod
    def from_config(cls, cfg: Mapping) -> "Patterns":
        return cls(
            version=str(cfg.get("version", "")),
            window=int(cfg.get("window_sentences", 3)),
            kinds=tuple(cfg.get("theorem_environments", CANONICAL_KINDS)),
            hypothesis={code: [re.compile(p) for p in pats] for code, pats in cfg["patterns"].items()},
            exclusions=[re.compile(p) for p in cfg.get("exclusions", [])],
            premise=[re.compile(p) for p in cfg.get("premise_phrases", [])],
        )

    def mask(self, text: str) -> str:
        for ex in self.exclusions:
            text = ex.sub(" ", text)
        return text

    def match(self, text: str) -> tuple[list[str], bool]:
        masked = self.mask(text)
        codes = [code for code, pats in self.hypothesis.items() if any(p.search(masked) for p in pats)]
        premise = any(p.search(masked) for p in self.premise)
        return codes, premise


# ---------------------------------------------------------------------------
# LaTeX helpers
# ---------------------------------------------------------------------------

_COMMENT = re.compile(r"(?<!\\)%[^\n]*")
_NEWTHEOREM = re.compile(r"\\newtheorem\*?\s*\{(\w+)\}\s*(?:\[[^\]]*\])?\s*\{([^}]*)\}")
_DECLARETHEOREM = re.compile(r"\\declaretheorem\s*(?:\[([^\]]*)\])?\s*\{(\w+)\}")
_SECTION = re.compile(r"\\(?:section|subsection|subsubsection|chapter|part)\*?\s*\{((?:[^{}]|\{[^{}]*\})*)\}")
_LABEL = re.compile(r"\\label\s*\{([^}]*)\}")
_SENT_END = re.compile(r"(?<=[.!?])\s+(?=[A-Z\\$(\[\"'])|\n[ \t]*\n")
_ABBREV = ("e.g.", "i.e.", "et al.", "vs.", "cf.", "w.r.t.", "resp.", "Fig.", "Thm.", "Lem.", "Cor.", "Prop.",
           "Sec.", "Eq.", "Def.", "no.", "approx.", "Ref.", "Refs.", "Ch.", "pp.")
_PDF_HEADING = re.compile(r"^(Theorem|Lemma|Corollary|Proposition|Claim|Observation|Conjecture|Hypothesis)"
                          r"\s*([0-9A-Z]+(?:\.[0-9]+)*)?\s*[.:]?\s*(\([^)]*\))?\s*", re.MULTILINE)


def strip_comments(tex: str) -> str:
    """Blank out LaTeX comments while preserving character offsets."""
    return _COMMENT.sub(lambda m: " " * len(m.group(0)), tex)


def theorem_environments(tex: str, kinds: Sequence[str] = CANONICAL_KINDS) -> dict[str, str]:
    """Map every theorem-like environment name used in ``tex`` to its canonical kind."""
    canon = {k.lower() for k in kinds}
    env_map: dict[str, str] = {k: k for k in canon}

    def kind_from_display(display: str) -> str | None:
        for word in display.lower().replace("-", " ").split():
            if word in canon:
                return word
            if word.endswith("s") and word[:-1] in canon:
                return word[:-1]
        return None

    for m in _NEWTHEOREM.finditer(tex):
        name, display = m.group(1), m.group(2)
        kind = kind_from_display(display) or ABBREVIATIONS.get(name.lower().rstrip("*"))
        if kind in canon:
            env_map[name] = kind
    for m in _DECLARETHEOREM.finditer(tex):
        opts, name = m.group(1) or "", m.group(2)
        nm = re.search(r"name\s*=\s*\{?([A-Za-z \-]+)", opts)
        kind = (kind_from_display(nm.group(1)) if nm else None) or ABBREVIATIONS.get(name.lower())
        if kind in canon:
            env_map[name] = kind
    for name, kind in ABBREVIATIONS.items():
        if kind in canon and re.search(r"\\begin\{" + re.escape(name) + r"\*?\}", tex):
            env_map.setdefault(name, kind)
    return env_map


_INLINE_CMDS = ("textbf", "textit", "emph", "text", "textsc", "textrm", "textsf", "texttt", "underline", "mathrm",
                "mathbf", "mathit", "mathsf", "mathcal", "operatorname", "mbox", "hbox")


def detex(s: str) -> str:
    """Lightly convert LaTeX to readable text; keeps math content, drops citations and labels."""
    s = re.sub(r"\\(?:cite[tp]?|citep|citet|citeauthor|citeyear|nocite)\*?(?:\[[^\]]*\])*\s*\{[^}]*\}", "[cite]", s)
    s = re.sub(r"\\(?:[cC]ref|ref|eqref|autoref|pageref|vref)\*?\s*\{[^}]*\}", "[ref]", s)
    s = re.sub(r"\\label\s*\{[^}]*\}", "", s)
    s = re.sub(r"\\(?:footnote|thanks)\s*\{((?:[^{}]|\{[^{}]*\})*)\}", r" (footnote: \1)", s)
    s = re.sub(r"\\href\s*\{[^}]*\}\s*\{((?:[^{}]|\{[^{}]*\})*)\}", r"\1", s)
    s = re.sub(r"\\url\s*\{([^}]*)\}", r"\1", s)
    for _ in range(3):
        s = re.sub(r"\\(?:" + "|".join(_INLINE_CMDS) + r")\s*\{((?:[^{}]|\{[^{}]*\})*)\}", r"\1", s)
    s = re.sub(r"\\(?:(?:sub)*section|(?:sub)?paragraph|title|author|institute|affil|affiliation)\*?\s*(?:\[[^\]]*\])?"
               r"\{((?:[^{}]|\{[^{}]*\})*)\}", r"\n\1\n", s)
    s = re.sub(r"\\(?:maketitle|date\s*\{[^}]*\}|and\b)", " ", s)
    s = re.sub(r"\\begin\{[a-zA-Z*]+\}(?:\[(?:[^\[\]]|\[[^\]]*\])*\])?|\\end\{[a-zA-Z*]+\}", " ", s)
    s = re.sub(r"\\(?:item|par|noindent|centering|smallskip|medskip|bigskip|newline|linebreak|hfill|vspace\*?\{[^}]*\}|hspace\*?\{[^}]*\})", " ", s)
    s = s.replace("\\\\", " ").replace("~", " ").replace("``", '"').replace("''", '"')
    s = re.sub(r"\\([#$%&_{}])", r"\1", s)                       # escaped characters
    s = s.replace("\\ ", " ")                                   # escaped space after a macro
    s = re.sub(r"(?<=\w)\\([A-Za-z]+)\*?(?:\{\})?", r" \1", s)  # macro glued to a word: x\in Q becomes x in Q
    s = re.sub(r"\\([A-Za-z]+)\*?(?:\{\})?", r"\1", s)          # remaining macros become their own name
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()


def _protect_abbreviations(text: str) -> str:
    """Replace the dots of known abbreviations by a placeholder of the same length."""
    out = text
    for ab in _ABBREV:
        out = out.replace(ab, ab.replace(".", "\u0001"))
    return out


def split_sentences(text: str) -> list[tuple[int, int]]:
    """Return (start, end) offsets of sentences in ``text`` (offsets refer to the original string)."""
    protected = _protect_abbreviations(text)
    spans: list[tuple[int, int]] = []
    start = 0
    for m in _SENT_END.finditer(protected):
        end = m.start()
        if text[start:end].strip():
            spans.append((start, end))
        start = m.end()
    if text[start:].strip():
        spans.append((start, len(text)))
    return spans


# ---------------------------------------------------------------------------
# Contexts
# ---------------------------------------------------------------------------

@dataclass
class Context:
    entry_id: str
    context_id: str
    text_basis: str
    kind: str                 # theorem or sentence
    env_kind: str             # theorem, lemma, ... or "" for sentence windows
    env_name: str
    ordinal: int              # running number of that env kind in the document, 0 for sentence windows
    label: str
    title: str
    section: str
    hypotheses: list[str]
    premise_phrase: bool
    char_start: int
    char_end: int
    text: str
    raw: str

    @staticmethod
    def make(entry_id: str, n: int, **kw) -> "Context":
        return Context(entry_id=entry_id, context_id=f"{entry_id}-C{n:03d}", **kw)


def _section_at(sections: Sequence[tuple[int, str]], pos: int) -> str:
    current = ""
    for p, title in sections:
        if p <= pos:
            current = title
        else:
            break
    return current


def _merge_windows(windows: list[tuple[int, int]]) -> list[tuple[int, int]]:
    merged: list[tuple[int, int]] = []
    for a, b in sorted(windows):
        if merged and a <= merged[-1][1] + 1:
            merged[-1] = (merged[-1][0], max(merged[-1][1], b))
        else:
            merged.append((a, b))
    return merged


def extract_latex(entry_id: str, tex_raw: str, patterns: Patterns, max_chars: int = 4000) -> list[Context]:
    tex = strip_comments(tex_raw)
    env_map = theorem_environments(tex, patterns.kinds)
    sections = [(m.start(), detex(m.group(1))) for m in _SECTION.finditer(tex)]
    contexts: list[Context] = []
    env_spans: list[tuple[int, int]] = []
    ordinals: dict[str, int] = {}

    env_names = sorted(env_map, key=len, reverse=True)
    env_re = re.compile(r"\\begin\{(" + "|".join(re.escape(n) for n in env_names) + r")(\*?)\}(?:\[((?:[^\[\]]|\[[^\]]*\])*)\])?")
    for m in env_re.finditer(tex):
        name, star = m.group(1), m.group(2)
        end_m = re.compile(r"\\end\{" + re.escape(name) + re.escape(star) + r"\}").search(tex, m.end())
        if not end_m:
            continue
        body = tex[m.end():end_m.start()]
        kind = env_map[name]
        ordinals[kind] = ordinals.get(kind, 0) + 1
        env_spans.append((m.start(), end_m.end()))
        title = detex(m.group(3) or "")
        plain = detex(body)
        codes, premise = patterns.match(plain + " " + title)
        if not codes:
            continue
        label_m = _LABEL.search(body)
        raw = tex_raw[m.start():end_m.end()]
        contexts.append(Context.make(
            entry_id, 0, text_basis="LATEX", kind="theorem", env_kind=kind, env_name=name + star,
            ordinal=ordinals[kind], label=label_m.group(1) if label_m else "", title=title,
            section=_section_at(sections, m.start()), hypotheses=codes, premise_phrase=premise,
            char_start=m.start(), char_end=end_m.end(), text=plain[:max_chars], raw=raw[:max_chars]))

    def inside_env(a: int, b: int) -> bool:
        """True when the sentence overlaps a theorem-like environment at all."""
        return any(a < e and s < b for s, e in env_spans)

    # Windows are built over sentences of the document body that lie outside
    # theorem-like environments: the preamble is blanked (offsets preserved) so
    # declarations never produce hits, and an environment never leaks into a
    # neighbouring window because it has its own context.
    doc_start = tex.find("\\begin{document}")
    body_tex = (" " * doc_start + tex[doc_start:]) if doc_start > 0 else tex
    sentences = [(max(a, doc_start), b) for (a, b) in split_sentences(body_tex) if not inside_env(a, b)]
    hits = [i for i, (a, b) in enumerate(sentences) if patterns.match(detex(tex[a:b]))[0]]
    windows = _merge_windows([(max(0, i - patterns.window), min(len(sentences) - 1, i + patterns.window)) for i in hits])
    for lo, hi in windows:
        a, b = sentences[lo][0], sentences[hi][1]
        first_hit = next(i for i in hits if lo <= i <= hi)
        plain = detex(tex[a:b])
        codes, premise = patterns.match(plain)
        contexts.append(Context.make(
            entry_id, 0, text_basis="LATEX", kind="sentence", env_kind="", env_name="", ordinal=0, label="",
            title="", section=_section_at(sections, sentences[first_hit][0]), hypotheses=codes, premise_phrase=premise,
            char_start=a, char_end=b, text=plain[:max_chars], raw=tex_raw[a:b][:max_chars]))

    contexts.sort(key=lambda c: c.char_start)
    for n, c in enumerate(contexts, start=1):
        c.context_id = f"{entry_id}-C{n:03d}"
    return contexts


def extract_plain(entry_id: str, text: str, patterns: Patterns, text_basis: str = "PDF",
                  max_chars: int = 4000, heading_body_chars: int = 1500) -> list[Context]:
    """Extraction for PDF text or abstracts: heading-based theorem blocks plus sentence windows."""
    contexts: list[Context] = []
    blocks: list[tuple[int, int]] = []
    ordinals: dict[str, int] = {}
    if text_basis == "PDF":
        for m in _PDF_HEADING.finditer(text):
            kind = m.group(1).lower()
            ordinals[kind] = ordinals.get(kind, 0) + 1
            rest = text[m.end():m.end() + heading_body_chars]
            cut = re.search(r"\n\s*\n|\n\s*Proof[.:\s]|\f|\n\s*(?:Theorem|Lemma|Corollary|Proposition|Claim|Observation|"
                            r"Conjecture|Hypothesis|Definition|Remark|Example)\b|\n\s*[0-9]+(?:\.[0-9]+)*\s+[A-Z][a-z]", rest)
            end = m.end() + (cut.start() if cut else len(rest))
            body = text[m.start():end]
            codes, premise = patterns.match(body)
            blocks.append((m.start(), end))
            if not codes:
                continue
            contexts.append(Context.make(
                entry_id, 0, text_basis=text_basis, kind="theorem", env_kind=kind, env_name=kind,
                ordinal=ordinals[kind], label=m.group(2) or "", title=(m.group(3) or "").strip("()"),
                section="", hypotheses=codes, premise_phrase=premise, char_start=m.start(), char_end=end,
                text=body[:max_chars], raw=body[:max_chars]))

    def inside_block(a: int, b: int) -> bool:
        return any(a < e and s < b for s, e in blocks)

    sentences = [(a, b) for (a, b) in split_sentences(text) if not inside_block(a, b)]
    hits = [i for i, (a, b) in enumerate(sentences) if patterns.match(text[a:b])[0]]
    windows = _merge_windows([(max(0, i - patterns.window), min(len(sentences) - 1, i + patterns.window)) for i in hits])
    for lo, hi in windows:
        a, b = sentences[lo][0], sentences[hi][1]
        chunk = text[a:b]
        codes, premise = patterns.match(chunk)
        contexts.append(Context.make(
            entry_id, 0, text_basis=text_basis, kind="sentence", env_kind="", env_name="", ordinal=0, label="",
            title="", section="", hypotheses=codes, premise_phrase=premise, char_start=a, char_end=b,
            text=chunk[:max_chars], raw=chunk[:max_chars]))
    contexts.sort(key=lambda c: c.char_start)
    for n, c in enumerate(contexts, start=1):
        c.context_id = f"{entry_id}-C{n:03d}"
    return contexts


def extract_entry(entry_id: str, text_basis: str, processed_path: Path, patterns: Patterns) -> list[Context]:
    text = Path(processed_path).read_text(encoding="utf-8", errors="replace")
    if text_basis == "LATEX":
        return extract_latex(entry_id, text, patterns)
    if text_basis in ("PDF", "ABSTRACT"):
        return extract_plain(entry_id, text, patterns, text_basis=text_basis)
    return []


def summarize(contexts: Iterable[Context]) -> dict:
    by_entry: dict[str, dict] = {}
    for c in contexts:
        s = by_entry.setdefault(c.entry_id, {"n_contexts": 0, "n_theorem": 0, "hypotheses": set(), "premise": False})
        s["n_contexts"] += 1
        s["n_theorem"] += int(c.kind == "theorem")
        s["hypotheses"].update(c.hypotheses)
        s["premise"] = s["premise"] or c.premise_phrase
    for s in by_entry.values():
        s["hypotheses"] = sorted(s["hypotheses"])
    return by_entry


def write_contexts(contexts: Iterable[Context], path: Path) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with open(path, "a", encoding="utf-8") as f:
        for c in contexts:
            f.write(json.dumps(asdict(c), ensure_ascii=False) + "\n")
            n += 1
    return n
