#!/usr/bin/env python3
"""
After each run: if any screen row has overlay=Y, or any open position carries a flag, open a GitHub
issue (one per distinct event, no duplicates) so GitHub's own notifications reach Quinny's phone/email.
Runs inside GitHub Actions with GITHUB_TOKEN via the `gh` CLI. Never fails the workflow.
"""
import csv, json, os, subprocess, sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def rows(name):
    p = ROOT / name
    if not p.exists():
        return []
    with open(p, newline="") as f:
        return list(csv.DictReader(f))

def main():
    events = []  # (key, title, body)
    for name, sleeve in (("screen.csv", "equity"), ("screen_macro.csv", "macro")):
        for r in rows(name):
            if r.get("overlay") == "Y":
                key = f"{sleeve} {r['contract']}"
                title = f"ALERT {date.today()}: {sleeve} pick {r['ticker']} {r['contract']} mid {r['mid']}"
                body = (f"{sleeve} screen passed every rule.\n\n"
                        f"- Contract: `{r['contract']}` ({r['expiry']}, {r['dte']} DTE, strike {r['strike']}, type {r['type']})\n"
                        f"- Spot {r['spot']} | add level: {r.get('add_level','')}\n"
                        f"- Bid {r['bid']} / ask {r['ask']} / mid {r['mid']} ({r['risk_pct_of_account']}% of fund), spread {r['spread_pct']}%\n"
                        f"- Delta {r['delta']}, prob ITM {r['prob_itm']}%, OI {r['oi']}, IV {r['iv']}\n"
                        f"- Earnings {r.get('earnings_date','')} (in window: {r.get('earnings_in_window','')})\n\n"
                        f"Routine: limit at the morning mid (<= cap) 9:50-10:30 ET; stop -50%, target +100%, time stop half the DTE. Ask Cowork: \"screen?\"")
                events.append((key, title, body))
    for r in rows("marks.csv"):
        if r.get("flags"):
            key = f"flag {r['contract']} {r['flags']}"
            title = f"ALERT {date.today()}: {r['flags']} on {r['contract']} (mid {r['mid']}, {r['pnl_pct']}%)"
            body = (f"Open position flagged **{r['flags']}**.\n\n- Contract `{r['contract']}`, cost {r['cost']}, mid {r['mid']}, P&L {r['pnl_pct']}% (${r['pnl_total']})\n"
                    f"- Stop {r['stop']} / target {r['target']} / time stop {r['time_stop']}\n\nRule: exit with a limit at mid, no debate. Then tell Cowork: \"log exit: sold ... at ...\"")
            events.append((key, title, body))
    if not events:
        print("alerts: nothing to report"); return
    for key, title, body in events:
        try:
            q = subprocess.run(["gh", "issue", "list", "--state", "open", "--search", f'"{key}" in:body', "--json", "number"],
                               capture_output=True, text=True, timeout=60)
            if q.returncode == 0 and json.loads(q.stdout or "[]"):
                print("alerts: already open:", key); continue
            body_full = body + f"\n\n<!-- alert-key: {key} -->"
            c = subprocess.run(["gh", "issue", "create", "--title", title, "--body", body_full, "--label", "alert"],
                               capture_output=True, text=True, timeout=60)
            if c.returncode != 0:
                # label may not exist yet
                c = subprocess.run(["gh", "issue", "create", "--title", title, "--body", body_full], capture_output=True, text=True, timeout=60)
            print("alerts:", title, "->", (c.stdout or c.stderr).strip()[:120])
        except Exception as e:  # noqa: BLE001
            print("alerts: failed", key, e)

if __name__ == "__main__":
    main()
