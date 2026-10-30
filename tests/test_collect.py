import json
from pathlib import Path

import pytest

from ethcensus import collect as C


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------

class FakeFetch:
    """Replays a scripted sequence of (status, body, headers) and records the calls."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def __call__(self, url, params, headers):
        self.calls.append((url, dict(params), dict(headers)))
        if not self.responses:
            raise AssertionError("no scripted response left for " + url)
        return self.responses.pop(0)


def no_sleep(_seconds):
    return None


def oa_work(wid, doi=None, title="A paper", year=2020, author="Alice Smith", arxiv=None, cited=5):
    rec = {
        "id": f"https://openalex.org/{wid}",
        "doi": f"https://doi.org/{doi}" if doi else None,
        "title": title,
        "publication_year": year,
        "type": "article",
        "cited_by_count": cited,
        "authorships": [{"author": {"display_name": author}}],
        "primary_location": {"source": {"display_name": "SODA"}, "landing_page_url": None},
        "best_oa_location": {"pdf_url": f"https://arxiv.org/pdf/{arxiv}" if arxiv else None},
        "open_access": {"oa_url": None},
    }
    return rec


def s2_item(pid, doi=None, title="A paper", year=2020, author="Alice Smith", arxiv=None, contexts=None):
    ext = {}
    if doi:
        ext["DOI"] = doi
    if arxiv:
        ext["ArXiv"] = arxiv
    return {
        "contexts": contexts or [],
        "intents": ["background"],
        "isInfluential": False,
        "citingPaper": {"paperId": pid, "externalIds": ext, "title": title, "year": year,
                        "authors": [{"name": author}], "venue": "ICALP", "citationCount": 3,
                        "publicationTypes": ["Conference"], "abstract": "must be dropped"},
    }


# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------

def test_normalize_doi_strips_prefixes_and_case():
    assert C.normalize_doi("https://doi.org/10.1145/2925416") == "10.1145/2925416"
    assert C.normalize_doi("DOI:10.1006/JCSS.2000.1727") == "10.1006/jcss.2000.1727"
    assert C.normalize_doi("") is None
    assert C.normalize_doi(None) is None


def test_normalize_arxiv_handles_ids_versions_and_urls():
    assert C.normalize_arxiv("1607.02986") == "1607.02986"
    assert C.normalize_arxiv("arXiv:1607.02986v2") == "1607.02986"
    assert C.normalize_arxiv("https://arxiv.org/pdf/1206.1775v1") == "1206.1775"
    assert C.normalize_arxiv("https://arxiv.org/abs/cs/0501001") == "cs/0501001"
    assert C.normalize_arxiv("https://doi.org/10.1145/2925416") is None


def test_title_and_surname_keys():
    assert C.title_key("On the  Complexity: of k-SAT!") == "on the complexity of k sat"
    assert C.surname_key("Ramamohan Paturi") == "paturi"
    assert C.surname_key("Paturi, Ramamohan") == "paturi"
    assert C.surname_key("Jesper Nederlof") == "nederlof"
    assert C.surname_key("Maxime Crochemore A") == "crochemore"      # stray initial seen in OpenAlex
    assert C.surname_key("Virginia Vassilevska W") == "vassilevska"
    assert C.surname_key("Klein, PN") == "klein"
    assert C.surname_key("") == ""


# ---------------------------------------------------------------------------
# Retry and throttling
# ---------------------------------------------------------------------------

def test_get_with_retry_retries_on_429_then_succeeds():
    fetch = FakeFetch([(429, {"error": "slow down"}, {"Retry-After": "0"}), (200, {"ok": True}, {})])
    slept = []
    body, _ = C.get_with_retry(fetch, "http://x", {}, {}, C.Throttle(0, sleep=no_sleep), sleep=slept.append)
    assert body == {"ok": True}
    assert slept == [0.0]
    assert len(fetch.calls) == 2


def test_get_with_retry_raises_auth_on_401():
    fetch = FakeFetch([(401, {"error": "key"}, {})])
    with pytest.raises(C.AuthError):
        C.get_with_retry(fetch, "http://x", {}, {}, C.Throttle(0, sleep=no_sleep), sleep=no_sleep)


def test_get_with_retry_raises_budget_on_403_budget_message():
    fetch = FakeFetch([(403, {"error": "Insufficient budget, resets at midnight UTC"}, {})])
    with pytest.raises(C.BudgetError):
        C.get_with_retry(fetch, "http://x", {}, {}, C.Throttle(0, sleep=no_sleep), sleep=no_sleep)


def test_get_with_retry_gives_up_after_max_retries():
    fetch = FakeFetch([(503, {}, {})] * 3)
    with pytest.raises(C.CollectError):
        C.get_with_retry(fetch, "http://x", {}, {}, C.Throttle(0, sleep=no_sleep), max_retries=2, sleep=no_sleep)


def test_throttle_waits_for_min_interval():
    slept = []
    clock = iter([0.0, 0.0, 0.2, 1.0, 1.0]).__next__
    t = C.Throttle(1.0, sleep=slept.append, clock=clock)
    t.wait()            # first call: no wait
    t.wait()            # 0.2 s elapsed: must sleep 0.8
    assert slept == [pytest.approx(0.8)]


# ---------------------------------------------------------------------------
# OpenAlex client
# ---------------------------------------------------------------------------

def test_openalex_cites_filter_joins_ids_and_rejects_empty():
    assert C.OpenAlexClient.cites_filter(["W1", "W2"]) == "cites:W1|W2"
    assert C.OpenAlexClient.cites_filter(["W1"], "publication_year:>2015") == "cites:W1,publication_year:>2015"
    with pytest.raises(ValueError):
        C.OpenAlexClient.cites_filter([])


def test_openalex_iter_citers_follows_cursor_to_exhaustion():
    page1 = {"meta": {"count": 3, "next_cursor": "c2"}, "results": [oa_work("W10"), oa_work("W11")]}
    page2 = {"meta": {"count": 3, "next_cursor": "c3"}, "results": [oa_work("W12")]}
    page3 = {"meta": {"count": 3, "next_cursor": None}, "results": []}
    fetch = FakeFetch([(200, page1, {"X-RateLimit-Remaining-USD": "0.9"}), (200, page2, {}), (200, page3, {})])
    client = C.OpenAlexClient("KEY", fetch_json=fetch, per_page=2, min_interval=0, sleep=no_sleep)
    got = list(client.iter_citers(["W1"], select=["id", "title"]))
    assert [r["id"] for r in got] == ["https://openalex.org/W10", "https://openalex.org/W11", "https://openalex.org/W12"]
    first_params = fetch.calls[0][1]
    assert first_params["cursor"] == "*"
    assert first_params["api_key"] == "KEY"
    assert first_params["filter"] == "cites:W1"
    assert first_params["select"] == "id,title"
    assert fetch.calls[1][1]["cursor"] == "c2"


def test_openalex_count_citers_reads_meta_count():
    fetch = FakeFetch([(200, {"meta": {"count": 2596}, "results": []}, {})])
    client = C.OpenAlexClient(None, fetch_json=fetch, min_interval=0, sleep=no_sleep)
    assert client.count_citers(["W1", "W2"]) == 2596
    assert "api_key" not in fetch.calls[0][1]


# ---------------------------------------------------------------------------
# Semantic Scholar client
# ---------------------------------------------------------------------------

def test_s2_iter_citations_pages_by_offset_until_next_absent():
    p1 = {"offset": 0, "next": 2, "data": [s2_item("a"), s2_item("b")]}
    p2 = {"offset": 2, "data": [s2_item("c")]}
    fetch = FakeFetch([(200, p1, {}), (200, p2, {})])
    client = C.SemanticScholarClient("S2KEY", fetch_json=fetch, limit=2, min_interval=0, sleep=no_sleep)
    got = list(client.iter_citations("PID", fields=["contexts", "title"]))
    assert [g["citingPaper"]["paperId"] for g in got] == ["a", "b", "c"]
    assert fetch.calls[0][2]["x-api-key"] == "S2KEY"
    assert fetch.calls[0][1] == {"fields": "contexts,title", "offset": "0", "limit": "2"}
    assert fetch.calls[1][1]["offset"] == "2"


# ---------------------------------------------------------------------------
# Candidates and merging
# ---------------------------------------------------------------------------

def test_candidate_from_openalex_extracts_fields_and_arxiv_from_pdf_url():
    c = C.candidate_from_openalex(oa_work("W5", doi="10.1/ABC", arxiv="1607.02986v1"), "IP01")
    assert c.source_id == "W5"
    assert c.doi == "10.1/abc"
    assert c.arxiv_id == "1607.02986"
    assert c.first_author == "Alice Smith"
    assert c.venue == "SODA"
    assert c.seed_code == "IP01"


def test_candidate_from_s2_drops_abstract_and_keeps_contexts():
    c = C.candidate_from_s2(s2_item("p1", doi="10.1/ABC", contexts=["We assume ETH."]), "IPZ01")
    assert c.doi == "10.1/abc"
    assert c.contexts[0]["context"] == "We assume ETH."
    assert c.contexts[0]["seed"] == "IPZ01"
    assert "abstract" not in c.raw


def test_merge_by_doi_arxiv_and_title():
    cands = [
        C.candidate_from_openalex(oa_work("W1", doi="10.1/x", title="Edit distance lower bound", year=2015), "IP01"),
        C.candidate_from_s2(s2_item("s1", doi="10.1/X", title="Edit distance lower bound", year=2015,
                                    contexts=["unless SETH fails"]), "CIP09"),
        C.candidate_from_openalex(oa_work("W2", title="Frechet hardness", year=2014, arxiv="1404.0001"), "IP01"),
        C.candidate_from_s2(s2_item("s2", title="Frechet hardness", year=2014, arxiv="1404.0001v3"), "IP01"),
        C.candidate_from_openalex(oa_work("W3", title="Tight treewidth bounds", year=2011, author="Daniel Lokshtanov"), "IP01"),
        C.candidate_from_openalex(oa_work("W4", doi="10.1/y", title="Tight treewidth bounds", year=2012, author="D. Lokshtanov"), "IPZ01"),
        C.candidate_from_openalex(oa_work("W5", title="Tight treewidth bounds", year=2025, author="Daniel Lokshtanov"), "IP01"),
    ]
    entries = C.merge_candidates(cands)
    titles = {e.title: e for e in entries}
    assert len(entries) == 4
    e1 = titles["Edit distance lower bound"]
    assert e1.openalex_ids == ["W1"] and e1.s2_paper_ids == ["s1"]
    assert e1.seeds_cited == ["CIP09", "IP01"]
    assert e1.contexts[0]["context"] == "unless SETH fails"
    assert any(k.startswith("doi:") for k in e1.merge_keys)
    e2 = titles["Frechet hardness"]
    assert e2.arxiv_id == "1404.0001" and e2.s2_paper_ids == ["s2"]
    tw = [e for e in entries if e.title == "Tight treewidth bounds"]
    assert sorted(len(e.openalex_ids) for e in tw) == [1, 2]
    merged = next(e for e in tw if len(e.openalex_ids) == 2)
    assert merged.openalex_ids == ["W3", "W4"] and merged.year == 2011 and merged.doi == "10.1/y"
    assert [e.entry_id for e in entries] == ["E000001", "E000002", "E000003", "E000004"]


def test_mark_seeds_flags_seed_records_only():
    entries = C.merge_candidates([
        C.candidate_from_openalex(oa_work("W1985572324", doi="10.1006/jcss.2000.1727", title="On the Complexity of k-SAT",
                                          year=2001, author="Russell Impagliazzo"), "IPZ01"),
        C.candidate_from_openalex(oa_work("W77", doi="10.1/other", title="Some other paper"), "IPZ01")])
    assert len(entries) == 2
    n = C.mark_seeds(entries, ["W1985572324", "W1507717186"], ["94ebc9130e780c017e6e851c8c3d24b7c61c727d"])
    assert n == 1
    flagged = {e.doi: e.is_seed for e in entries}
    assert flagged == {"10.1006/jcss.2000.1727": True, "10.1/other": False}


def test_title_rule_withheld_for_generic_short_or_undated_titles():
    # Found in the EXP-001 smoke: ten S2 records titled with repository boilerplate, no year, same surname.
    generic = [C.Candidate("s2", f"s{i}", "VW18", title="UvA-DARE (Digital Academic Repository)", first_author="Yan-Lin Chen")
               for i in range(5)]
    assert len(C.merge_candidates(generic)) == 5
    short = [C.Candidate("s2", "s1", "IP01", title="Treewidth bounds", first_author="A. Author", year=2020),
             C.Candidate("openalex", "W1", "IP01", title="Treewidth bounds", first_author="B. Author", year=2020)]
    assert len(C.merge_candidates(short)) == 2
    undated = [C.Candidate("s2", "s1", "IP01", title="On treewidth and stable marriage", first_author="Sushmita Gupta"),
               C.Candidate("s2", "s2", "IP01", title="On Treewidth and Stable Marriage", first_author="S. Gupta")]
    assert len(C.merge_candidates(undated)) == 2
    one_dated = [C.Candidate("s2", "s1", "IP01", title="On treewidth and stable marriage", first_author="Sushmita Gupta"),
                 C.Candidate("openalex", "W1", "IP01", title="On Treewidth and Stable Marriage", first_author="S. Gupta", year=2022)]
    merged = C.merge_candidates(one_dated)
    assert len(merged) == 1 and merged[0].sources == ["openalex", "s2"]
    # Conference and journal versions sit years apart (SODA 2011 and TALG 2018 in the smoke); the tolerance covers that.
    versions = [C.Candidate("openalex", "W1", "IP01", title="Known algorithms on graphs of bounded treewidth are probably optimal",
                            first_author="Daniel Lokshtanov", year=2011),
                C.Candidate("s2", "s1", "IP01", title="Known Algorithms on Graphs of Bounded Treewidth Are Probably Optimal",
                            first_author="D. Lokshtanov", year=2018)]
    assert len(C.merge_candidates(versions)) == 1
    assert len(C.merge_candidates(versions, year_tolerance=1)) == 2


def test_merge_same_source_record_twice_collapses():
    rec = oa_work("W9", doi="10.1/z")
    entries = C.merge_candidates([C.candidate_from_openalex(rec, "IP01"), C.candidate_from_openalex(rec, "IPZ01")])
    assert len(entries) == 1
    assert entries[0].seeds_cited == ["IP01", "IPZ01"]


# ---------------------------------------------------------------------------
# Snapshot, checksums, counts, environment
# ---------------------------------------------------------------------------

def test_write_snapshot_and_checksums(tmp_path: Path):
    data_dir = tmp_path / "data"
    raw = data_dir / "raw"
    entries = C.merge_candidates([C.candidate_from_openalex(oa_work("W1", doi="10.1/x"), "IP01")])
    paths = C.write_snapshot(entries, raw, "2026-10-29")
    jsonl = Path(paths["jsonl"])
    assert jsonl.name == "corpus_snapshot_2026-10-29.jsonl"
    line = json.loads(jsonl.read_text(encoding="utf-8").splitlines()[0])
    assert line["entry_id"] == "E000001" and line["doi"] == "10.1/x"
    manifest = Path(paths["manifest"]).read_text(encoding="utf-8").splitlines()
    assert manifest[0].startswith("entry_id,doi,arxiv_id") and manifest[0].endswith("is_seed,merge_keys")
    assert len(manifest) == 2 and manifest[1].split(",")[-2] == "0"
    with pytest.raises(FileExistsError):
        C.write_snapshot(entries, raw, "2026-10-29")
    out = C.update_checksums(data_dir, [jsonl, Path(paths["manifest"])])
    lines = out.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    assert lines[0].endswith("data/raw/corpus_snapshot_2026-10-29.jsonl")
    assert len(lines[0].split("  ")[0]) == 64
    C.update_checksums(data_dir, [jsonl])
    assert len(out.read_text(encoding="utf-8").splitlines()) == 2


def test_snapshot_compression_and_readers(tmp_path: Path):
    raw = tmp_path / "data" / "raw"
    entries = C.merge_candidates([C.candidate_from_openalex(oa_work("W1", doi="10.1/x"), "IP01"),
                                  C.candidate_from_openalex(oa_work("W2", doi="10.1/y", title="Another one"), "IP01")])
    paths = C.write_snapshot(entries, raw, "2026-10-30")
    plain = Path(paths["jsonl"])
    gz = C.compress_snapshot(plain)
    assert gz.name == "corpus_snapshot_2026-10-30.jsonl.gz"
    assert [e["entry_id"] for e in C.iter_snapshot(gz)] == [e["entry_id"] for e in C.iter_snapshot(plain)] == ["E000001", "E000002"]
    assert C.snapshot_label(gz) == "2026-10-30" and C.snapshot_label(plain) == "2026-10-30"
    with pytest.raises(FileExistsError):
        C.compress_snapshot(plain)
    gz2 = C.compress_snapshot(plain.rename(plain.with_name("corpus_snapshot_copy.jsonl")))
    assert gz2.read_bytes()[:10] == gz.read_bytes()[:10]      # deterministic header (no mtime)


def test_snapshot_counts_reports_stage_counts():
    cands = [C.candidate_from_openalex(oa_work("W1", doi="10.1/x", arxiv="1607.02986"), "IP01"),
             C.candidate_from_s2(s2_item("s1", doi="10.1/x"), "IP01")]
    entries = C.merge_candidates(cands)
    counts = C.snapshot_counts(entries, cands)
    assert counts["candidates_total"] == 2
    assert counts["entries_total"] == 1
    assert counts["entries_in_both_sources"] == 1
    assert counts["entries_with_arxiv"] == 1
    assert counts["candidates_by_seed_and_source"] == {"IP01:openalex": 1, "IP01:s2": 1}
    assert counts["entries_merged_by_title_only"] == 0 and counts["entries_with_multiple_openalex_ids"] == 0
    title_only = C.merge_candidates([C.candidate_from_openalex(oa_work("W3", title="Tight treewidth bounds", year=2011), "IP01"),
                                     C.candidate_from_openalex(oa_work("W4", title="Tight treewidth bounds", year=2012), "IP01")])
    c2 = C.snapshot_counts(title_only, [])
    assert c2["entries_merged_by_title_only"] == 1 and c2["entries_with_multiple_openalex_ids"] == 1


def test_environment_snapshot_has_required_keys(tmp_path: Path):
    env = C.environment_snapshot(tmp_path)
    for key in ("timestamp", "platform", "python_version", "git_commit", "git_dirty", "packages"):
        assert key in env
