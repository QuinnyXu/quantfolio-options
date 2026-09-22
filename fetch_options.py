#!/usr/bin/env python3
"""
quantfolio-options: end-of-day option data pipeline.

Runs in GitHub Actions. Pulls delayed option chains (CBOE JSON first,
yfinance fallback), then writes:
  marks.csv                    - every contract in positions.csv, marked with Greeks & P&L
  screen.csv                   - long-option candidates for the small-account experiment
  snapshots/<date>/<TICKER>.csv- trimmed chain history
  status.json                  - run metadata (timestamp, source per ticker, errors)

Config lives in config.json. No credentials anywhere.
"""
import csv
import json
import math
import os
import sys
from datetime import date, datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent
CBOE_URL = "https://cdn.cboe.com/api/global/delayed_quotes/options/{sym}.json"
HEADERS = {"User-Agent": "Mozilla/5.0 (quantfolio-options; +https://github.com)"}

# --------------------------------------------------------------------------- #
# Black-Scholes (used when the source has no Greeks, and for POP estimates)
# --------------------------------------------------------------------------- #
def _n(x):
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))

def _pdf(x):
    return math.exp(-0.5 * x * x) / math.sqrt(2.0 * math.pi)

def bs_greeks(S, K, T, sigma, opt_type, r=0.04):
    """Return dict(theo, delta, gamma, theta_per_day, vega_per_1pct)."""
    if S <= 0 or K <= 0 or T <= 0 or sigma <= 0:
        return dict(theo=None, delta=None, gamma=None, theta=None, vega=None)
    sq = sigma * math.sqrt(T)
    d1 = (math.log(S / K) + (r + 0.5 * sigma * sigma) * T) / sq
    d2 = d1 - sq
    disc = math.exp(-r * T)
    if opt_type == "C":
        theo = S * _n(d1) - K * disc * _n(d2)
        delta = _n(d1)
        theta = (-S * _pdf(d1) * sigma / (2 * math.sqrt(T)) - r * K * disc * _n(d2)) / 365.0
    else:
        theo = K * disc * _n(-d2) - S * _n(-d1)
        delta = _n(d1) - 1.0
        theta = (-S * _pdf(d1) * sigma / (2 * math.sqrt(T)) + r * K * disc * _n(-d2)) / 365.0
    gamma = _pdf(d1) / (S * sq)
    vega = S * _pdf(d1) * math.sqrt(T) / 100.0
    return dict(theo=theo, delta=delta, gamma=gamma, theta=theta, vega=vega)

def prob_itm(S, K, T, sigma, opt_type, r=0.04):
    if S <= 0 or K <= 0 or T <= 0 or sigma <= 0:
        return None
    sq = sigma * math.sqrt(T)
    d2 = (math.log(S / K) + (r - 0.5 * sigma * sigma) * T) / sq
    return _n(d2) if opt_type == "C" else _n(-d2)

# --------------------------------------------------------------------------- #
# OCC symbol helpers
# --------------------------------------------------------------------------- #
def parse_occ(sym):
    """'VST270115C00160000' -> (root, expiry date, type, strike)."""
    sym = sym.strip().upper().replace(" ", "")
    root = sym[:-15]
    yymmdd, cp, strike = sym[-15:-9], sym[-9], sym[-8:]
    exp = datetime.strptime(yymmdd, "%y%m%d").date()
    return root, exp, cp, int(strike) / 1000.0

def make_occ(root, exp, cp, strike):
    return f"{root.upper()}{exp.strftime('%y%m%d')}{cp}{int(round(strike * 1000)):08d}"

# --------------------------------------------------------------------------- #
# Data sources
# --------------------------------------------------------------------------- #
def fetch_cboe(sym):
    r = requests.get(CBOE_URL.format(sym=sym.upper()), headers=HEADERS, timeout=30)
    r.raise_for_status()
    js = r.json()
    data = js.get("data", js)
    spot = float(data.get("current_price") or data.get("close") or 0)
    rows = []
    for o in data.get("options", []):
        try:
            root, exp, cp, strike = parse_occ(o["option"])
        except Exception:
            continue
        rows.append(dict(
            contract=o["option"].upper(), ticker=root, expiry=exp.isoformat(), type=cp,
            strike=strike,
            bid=_f(o.get("bid")), ask=_f(o.get("ask")), last=_f(o.get("last_trade_price")),
            iv=_f(o.get("iv")), delta=_f(o.get("delta")), gamma=_f(o.get("gamma")),
            theta=_f(o.get("theta")), vega=_f(o.get("vega")),
            volume=_i(o.get("volume")), oi=_i(o.get("open_interest")),
        ))
    if not rows:
        raise RuntimeError("CBOE returned no options")
    return spot, rows, "cboe"

def fetch_yf(sym):
    import yfinance as yf  # imported lazily so CBOE-only runs stay light
    t = yf.Ticker(sym)
    spot = None
    try:
        spot = float(t.fast_info["last_price"])
    except Exception:
        hist = t.history(period="1d")
        if len(hist):
            spot = float(hist["Close"].iloc[-1])
    if not spot:
        raise RuntimeError("yfinance: no spot")
    rows = []
    for exp_str in t.options:
        try:
            ch = t.option_chain(exp_str)
        except Exception:
            continue
        exp = datetime.strptime(exp_str, "%Y-%m-%d").date()
        for cp, df in (("C", ch.calls), ("P", ch.puts)):
            for _, o in df.iterrows():
                rows.append(dict(
                    contract=str(o["contractSymbol"]).upper(), ticker=sym.upper(),
                    expiry=exp.isoformat(), type=cp, strike=float(o["strike"]),
                    bid=_f(o.get("bid")), ask=_f(o.get("ask")), last=_f(o.get("lastPrice")),
                    iv=_f(o.get("impliedVolatility")), delta=None, gamma=None,
                    theta=None, vega=None,
                    volume=_i(o.get("volume")), oi=_i(o.get("openInterest")),
                ))
    if not rows:
        raise RuntimeError("yfinance returned no options")
    return spot, rows, "yfinance"

def fetch_chain(sym, errors):
    for fn in (fetch_cboe, fetch_yf):
        try:
            return fn(sym)
        except Exception as e:  # noqa: BLE001
            errors.append(f"{sym}:{fn.__name__}:{type(e).__name__}:{str(e)[:120]}")
    return None, [], None

# --------------------------------------------------------------------------- #
# Enrichment
# --------------------------------------------------------------------------- #
def enrich(rows, spot, today):
    for o in rows:
        exp = date.fromisoformat(o["expiry"])
        o["dte"] = (exp - today).days
        bid, ask = o.get("bid") or 0.0, o.get("ask") or 0.0
        o["mid"] = round((bid + ask) / 2, 4) if bid and ask else (o.get("last") or None)
        o["spread_pct"] = round((ask - bid) / o["mid"] * 100, 1) if (o["mid"] and bid and ask) else None
        o["spot"] = spot
        o["moneyness_pct"] = round((o["strike"] / spot - 1) * 100, 2) if spot else None
        T = max(o["dte"], 0) / 365.0
        iv = o.get("iv")
        if iv and iv > 3:      # CBOE sometimes reports IV in percent
            iv = iv / 100.0
            o["iv"] = iv
        if iv and T > 0:
            g = bs_greeks(spot, o["strike"], T, iv, o["type"])
            for k in ("delta", "gamma", "theta", "vega"):
                if o.get(k) is None and g[k] is not None:
                    o[k] = round(g[k], 5)
            o["theo"] = round(g["theo"], 4) if g["theo"] is not None else None
            p = prob_itm(spot, o["strike"], T, iv, o["type"])
            o["prob_itm"] = round(p * 100, 1) if p is not None else None
        else:
            o.setdefault("theo", None)
            o.setdefault("prob_itm", None)
    return rows

# --------------------------------------------------------------------------- #
# Outputs
# --------------------------------------------------------------------------- #
CHAIN_COLS = ["contract", "ticker", "expiry", "dte", "type", "strike", "moneyness_pct", "spot",
              "bid", "ask", "mid", "last", "spread_pct", "iv", "delta", "gamma", "theta", "vega",
              "theo", "prob_itm", "volume", "oi"]

def write_csv(path, rows, cols):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({c: ("" if r.get(c) is None else r.get(c)) for c in cols})

def read_positions():
    p = ROOT / "positions.csv"
    if not p.exists():
        return []
    with open(p, newline="") as f:
        return [r for r in csv.DictReader(f) if r.get("contract", "").strip() and r.get("status", "open").strip().lower() != "closed"]

def build_marks(positions, chains, today, run_ts):
    out = []
    for pos in positions:
        c = pos["contract"].strip().upper()
        root, exp, cp, strike = parse_occ(c)
        chain = chains.get(root)
        row = dict(asof=run_ts, contract=c, ticker=root, expiry=exp.isoformat(), type=cp, strike=strike,
                   qty=pos.get("qty", ""), cost=pos.get("cost", ""), opened=pos.get("opened", ""),
                   stop=pos.get("stop", ""), target=pos.get("target", ""), time_stop=pos.get("time_stop", ""),
                   note=pos.get("note", ""))
        if not chain:
            row["error"] = "no chain"
            out.append(row)
            continue
        spot, rows = chain
        m = next((o for o in rows if o["contract"] == c), None)
        if m is None:
            m = next((o for o in rows if o["expiry"] == exp.isoformat() and o["type"] == cp and abs(o["strike"] - strike) < 1e-6), None)
        if m is None:
            row["error"] = "contract not in chain"
            out.append(row)
            continue
        row.update({k: m.get(k) for k in ("spot", "dte", "bid", "ask", "mid", "last", "spread_pct", "iv",
                                            "delta", "gamma", "theta", "vega", "theo", "prob_itm", "volume", "oi",
                                            "moneyness_pct")})
        try:
            qty, cost, mid = float(pos.get("qty") or 1), float(pos["cost"]), float(m["mid"])
            row["pnl_per_contract"] = round(mid - cost, 2)
            row["pnl_pct"] = round((mid / cost - 1) * 100, 1)
            row["pnl_total"] = round((mid - cost) * 100 * qty, 2)
            row["breakeven"] = round(strike + cost if cp == "C" else strike - cost, 2)
            row["breakeven_move_pct"] = round((row["breakeven"] / spot - 1) * 100, 1)
            flags = []
            if pos.get("stop") and mid <= float(pos["stop"]):
                flags.append("STOP_HIT")
            if pos.get("target") and mid >= float(pos["target"]):
                flags.append("TARGET_HIT")
            if pos.get("time_stop") and today >= date.fromisoformat(pos["time_stop"]):
                flags.append("TIME_STOP")
            row["flags"] = "|".join(flags)
        except Exception as e:  # noqa: BLE001
            row["error"] = f"calc:{e}"
        out.append(row)
    return out

MARK_COLS = ["asof", "contract", "ticker", "expiry", "dte", "type", "strike", "qty", "cost", "opened", "spot",
             "moneyness_pct", "bid", "ask", "mid", "last", "spread_pct", "pnl_per_contract", "pnl_pct", "pnl_total",
             "breakeven", "breakeven_move_pct", "iv", "delta", "gamma", "theta", "vega", "theo", "prob_itm",
             "volume", "oi", "stop", "target", "time_stop", "flags", "note", "error"]

def build_screen(cfg, chains):
    s = cfg["screen"]
    out = []
    for tkr, (spot, rows) in chains.items():
        if not spot or spot > s["max_underlying_price"]:
            continue
        for o in rows:
            if o["type"] not in s["types"]:
                continue
            if not (s["min_dte"] <= o["dte"] <= s["max_dte"]):
                continue
            if o["mid"] is None or o["mid"] > s["max_premium"] or o["mid"] < s["min_premium"]:
                continue
            if (o.get("oi") or 0) < s["min_oi"]:
                continue
            if o["spread_pct"] is None or o["spread_pct"] > s["max_spread_pct"]:
                continue
            d = abs(o.get("delta") or 0)
            if not (s["min_abs_delta"] <= d <= s["max_abs_delta"]):
                continue
            o2 = dict(o)
            o2["max_loss"] = round(o["mid"] * 100, 2)
            o2["score"] = round(d * 100 - (o["spread_pct"] or 0), 1)
            out.append(o2)
    out.sort(key=lambda r: (-r["score"], r["spread_pct"] or 99))
    return out[: s["max_rows"]]

SCREEN_COLS = ["ticker", "contract", "expiry", "dte", "type", "strike", "moneyness_pct", "spot", "bid", "ask", "mid",
               "max_loss", "spread_pct", "iv", "delta", "theta", "prob_itm", "volume", "oi", "score"]

# --------------------------------------------------------------------------- #
def _f(x):
    try:
        v = float(x)
        return None if math.isnan(v) else v
    except (TypeError, ValueError):
        return None

def _i(x):
    try:
        v = float(x)
        return 0 if math.isnan(v) else int(v)
    except (TypeError, ValueError):
        return 0

def main():
    cfg = json.loads((ROOT / "config.json").read_text())
    today = date.today()
    run_ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    positions = read_positions()
    tickers = {parse_occ(p["contract"])[0] for p in positions}
    tickers |= {t.strip().upper() for t in cfg.get("watchlist", []) if t.strip()}

    errors, chains, sources = [], {}, {}
    snap = cfg["snapshot"]
    for tkr in sorted(tickers):
        spot, rows, src = fetch_chain(tkr, errors)
        if not rows:
            continue
        rows = enrich(rows, spot, today)
        chains[tkr] = (spot, rows)
        sources[tkr] = src
        lo, hi = spot * (1 - snap["strike_band_pct"] / 100), spot * (1 + snap["strike_band_pct"] / 100)
        trimmed = [o for o in rows if snap["min_dte"] <= o["dte"] <= snap["max_dte"] and lo <= o["strike"] <= hi]
        write_csv(ROOT / "snapshots" / today.isoformat() / f"{tkr}.csv", trimmed, CHAIN_COLS)

    marks = build_marks(positions, chains, today, run_ts)
    write_csv(ROOT / "marks.csv", marks, MARK_COLS)
    # append marks to history so theta bleed is visible over time
    hist = ROOT / "marks_history.csv"
    new = not hist.exists()
    with open(hist, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=MARK_COLS, extrasaction="ignore")
        if new:
            w.writeheader()
        for r in marks:
            w.writerow({c: ("" if r.get(c) is None else r.get(c)) for c in MARK_COLS})

    write_csv(ROOT / "screen.csv", build_screen(cfg, chains), SCREEN_COLS)

    status = dict(asof=run_ts, date=today.isoformat(), tickers=sorted(tickers), sources=sources,
                  spots={t: chains[t][0] for t in chains}, errors=errors)
    (ROOT / "status.json").write_text(json.dumps(status, indent=2))
    print(json.dumps(status, indent=2))
    if not chains:
        sys.exit(1)

if __name__ == "__main__":
    main()
