"""EXP-001 entry point: build the corpus snapshot from OpenAlex and Semantic Scholar.

Usage (PowerShell, from the repository root):

    python scripts/collect_corpus.py --out experiments/EXP-001 --count-only
    python scripts/collect_corpus.py --out experiments/EXP-001 --max-pages 1 --data-dir experiments/EXP-001/smoke
    python scripts/collect_corpus.py --out experiments/EXP-001

The script freezes its effective configuration and an environment snapshot into
the experiment directory before touching the network, writes the dated corpus
snapshot under data/raw/, appends checksums, and writes counts.json.
Keys are read from .env (OPENALEX_API_KEY, S2_API_KEY).
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import date
from pathlib import Path

import yaml
from dotenv import load_dotenv

from ethcensus import collect as C

log = logging.getLogger("collect_corpus")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--config", default="configs/base.yaml")
    p.add_argument("--seeds", default="configs/seeds.yaml")
    p.add_argument("--out", required=True, help="experiment directory, for example experiments/EXP-001")
    p.add_argument("--groups", nargs="+", default=["core", "aux"], choices=["core", "aux"])
    p.add_argument("--sources", nargs="+", default=["openalex", "s2"], choices=["openalex", "s2"])
    p.add_argument("--snapshot-date", default=date.today().isoformat(),
                   help="label of the snapshot files; defaults to today (ISO date)")
    p.add_argument("--data-dir", default="data")
    p.add_argument("--max-pages", type=int, default=None, help="limit pages per seed and source (smoke tests only)")
    p.add_argument("--count-only", action="store_true", help="print OpenAlex citer counts per seed and exit")
    p.add_argument("--verbose", action="store_true")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    load_dotenv()
    openalex_key = os.environ.get("OPENALEX_API_KEY") or None
    s2_key = os.environ.get("S2_API_KEY") or None
    if "openalex" in args.sources and not openalex_key:
        log.warning("OPENALEX_API_KEY is empty: cursor paging past the first page will fail with 401")
    if "s2" in args.sources and not s2_key:
        log.warning("S2_API_KEY is empty: expect 429 responses from the shared unauthenticated pool")

    config = yaml.safe_load(Path(args.config).read_text(encoding="utf-8"))
    seeds_cfg = yaml.safe_load(Path(args.seeds).read_text(encoding="utf-8"))
    seeds = [s for s in seeds_cfg["seeds"] if s["group"] in args.groups]

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "results").mkdir(exist_ok=True)
    (out / "logs").mkdir(exist_ok=True)
    frozen = {"base": config, "seeds": seeds_cfg, "args": vars(args)}
    (out / "config.yaml").write_text(yaml.safe_dump(frozen, sort_keys=False), encoding="utf-8")
    (out / "environment.json").write_text(json.dumps(C.environment_snapshot(Path(".")), indent=2), encoding="utf-8")
    (out / "seed.json").write_text(json.dumps({"master_seed": config.get("master_seed"),
                                               "notes": "corpus collection is deterministic given the API state"}, indent=2),
                                   encoding="utf-8")

    oa_cfg = config["apis"]["openalex"]
    s2_cfg = config["apis"]["semanticscholar"]
    oa = C.OpenAlexClient(openalex_key, base_url=oa_cfg["base_url"], per_page=min(100, int(oa_cfg.get("per_page", 100))))
    s2 = C.SemanticScholarClient(s2_key, base_url=s2_cfg["base_url"], limit=min(1000, int(s2_cfg.get("limit", 1000))),
                                 min_interval=float(s2_cfg.get("min_interval_seconds", 1.1)))

    if args.count_only:
        counts = {}
        for s in seeds:
            counts[s["code"]] = oa.count_citers(s["openalex"])
            log.info("%s (%s): %d OpenAlex citers; remaining budget %s", s["code"], s["hypothesis"], counts[s["code"]],
                     oa.last_headers.get("X-RateLimit-Remaining-USD", oa.last_headers.get("x-ratelimit-remaining-usd")))
        all_core = [w for s in seeds if s["group"] == "core" for w in s["openalex"]]
        if all_core:
            counts["union_core"] = oa.count_citers(all_core)
            log.info("union of core seeds: %d distinct OpenAlex citers", counts["union_core"])
        (out / "results" / "counts_openalex_only.json").write_text(json.dumps(counts, indent=2), encoding="utf-8")
        print(json.dumps(counts, indent=2))
        return 0

    candidates: list[C.Candidate] = []
    per_seed_counts: dict[str, dict] = {}
    for s in seeds:
        code = s["code"]
        per_seed_counts[code] = {}
        if "openalex" in args.sources:
            n_meta = oa.count_citers(s["openalex"])
            n = 0
            for rec in oa.iter_citers(s["openalex"], max_pages=args.max_pages):
                candidates.append(C.candidate_from_openalex(rec, code))
                n += 1
            per_seed_counts[code]["openalex_meta_count"] = n_meta
            per_seed_counts[code]["openalex_fetched"] = n
            log.info("%s: OpenAlex meta.count=%d fetched=%d", code, n_meta, n)
        if "s2" in args.sources:
            n = 0
            for item in s2.iter_citations(s["s2"], max_pages=args.max_pages):
                candidates.append(C.candidate_from_s2(item, code))
                n += 1
            per_seed_counts[code]["s2_fetched"] = n
            log.info("%s: Semantic Scholar fetched=%d", code, n)

    entries = C.merge_candidates(candidates)
    all_seeds = seeds_cfg["seeds"] + seeds_cfg.get("recall_check_seeds", [])
    n_seed = C.mark_seeds(entries, [w for s in all_seeds for w in s["openalex"]], [s["s2"] for s in all_seeds])
    log.info("%d entries are seed works themselves (flagged is_seed)", n_seed)
    data_dir = Path(args.data_dir)
    paths = C.write_snapshot(entries, data_dir / "raw", args.snapshot_date)
    checksum_file = C.update_checksums(data_dir, [Path(paths["jsonl"]), Path(paths["manifest"])])
    counts = C.snapshot_counts(entries, candidates)
    core_codes = {s["code"] for s in seeds if s["group"] == "core"}
    counts["entries_citing_core"] = sum(1 for e in entries if core_codes & set(e.seeds_cited))   # the pre-registered union
    counts["entries_aux_only"] = sum(1 for e in entries if not (core_codes & set(e.seeds_cited)))
    counts["per_seed"] = per_seed_counts
    counts["snapshot"] = paths
    counts["checksums"] = str(checksum_file)
    (out / "results" / "counts.json").write_text(json.dumps(counts, indent=2), encoding="utf-8")
    log.info("wrote %d entries to %s", len(entries), paths["jsonl"])
    print(json.dumps({k: v for k, v in counts.items() if k != "per_seed"}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
