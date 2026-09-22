# quantfolio-options

End-of-day option data + trade journal for the small-account experiment. Runs on GitHub Actions; no credentials, no manual pasting.

## Files
| File | Purpose |
|---|---|
| `positions.csv` | Contracts to mark every run (OCC symbol, cost, stop/target/time-stop). Set `status=closed` to stop tracking. |
| `config.json` | Watchlist for snapshots + screen filter thresholds. |
| `marks.csv` | Latest mark, Greeks, P&L and rule flags (`STOP_HIT`, `TARGET_HIT`, `TIME_STOP`) per open position. |
| `marks_history.csv` | Same, appended every run (theta bleed over time). |
| `screen.csv` | Long-option candidates passing the Level-2 filter, best first. |
| `snapshots/<date>/<TICKER>.csv` | Trimmed chain history. |
| `journal.csv` | Trade journal. Claude drafts rows; Quinny commits. |
| `status.json` | Run timestamp, data source per ticker, errors. |

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
Weekdays 20:25 UTC (≈4:25 pm ET) and 16:05 UTC (≈12:05 pm ET). Change in `.github/workflows/options.yml`.

## Adding a position
Append a row to `positions.csv`. OCC symbol format: `TICKER` + `YYMMDD` + `C|P` + strike×1000 padded to 8 digits, e.g. `VST270115C00160000`.

## Claude's read path
```
curl -s https://raw.githubusercontent.com/QuinnyXu/quantfolio-options/main/marks.csv
curl -s https://raw.githubusercontent.com/QuinnyXu/quantfolio-options/main/screen.csv
```
