"""Corpus collection from the OpenAlex and Semantic Scholar citation graphs.

All network access goes through a ``fetch_json`` callable with the signature
``fetch_json(url, params, headers) -> (status_code, body, response_headers)``
so that every function in this module is testable without a network. The
only place ``requests`` is used is :func:`default_fetch_json`.

Pipeline: ``OpenAlexClient.iter_citers`` and ``SemanticScholarClient.iter_citations``
yield raw records; :func:`candidate_from_openalex` and :func:`candidate_from_s2`
turn them into :class:`Candidate` objects; :func:`merge_candidates` unions them
into :class:`CorpusEntry` objects; :func:`write_snapshot` writes the dated,
hashed snapshot that later experiments read.
"""
from __future__ import annotations

import csv
import hashlib
import json
import logging
import platform
import re
import subprocess
import sys
import time
import unicodedata
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterable, Iterator, Mapping, Sequence

log = logging.getLogger(__name__)

OPENALEX_BASE = "https://api.openalex.org"
S2_BASE = "https://api.semanticscholar.org/graph/v1"

OPENALEX_SELECT = [
    "id", "doi", "ids", "title", "display_name", "publication_year", "publication_date",
    "type", "language", "authorships", "primary_location", "best_oa_location",
    "open_access", "referenced_works", "referenced_works_count", "cited_by_count",
    "topics", "primary_topic", "abstract_inverted_index", "has_fulltext", "indexed_in",
    "updated_date",
]

# Citation-level fields first, then fields of the citing paper. The abstract is
# deliberately not requested (see data/DATA_README.md).
S2_FIELDS = [
    "contexts", "intents", "isInfluential",
    "paperId", "corpusId", "externalIds", "url", "title", "venue", "publicationVenue",
    "year", "referenceCount", "citationCount", "influentialCitationCount",
    "isOpenAccess", "openAccessPdf", "fieldsOfStudy", "s2FieldsOfStudy",
    "publicationTypes", "publicationDate", "journal", "authors",
]

FetchJson = Callable[[str, Mapping[str, str], Mapping[str, str]], tuple[int, object, Mapping[str, str]]]


class CollectError(RuntimeError):
    """Base class for collection failures."""


class AuthError(CollectError):
    """The service rejected the credentials (HTTP 401 or 403 without a key)."""


class BudgetError(CollectError):
    """The service reported an exhausted budget (OpenAlex credits)."""


def default_fetch_json(url: str, params: Mapping[str, str], headers: Mapping[str, str]):
    """Perform one GET with ``requests`` and return ``(status, body, headers)``."""
    import requests  # imported here so the module imports without network libraries in tests

    response = requests.get(url, params=dict(params), headers=dict(headers), timeout=60)
    try:
        body = response.json()
    except ValueError:
        body = {"text": response.text}
    return response.status_code, body, dict(response.headers)


class Throttle:
    """Enforce a minimum interval between calls. ``sleep`` is injectable for tests."""

    def __init__(self, min_interval: float, sleep: Callable[[float], None] = time.sleep,
                 clock: Callable[[], float] = time.monotonic):
        self.min_interval = min_interval
        self._sleep = sleep
        self._clock = clock
        self._last: float | None = None

    def wait(self) -> None:
        now = self._clock()
        if self._last is not None:
            remaining = self.min_interval - (now - self._last)
            if remaining > 0:
                self._sleep(remaining)
        self._last = self._clock()


def get_with_retry(fetch_json: FetchJson, url: str, params: Mapping[str, str], headers: Mapping[str, str],
                   throttle: Throttle, max_retries: int = 8, sleep: Callable[[float], None] = time.sleep,
                   base_backoff: float = 2.0, max_backoff: float = 60.0):
    """GET with throttling and retries on 429 and 5xx. Raises on 401, 403 and persistent failure."""
    attempt = 0
    while True:
        throttle.wait()
        status, body, resp_headers = fetch_json(url, params, headers)
        if status == 200:
            return body, resp_headers
        if status == 401:
            raise AuthError(f"401 from {url}: an API key is required for this request")
        if status == 403:
            text = json.dumps(body) if not isinstance(body, str) else body
            if "budget" in text.lower() or "credit" in text.lower():
                raise BudgetError(f"403 from {url}: {text[:300]}")
            raise AuthError(f"403 from {url}: {text[:300]}")
        if status == 429 or 500 <= status < 600:
            attempt += 1
            if attempt > max_retries:
                raise CollectError(f"{status} from {url} after {max_retries} retries")
            retry_after = resp_headers.get("Retry-After") or resp_headers.get("retry-after")
            try:
                wait = float(retry_after) if retry_after else min(max_backoff, base_backoff * (2 ** (attempt - 1)))
            except ValueError:
                wait = min(max_backoff, base_backoff * (2 ** (attempt - 1)))
            log.warning("%s from %s; retry %d/%d after %.1fs", status, url, attempt, max_retries, wait)
            sleep(wait)
            continue
        raise CollectError(f"unexpected status {status} from {url}: {str(body)[:300]}")


class OpenAlexClient:
    """Minimal OpenAlex client for the ``cites`` filter with cursor pagination.

    Budget facts (help.openalex.org, 2026-10-29): without a key, requests share a
    $0.10 per day budget per IP and cursor paging past the first page returns 401;
    a free key gives $1 per day, at $0.0001 per list call.
    """

    def __init__(self, api_key: str | None, fetch_json: FetchJson = default_fetch_json,
                 base_url: str = OPENALEX_BASE, per_page: int = 100, min_interval: float = 0.05,
                 sleep: Callable[[float], None] = time.sleep):
        self.api_key = api_key
        self.fetch_json = fetch_json
        self.base_url = base_url.rstrip("/")
        self.per_page = per_page
        self.throttle = Throttle(min_interval, sleep=sleep)
        self.sleep = sleep
        self.last_headers: Mapping[str, str] = {}

    def _params(self, **extra: str) -> dict[str, str]:
        params = dict(extra)
        if self.api_key:
            params["api_key"] = self.api_key
        return params

    @staticmethod
    def cites_filter(seed_ids: Sequence[str], extra_filters: str | None = None) -> str:
        if not seed_ids:
            raise ValueError("at least one seed id is required")
        if len(seed_ids) > 100:
            raise ValueError("OpenAlex accepts at most 100 OR values in one filter")
        filt = "cites:" + "|".join(seed_ids)
        if extra_filters:
            filt = filt + "," + extra_filters
        return filt

    def count_citers(self, seed_ids: Sequence[str], extra_filters: str | None = None) -> int:
        body, headers = get_with_retry(
            self.fetch_json, f"{self.base_url}/works",
            self._params(filter=self.cites_filter(seed_ids, extra_filters), per_page="1"),
            {}, self.throttle, sleep=self.sleep)
        self.last_headers = headers
        return int(body["meta"]["count"])

    def iter_citers(self, seed_ids: Sequence[str], select: Sequence[str] = OPENALEX_SELECT,
                    extra_filters: str | None = None, max_pages: int | None = None) -> Iterator[dict]:
        """Yield every work citing any of ``seed_ids``, following ``meta.next_cursor`` to exhaustion."""
        cursor = "*"
        pages = 0
        while cursor:
            if max_pages is not None and pages >= max_pages:
                return
            body, headers = get_with_retry(
                self.fetch_json, f"{self.base_url}/works",
                self._params(filter=self.cites_filter(seed_ids, extra_filters), per_page=str(self.per_page),
                             cursor=cursor, select=",".join(select)),
                {}, self.throttle, sleep=self.sleep)
            self.last_headers = headers
            pages += 1
            results = body.get("results", [])
            for rec in results:
                yield rec
            cursor = body.get("meta", {}).get("next_cursor")
            if not results:
                return


class SemanticScholarClient:
    """Minimal Semantic Scholar Graph API client for ``/paper/{id}/citations``.

    With a key the introductory limit is 1 request per second; the citations
    endpoint returns ``{"offset", "next", "data": [...]}`` and omits ``next``
    when exhausted (API spec, 2026-10-29).
    """

    def __init__(self, api_key: str | None, fetch_json: FetchJson = default_fetch_json,
                 base_url: str = S2_BASE, limit: int = 1000, min_interval: float = 1.0,
                 sleep: Callable[[float], None] = time.sleep):
        self.api_key = api_key
        self.fetch_json = fetch_json
        self.base_url = base_url.rstrip("/")
        self.limit = limit
        self.throttle = Throttle(min_interval, sleep=sleep)
        self.sleep = sleep

    def _headers(self) -> dict[str, str]:
        return {"x-api-key": self.api_key} if self.api_key else {}

    def iter_citations(self, paper_id: str, fields: Sequence[str] = S2_FIELDS,
                       max_pages: int | None = None) -> Iterator[dict]:
        offset = 0
        pages = 0
        while True:
            if max_pages is not None and pages >= max_pages:
                return
            body, _ = get_with_retry(
                self.fetch_json, f"{self.base_url}/paper/{paper_id}/citations",
                {"fields": ",".join(fields), "offset": str(offset), "limit": str(self.limit)},
                self._headers(), self.throttle, sleep=self.sleep)
            pages += 1
            data = body.get("data", [])
            for item in data:
                yield item
            if "next" not in body or body.get("next") is None or not data:
                return
            offset = int(body["next"])


# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------

_DOI_PREFIX = re.compile(r"^(https?://(dx\.)?doi\.org/|doi:)\s*", re.IGNORECASE)
_ARXIV_URL = re.compile(r"arxiv\.org/(?:abs|pdf|e-print)/([0-9]{4}\.[0-9]{4,5}|[a-z\-]+(?:\.[A-Z]{2})?/[0-9]{7})(v[0-9]+)?", re.IGNORECASE)
_ARXIV_ID = re.compile(r"^(?:arxiv:)?\s*([0-9]{4}\.[0-9]{4,5}|[a-z\-]+(?:\.[A-Z]{2})?/[0-9]{7})(?:v[0-9]+)?$", re.IGNORECASE)


def normalize_doi(doi: str | None) -> str | None:
    if not doi:
        return None
    doi = _DOI_PREFIX.sub("", doi.strip())
    doi = doi.strip().lower()
    return doi or None


def normalize_arxiv(value: str | None) -> str | None:
    """Accept bare ids, ``arXiv:`` prefixes, and arxiv.org URLs; drop version suffixes."""
    if not value:
        return None
    m = _ARXIV_ID.match(value.strip())
    if m:
        return m.group(1).lower()
    m = _ARXIV_URL.search(value)
    if m:
        return m.group(1).lower()
    return None


def title_key(title: str | None) -> str:
    if not title:
        return ""
    text = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode("ascii").lower()
    text = re.sub(r"[^a-z0-9 ]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def surname_key(name: str | None) -> str:
    if not name:
        return ""
    text = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii").lower()
    text = re.sub(r"[^a-z ]+", " ", text).strip()
    if "," in name:
        text = re.sub(r"[^a-z ]+", " ", name.split(",")[0].lower()).strip()
    parts = text.split()
    # OpenAlex sometimes appends a stray initial ("Maxime Crochemore A"); a single letter is never the surname
    # when a longer token exists.
    long_parts = [p for p in parts if len(p) >= 2]
    parts = long_parts or parts
    return parts[-1] if parts else ""


def openalex_short_id(value: str | None) -> str | None:
    if not value:
        return None
    return value.rsplit("/", 1)[-1]


# Titles that are repository or volume boilerplate rather than the name of a paper. Records that
# carry one are never united by the title rule (found in the EXP-001 smoke: ten Semantic Scholar
# records titled "UvA-DARE (Digital Academic Repository)" belonging to different papers).
_GENERIC_TITLE = re.compile(r"\b(repository|front matter|table of contents|proceedings|editorial|preface|index|"
                            r"corrigendum|erratum|untitled)\b")
MIN_TITLE_WORDS = 3


# ---------------------------------------------------------------------------
# Candidates and corpus entries
# ---------------------------------------------------------------------------

@dataclass
class Candidate:
    source: str                      # "openalex" or "s2"
    source_id: str
    seed_code: str
    doi: str | None = None
    arxiv_id: str | None = None
    title: str = ""
    year: int | None = None
    first_author: str = ""
    venue: str = ""
    doc_type: str = ""
    oa_pdf_url: str | None = None
    cited_by_count: int | None = None
    contexts: list[dict] = field(default_factory=list)
    raw: dict = field(default_factory=dict)


def candidate_from_openalex(rec: dict, seed_code: str) -> Candidate:
    arxiv = None
    for loc in [rec.get("primary_location"), rec.get("best_oa_location")] + list(rec.get("locations") or []):
        if not loc:
            continue
        for key in ("landing_page_url", "pdf_url"):
            arxiv = arxiv or normalize_arxiv(loc.get(key))
    authorships = rec.get("authorships") or []
    first_author = ""
    if authorships:
        first_author = (authorships[0].get("author") or {}).get("display_name") or authorships[0].get("raw_author_name") or ""
    primary = rec.get("primary_location") or {}
    venue = ((primary.get("source") or {}).get("display_name")) or ""
    best = rec.get("best_oa_location") or {}
    return Candidate(
        source="openalex",
        source_id=openalex_short_id(rec.get("id")) or "",
        seed_code=seed_code,
        doi=normalize_doi(rec.get("doi")),
        arxiv_id=arxiv,
        title=rec.get("title") or rec.get("display_name") or "",
        year=rec.get("publication_year"),
        first_author=first_author,
        venue=venue,
        doc_type=rec.get("type") or "",
        oa_pdf_url=best.get("pdf_url") or (rec.get("open_access") or {}).get("oa_url"),
        cited_by_count=rec.get("cited_by_count"),
        raw=rec,
    )


def candidate_from_s2(item: dict, seed_code: str) -> Candidate:
    paper = item.get("citingPaper") or {}
    ext = paper.get("externalIds") or {}
    authors = paper.get("authors") or []
    oa = paper.get("openAccessPdf") or {}
    contexts = [{"seed": seed_code, "context": c, "intents": item.get("intents") or [],
                 "influential": bool(item.get("isInfluential"))} for c in (item.get("contexts") or [])]
    kept = {k: v for k, v in paper.items() if k != "abstract"}
    return Candidate(
        source="s2",
        source_id=paper.get("paperId") or "",
        seed_code=seed_code,
        doi=normalize_doi(ext.get("DOI")),
        arxiv_id=normalize_arxiv(ext.get("ArXiv")),
        title=paper.get("title") or "",
        year=paper.get("year"),
        first_author=(authors[0].get("name") if authors else "") or "",
        venue=paper.get("venue") or "",
        doc_type=",".join(paper.get("publicationTypes") or []),
        oa_pdf_url=oa.get("url"),
        cited_by_count=paper.get("citationCount"),
        contexts=contexts,
        raw=kept,
    )


@dataclass
class CorpusEntry:
    entry_id: str
    doi: str | None
    arxiv_id: str | None
    openalex_ids: list[str]
    s2_paper_ids: list[str]
    title: str
    year: int | None
    first_author: str
    venue: str
    doc_type: str
    seeds_cited: list[str]
    oa_pdf_url: str | None
    cited_by_count: int | None
    sources: list[str]
    contexts: list[dict]
    merge_keys: list[str]
    openalex_records: list[dict]
    s2_records: list[dict]
    is_seed: bool = False


class _UnionFind:
    def __init__(self, n: int):
        self.parent = list(range(n))

    def find(self, i: int) -> int:
        while self.parent[i] != i:
            self.parent[i] = self.parent[self.parent[i]]
            i = self.parent[i]
        return i

    def union(self, a: int, b: int) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[rb] = ra


YEAR_TOLERANCE = 10


def merge_candidates(cands: Sequence[Candidate], year_tolerance: int = YEAR_TOLERANCE) -> list[CorpusEntry]:
    """Union candidates that are the same paper.

    Match order: identical source record; same DOI; same arXiv id; same normalized
    title and first-author surname with years within ``year_tolerance``. The tolerance
    is wide because journal versions of theory papers appear two to eight years after
    the conference version (EXP-001 smoke: 45 of 45 same-title pairs kept apart by a
    one-year tolerance were versions of one paper). The title rule is withheld for
    titles of fewer than ``MIN_TITLE_WORDS`` words or matching ``_GENERIC_TITLE``, and
    for pairs in which neither record carries a year. Every applied key is recorded in
    ``merge_keys`` of the resulting entry.
    """
    uf = _UnionFind(len(cands))
    keys_applied: dict[int, set[str]] = {i: set() for i in range(len(cands))}

    def link(group: Iterable[int], label: str) -> None:
        group = list(group)
        for i in group[1:]:
            uf.union(group[0], i)
        if len(group) > 1:
            for i in group:
                keys_applied[i].add(label)

    by_source: dict[tuple[str, str], list[int]] = {}
    by_doi: dict[str, list[int]] = {}
    by_arxiv: dict[str, list[int]] = {}
    by_title: dict[tuple[str, str], list[int]] = {}
    for i, c in enumerate(cands):
        by_source.setdefault((c.source, c.source_id), []).append(i)
        if c.doi:
            by_doi.setdefault(c.doi, []).append(i)
        if c.arxiv_id:
            by_arxiv.setdefault(c.arxiv_id, []).append(i)
        tk, sk = title_key(c.title), surname_key(c.first_author)
        if tk and sk:
            by_title.setdefault((tk, sk), []).append(i)
    for (src, sid), group in by_source.items():
        link(group, f"source:{src}:{sid}")
    for doi, group in by_doi.items():
        link(group, f"doi:{doi}")
    for aid, group in by_arxiv.items():
        link(group, f"arxiv:{aid}")
    withheld = 0
    for (tk, sk), group in by_title.items():
        if len(group) < 2:
            continue
        if len(tk.split()) < MIN_TITLE_WORDS or _GENERIC_TITLE.search(tk):
            withheld += len(group) - 1
            continue
        group = sorted(group, key=lambda i: (cands[i].year is None, cands[i].year or 0))
        for a_pos, a in enumerate(group):
            for b in group[a_pos + 1:]:
                ya, yb = cands[a].year, cands[b].year
                if ya is None and yb is None:
                    withheld += 1
                    continue
                if ya is None or yb is None or abs(ya - yb) <= year_tolerance:
                    link([a, b], f"title:{tk[:40]}|{sk}")
    if withheld:
        log.info("title rule withheld for %d candidate pairs (generic or short title, or no year on either record)", withheld)

    clusters: dict[int, list[int]] = {}
    for i in range(len(cands)):
        clusters.setdefault(uf.find(i), []).append(i)

    entries: list[CorpusEntry] = []
    for members in clusters.values():
        members.sort()
        cs = [cands[i] for i in members]
        oa = [c for c in cs if c.source == "openalex"]
        s2 = [c for c in cs if c.source == "s2"]
        primary = oa[0] if oa else cs[0]
        years = [c.year for c in cs if c.year is not None]
        cited = [c.cited_by_count for c in oa if c.cited_by_count is not None] or \
                [c.cited_by_count for c in cs if c.cited_by_count is not None]
        contexts = [ctx for c in cs for ctx in c.contexts]
        keys = sorted(set().union(*(keys_applied[i] for i in members)))
        entries.append(CorpusEntry(
            entry_id="",
            doi=next((c.doi for c in cs if c.doi), None),
            arxiv_id=next((c.arxiv_id for c in cs if c.arxiv_id), None),
            openalex_ids=sorted({c.source_id for c in oa}),
            s2_paper_ids=sorted({c.source_id for c in s2}),
            title=primary.title,
            year=min(years) if years else None,
            first_author=primary.first_author,
            venue=primary.venue,
            doc_type=primary.doc_type,
            seeds_cited=sorted({c.seed_code for c in cs}),
            oa_pdf_url=next((c.oa_pdf_url for c in cs if c.oa_pdf_url), None),
            cited_by_count=max(cited) if cited else None,
            sources=sorted({c.source for c in cs}),
            contexts=contexts,
            merge_keys=keys,
            openalex_records=[c.raw for c in oa],
            s2_records=[c.raw for c in s2],
        ))
    entries.sort(key=lambda e: (e.year is None, e.year or 0, e.title.lower(), e.doi or "", e.arxiv_id or ""))
    for n, e in enumerate(entries, start=1):
        e.entry_id = f"E{n:06d}"
    return entries


def mark_seeds(entries: Sequence[CorpusEntry], seed_openalex_ids: Iterable[str], seed_s2_ids: Iterable[str]) -> int:
    """Flag entries that are themselves seed works (hypothesis-defining papers citing other seeds)."""
    oa = set(seed_openalex_ids)
    s2 = set(seed_s2_ids)
    n = 0
    for e in entries:
        if any(i in oa for i in e.openalex_ids) or any(i in s2 for i in e.s2_paper_ids):
            e.is_seed = True
            n += 1
    return n


# ---------------------------------------------------------------------------
# Snapshot, counts, checksums, environment
# ---------------------------------------------------------------------------

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def write_snapshot(entries: Sequence[CorpusEntry], data_raw_dir: Path, snapshot_date: str) -> dict[str, str]:
    """Write ``corpus_snapshot_<date>.jsonl`` and ``manifest.csv``; refuse to overwrite a snapshot."""
    data_raw_dir.mkdir(parents=True, exist_ok=True)
    jsonl_path = data_raw_dir / f"corpus_snapshot_{snapshot_date}.jsonl"
    if jsonl_path.exists():
        raise FileExistsError(f"{jsonl_path} exists; snapshots are never overwritten")
    with open(jsonl_path, "w", encoding="utf-8") as f:
        for e in entries:
            f.write(json.dumps(asdict(e), ensure_ascii=False) + "\n")
    manifest_path = data_raw_dir / f"manifest_{snapshot_date}.csv"
    with open(manifest_path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["entry_id", "doi", "arxiv_id", "openalex_ids", "s2_paper_ids", "title", "year",
                    "first_author", "venue", "doc_type", "seeds_cited", "oa_pdf_url", "cited_by_count",
                    "sources", "n_contexts", "is_seed", "merge_keys"])
        for e in entries:
            w.writerow([e.entry_id, e.doi or "", e.arxiv_id or "", ";".join(e.openalex_ids), ";".join(e.s2_paper_ids),
                        e.title, e.year if e.year is not None else "", e.first_author, e.venue, e.doc_type,
                        ";".join(e.seeds_cited), e.oa_pdf_url or "", e.cited_by_count if e.cited_by_count is not None else "",
                        ";".join(e.sources), len(e.contexts), int(e.is_seed), ";".join(e.merge_keys)])
    return {"jsonl": str(jsonl_path), "manifest": str(manifest_path)}


def update_checksums(data_dir: Path, paths: Iterable[Path]) -> Path:
    """Append SHA-256 lines for ``paths`` to ``data/checksums.sha256`` (sha256sum format)."""
    out = data_dir / "checksums.sha256"
    existing: set[str] = set()
    if out.exists():
        existing = {line.split("  ", 1)[1].strip() for line in out.read_text(encoding="utf-8").splitlines() if "  " in line}
    with open(out, "a", encoding="utf-8") as f:
        for p in paths:
            rel = p.relative_to(data_dir.parent).as_posix()
            if rel in existing:
                continue
            f.write(f"{sha256_file(p)}  {rel}\n")
    return out


def snapshot_counts(entries: Sequence[CorpusEntry], cands: Sequence[Candidate]) -> dict:
    by_seed_source: dict[str, int] = {}
    for c in cands:
        by_seed_source[f"{c.seed_code}:{c.source}"] = by_seed_source.get(f"{c.seed_code}:{c.source}", 0) + 1
    by_seed: dict[str, int] = {}
    for e in entries:
        for s in e.seeds_cited:
            by_seed[s] = by_seed.get(s, 0) + 1
    return {
        "candidates_total": len(cands),
        "candidates_by_seed_and_source": dict(sorted(by_seed_source.items())),
        "entries_total": len(entries),
        "entries_by_seed": dict(sorted(by_seed.items())),
        "entries_with_doi": sum(1 for e in entries if e.doi),
        "entries_with_arxiv": sum(1 for e in entries if e.arxiv_id),
        "entries_with_oa_pdf_url": sum(1 for e in entries if e.oa_pdf_url),
        "entries_in_both_sources": sum(1 for e in entries if len(e.sources) == 2),
        "entries_with_multiple_openalex_ids": sum(1 for e in entries if len(e.openalex_ids) > 1),
        "entries_merged_by_title_only": sum(
            1 for e in entries
            if len(e.openalex_ids) + len(e.s2_paper_ids) > 1
            and any(k.startswith("title:") for k in e.merge_keys)
            and not any(k.startswith(("doi:", "arxiv:")) for k in e.merge_keys)),
        "entries_is_seed": sum(1 for e in entries if e.is_seed),
    }


def environment_snapshot(repo_dir: Path | None = None) -> dict:
    """Record platform, Python, package versions and git state for an experiment directory."""
    from importlib import metadata

    def git(args: list[str]) -> str | None:
        try:
            return subprocess.run(["git", *args], cwd=repo_dir, capture_output=True, text=True, check=True).stdout.strip()
        except (OSError, subprocess.CalledProcessError):
            return None

    packages = {}
    for name in ("requests", "pyyaml", "pandas", "numpy", "scipy", "tqdm", "python-dotenv", "ethcensus"):
        try:
            packages[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            packages[name] = None
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "platform": platform.platform(),
        "python_version": sys.version,
        "git_commit": git(["rev-parse", "HEAD"]),
        "git_dirty": bool(git(["status", "--porcelain"])),
        "packages": packages,
    }
