# Options experiment — Cowork working notes (updated 2026-09-25 09:00 ET)

Mirrored from the Claude Project doc `claude/options-experiment-notes.md` (Quinny's request). On every push, Claude rewrites this file from that doc so both stay identical. Human-facing rulebook: `../options_experiment_handover.md`.

Source of truth: `options_experiment_handover.md` in `C:\Users\xkxuq\Documents\Starup\quantfolio-options` (repo `QuinnyXu/quantfolio-options`, public). That folder is Cowork's working folder: Claude edits files there directly and ends with a single-line PowerShell line for Quinny — order matters: `git add -A; git commit -m "..."; git pull --rebase; git push` (the bot commits 3×/day, so rebase is always needed). Claude cannot push. Code channel parked. Git in the folder: read-only commands with `--no-optional-locks`; a stale `.git/index.lock` needs `del .git\index.lock` on Quinny's side. Windows shows line-ending-only diffs on files Claude didn't touch — harmless; check real changes with `git diff --ignore-all-space --stat`. Live data: raw GitHub URLs for marks/screen/status (or `git fetch` + `git show origin/main:<file>` in the folder). `Quantfolio_Index.csv` in the Tracker folder is READ-ONLY.

## Rules v2.1 (live on GitHub; v2.2 gate pending push)
- Fund $1,000 = `fund_value` in config.json (Claude updates on every logged exit). Max premium 25% of fund; 15% while fund < $700. `active_cap()` in fetch_options.py; status.json shows cap_pct/max_premium.
- Calls only. One open experiment position. Screen 60–180 DTE, delta 0.35–0.55, premium ≥ 0.30, OI ≥ 300, spread ≤ 10%. `earnings_date` / `earnings_in_window` columns (info, not a filter).
- Overlay gate (v2.2, 2026-09-25, Quinny's logic): verdict Buy / Buy on weakness AND spot ≤ `add_level` from Quantfolio_Index.csv. `config.json.overlay` = {ticker: add_level} (public, Quinny OK'd). The run fetches ONLY overlay names + open positions (Trim/Hold never fetched). screen.csv has `overlay` and `add_level` columns; overlay=Y = every rule met; non-Y rows = overlay names above their add level (near-misses). Position-only tickers are marked, not screened.
- Entry 1 contract limit at the morning mid; skip if that mid is >10% above the evening screen mid. Exits mechanical: stop −50%, target +100%, time stop = half DTE at entry.
- Good-firm framework only. No index/sector/macro ETFs. "Macro overlay v1" (TLT/IAU/GDX, 4 tests) proposed 2026-09-24 and shelved by Quinny; don't re-raise unless asked.
- Graduation unchanged: 20 logged trades, no violations, positive expectancy.
- VST 160C Jan-2027 (8.65) = Trade 0, outside experiment; stop 4.30 / target 13.00 / time stop 2026-12-01. 2026-09-24 close: VST 137.94, mid 6.93, −19.9%.

## Data feeds
- CBOE free JSON = overnight snapshot (stale intraday); everything that matters now comes yfinance-first (~15 min delayed). `status.json` → `sources`, `quote_times`.
- GitHub cron: 9:50 am slot keeps being skipped; midday/3:57/7:17 pm ET runs land reliably. If the morning one matters later, move it to an odd minute.

## Universe (2026-09-25)
- Overlay (12, with add levels): ADSK≤268 AMZN≤243 AVGO≤357 GOOGL≤280 INTU≤351 NOW≤151 NVDA≤256 NYT≤63.75 PTC≤130 UBER≤75 VEEV≤241 VST≤157. Below add level on 09-24 close: ADSK, INTU, NOW, NVDA, UBER, VST, NYT (63.05). Above: GOOGL, VEEV, AMZN, AVGO.
- Reachable under $250 at our deltas: UBER, NYT, PTC, VST-on-a-dip. Others share-only.
- Rebuild lists with `python tools/build_pool.py` after any index change (also after each quantfolio-analyst report).

## Observation list (Quinny)
- NYT: 63.05, add 63.75 → gate passes, but options too thin (Dec/Jan calls OI 35–134, spreads 30–75%) → fails spread ≤10%. Shares outside experiment if any.
- UBER: 69.22, add 75 → gate passes. Nov-20 75C 2.38 mid, delta 0.36, spread 5%, OI 6.4k — fails only DTE (58 < 60). Dec-18 same delta ~3.18 > cap. Re-check as expiries roll / on a dip.
- 09-24 close screen: KO Jan 92.5C, NEE Jan 80C (Trim/Hold) ⇒ no trade 09-25. After v2.2 those names won't even be fetched.

## Routine (ET)
Evening after ~4:45 pm: "screen?" → one pick or no trade. Morning 9:50–10:30: place limit, then "log trade: …". ~12:20 pm: check marks, exit on flag, "log exit: …". 4:25 run flags → exit next morning. DST: shift cron −1h around Oct 30.

## Pending
- v2.2 gate edits in folder (build_pool.py, fetch_options.py, config.json, handover, README, notes mirror); push line handed to Quinny 2026-09-25 morning. After the push, verify status.json tickers = 13 (12 overlay + VST) and screen.csv has add_level column.
