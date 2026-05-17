# Sector membership (Yahoo screener snapshots)

Static lists of US equities per sector for [Ritual ROI](https://roi.kevencraftrituals.com) market-tape browse. **Not** fetched live by the website.

## Regenerate (local)

```bash
cd train
python3 scripts/fetch-yahoo-sector-members.py --sector technology   # one sector first
python3 scripts/fetch-yahoo-sector-members.py                       # all sectors in manifest
```

Throttle is built in (`--sleep 1.25` default). Run weekly, not on every page view.

## Commit & publish

```bash
git add public/data/sector-members scripts/fetch-yahoo-sector-members.py scripts/yahoo-sector-screeners.json
git commit -m "Refresh Yahoo sector membership snapshots."
git push origin main
```

CDN URL (jsDelivr):

`https://cdn.jsdelivr.net/gh/kevencraftrituals/train@main/public/data/sector-members/index.json`

## Files

| File | Contents |
|------|----------|
| `index.json` | Manifest + counts |
| `technology.json` | Tickers for Technology screener |
| … | One JSON per sector in `scripts/yahoo-sector-screeners.json` |

Each sector file: `{ sectorId, sectorLabel, yahooScrId, updated, count, tickers: [{ sy, name }] }`.
