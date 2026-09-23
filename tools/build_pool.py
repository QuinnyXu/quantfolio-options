#!/usr/bin/env python3
"""Rebuild the `pool` in config.json from the private Quantfolio_Index.csv.

Rule (Quinny, 2026-09-22): score >= 20 and forensic_severity != KILL.
The index lives outside this public repo; only the resulting ticker list is written here.

Usage:  python tools/build_pool.py [path/to/Quantfolio_Index.csv]
Default path: ../Quantfolio Tracker/Quantfolio_Index.csv (sibling folder).
"""
import csv, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MIN_SCORE = 20

def main():
    idx = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT.parent / "Quantfolio Tracker" / "Quantfolio_Index.csv"
    rows = list(csv.DictReader(open(idx, newline="", encoding="utf-8")))
    pool = []
    for r in rows:
        try:
            score = float(r.get("score") or 0)
        except ValueError:
            continue
        if score >= MIN_SCORE and "KILL" not in (r.get("forensic_severity") or "").upper():
            pool.append(r["ticker"].strip().upper())
    pool = sorted(set(pool))
    cfg_path = ROOT / "config.json"
    cfg = json.loads(cfg_path.read_text())
    old = cfg.get("pool", [])
    cfg["pool"] = pool
    cfg["pool_rule"] = f"Quantfolio_Index.csv: score >= {MIN_SCORE} and forensic_severity != KILL (rebuilt by tools/build_pool.py)"
    cfg_path.write_text(json.dumps(cfg, indent=2) + "\n")
    print(f"pool: {len(pool)} tickers (was {len(old)})")
    print("added:", sorted(set(pool) - set(old)) or "-")
    print("removed:", sorted(set(old) - set(pool)) or "-")

if __name__ == "__main__":
    main()
