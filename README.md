# quantfolio-options

End-of-day option data + trade journal for the small-account experiment. Runs on GitHub Actions; no credentials, no manual pasting.

## Files
| File | Purpose |
|---|---|
| `positions.csv` | Contracts to mark every run (OCC symbol, cost, stop/target/time-stop). Set `status=closed` to stop tracking. |
| `config.json` | Pool for snapshots (rebuilt from the private Quantfolio index by `tools/build_pool.py`: score ≥ 20, no forensic KILL) + screen filter thresholds. |
| `marks.csv` | Latest mark, Greeks, P&L and rule flags (`STOP_HIT`, `TARGET_HIT`, `TIME_STOP`) per open position. |
| `marks_history.csv` | Same, appended every run (theta bleed over time). |
| `screen.csv` | Long-option candidates passing the v2.1 filter (60–180 DTE, premium ≤ cap, delta 0.35–0.55), best first, with earnings date. |
| `snapshots/<date>/<TICKER>.csv` | Trimmed chain history. |
| `journal.csv` | Trade journal. Claude drafts rows; Quinny commits. |
| `status.json` | Run timestamp, active risk cap, data source per ticker, errors. |

Data: CBOE delayed quotes (15 min) with yfinance fallback. Greeks come from CBOE when present, otherwise Black-Scholes from IV.

## One-time setup
1. Create a **public** repo `quantfolio-options` on GitHub (public so Claude can read raw files without a token).
2. Unzip this bundle into it, then:
   ```powershell
   cd <folder>; git init; git add -A; git commit -m "init"; git branch -M main; git remote add origin https://github.com/QuinnyXu/quantfolio-options.git; git push -u origin main
   ```
3. Repo → Settings → Actions → General → Workflow permissions → **Read and write** → Save.
4. Actions tab → `options-eod` → **Run workflow** once to verify. Check `status.json` for `sources` and `errors`.
5. Add to the Project notes: `Options data: https://raw.githubusercontent.com/QuinnyXu/quantfolio-options/main/`

## Schedule
Weekdays 13:50, 16:05 and 20:25 UTC (≈9:50 am, 12:05 pm, 4:25 pm EDT; one hour later in ET after Nov 1). Change in `.github/workflows/options.yml`.

## Rules (v2.1)
- Experiment fund: $1,000 (`fund_value` in `config.json`). Max premium per trade 25% of the fund; 15% while the fund is below $700. The premium is the max loss.
- One open experiment position at a time, one contract, limit orders only. The VST 160C is tracked separately, not counted.
- Screen: calls only, 60–180 DTE, delta 0.35–0.55, OI ≥ 300, spread ≤ 10%. Exits: stop −50%, target +100%, time stop at half the DTE at entry.
- A pick also needs a Buy / Buy-on-weakness verdict in the Quantfolio index (kept outside this repo).
- Pool names above ~$150 price beyond the cap at these deltas, so the screen mostly covers the watchlist plus UBER/NYT. `earnings_in_window` flags contracts whose expiry is after the next earnings date.
- Full rules and routine: `options_experiment_handover.md`.

## Adding a position
Append a row to `positions.csv`. OCC symbol format: `TICKER` + `YYMMDD` + `C|P` + strike×1000 padded to 8 digits, e.g. `VST270115C00160000`.

## Claude's read path
```
curl -s https://raw.githubusercontent.com/QuinnyXu/quantfolio-options/main/marks.csv
curl -s https://raw.githubusercontent.com/QuinnyXu/quantfolio-options/main/screen.csv
```
