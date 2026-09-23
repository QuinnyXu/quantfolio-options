# Options experiment — handover (rules v2.1, 2026-09-22)

## Setup
- Account: Robinhood, Level 2 (long calls/puts only; no spreads).
- Experiment fund: $1,000 (`fund_value` in `config.json`, updated after every closed trade).
- Max premium per trade: 25% of `fund_value` ($250 today). If `fund_value` drops below $700 the cap steps down to 15% until it recovers. The premium is the max loss.
- One open experiment position at a time. Skipping a setup while in a trade is intended ("there will be another one").
- VST 160C Jan-15-2027 (cost 8.65, 1 contract) is Trade 0, tracked but outside the experiment. Don't repeat its shape (115-DTE OTM call on a multi-year value thesis).
- Data + journal repo (public): https://github.com/QuinnyXu/quantfolio-options
- Local folder `C:\Users\xkxuq\Documents\Starup\quantfolio-options` is Cowork's working folder. Claude edits files there; Quinny runs the one-line commit + push Claude hands over. Git from the sandbox only with `--no-optional-locks`; stray `.git/*.lock` files can be deleted.
- Fundamental overlay: `Quantfolio_Index.csv` in the Quantfolio Tracker folder (schema v3). No company-insight files in this public repo.

## Automation (GitHub Actions, no manual steps)
Runs weekdays 9:50 am, 12:05 pm, 4:25 pm ET (cron in UTC; shifts +1h after Nov 1 — adjust then). Also runs on any push to `config.json`, `positions.csv`, `fetch_options.py`, or the workflow.
Source: CBOE delayed quotes (15 min), yfinance fallback. Greeks from CBOE or Black-Scholes. Earnings dates from yfinance (blank if unavailable).

Outputs (raw URL base `https://raw.githubusercontent.com/QuinnyXu/quantfolio-options/main/`):
- `marks.csv` — each open position: mid, Greeks, P&L, break-even, `earnings_date`, flags `STOP_HIT` / `TARGET_HIT` / `TIME_STOP`
- `marks_history.csv` — the same, appended every run
- `screen.csv` — long-option candidates: 60–180 DTE, premium $0.30 to the active cap, OI ≥300, spread ≤10%, |delta| 0.35–0.55; `in_pool=Y` marks Quinny's names; `earnings_in_window` says whether earnings fall before expiry
- `snapshots/<date>/<TICKER>.csv` — trimmed chain history
- `journal.csv`, `positions.csv`, `config.json`, `status.json` (run time, sources, active cap, errors)

Pool: every company in `Quantfolio_Index.csv` with score ≥ 20 and no forensic KILL (47 names on 2026-09-22), rebuilt with `python tools/build_pool.py` after any index change. Watchlist is empty; no speculative names.
Note: most pool names price beyond the cap at these deltas; the reachable set is roughly the sub-$130 names (UBER, NYT, T, KO, SO, EW, NEE, AEP, TJX, BSY, NFLX, CSCO). NOW, ADSK, NVDA and the other large names are share-only at this fund size.

## Daily routine
1. Evening (after 4:25 pm run): in Cowork, ask "screen?" → Claude reads `screen.csv` + `marks.csv`, applies the Quantfolio overlay, returns ONE pick or "no trade" with entry (limit at mid), stop (−50%), target (+100%), time stop (half the DTE at entry). Most evenings the answer is "no trade".
2. Morning 9:50–10:30 ET: place the limit order in Robinhood. No market orders.
3. Log it in Cowork: "log trade: bought <TICKER> <expiry> <strike><C/P> at <price>, 1 contract" → Claude appends `journal.csv`, adds the row to `positions.csv`, hands over the commit command. The push re-runs the marks.
4. Noon and close: if `marks.csv` shows a flag, exit. No debate. Then "log exit: sold ... at ..." → Claude sets `status=closed`, fills pnl, updates `fund_value` in `config.json`, hands over the commit command.
5. Journal fields: id, dates, ticker, strategy, contract, qty, entry/exit, max_loss, delta & prob at entry, thesis, exit_rule, pnl, rule_violation, feeling, lesson.

## Rules (fixed until graduation)
- Sizing: 25% of fund per trade (15% below $700), one open experiment position, one contract, limit at mid.
- Overlay gate: the ticker must have a `Quantfolio_Index.csv` row whose verdict is Buy / Buy on weakness (for calls) or Sell / Trim (for puts). No row → not tradable until scored ("quantfolio <ticker>").
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
