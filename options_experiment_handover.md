# Options experiment — handover (rules v2.1, 2026-09-22)

## Setup
- Account: Robinhood, Level 2. Experiment trades are long calls only; no puts (we don't use this fund to bet against good firms), no spreads.
- Experiment fund: $1,000 (`fund_value` in `config.json`, updated after every closed trade).
- Max premium per trade: 25% of `fund_value` ($250 today). If `fund_value` drops below $700 the cap steps down to 15% until it recovers. The premium is the max loss.
- One open experiment position at a time. Skipping a setup while in a trade is intended ("there will be another one").
- VST 160C Jan-15-2027 (cost 8.65, 1 contract) is Trade 0, tracked but outside the experiment. Don't repeat its shape (115-DTE OTM call on a multi-year value thesis).
- Data + journal repo (public): https://github.com/QuinnyXu/quantfolio-options
- Local folder `C:\Users\xkxuq\Documents\Starup\quantfolio-options` is Cowork's working folder. Claude edits files there; Quinny runs the one-line commit + push Claude hands over. Git from the sandbox only with `--no-optional-locks`; stray `.git/*.lock` files can be deleted.
- Fundamental overlay: `Quantfolio_Index.csv` in the Quantfolio Tracker folder (schema v3). No company-insight files in this public repo.

## Automation (GitHub Actions, no manual steps)
Runs weekdays at **11:25 am and 3:25 pm ET** (cron 15:25 / 19:25 UTC while on EDT; shift to 16:25 / 20:25 UTC after Nov 1). GitHub's queue adds 20–90 minutes, so expect the first to land around noon–1 pm (the exit check) and the second around 3:45–5 pm (the closing read for the evening pick). Also runs on any push to `config.json`, `positions.csv`, `fetch_options.py`, `tools/macro_score.py`, or the workflow; "Run workflow" on the Actions page runs it on demand.
Source: yfinance (~15 min delayed) for open positions, overlay names and TLT; CBOE for nothing that matters any more. Greeks from Black-Scholes. Earnings dates from yfinance (blank if unavailable).
**Alerts:** after every run, `tools/alerts.py` opens a GitHub issue (title starts with `ALERT`) when a screen row has `overlay=Y` or an open position carries a flag — one issue per event, no duplicates. Turn on GitHub notifications for the repo (mobile app or email) and a buzz means something passed every rule; silence means nothing to do.

Outputs (raw URL base `https://raw.githubusercontent.com/QuinnyXu/quantfolio-options/main/`):
- `marks.csv` — each open position: mid, Greeks, P&L, break-even, `earnings_date`, flags `STOP_HIT` / `TARGET_HIT` / `TIME_STOP`
- `marks_history.csv` — the same, appended every run
- `screen_macro.csv` — macro-sleeve candidates (TLT) under the same numeric filters; `overlay=Y` = macro scorecard eligible
- `macro_overlay.csv` / `macro_overlay_history.csv` — the 4-test macro scorecard with every input (FRED + price data)
- `screen.csv` — long-call candidates on overlay names only: 60–180 DTE, premium $0.30 to the active cap, OI ≥300, spread ≤10%, delta 0.35–0.55. `overlay=Y` means the row meets every rule, including the Quantfolio gate: verdict Buy / Buy on weakness AND spot ≤ `add_level` (shown in the row). Rows without Y are overlay names currently above their add level (near-misses, not tradable); `earnings_in_window` says whether earnings fall before expiry
- `snapshots/<date>/<TICKER>.csv` — trimmed chain history
- `journal.csv`, `positions.csv`, `config.json`, `status.json` (run time, sources, active cap, errors)

Universe: `tools/build_pool.py` reads the private `Quantfolio_Index.csv` and writes two ticker lists to `config.json`: `pool` (score ≥ 20, no forensic KILL — reference only) and `overlay` (pool members whose verdict is Buy / Buy on weakness, each with its `add_level`). The run fetches only the overlay names plus open positions; Trim/Hold names are never fetched because they can never be a trade. Re-run the script after any index change.
Note: most overlay names price beyond the cap at these deltas (NOW, ADSK, NVDA, AVGO, GOOGL, AMZN, VEEV, INTU are share-only at this fund size); in practice UBER, NYT, PTC and VST are the ones that can fit.

## Macro sleeve (v1, added 2026-09-30, two-sided 2026-10-01) — TLT
A second, separate screen for macro ETFs, starting with TLT (long Treasuries). It does **not** use the good-firm framework; it uses a mechanical 4-test scorecard (`tools/macro_score.py`, written to `macro_overlay.csv` every run, history in `macro_overlay_history.csv`). Because TLT is not a good firm, **both directions are allowed**: a bull scorecard (calls) and a mirrored bear scorecard (puts) from the same inputs.
- T1 Value anchor: 30-yr yield percentile in its 15-yr window. Bull: ≥90th = 2, ≥75th = 1. Bear: ≤10th = 2, ≤25th = 1.
- T2 Regime: 63-day change in the 2-yr yield (the market's Fed path). Bull: ≤ −25 bp = 2, −25..+10 = 1. Bear: ≥ +25 bp = 2, ≥ −10 = 1.
- T3 Impulse: Bull: +1 if core PCE 3-mo annualized ≤ 3.0%, +1 if unemployment rose ≥ 0.3 pt in 3 months. Bear: +1 if core PCE ≥ 3.5%, +1 if unemployment flat or lower.
- T4 Trend gate: Bull: TLT above its 50-day average and at/above its prior 20-day high = 2; above the 20-day only = 1. Bear: below the 50-day and at/below its prior 20-day low = 2; below the 20-day only = 1.
Eligible = total ≥ 6 **and** trend ≥ 1 **and** value ≥ 1 on that side — never a dated option against the trend, and never chasing the extreme (no puts at record-high yields, no calls at record-low yields). `screen_macro.csv` lists TLT calls and puts that pass the same numeric filters; `overlay=Y` marks the side the scorecard allows, and the `add_level` column shows the scores (e.g. `macro bull/bear 6/2 Buy calls`).
Rules: same fund, same cap, same exits (stop −50%, target +100%, time stop half the DTE). **One open position across both sleeves.** Macro trades are logged in `journal.csv` with `layer=macro`; they are reviewed separately after 10 trades and do not count toward the equity sleeve's 20-trade gate. Data: FRED public CSVs first; when FRED times out (GitHub runners often can't reach it) the script falls back to Yahoo's ^TYX for the 30-yr yield, the Treasury's daily par-yield CSV for the 2-yr, and the BLS public API for core CPI (stand-in for core PCE, same thresholds) and unemployment. The source used is written beside each input in `macro_overlay.csv`. Extension to IAU/GDX needs a gold scorer (not written yet).

## Daily routine
1. Evening (after 4:25 pm run): in Cowork, ask "screen?" → Claude reads `screen.csv` + `marks.csv`, applies the Quantfolio overlay, returns ONE pick or "no trade" with entry (limit at mid), stop (−50%), target (+100%), time stop (half the DTE at entry). Most evenings the answer is "no trade".
2. Morning 9:50–10:30 ET: place the limit order in Robinhood. No market orders.
3. Log it in Cowork: "log trade: bought <TICKER> <expiry> <strike><C/P> at <price>, 1 contract" → Claude appends `journal.csv`, adds the row to `positions.csv`, hands over the commit command. The push re-runs the marks.
4. Noon and close: if `marks.csv` shows a flag, exit. No debate. Then "log exit: sold ... at ..." → Claude sets `status=closed`, fills pnl, updates `fund_value` in `config.json`, hands over the commit command.
5. Journal fields: id, dates, ticker, strategy, contract, qty, entry/exit, max_loss, delta & prob at entry, thesis, exit_rule, pnl, rule_violation, feeling, lesson.

## Rules (fixed until graduation)
- Sizing: 25% of fund per trade (15% below $700), one open experiment position, one contract, limit at mid.
- Overlay gate: the ticker's `Quantfolio_Index.csv` verdict is Buy / Buy on weakness AND the current price is at or below its `add_level` (the framework's own definition of "weakness"). Calls only; Trim/Exit/Hold names are not traded. No row, a v1 row, or no add level → not tradable until scored ("quantfolio <ticker>").
- Earnings inside the window must be named in the thesis; it is allowed, not hidden.
- Exits are mechanical: stop −50%, target +100%, time stop at half the DTE at entry.
- VST 160C: stop 4.30, target 13.00, time stop 2026-12-01; decide before Q3 earnings (early Nov) whether to hold through.
- Graduation gate before changing size: 20 logged trades, no rule violations, positive expectancy.
- Why these numbers: a selective long-option process still stops out roughly 40–50% of the time (timing, not direction). With +100% / −50% payoffs that is about +17% expectancy per trade and a growth-optimal size near 35% of fund; 25% is a deliberate haircut, and the step-down protects the 20-trade sample.
- Claude is not a financial advisor; it grades setups against the rules and Quinny places every order.

## Channel roles
- Cowork (Project "quantfolio", working folder above): analysis, picks, screen/marks reading, journal/positions/config edits, commit commands.
- Code (claude.ai/code): optional, for larger code changes to `fetch_options.py` or the workflow.

## Positions.csv format
`contract,qty,cost,opened,stop,target,time_stop,status,note` — OCC symbol e.g. `VST270115C00160000`.
