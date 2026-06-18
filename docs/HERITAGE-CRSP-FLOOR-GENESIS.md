# Heritage genesis — CRSP / Macrotrends tape floor (1962-01-02)

## Problem

Yahoo max-history and CRSP daily files often start at **1962-01-02** (first NY trading day of 1962 in standardized databases). For **continuous NYSE heritage names**, that date is a **digital tape anchor**, not the exchange listing genesis.

Same failure class as Coca-Cola (`1962-01-02` catalog proxy vs **1919-09-05** heritage) — see `listing-genesis-corrections.json` → `KO`.

## Current US equity sweep (catalog `ft` = 1962-01-02)

| Ticker | Heritage genesis | Clock | Supersedes |
|--------|------------------|-------|------------|
| **XOM** | 1920-03-01 | 10:00 NY | CRSP 1962 — Jersey Standard NYSE listing |
| **CVX** | 1921-06-30 | 10:00 NY | NYSE main floor (from Curb Market) — supersedes 1929-02-20 guess + CRSP 1962 |
| **GE** | 1892-04-24 | 10:00 NY | GE-OG registry; post-2024 aerospace spin is separate |
| **JNJ** | 1944-09-25 | 10:00 NY | J&J NYSE public listing |
| **MO** | 1919-08-13 | 10:00 NY | Philip Morris NYSE heritage line |
| **KR** | 1928-01-26 | 10:00 NY | Kroger NYSE listing |
| **GD** | 1952-04-24 | 10:00 NY | General Dynamics NYSE formation |
| **DTE** | 1926-01-05 | 10:00 NY | Detroit Edison NYSE heritage |
| **AA** | 1925-04-03 | 10:00 NY | Alcoa NYSE listing |
| **GT** | 1927-08-05 | 10:00 NY | Goodyear NYSE listing |

All promoted as **grade B · heritage_open** until first-trade tape is verified to the minute.

## Workflow

```bash
cd train
python3 scripts/audit_crsp_floor_genesis.py
python3 scripts/audit_crsp_floor_genesis.py --json public/data/reports/crsp-floor-genesis-sweep.json
npm run patch:listing-showcase
```

After `prepare:data`, always re-run `npm run patch:listing-showcase` (wired into `prepare:data`).

Mirror rows into `ipo-astro-lookup/data/listing-genesis-corrections.json` for SPA override until catalog deploys.

## Do not use 1962 for

- Mood / war-sky genesis on energy majors (XOM, CVX vs OXY peer work)
- Heritage financials (JPM/KO pattern)
- Backtest baskets without explicit “tape-start” labeling

## Related

- `docs/YAHOO-GENESIS-VERIFICATION.md`
- `public/data/listing-genesis-showcase.json`
- `ipo-astro-lookup/docs/BACKTEST-VINTAGE-CHARTS.md` (GE-OG spin caveat)
