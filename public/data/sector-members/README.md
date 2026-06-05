# Sector membership (Yahoo screener snapshots)

Static lists of US equities per sector for [Ritual ROI](https://roi.kevencraftrituals.com) market-tape browse. **Not** fetched live by the website.

## Regenerate (local)

```bash
cd train
python3 scripts/fetch-yahoo-sector-members.py --sector technology   # one sector first
python3 scripts/fetch-yahoo-sector-members.py                       # all sectors in manifest
python3 scripts/fetch-yahoo-sector-members.py --enrich-industry     # fetch + industry enrichment
```

### Industry enrichment (separate step)

Yahoo screeners return only `sy` + `name`. Run this to add `sector` + `industry` per ticker (Yahoo search API, cached):

```bash
python3 scripts/enrich-sector-members-industry.py --sector industrials
python3 scripts/enrich-sector-members-industry.py
```

Throttle is built in (`--sleep 0.35` default). ~4k unique symbols ≈ 25 min first run; cache makes re-runs fast.

## Commit & publish

```bash
git add public/data/sector-members scripts/
git commit -m "Refresh sector membership and industry labels."
git push origin main
```

CDN URL (jsDelivr):

`https://cdn.jsdelivr.net/gh/kevencraftrituals/train@main/public/data/sector-members/index.json`

## Files

| File | Contents |
|------|----------|
| `index.json` | Manifest + counts |
| `industry-cache.json` | Yahoo industry lookup cache (sy → sector/industry) |
| `technology.json` | Tickers for Technology screener |
| … | One JSON per sector in `scripts/yahoo-sector-screeners.json` |

## Ticker schema

Each sector file:

```json
{
  "sectorId": "industrials",
  "sectorLabel": "Industrials",
  "yahooScrId": "sec-ind_sec-largest-equities_industrials",
  "updated": "2026-05-17",
  "industryEnriched": "2026-06-05",
  "industrySource": "yahoo_finance_search",
  "count": 483,
  "tickers": [
    {
      "sy": "UNP",
      "name": "Union Pacific Corporation",
      "sector": "Industrials",
      "industry": "Railroads"
    }
  ]
}
```

| Field | Source | Purpose |
|-------|--------|---------|
| `sy`, `name` | Yahoo screener | Identity |
| `sector` | Yahoo search | Issuer GICS-style sector label |
| `industry` | Yahoo search | Sub-sector browse filtering in Ritual ROI |

Taxonomy mappings: `scripts/sector-taxonomy.json`
