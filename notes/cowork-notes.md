# Options experiment — Cowork working notes (updated 2026-09-30 20:00 ET)

Mirrored from the Claude Project doc `claude/options-experiment-notes.md` (Quinny's request). On every push, Claude rewrites this file from that doc so both stay identical. Human-facing rulebook: `../options_experiment_handover.md`.

Source of truth: `options_experiment_handover.md` in `C:\Users\xkxuq\Documents\Starup\quantfolio-options` (repo `QuinnyXu/quantfolio-options`, public). That folder is Cowork's working folder: Claude edits files there directly and ends with a single-line PowerShell line for Quinny — order matters: `git add -A; git commit -m "..."; git pull --rebase; git push`. Claude cannot push. Git in the folder: read-only commands with `--no-optional-locks`; check real changes with `git diff --ignore-all-space --stat`. Live data: `git fetch` + `git show origin/main:<file>` in the folder (raw.githubusercontent via WebFetch is cached/stale). FRED/Yahoo/CBOE are unreachable from both sandbox shells — the GitHub run is the only place live macro data can be pulled. Tracker folder: Claude edits reports/index/xlsx there too, never pushes.

## Rules v2.2 (equity sleeve, live on GitHub since 2026-09-25)
- Fund $1,000 = `fund_value` in config.json. Max premium 25% of fund ($250); 15% while fund < $700.
- Calls only. One open position across both sleeves. Screen 60–180 DTE, delta 0.35–0.55, premium ≥ 0.30, OI ≥ 300, spread ≤ 10%.
- Overlay gate: verdict Buy / Buy on weakness AND spot ≤ `add_level`. Only overlay names + positions (+ macro names) are fetched; `overlay=Y` in screen.csv = every rule met.
- Entry 1 contract, limit at the morning mid (resting limit below the mid at the cap is allowed). Skip if morning mid >10% above the evening mid. Exits mechanical: stop −50%, target +100%, time stop = half DTE at entry.
- Graduation: 20 logged equity trades. journal.csv has a `layer` column (equity / macro).
- VST 160C Jan-2027 (8.65) = Trade 0, outside experiment; stop 4.30 / target 13.00 / time stop 2026-12-01. 09-30 close: 138.35, mid 6.85, −20.8%.

## Macro sleeve v1 (added 2026-09-30)
- `config.json`: `macro: ["TLT"]`, `macro_rules {min_score 6, min_trend 1, value_window_years 15}`.
- `tools/macro_score.py` runs in Actions before fetch_options.py → `macro_overlay.csv` (+ `_history`). Tests ×0–2: T1 DGS30 percentile in 15y (≥90→2, ≥75→1); T2 63-day change in DGS2 (≤−25bp→2, ≤+10→1, else 0); T3 core PCE 3m-annualized ≤3.0% (+1) and UNRATE +≥0.3 in 3m (+1); T4 trend: close > MA50 and ≥ prior 20-day high → 2, > MA20 → 1, else 0. Eligible = total ≥6 AND T4 ≥1. All inputs written to the CSV.
- `fetch_options.py`: equity screen excludes macro names; `screen_macro.csv` = TLT contracts under the same numeric filters, overlay=Y iff scorecard eligible; add_level column shows "macro N/8 verdict".
- First real scorecard arrives with the first Actions run after the push. Expectation: T4 0 (TLT at record lows) → not eligible yet. Gold (IAU/GDX) scorer not written.

## Universe (equity, 2026-09-29)
- Overlay (12): ADSK≤225 AMZN≤243 AVGO≤357 GOOGL≤280 INTU≤351 NOW≤151 NVDA≤256 NYT≤63.75 PTC≤130 UBER≤75 VEEV≤241 VST≤157. Reachable under $250: UBER, NYT, PTC.

## Log so far
- 09-25 → 09-30: no equity trade (screen empty). 09-30 close: UBER 68.51, Dec 75C 2.69 mid — $19 over cap; NYT 63.70 (gate open, options illiquid → not tradable at any price).
- 09-28 conditional pick UBER Dec-18 75C at 2.50 — not filled 09-29 (opened >3.00). Correct skip.
- PRCT (outside experiment): bought Jan-27 20C at 1.60, sold 1.65 (+$5). "Stay away from Avoid."
- ADSK re-scored 09-29 (21/25 Like, FV 191/265/320, Buy on weakness); pushes landed.

## Routine (ET)
Evening after ~4:45 pm: "screen?" → one pick or no trade (also read screen_macro.csv + macro_overlay.csv). Morning 9:50–10:30: place limit, then "log trade: …". ~12:20 pm: check marks, exit on flag. DST: shift cron −1h around Oct 30.
