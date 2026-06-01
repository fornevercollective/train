# Dataset coverage snapshot

Monthly reference for Train static data completeness. Regenerate counts with:

```bash
npm run database:report
```

**Last updated:** 2026-06-01 (cron: train documentation updates)

## Catalog (`public/data/catalog.json`)

| Metric | Count |
| --- | --- |
| Total listings | 56,307 |
| Countries | 80 |
| Exchanges | 71 |
| Stocks | 40,962 |
| ETFs | 15,345 |
| Date coverage (`dc`) complete | 56,307 |
| IPO/founding (`ic`/`fc`) complete | 3,019 / 224 (LLC original filing) |

Source CSV: `../../erika/artifacts/ticker_checklist.csv` (see `public/data/catalog-meta.json` for full facet breakdown).

## History (`public/data/history/`)

| Metric | Count |
| --- | --- |
| Listings with daily OHLCV series | 19,942 |
| Manifest | `public/data/history/manifest.json` (per-ticker etags) |

Backfill: `npm run database:backfill -- --phase history` or `python3 scripts/fetch_us_history.py`.

## Session quotes (`public/data/quotes/`)

| Metric | Count |
| --- | --- |
| Tickers with latest quote row | 19,812 |

Backfill: `npm run database:backfill -- --phase quotes`.

## Snowflake coverage (`public/data/health/`)

| Metric | Count |
| --- | --- |
| Sharded profiles | All catalog tickers (via `build_health_shards.py`) |
| Manual patches | 2 (`public/data/health/patches/v1/`) |

API mirror: `workers/api-qbitos-ai` (`GET /v1/coverage/*`, `GET /v1/history/*`).

## Attribution-safe enrichment

| Metric | Count |
| --- | --- |
| Overlay rows applied | 227 |
| Overlay file | `public/data/enrichment/attribution-safe.json` |

Fetch: `npm run enrichment:fetch` · merge: `npm run enrichment:build` · catalog: `npm run prepare:data`.

## Session ledger

| Asset | Path |
| --- | --- |
| Sessions index | `public/data/ledger/sessions.json` |
| UI | `/ledger/` |

## Futures natal (metals + energy)

| Metric | Value |
| --- | --- |
| Manifest rows | 11 (`public/data/futures-symbol-manifest.csv`) |
| Verified outright genesis | 10 |
| Skipped | 1 (HO heating oil) |
| Config | `public/data/futures-natal-config.json` |

Workflow: [`FUTURES-SYMBOL-MANIFEST.md`](FUTURES-SYMBOL-MANIFEST.md).

## Related commands

```bash
npm run database:report          # JSON coverage summary
npm run database:normalize       # normalize dc/ic/fc from catalog dates
npm run database:backfill -- --phase all --limit 300
npm run prepare:data             # catalog + health shards + history manifest
```
