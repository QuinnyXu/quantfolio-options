# Options experiment — Cowork working notes (updated 2026-09-22 late)

Mirrored from the Claude Project doc `claude/options-experiment-notes.md` (Quinny's request). On every push, Claude rewrites this file from that doc so both stay identical. Human-facing rulebook: `../options_experiment_handover.md`.

Source of truth: `options_experiment_handover.md` in `C:\Users\xkxuq\Documents\Starup\quantfolio-options` (repo `QuinnyXu/quantfolio-options`, public). **That folder is Cowork's working folder**: Claude edits files there directly and ends with a single-line PowerShell commit+push for Quinny. Claude cannot push (no GitHub credentials in the sandbox shell — verified). Code channel parked. After Quinny pushes: `git --no-optional-locks fetch origin && git --no-optional-locks merge --ff-only origin/main` in the folder (stash local edits first); delete `.git/*.lock` if present (needs delete permission each session). Live data: `https://raw.githubusercontent.com/QuinnyXu/quantfolio-options/main/{marks,screen,status}.csv|json`. `Quantfolio_Index.csv` in the Tracker folder is READ-ONLY for this experiment.

## Rules v2.1 (live on GitHub)
- Fund $1,000 = `fund_value` in config.json (Claude updates on every logged exit). Max premium 25% of fund; 15% while fund < $700. `active_cap()` in fetch_options.py; status.json shows cap_pct/max_premium.
- **Calls only** (types ["C"], live since commit 8783149). One open experiment position. Screen 60–180 DTE, delta 0.35–0.55, premium ≥ 0.30, OI ≥ 300, spread ≤ 10%. `earnings_date` / `earnings_in_window` columns (always True at these DTEs; info, not a filter).
- Overlay gate: Quantfolio_Index.csv verdict Buy / Buy on weakness. Trim/Exit/Hold names are not traded. v1 rows (e.g. T) need a v2 re-score first.
- Entry 1 contract limit at the morning mid; skip if that mid is >10% above the evening screen mid. Exits mechanical: stop −50%, target +100%, time stop = half DTE at entry.
- Graduation unchanged: 20 logged trades, no violations, positive expectancy.
- VST 160C Jan-2027 (8.65) = Trade 0, outside experiment, does NOT block experiment trades; stop 4.30 / target 13.00 / time stop 2026-12-01.

## Universe (live since 2026-09-23 01:17Z)
- Pool = every Quantfolio_Index.csv row with score ≥ 20 and forensic_severity ≠ KILL → 47 tickers. Rebuild with `python tools/build_pool.py` (reads the Tracker CSV, writes only config.json) after any index change. Watchlist empty.
- First run on the new pool: 47 tickers, no errors, screen = 1 row (KO Dec 92.5C, Trim → ineligible) ⇒ "no trade". Reachable under $250 at these deltas: sub-$130 names (NYT, T, KO, SO, EW, NEE, AEP, TJX, BSY, NFLX, CSCO; UBER ~$330). Big names are share-only. Expect "no trade" most evenings.

## Routine (ET)
Evening after ~4:45 pm: "screen?" → one pick or no trade. Morning 9:50–10:30: place limit, then "log trade: …". ~12:20 pm: check marks, exit on flag, "log exit: …". 4:25 run flags → exit next morning. DST: shift cron −1h around Oct 30. Optional: scheduled task for a 5 pm ET automatic screen (offered, not set up).

## Pending
- `notes/cowork-notes.md` added 2026-09-22 late; push line handed to Quinny.
