"""Print the records behind merged corpus entries so that merge decisions can be checked by eye.

Usage (PowerShell, from the repository root):

    python scripts/inspect_merges.py --snapshot data/raw/corpus_snapshot_<date>.jsonl --mode title-only
    python scripts/inspect_merges.py --snapshot data/raw/corpus_snapshot_<date>.jsonl --mode cross-source --limit 25

Modes: ``title-only`` (entries whose records were united by title, surname and year
alone, never by DOI or arXiv identifier), ``cross-source`` (entries with records from
both OpenAlex and Semantic Scholar), ``all`` (every entry with two or more records),
``split`` (groups of distinct entries that share normalized title and first-author
surname, that is, pairs the title rule declined to unite because of a short or generic
title, missing years, or a year gap above the tolerance).
With ``--limit`` a reproducible random sample is drawn with ``--seed`` (default: the
project master seed). The output is read, not parsed; the spot check and its verdict
are recorded in LOGBOOK.md.
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

from ethcensus import collect as C


def parse_args(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--snapshot", required=True)
    p.add_argument("--mode", choices=["title-only", "cross-source", "all", "split"], default="title-only")
    p.add_argument("--limit", type=int, default=None, help="print at most this many entries (random sample)")
    p.add_argument("--seed", type=int, default=20261029)
    return p.parse_args(argv)


def records(entry: dict) -> list[tuple[str, C.Candidate]]:
    out = []
    for rec in entry.get("openalex_records") or []:
        out.append(("openalex", C.candidate_from_openalex(rec, "?")))
    for rec in entry.get("s2_records") or []:
        # The snapshot stores the citing paper itself; candidate_from_s2 expects the citation item around it.
        out.append(("s2", C.candidate_from_s2({"citingPaper": rec}, "?")))
    return out


def selected(entry: dict, mode: str) -> bool:
    if len(entry["openalex_ids"]) + len(entry["s2_paper_ids"]) < 2:
        return False
    keys = entry["merge_keys"]
    if mode == "title-only":
        return any(k.startswith("title:") for k in keys) and not any(k.startswith(("doi:", "arxiv:")) for k in keys)
    if mode == "cross-source":
        return len(entry["sources"]) == 2
    return True


def split_groups(all_entries: list[dict]) -> list[dict]:
    """Entries sharing (title key, surname key) with another entry, ordered by that key."""
    groups: dict[tuple[str, str], list[dict]] = {}
    for e in all_entries:
        key = (C.title_key(e["title"]), C.surname_key(e["first_author"]))
        if key[0] and key[1]:
            groups.setdefault(key, []).append(e)
    out = []
    for key in sorted(groups):
        if len(groups[key]) > 1:
            out.extend(groups[key])
    return out


def main(argv=None) -> int:
    args = parse_args(argv)
    entries = []
    all_entries = []
    with open(Path(args.snapshot), encoding="utf-8") as f:
        for line in f:
            if line.strip():
                e = json.loads(line)
                all_entries.append(e)
                if args.mode != "split" and selected(e, args.mode):
                    entries.append(e)
    if args.mode == "split":
        entries = split_groups(all_entries)
    total = len(entries)
    if args.limit is not None and total > args.limit and args.mode != "split":
        entries = random.Random(args.seed).sample(entries, args.limit)
        entries.sort(key=lambda e: e["entry_id"])
    print(f"# mode={args.mode} matching={total} shown={len(entries)} seed={args.seed}")
    for e in entries:
        keys = ";".join(k[:48] for k in e["merge_keys"])
        print(f"{e['entry_id']} sources={','.join(e['sources'])} seeds={','.join(e['seeds_cited'])} keys={keys}")
        for src, c in records(e):
            year = c.year if c.year is not None else "----"
            print(f"    {src:8} {year} {(c.first_author or '')[:22]:22} {(c.title or '')[:88]} | {(c.venue or '')[:32]}"
                  f" | doi={c.doi or ''} arxiv={c.arxiv_id or ''}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
