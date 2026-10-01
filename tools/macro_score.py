#!/usr/bin/env python3
"""
Macro overlay v1 (Quinny, 2026-09-30): a mechanical 4-test scorecard for macro ETFs (TLT first).
Runs in GitHub Actions before fetch_options.py and writes macro_overlay.csv.

Four tests, each 0-2, total /8. Eligible ("Buy on weakness") = total >= 6 AND trend >= 1.
  T1 Value anchor   - where the 30-yr Treasury yield sits in its trailing window (FRED DGS30):
                      >= 90th percentile = 2, >= 75th = 1, else 0
  T2 Regime         - market-implied Fed path = 63-trading-day change in the 2-yr yield (FRED DGS2):
                      <= -25 bp = 2, -25..+10 bp = 1, > +10 bp = 0
  T3 Impulse        - growth/inflation: +1 if core PCE 3-month annualized <= 3.0% (FRED PCEPILFE),
                      +1 if the unemployment rate rose >= 0.3 pt over 3 months (FRED UNRATE)
  T4 Trend gate     - TLT close > 50-day average AND close >= prior 20-day high = 2;
                      close > 20-day average only = 1; else 0  (never buy a dated call on new lows)
Data: FRED public CSV (no key) + yfinance price history. Every input is written to the CSV so the
score is auditable. No forecasts; only observed numbers.
"""
import csv, json, sys, math
from datetime import date, datetime, timedelta
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parents[1]
FRED = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}"
HEADERS = {"User-Agent": "Mozilla/5.0 (quantfolio-options macro overlay)"}

def fred(sid):
    r = requests.get(FRED.format(sid=sid), headers=HEADERS, timeout=30)
    r.raise_for_status()
    out = []
    for row in csv.reader(r.text.splitlines()):
        if len(row) < 2 or row[0] in ("DATE", "observation_date"):
            continue
        try:
            out.append((date.fromisoformat(row[0]), float(row[1])))
        except ValueError:
            continue  # "." = missing
    if not out:
        raise RuntimeError(f"FRED {sid}: no data")
    return out

def percentile_rank(series_vals, x):
    n = len(series_vals)
    return sum(1 for v in series_vals if v <= x) / n * 100.0

def prices(sym, days=400):
    import yfinance as yf
    h = yf.Ticker(sym).history(period="2y", auto_adjust=False)
    closes = [(d.date(), float(c)) for d, c in zip(h.index, h["Close"]) if not math.isnan(float(c))]
    if len(closes) < 60:
        raise RuntimeError(f"yfinance {sym}: only {len(closes)} closes")
    return closes[-days:]

def score_tlt(rules):
    inp, err = {}, []
    t1 = t2 = t3 = t4 = None
    # T1 value anchor
    try:
        s = fred("DGS30"); cutoff = s[-1][0] - timedelta(days=365 * rules.get("value_window_years", 15))
        win = [v for d, v in s if d >= cutoff]; last = s[-1][1]
        pct = percentile_rank(win, last)
        inp.update(dgs30=last, dgs30_date=s[-1][0].isoformat(), dgs30_pct=round(pct, 1))
        t1 = 2 if pct >= 90 else 1 if pct >= 75 else 0
    except Exception as e:  # noqa: BLE001
        err.append(f"T1:{e}")
    # T2 regime
    try:
        s = fred("DGS2"); last = s[-1][1]; prev = s[-64][1] if len(s) > 64 else s[0][1]
        chg = (last - prev) * 100  # bp
        inp.update(dgs2=last, dgs2_chg_63d_bp=round(chg, 0))
        t2 = 2 if chg <= -25 else 1 if chg <= 10 else 0
    except Exception as e:  # noqa: BLE001
        err.append(f"T2:{e}")
    # T3 impulse
    try:
        p = fred("PCEPILFE"); l = p[-1][1]; l3 = p[-4][1]
        pce3 = ((l / l3) ** 4 - 1) * 100
        u = fred("UNRATE"); uchg = u[-1][1] - u[-4][1]
        inp.update(core_pce_3m_ann=round(pce3, 2), core_pce_date=p[-1][0].isoformat(),
                   unrate=u[-1][1], unrate_chg_3m=round(uchg, 1))
        t3 = (1 if pce3 <= 3.0 else 0) + (1 if uchg >= 0.3 else 0)
    except Exception as e:  # noqa: BLE001
        err.append(f"T3:{e}")
    # T4 trend gate
    try:
        px = prices("TLT"); closes = [c for _, c in px]; last = closes[-1]
        ma20 = sum(closes[-20:]) / 20; ma50 = sum(closes[-50:]) / 50; hi20 = max(closes[-21:-1])
        inp.update(tlt_close=round(last, 2), tlt_date=px[-1][0].isoformat(), tlt_ma20=round(ma20, 2),
                   tlt_ma50=round(ma50, 2), tlt_prior_20d_high=round(hi20, 2))
        t4 = 2 if (last > ma50 and last >= hi20) else 1 if last > ma20 else 0
    except Exception as e:  # noqa: BLE001
        err.append(f"T4:{e}")
    return dict(t1=t1, t2=t2, t3=t3, t4=t4), inp, err

SCORERS = {"TLT": score_tlt}

def main():
    cfg = json.loads((ROOT / "config.json").read_text())
    rules = cfg.get("macro_rules", {})
    min_score, min_trend = rules.get("min_score", 6), rules.get("min_trend", 1)
    rows = []
    for tkr in cfg.get("macro", []):
        fn = SCORERS.get(tkr.upper())
        if not fn:
            rows.append(dict(asof=datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"), ticker=tkr, verdict="no scorer", eligible=""))
            continue
        sc, inp, err = fn(rules)
        known = [v for v in sc.values() if v is not None]
        total = sum(known) if len(known) == 4 else None
        if total is None:
            verdict, elig = "incomplete", ""
        elif total >= min_score and (sc["t4"] or 0) >= min_trend:
            verdict, elig = "Buy on weakness", "Y"
        elif total >= 4:
            verdict, elig = "Hold", ""
        else:
            verdict, elig = "Avoid", ""
        row = dict(asof=datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"), ticker=tkr,
                   t1_value=sc["t1"], t2_regime=sc["t2"], t3_impulse=sc["t3"], t4_trend=sc["t4"],
                   total=total, verdict=verdict, eligible=elig, errors="|".join(err))
        row.update(inp)
        rows.append(row)
    cols = ["asof", "ticker", "t1_value", "t2_regime", "t3_impulse", "t4_trend", "total", "verdict", "eligible",
            "dgs30", "dgs30_date", "dgs30_pct", "dgs2", "dgs2_chg_63d_bp", "core_pce_3m_ann", "core_pce_date",
            "unrate", "unrate_chg_3m", "tlt_close", "tlt_date", "tlt_ma20", "tlt_ma50", "tlt_prior_20d_high", "errors"]
    with open(ROOT / "macro_overlay.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore"); w.writeheader()
        for r in rows:
            w.writerow({c: ("" if r.get(c) is None else r.get(c)) for c in cols})
    # append history
    hist = ROOT / "macro_overlay_history.csv"; new = not hist.exists()
    with open(hist, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        if new: w.writeheader()
        for r in rows: w.writerow({c: ("" if r.get(c) is None else r.get(c)) for c in cols})
    for r in rows:
        print(r["ticker"], r.get("total"), r.get("verdict"), r.get("errors", ""))

if __name__ == "__main__":
    main()
