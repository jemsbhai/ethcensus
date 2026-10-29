import gzip
import io
import tarfile
from pathlib import Path

import pytest

from ethcensus import fetch as F


def make_targz(files: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for name, data in files.items():
            info = tarfile.TarInfo(name)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
    return buf.getvalue()


def make_pdf(text: str) -> bytes:
    fitz = pytest.importorskip("fitz")
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), text)
    return doc.tobytes()


MAIN = b"\\documentclass{article}\n\\begin{document}\n\\input{sections/intro}\nBody. \\include{conclusion}\n\\end{document}\n"
INTRO = b"Intro text with \\input{sections/deeper.tex}.\n"
DEEPER = b"Deep text.\n"
CONCL = b"Conclusion text.\n"


class FakeFetchBytes:
    def __init__(self, table):
        self.table = table
        self.calls = []

    def __call__(self, url, headers):
        self.calls.append((url, headers))
        return self.table.get(url, (404, "text/html", b"<html>not found</html>"))


def no_sleep(_s):
    return None


# ---------------------------------------------------------------------------
# Content handling
# ---------------------------------------------------------------------------

def test_sniff_detects_formats():
    assert F.sniff(b"%PDF-1.7 ...") == "pdf"
    assert F.sniff(gzip.compress(b"x")) == "gzip"
    assert F.sniff(b"<!DOCTYPE html><html>") == "html"
    assert F.sniff(b"\\documentclass{article}") == "text"
    assert F.sniff(make_targz({"a.tex": b"x"})) == "gzip"


def test_read_tex_bundle_from_targz_and_single_gz():
    bundle = make_targz({"main.tex": MAIN, "sections/intro.tex": INTRO, "sections/deeper.tex": DEEPER,
                         "conclusion.tex": CONCL, "fig.png": b"\x89PNG", "../evil.tex": b"bad"})
    files = F.read_tex_bundle(bundle)
    assert set(files) == {"main.tex", "sections/intro.tex", "sections/deeper.tex", "conclusion.tex"}
    single = F.read_tex_bundle(gzip.compress(MAIN))
    assert list(single) == ["main.tex"] and single["main.tex"].startswith("\\documentclass")
    assert F.read_tex_bundle(gzip.compress(b"%PDF-1.4 fake")) == {}


def test_find_main_tex_prefers_begin_document_and_shallow_conventional_names():
    files = {"old/draft.tex": "\\documentclass{article}\\begin{document}x\\end{document}",
             "main.tex": "\\documentclass{article}\\begin{document}y\\end{document}",
             "macros.tex": "\\newcommand{\\x}{1}",
             "preamble.tex": "\\documentclass{article}"}
    assert F.find_main_tex(files) == "main.tex"
    assert F.find_main_tex({"macros.tex": "\\newcommand{\\x}{1}"}) is None


def test_flatten_tex_inlines_inputs_recursively():
    files = {"main.tex": MAIN.decode(), "sections/intro.tex": INTRO.decode(),
             "sections/deeper.tex": DEEPER.decode(), "conclusion.tex": CONCL.decode()}
    text = F.flatten_tex(files, "main.tex")
    assert "Intro text" in text and "Deep text" in text and "Conclusion text" in text
    assert "\\input{" not in text
    cyclic = {"a.tex": "\\documentclass{x}\\input{b}", "b.tex": "\\input{a} B"}
    assert "B" in F.flatten_tex(cyclic, "a.tex")


def test_abstract_from_inverted_index_restores_word_order():
    idx = {"hard.": [3], "is": [1], "SAT": [0], "very": [2]}
    assert F.abstract_from_inverted_index(idx) == "SAT is very hard."
    assert F.abstract_from_inverted_index(None) == ""


def test_pdf_to_text_extracts_inserted_text():
    text = F.pdf_to_text(make_pdf("Theorem 1. Assuming ETH, nothing is fast."))
    assert "Assuming ETH" in text


# ---------------------------------------------------------------------------
# Acquisition flows
# ---------------------------------------------------------------------------

def entry(entry_id="E000001", arxiv_id=None, oa=None, openalex_ids=None, abstract_index=None):
    recs = [{"abstract_inverted_index": abstract_index}] if abstract_index else []
    return {"entry_id": entry_id, "arxiv_id": arxiv_id, "oa_pdf_url": oa,
            "openalex_ids": openalex_ids or [], "openalex_records": recs}


def fetcher(tmp_path, table, **kw):
    return F.FullTextFetcher(tmp_path / "raw", tmp_path / "proc", fetch_bytes=FakeFetchBytes(table),
                             contact="test@example.org", sleep=no_sleep, now=lambda: "2026-10-29T00:00:00+0000", **kw)


def test_fetch_entry_latex_from_eprint(tmp_path: Path):
    bundle = make_targz({"main.tex": MAIN, "sections/intro.tex": INTRO, "sections/deeper.tex": DEEPER, "conclusion.tex": CONCL})
    fx = fetcher(tmp_path, {"https://arxiv.org/e-print/1607.02986": (200, "application/gzip", bundle)})
    r = fx.fetch_entry(entry(arxiv_id="1607.02986"))
    assert r.text_basis == "LATEX" and r.source == "arxiv_eprint"
    assert Path(r.processed_path).read_text(encoding="utf-8").count("Deep text") == 1
    assert Path(r.raw_path).read_bytes() == bundle
    assert len(r.sha256) == 64 and r.nbytes == len(bundle)
    assert fx.fetch_bytes.calls[0][1]["User-Agent"].startswith("ethcensus/")


def test_fetch_entry_falls_back_to_arxiv_pdf_when_eprint_is_pdf_only(tmp_path: Path):
    pdf = make_pdf("Only a PDF was submitted.")
    fx = fetcher(tmp_path, {"https://arxiv.org/e-print/2001.00001": (200, "application/pdf", pdf)})
    r = fx.fetch_entry(entry(arxiv_id="2001.00001"))
    assert r.text_basis == "PDF" and r.source == "arxiv_eprint" and r.note == "pdf-only submission"
    assert "PDF was submitted" in Path(r.processed_path).read_text(encoding="utf-8")


def test_fetch_entry_uses_arxiv_pdf_when_eprint_fails(tmp_path: Path):
    pdf = make_pdf("From the PDF endpoint.")
    fx = fetcher(tmp_path, {"https://arxiv.org/e-print/2001.00002": (403, "text/html", b"<html>no</html>"),
                            "https://arxiv.org/pdf/2001.00002": (200, "application/pdf", pdf)})
    r = fx.fetch_entry(entry(arxiv_id="2001.00002"))
    assert r.text_basis == "PDF" and r.source == "arxiv_pdf"


def test_fetch_entry_uses_oa_pdf_then_abstract_then_none(tmp_path: Path):
    pdf = make_pdf("Open access copy.")
    fx = fetcher(tmp_path, {"https://example.org/paper.pdf": (200, "application/pdf", pdf),
                            "https://example.org/landing": (200, "text/html", b"<html>landing</html>")})
    r = fx.fetch_entry(entry(oa="https://example.org/paper.pdf"))
    assert r.text_basis == "PDF" and r.source == "oa_pdf"
    r2 = fx.fetch_entry(entry("E000002", oa="https://example.org/landing", abstract_index={"Hello": [0], "world": [1]}))
    assert r2.text_basis == "ABSTRACT" and r2.source == "abstract" and "status=200" in r2.note
    assert Path(r2.processed_path).read_text(encoding="utf-8") == "Hello world"
    r3 = fx.fetch_entry(entry("E000003"))
    assert r3.text_basis == "NONE" and r3.note == "no oa url"


def test_fetch_entry_openalex_content_only_when_enabled(tmp_path: Path):
    pdf = make_pdf("Cached by OpenAlex.")
    table = {"https://content.openalex.org/works/W1.pdf?api_key=K": (200, "application/pdf", pdf)}
    off = fetcher(tmp_path, table, openalex_api_key="K", use_openalex_content=False)
    assert off.fetch_entry(entry(openalex_ids=["W1"])).text_basis == "NONE"
    on = fetcher(tmp_path, table, openalex_api_key="K", use_openalex_content=True)
    r = on.fetch_entry(entry(openalex_ids=["W1"]))
    assert r.text_basis == "PDF" and r.source == "openalex_content"
    assert "api_key" not in r.url


def test_arxiv_requests_are_throttled_separately(tmp_path: Path):
    slept = []
    fx = F.FullTextFetcher(tmp_path / "raw", tmp_path / "proc",
                           fetch_bytes=FakeFetchBytes({}), sleep=slept.append, arxiv_interval=3.0,
                           now=lambda: "t")
    fx.throttles["arxiv.org"]._clock = iter([0.0, 0.0, 0.5, 3.5]).__next__
    fx.fetch_entry(entry(arxiv_id="2001.00003"))     # e-print then pdf: second arxiv call must wait
    assert slept and slept[0] == pytest.approx(2.5)


# ---------------------------------------------------------------------------
# Status file
# ---------------------------------------------------------------------------

def test_status_file_is_resumable_and_summarized(tmp_path: Path):
    status = tmp_path / "data" / "processed" / "fulltext_status_2026-10-29.csv"
    assert F.load_done(status) == set()
    r = F.FetchResult("E000001", "LATEX", "arxiv_eprint", "u", "r", "p", "0" * 64, 10, 200, "", "t")
    F.append_status(status, r)
    F.append_status(status, F.FetchResult("E000002", "NONE", "none", "", "", "", "", 0, None, "no oa url", "t"))
    assert F.load_done(status) == {"E000001", "E000002"}
    summary = F.summarize_status(status)
    assert summary == {"by_text_basis": {"LATEX": 1, "NONE": 1}, "by_source": {"arxiv_eprint": 1, "none": 1}, "total": 2}
