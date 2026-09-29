# Options experiment — Cowork working notes (updated 2026-09-29 15:00 ET)

Mirrored from the Claude Project doc `claude/options-experiment-notes.md` (Quinny's request). On every push, Claude rewrites this file from that doc so both stay identical. Human-facing rulebook: `../options_experiment_handover.md`.

Source of truth: `options_experiment_handover.md` in `C:\Users\xkxuq\Documents\Starup\quantfolio-options` (repo `QuinnyXu/quantfolio-options`, public). That folder is Cowork's working folder: Claude edits files there directly and ends with a single-line PowerShell line for Quinny — order matters: `git add -A; git commit -m "..."; git pull --rebase; git push`. Claude cannot push. Git in the folder: read-only commands with `--no-optional-locks`; check real changes with `git diff --ignore-all-space --stat` (Windows CRLF noise otherwise). Live data: `git fetch` + `git show origin/main:<file>` in the folder (raw.githubusercontent via WebFetch is cached/stale for hours — don't trust it). Tracker folder: Claude edits reports/index/xlsx there too (analyst skill), never pushes; Quinny pushes.

## Rules v2.2 (live on GitHub since 2026-09-25)
- Fund $1,000 = `fund_value` in config.json. Max premium 25% of fund ($250); 15% while fund < $700.
- Calls only. One open experiment position. Screen 60–180 DTE, delta 0.35–0.55, premium ≥ 0.30, OI ≥ 300, spread ≤ 10%.
- Overlay gate: verdict Buy / Buy on weakness AND spot ≤ `add_level`. `config.json.overlay` = {ticker: add_level}; only overlay names + positions are fetched; `overlay=Y` in screen.csv = every rule met.
- Entry 1 contract, limit at the morning mid (a resting limit below the mid at the cap is allowed — conservative). Skip if morning mid >10% above the evening mid. Exits mechanical: stop −50%, target +100%, time stop = half DTE at entry.
- Good-firm framework only; macro overlay shelved (don't re-raise). Graduation: 20 logged trades.
- VST 160C Jan-2027 (8.65) = Trade 0, outside experiment; stop 4.30 / target 13.00 / time stop 2026-12-01. 09-28 close: 138.02, mid 6.70, −22.5%.

## Universe (2026-09-29)
- Overlay (12): ADSK≤225 (re-scored 09-29) AMZN≤243 AVGO≤357 GOOGL≤280 INTU≤351 NOW≤151 NVDA≤256 NYT≤63.75 PTC≤130 UBER≤75 VEEV≤241 VST≤157.
- Reachable under $250: UBER, NYT, PTC. Everything else share-only.
- Rebuild with `python tools/build_pool.py` after any index change (done 09-29 after ADSK).

## Log so far
- 09-25 → 09-29: no trade every day (screen empty under v2.2).
- 09-28 evening: conditional pick UBER Dec-18 75C, resting limit 2.50 (mid was 2.57, delta 0.356, spread 5.4%, OI 6.9k). 09-29 morning it opened >$3.00 — not filled, correctly skipped. Keep watching Dec 75C / 77.5C and Jan 77.5C/80C.
- NYT: above add level again (64.17). Options too thin anyway.
- PRCT (09-25, outside experiment): prior record 11/25 Avoid, Amber; stock 17.14; only Jan-2027 20C has a market (1.45/1.80, 21% spread, IV 69%) — an earnings binary on the Nov 4 print; shares are the cleaner instrument; not logged. Re-score after Q3 print.
- ADSK (09-29): full v2.2 re-score written to Tracker `03_reports/2026-Q3/ADSK_Q2_FY2027_Quantfolio.md`: 21/25 Like (from 23 Love; Test 3 & 4 capped by v2.2 evidence rules), Clean, FV 191/265/320, price 207.19 (09-28 close), MoS +21.8%, Lens D ≈18% (17.9% no re-rating), reverse-DCF implied g 9.0%, panic checklist 5/6 → Buy on weakness, 5% in two tranches (add ≤225, aggressive ≤199, trim >320, exit >352). Index row upserted, xlsx row 106 appended, Quantfolio_Index.md rebuilt, options overlay add level 268→225. Options: cheapest qualifying call ~$735 → share-only.

## Routine (ET)
Evening after ~4:45 pm: "screen?" → one pick or no trade. Morning 9:50–10:30: place limit, then "log trade: …". ~12:20 pm: check marks, exit on flag, "log exit: …". 4:25 run flags → exit next morning. DST: shift cron −1h around Oct 30. 9:50 am cron slot is usually skipped by GitHub; midday often ~2h late.

## Pending pushes (2026-09-29)
- Tracker repo: ADSK report + Quantfolio_Index.csv + Quantfolio_Index.md + portfolio_tracker.xlsx.
- Options repo: config.json (ADSK add level 225) + this notes mirror.
