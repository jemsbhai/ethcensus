"""EXP-002 entry point: extract hypothesis contexts from every fetched full text.

Usage (PowerShell, from the repository root):

    python scripts/extract_contexts.py --status data/processed/fulltext_status_2026-10-30.csv --out experiments/EXP-002

Reads the full-text status file written by scripts/fetch_fulltext.py, runs the
extractor on every entry whose text basis is LATEX, PDF or ABSTRACT, and writes
data/processed/contexts_<label>.jsonl (never overwritten), a per-entry summary
and stage counts under the experiment directory. The patterns file is hashed so
the run is tied to one pattern version.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import logging
import sys
from pathlib import Path

from ethcensus import collect as C
from ethcensus import extract as X

log = logging.getLogger("extract_contexts")


def parse_args(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--status", required=True, help="full-text status CSV from fetch_fulltext.py")
    p.add_argument("--patterns", default="configs/patterns.yaml")
    p.add_argument("--out", required=True, help="experiment directory, for example experiments/EXP-002")
    p.add_argument("--data-dir", default="data")
    p.add_argument("--label", default=None, help="label of the contexts file; defaults to the status file's date")
    p.add_argument("--limit", type=int, default=None, help="process at most this many entries (smoke tests)")
    p.add_argument("--verbose", action="store_true")
    return p.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    status_path = Path(args.status)
    label = args.label or status_path.stem.replace("fulltext_status_", "")
    data_dir = Path(args.data_dir)
    out = Path(args.out)
    (out / "results").mkdir(parents=True, exist_ok=True)
    contexts_path = data_dir / "processed" / f"contexts_{label}.jsonl"
    if contexts_path.exists():
        raise FileExistsError(f"{contexts_path} exists; extraction outputs are never overwritten")

    patterns_text = Path(args.patterns).read_text(encoding="utf-8")
    patterns = X.Patterns.from_config(__import__("yaml").safe_load(patterns_text))
    patterns_hash = hashlib.sha256(patterns_text.encode("utf-8")).hexdigest()
    (out / "config.yaml").write_text(
        f"patterns_file: {args.patterns}\npatterns_version: {patterns.version}\npatterns_sha256: {patterns_hash}\n"
        f"status_file: {status_path}\nlabel: {label}\n", encoding="utf-8")
    (out / "environment.json").write_text(json.dumps(C.environment_snapshot(Path(".")), indent=2), encoding="utf-8")

    with open(status_path, encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    processed = 0
    total_contexts = 0
    by_basis: dict[str, dict[str, int]] = {}
    summaries: dict[str, dict] = {}
    for row in rows:
        basis = row["text_basis"]
        stats = by_basis.setdefault(basis, {"entries": 0, "with_contexts": 0, "contexts": 0, "theorem_contexts": 0})
        stats["entries"] += 1
        if basis not in ("LATEX", "PDF", "ABSTRACT") or not row.get("processed_path"):
            continue
        try:
            ctx = X.extract_entry(row["entry_id"], basis, Path(row["processed_path"]), patterns)
        except Exception as exc:  # one bad file must not stop the run; it is logged as data
            log.warning("%s: extraction failed: %s", row["entry_id"], exc)
            summaries[row["entry_id"]] = {"error": str(exc)[:200]}
            continue
        processed += 1
        if ctx:
            stats["with_contexts"] += 1
            stats["contexts"] += len(ctx)
            stats["theorem_contexts"] += sum(1 for c in ctx if c.kind == "theorem")
            total_contexts += X.write_contexts(ctx, contexts_path)
            summaries.update(X.summarize(ctx))
        if processed % 100 == 0:
            log.info("processed %d entries, %d contexts so far", processed, total_contexts)
        if args.limit is not None and processed >= args.limit:
            break

    counts = {"label": label, "patterns_version": patterns.version, "patterns_sha256": patterns_hash,
              "entries_in_status": len(rows), "entries_processed": processed, "contexts_total": total_contexts,
              "by_text_basis": by_basis, "contexts_file": str(contexts_path)}
    (out / "results" / f"extract_counts_{label}.json").write_text(json.dumps(counts, indent=2), encoding="utf-8")
    (out / "results" / f"entry_summaries_{label}.json").write_text(json.dumps(summaries, indent=2), encoding="utf-8")
    if contexts_path.exists():
        C.update_checksums(data_dir, [contexts_path])
    print(json.dumps(counts, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
