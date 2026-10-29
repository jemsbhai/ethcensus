"""Full-text acquisition for corpus entries (EXP-001, stage 2; PREREGISTRATION.md 3.3).

Order of preference per entry: arXiv e-print (LaTeX source), arXiv PDF, open-access
PDF URL from the snapshot, OpenAlex cached PDF (only when explicitly enabled, it
costs credits), abstract only. Every network call goes through an injectable
``fetch_bytes(url, headers) -> (status, content_type, body)`` so the module is
testable offline. arXiv Terms of Use are respected: one request every three
seconds on arxiv.org, single connection, identifying User-Agent.

Raw downloads are stored under ``data/raw/fulltext/<entry_id>/`` and derived text
under ``data/processed/fulltext/<entry_id>/``; both are git-ignored. The status
file ``data/processed/fulltext_status_<date>.csv`` and the SHA-256 lines appended
to ``data/checksums.sha256`` are committed, so a reproduction can verify that it
obtained the same inputs. Full texts are never redistributed.
"""
from __future__ import annotations

import csv
import gzip
import hashlib
import io
import json
import logging
import re
import tarfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping
from urllib.parse import urlparse

from .collect import Throttle

log = logging.getLogger(__name__)

FetchBytes = Callable[[str, Mapping[str, str]], tuple[int, str, bytes]]

ARXIV_EPRINT = "https://arxiv.org/e-print/{id}"
ARXIV_PDF = "https://arxiv.org/pdf/{id}"
OPENALEX_CONTENT = "https://content.openalex.org/works/{wid}.pdf"
MAX_BYTES = 80 * 1024 * 1024

STATUS_FIELDS = ["entry_id", "text_basis", "source", "url", "raw_path", "processed_path", "sha256", "bytes",
                 "http_status", "note", "timestamp"]


def default_fetch_bytes(url: str, headers: Mapping[str, str]) -> tuple[int, str, bytes]:
    import requests

    with requests.get(url, headers=dict(headers), timeout=120, stream=True, allow_redirects=True) as r:
        chunks, total = [], 0
        for chunk in r.iter_content(1 << 16):
            total += len(chunk)
            if total > MAX_BYTES:
                raise RuntimeError(f"{url}: response larger than {MAX_BYTES} bytes")
            chunks.append(chunk)
        return r.status_code, r.headers.get("Content-Type", ""), b"".join(chunks)


# ---------------------------------------------------------------------------
# Content detection and LaTeX handling
# ---------------------------------------------------------------------------

def sniff(body: bytes) -> str:
    """Return one of gzip, pdf, tar, html, text, unknown from magic bytes."""
    if body[:2] == b"\x1f\x8b":
        return "gzip"
    if body[:5] == b"%PDF-":
        return "pdf"
    if len(body) > 262 and body[257:262] == b"ustar":
        return "tar"
    head = body[:512].lstrip().lower()
    if head.startswith(b"<!doctype html") or head.startswith(b"<html"):
        return "html"
    try:
        body[:2048].decode("utf-8")
        return "text"
    except UnicodeDecodeError:
        return "unknown"


def _safe_member(name: str) -> bool:
    p = Path(name)
    return not p.is_absolute() and ".." not in p.parts and name.strip() != ""


def read_tex_bundle(body: bytes) -> dict[str, str]:
    """Return ``{relative_path: text}`` for the .tex and .bib members of an arXiv e-print.

    Handles gzip-compressed tar bundles, gzip-compressed single files and plain tar.
    Non-text members (figures) are ignored. Returns an empty dict for PDF-only submissions.
    """
    kind = sniff(body)
    if kind == "gzip":
        body = gzip.decompress(body)
        kind = sniff(body)
    if kind == "pdf":
        return {}
    files: dict[str, str] = {}
    if kind == "tar" or tarfile.is_tarfile(io.BytesIO(body)):
        with tarfile.open(fileobj=io.BytesIO(body), mode="r:*") as tar:
            for member in tar.getmembers():
                if not member.isfile() or not _safe_member(member.name):
                    continue
                if not member.name.lower().endswith((".tex", ".bib", ".sty", ".cls", ".bbl")):
                    continue
                extracted = tar.extractfile(member)
                if extracted is None:
                    continue
                files[Path(member.name).as_posix()] = extracted.read().decode("utf-8", errors="replace")
        return files
    if kind == "text":
        return {"main.tex": body.decode("utf-8", errors="replace")}
    return {}


_DOCCLASS = re.compile(r"\\documentclass")
_BEGINDOC = re.compile(r"\\begin\{document\}")
_INPUT = re.compile(r"\\(?:input|include|subfile)\s*\{([^}]+)\}")


def find_main_tex(files: Mapping[str, str]) -> str | None:
    """Pick the entry file: has \\documentclass, prefers \\begin{document}, shallow path, conventional name."""
    candidates = [name for name, text in files.items() if name.lower().endswith(".tex") and _DOCCLASS.search(text)]
    if not candidates:
        return None

    def rank(name: str):
        text = files[name]
        base = Path(name).name.lower()
        return (0 if _BEGINDOC.search(text) else 1, len(Path(name).parts),
                0 if base in ("main.tex", "paper.tex", "ms.tex", "article.tex") else 1, len(name), name)

    return sorted(candidates, key=rank)[0]


def flatten_tex(files: Mapping[str, str], main: str, max_depth: int = 20) -> str:
    """Inline \\input and \\include recursively, relative to the including file and to the root."""
    seen: set[str] = set()

    def resolve(ref: str, from_dir: str) -> str | None:
        ref = ref.strip()
        variants = [ref, ref + ".tex"]
        bases = [from_dir, ""]
        for base in bases:
            for v in variants:
                candidate = (Path(base) / v).as_posix() if base else Path(v).as_posix()
                candidate = candidate.lstrip("./")
                if candidate in files:
                    return candidate
        return None

    def expand(name: str, depth: int) -> str:
        if name in seen or depth > max_depth:
            return ""
        seen.add(name)
        text = files[name]
        from_dir = Path(name).parent.as_posix()
        if from_dir == ".":
            from_dir = ""

        def repl(m: re.Match) -> str:
            target = resolve(m.group(1), from_dir)
            if target is None:
                return m.group(0)
            return "\n" + expand(target, depth + 1) + "\n"

        return _INPUT.sub(repl, text)

    return expand(main, 0)


def pdf_to_text(body: bytes) -> str:
    """Extract page texts with PyMuPDF, separated by form feeds (one per page)."""
    import fitz  # PyMuPDF

    with fitz.open(stream=body, filetype="pdf") as doc:
        return "\f".join(page.get_text("text") for page in doc)


def abstract_from_inverted_index(index: Mapping[str, list[int]] | None) -> str:
    if not index:
        return ""
    positions: list[tuple[int, str]] = []
    for word, poss in index.items():
        for p in poss:
            positions.append((p, word))
    positions.sort()
    return " ".join(w for _, w in positions)


# ---------------------------------------------------------------------------
# Acquisition
# ---------------------------------------------------------------------------

@dataclass
class FetchResult:
    entry_id: str
    text_basis: str          # LATEX, PDF, ABSTRACT, NONE
    source: str              # arxiv_eprint, arxiv_pdf, oa_pdf, openalex_content, abstract, none
    url: str
    raw_path: str
    processed_path: str
    sha256: str
    nbytes: int
    http_status: int | None
    note: str
    timestamp: str

    def row(self) -> list:
        return [self.entry_id, self.text_basis, self.source, self.url, self.raw_path, self.processed_path,
                self.sha256, self.nbytes, self.http_status if self.http_status is not None else "", self.note,
                self.timestamp]


class FullTextFetcher:
    def __init__(self, raw_dir: Path, processed_dir: Path, fetch_bytes: FetchBytes = default_fetch_bytes,
                 contact: str = "", openalex_api_key: str | None = None, use_openalex_content: bool = False,
                 arxiv_interval: float = 3.0, other_interval: float = 1.0,
                 sleep: Callable[[float], None] = time.sleep, now: Callable[[], str] | None = None):
        self.raw_dir = raw_dir
        self.processed_dir = processed_dir
        self.fetch_bytes = fetch_bytes
        self.user_agent = f"ethcensus/0.0.1 (research census; mailto:{contact})" if contact else "ethcensus/0.0.1 (research census)"
        self.openalex_api_key = openalex_api_key
        self.use_openalex_content = use_openalex_content and bool(openalex_api_key)
        self.throttles = {"arxiv.org": Throttle(arxiv_interval, sleep=sleep), "other": Throttle(other_interval, sleep=sleep)}
        self.now = now or (lambda: time.strftime("%Y-%m-%dT%H:%M:%S%z"))

    def _get(self, url: str) -> tuple[int, str, bytes]:
        host = urlparse(url).netloc.lower()
        key = "arxiv.org" if host.endswith("arxiv.org") else "other"
        self.throttles[key].wait()
        try:
            return self.fetch_bytes(url, {"User-Agent": self.user_agent})
        except Exception as exc:  # network errors are data, not crashes
            log.warning("%s: %s", url, exc)
            return 0, "", b""

    def _store(self, entry_id: str, filename: str, body: bytes) -> tuple[Path, str]:
        d = self.raw_dir / entry_id
        d.mkdir(parents=True, exist_ok=True)
        p = d / filename
        p.write_bytes(body)
        return p, hashlib.sha256(body).hexdigest()

    def _store_processed(self, entry_id: str, filename: str, text: str) -> Path:
        d = self.processed_dir / entry_id
        d.mkdir(parents=True, exist_ok=True)
        p = d / filename
        p.write_text(text, encoding="utf-8")
        return p

    def fetch_entry(self, entry: Mapping) -> FetchResult:
        entry_id = entry["entry_id"]
        arxiv_id = entry.get("arxiv_id")
        stamp = self.now()

        if arxiv_id:
            url = ARXIV_EPRINT.format(id=arxiv_id)
            status, _, body = self._get(url)
            if status == 200 and body:
                try:
                    inner = gzip.decompress(body) if sniff(body) == "gzip" else body
                    files = read_tex_bundle(body)
                except (OSError, EOFError, tarfile.TarError) as exc:
                    log.warning("%s: unreadable e-print (%s); falling back to PDF", entry_id, exc)
                    inner, files = b"", {}
                main = find_main_tex(files) if files else None
                if main:
                    raw_path, digest = self._store(entry_id, "arxiv_eprint.bin", body)
                    text = flatten_tex(files, main)
                    proc = self._store_processed(entry_id, "main.tex", text)
                    return FetchResult(entry_id, "LATEX", "arxiv_eprint", url, str(raw_path), str(proc), digest,
                                       len(body), status, f"main={main}; files={len(files)}", stamp)
                if inner and sniff(inner) == "pdf":
                    raw_path, digest = self._store(entry_id, "arxiv.pdf", inner)
                    proc = self._store_processed(entry_id, "text.txt", pdf_to_text(inner))
                    return FetchResult(entry_id, "PDF", "arxiv_eprint", url, str(raw_path), str(proc), digest,
                                       len(inner), status, "pdf-only submission", stamp)
                log.info("%s: e-print without a usable main file; falling back to PDF", entry_id)
            url = ARXIV_PDF.format(id=arxiv_id)
            status, _, body = self._get(url)
            if status == 200 and sniff(body) == "pdf":
                raw_path, digest = self._store(entry_id, "arxiv.pdf", body)
                proc = self._store_processed(entry_id, "text.txt", pdf_to_text(body))
                return FetchResult(entry_id, "PDF", "arxiv_pdf", url, str(raw_path), str(proc), digest,
                                   len(body), status, "", stamp)

        oa_url = entry.get("oa_pdf_url")
        if oa_url and not (arxiv_id and "arxiv.org" in oa_url):
            status, ctype, body = self._get(oa_url)
            if status == 200 and sniff(body) == "pdf":
                raw_path, digest = self._store(entry_id, "oa.pdf", body)
                proc = self._store_processed(entry_id, "text.txt", pdf_to_text(body))
                return FetchResult(entry_id, "PDF", "oa_pdf", oa_url, str(raw_path), str(proc), digest,
                                   len(body), status, "", stamp)
            note_oa = f"oa url returned status={status} type={ctype[:40]} kind={sniff(body) if body else 'empty'}"
        else:
            note_oa = "no oa url"

        if self.use_openalex_content and entry.get("openalex_ids"):
            wid = entry["openalex_ids"][0]
            url = OPENALEX_CONTENT.format(wid=wid) + f"?api_key={self.openalex_api_key}"
            status, _, body = self._get(url)
            if status == 200 and sniff(body) == "pdf":
                raw_path, digest = self._store(entry_id, "openalex.pdf", body)
                proc = self._store_processed(entry_id, "text.txt", pdf_to_text(body))
                return FetchResult(entry_id, "PDF", "openalex_content", OPENALEX_CONTENT.format(wid=wid),
                                   str(raw_path), str(proc), digest, len(body), status, "", stamp)

        abstract = ""
        for rec in entry.get("openalex_records") or []:
            abstract = abstract_from_inverted_index(rec.get("abstract_inverted_index"))
            if abstract:
                break
        if abstract:
            proc = self._store_processed(entry_id, "abstract.txt", abstract)
            return FetchResult(entry_id, "ABSTRACT", "abstract", "", "", str(proc),
                               hashlib.sha256(abstract.encode("utf-8")).hexdigest(), len(abstract), None, note_oa, stamp)
        return FetchResult(entry_id, "NONE", "none", "", "", "", "", 0, None, note_oa, stamp)


# ---------------------------------------------------------------------------
# Status file (resumable)
# ---------------------------------------------------------------------------

def load_done(status_path: Path) -> set[str]:
    if not status_path.exists():
        return set()
    with open(status_path, encoding="utf-8", newline="") as f:
        return {row["entry_id"] for row in csv.DictReader(f)}


def append_status(status_path: Path, result: FetchResult) -> None:
    new = not status_path.exists()
    status_path.parent.mkdir(parents=True, exist_ok=True)
    with open(status_path, "a", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(STATUS_FIELDS)
        w.writerow(result.row())


def read_snapshot(jsonl_path: Path):
    with open(jsonl_path, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                yield json.loads(line)


def summarize_status(status_path: Path) -> dict:
    counts: dict[str, int] = {}
    sources: dict[str, int] = {}
    with open(status_path, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            counts[row["text_basis"]] = counts.get(row["text_basis"], 0) + 1
            sources[row["source"]] = sources.get(row["source"], 0) + 1
    return {"by_text_basis": dict(sorted(counts.items())), "by_source": dict(sorted(sources.items())),
            "total": sum(counts.values())}
