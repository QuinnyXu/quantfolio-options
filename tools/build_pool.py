#!/usr/bin/env python3
"""Rebuild the `pool` in config.json from the private Quantfolio_Index.csv.

Rules (Quinny, 2026-09-22/23):
  pool    = score >= 20 and forensic_severity != KILL          (snapshotted + screened)
  overlay = pool members whose verdict starts with Buy, with their add_level
            (tradable only while spot <= add_level; the GitHub run checks this)
The index lives outside this public repo; only ticker lists are written here.

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
    pool, overlay = [], {}
    for r in rows:
        try:
            score = float(r.get("score") or 0)
        except ValueError:
            continue
        if score >= MIN_SCORE and "KILL" not in (r.get("forensic_severity") or "").upper():
            t = r["ticker"].strip().upper()
            pool.append(t)
            if (r.get("verdict") or "").strip().lower().startswith("buy"):
                try:
                    overlay[t] = float(r.get("add_level") or 0) or None
                except ValueError:
                    overlay[t] = None
    pool = sorted(set(pool))
    overlay = {t: overlay[t] for t in sorted(overlay)}
    cfg_path = ROOT / "config.json"
    cfg = json.loads(cfg_path.read_text())
    old = cfg.get("pool", [])
    cfg["pool"] = pool
    cfg["pool_rule"] = f"Quantfolio_Index.csv: score >= {MIN_SCORE} and forensic_severity != KILL (rebuilt by tools/build_pool.py)"
    cfg["overlay"] = overlay
    cfg["overlay_rule"] = ("pool members whose Quantfolio verdict is Buy / Buy on weakness, with add_level; "
                           "screen.csv overlay=Y means verdict Buy AND spot <= add_level AND every numeric rule; "
                           "a null add_level means not tradable until scored")
    cfg_path.write_text(json.dumps(cfg, indent=2) + "\n")
    print(f"pool: {len(pool)} tickers (was {len(old)})")
    print("added:", sorted(set(pool) - set(old)) or "-")
    print("removed:", sorted(set(old) - set(pool)) or "-")
    print(f"overlay: {len(overlay)} tickers:", " ".join(f"{t}<={overlay[t]}" for t in overlay))

if __name__ == "__main__":
    main()
