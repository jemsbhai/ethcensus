"""EXP-001 stage 2: acquire full texts for every entry of a corpus snapshot.

Usage (PowerShell, from the repository root):

    python scripts/fetch_fulltext.py --snapshot data/raw/corpus_snapshot_2026-10-30.jsonl --out experiments/EXP-001 --limit 5
    python scripts/fetch_fulltext.py --snapshot data/raw/corpus_snapshot_2026-10-30.jsonl --out experiments/EXP-001

Resumable: entries already present in the status file are skipped, so an
interrupted run continues where it stopped. Respects the arXiv Terms of Use
(one request every three seconds). The OpenAlex cached-PDF fallback costs
credits and is used only with --use-openalex-content.

After a change to the text processing (LaTeX flattening or PDF text extraction),
``--reprocess`` re-derives every processed text in the status file from the stored,
checksummed raw downloads without any network call, then exits.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

from ethcensus import collect as C
from ethcensus import fetch as F

log = logging.getLogger("fetch_fulltext")


def parse_args(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--snapshot", required=True, help="path to data/raw/corpus_snapshot_<date>.jsonl")
    p.add_argument("--out", required=True, help="experiment directory, for example experiments/EXP-001")
    p.add_argument("--data-dir", default="data")
    p.add_argument("--status-date", default=None, help="label of the status file; defaults to the snapshot's date")
    p.add_argument("--limit", type=int, default=None, help="stop after this many newly fetched entries (smoke tests)")
    p.add_argument("--only-arxiv", action="store_true", help="skip entries without an arXiv identifier")
    p.add_argument("--use-openalex-content", action="store_true")
    p.add_argument("--reprocess", action="store_true",
                   help="re-derive processed texts from the stored raw files for every row of the status file, no network")
    p.add_argument("--verbose", action="store_true")
    return p.parse_args(argv)


def reprocess(status_path: Path) -> dict:
    import csv

    counts: dict[str, int] = {}
    with open(status_path, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            note = F.reprocess_row(row)
            key = f"{row['text_basis']}:{note.split('=')[0].split(';')[0]}"
            counts[key] = counts.get(key, 0) + 1
            log.debug("%s: %s", row["entry_id"], note)
    return {"status_file": str(status_path), "reprocessed": dict(sorted(counts.items()))}


def main(argv=None) -> int:
    args = parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    load_dotenv()
    snapshot = Path(args.snapshot)
    label = args.status_date or C.snapshot_label(snapshot) or date.today().isoformat()
    data_dir = Path(args.data_dir)
    raw_dir = data_dir / "raw" / "fulltext"
    processed_dir = data_dir / "processed" / "fulltext"
    status_path = data_dir / "processed" / f"fulltext_status_{label}.csv"
    out = Path(args.out)
    (out / "results").mkdir(parents=True, exist_ok=True)

    if args.reprocess:
        summary = reprocess(status_path)
        print(json.dumps(summary, indent=2))
        return 0

    fetcher = F.FullTextFetcher(raw_dir, processed_dir,
                                contact=os.environ.get("CONTACT_EMAIL") or os.environ.get("OPENALEX_MAILTO") or "",
                                openalex_api_key=os.environ.get("OPENALEX_API_KEY") or None,
                                use_openalex_content=args.use_openalex_content)
    done = F.load_done(status_path)
    log.info("%d entries already in %s", len(done), status_path)

    fetched = 0
    new_raw_files: list[Path] = []
    try:
        for entry in F.read_snapshot(snapshot):
            if entry["entry_id"] in done:
                continue
            if args.only_arxiv and not entry.get("arxiv_id"):
                continue
            result = fetcher.fetch_entry(entry)
            F.append_status(status_path, result)
            if result.raw_path:
                new_raw_files.append(Path(result.raw_path))
            fetched += 1
            if fetched % 25 == 0:
                log.info("fetched %d new entries; last %s -> %s", fetched, result.entry_id, result.text_basis)
            if args.limit is not None and fetched >= args.limit:
                break
    except KeyboardInterrupt:
        log.warning("interrupted after %d new entries; status file is consistent, rerun to resume", fetched)
    finally:
        if new_raw_files:
            C.update_checksums(data_dir, new_raw_files)
            log.info("appended %d checksum lines", len(new_raw_files))
    summary = F.summarize_status(status_path) if status_path.exists() else {"total": 0}
    summary["status_file"] = str(status_path)
    summary["new_this_run"] = fetched
    (out / "results" / f"fulltext_counts_{label}.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
