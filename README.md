<img width="1284" height="794" alt="Screenshot 2026-05-10 at 5 37 26 PM" src="https://github.com/user-attachments/assets/919025e0-1f21-45e1-95f8-8a7c7ecac673" />
-
<img width="1284" height="794" alt="Screenshot 2026-05-10 at 5 37 12 PM" src="https://github.com/user-attachments/assets/512008fd-ea76-4a58-bc73-111860f2de6f" />
-
<img width="1284" height="794" alt="Screenshot 2026-05-10 at 5 37 36 PM" src="https://github.com/user-attachments/assets/83f1403b-396a-426a-8e5d-bd529eed7201" />
-
<img width="1284" height="794" alt="Screenshot 2026-05-10 at 5 37 49 PM" src="https://github.com/user-attachments/assets/e0b58d98-796a-4991-9cbc-2cbd7bc3ead8" />
-
# Train Market Data - /* | *\ - COLLAB WITH ERIKA out SOOON
-
<img width="1284" height="794" alt="Screenshot 2026-05-10 at 5 43 14 PM" src="https://github.com/user-attachments/assets/5357a14f-35c7-46b2-98b0-722c7036add4" />
-
-
This project turns the Train market dataset into a static directory site designed for GitHub
Pages. It behaves like a searchable catalog, with a landing page for discovery and a dedicated
profile view for individual listings.

## Architecture

- **Astro static site** for presentation and page generation
- **Python build step** that reads `../../erika/artifacts/ticker_checklist.csv`
- **Static JSON catalog** served from `public/data/catalog.json`
- **Server-rendered summary data** written to `src/generated/catalog-meta.json`

The site does not require a runtime backend. Search and filtering happen in the browser against
the generated JSON catalog.

## Companion Game console (predictions + live desk)

The sibling **Game** Next.js app (`…/cursor/game`) hosts the interactive predictions strip (flat
$100 → payout framing, reference-only demo), the merged **`/live`** route with μgrad sports-field
and Bloomberg side-chat iframes, and env-driven embed URLs (`NEXT_PUBLIC_UGRAD_SPORTS_URL`,
`NEXT_PUBLIC_UGRAD_TOOLS_DECK_URL`, `NEXT_PUBLIC_BLOOMBERG_CHAT_URL`).

Train ships dedicated routes for each top tab: **`/directory/`** (full catalog explorer with filters
and pagination), **`/predictions/`** (Game-style card grid), **`/sports/`** (streaming-style layout shell
for live tiles and rails — static on Pages), **`/broadcast/`** (placeholder roadmap for encoder / pipeline /
collab surfaces; optional `PUBLIC_BROADCAST_PIPELINE_URL` for your live workpad origin), plus Featured,
Listing, and Raw. The
site header uses pill navigation with the **Directory search** field first, then the eyebrow and
title, then the educational row, then the tab row (Home, Featured, Predictions, Sports, Broadcast, Models, Directory, Listing,
Raw, Captions, Ledger) plus optional Game / Live when `PUBLIC_GAME_CONSOLE_URL` is set. From any non-directory page,
pressing **Enter** in the header search jumps to `/directory/?q=…`.

Train’s homepage links out when you set at **build** time:

- **`PUBLIC_GAME_CONSOLE_URL`** — Game origin with no trailing slash (for example `http://localhost:3000` or your deployed base).
- **`PUBLIC_BROADCAST_PIPELINE_URL`** (optional) — Origin with no trailing slash for a separate live pipeline / encoder workpad; the **Broadcast** tab shows an “Open pipeline workpad” button when set.
- **`PUBLIC_BROADCAST_EMBED_HOSTS`** (optional) — Comma-separated hostnames (e.g. `127.0.0.1,localhost,pipeline.example.com`). When set, the Broadcast **iframe** loads only if the pipeline URL’s host matches one entry. When unset, any `http`/`https` pipeline URL from the variable may embed (still no user/password in the URL).

Example:

```bash
PUBLIC_GAME_CONSOLE_URL=http://localhost:3000 npm run build
```

Pipeline workpad (optional):

```bash
PUBLIC_BROADCAST_PIPELINE_URL=http://127.0.0.1:8787 PUBLIC_GAME_CONSOLE_URL=http://localhost:3000 npm run build
```

If unset, the new homepage sections still show demo cards and wiring notes; the site header omits
the “Game console” / “Live desk” shortcuts until the variable is provided.

For **GitHub Actions** deploys, define a repository variable `PUBLIC_GAME_CONSOLE_URL` (Settings →
Secrets and variables → Actions → Variables) so Pages builds pick up the same origin. Add
`PUBLIC_BROADCAST_PIPELINE_URL` when your pipeline workpad has a stable URL, and optional
`PUBLIC_BROADCAST_EMBED_HOSTS` to allowlist which hosts may load in the Broadcast iframe.

## Liquid AI live tuning

Train includes `/models/liquid-ai/`, a local-only tuning desk under the Models section for the mirrored LiquidAI LFM2 transcript
GGUF. It calls an Ollama-compatible `POST /api/generate` endpoint from the browser, then lets you
score the result and export JSONL tuning pairs.

```bash
npm run dev:liquid
```

That command creates the local Ollama model `liquidai-lfm2-transcript:q4km` from
`Modelfile.liquidai-lfm2-transcript` when needed, starts Ollama if it is not already responding, and
then starts Astro. Open `http://localhost:4321/models/liquid-ai/`.

If Ollama is already running and the browser blocks the request, restart Ollama with matching local
origins, for example `OLLAMA_ORIGINS=http://localhost:4321,http://127.0.0.1:4321 ollama serve`.

## Low-latency access model

The homepage now includes an indicative **hop and speed analysis** layer for major exchange and
index routes, relay points, live pipeline stages, junction bottlenecks, and hardware profiles. It
is meant as planning guidance for getting market data into Train at speed, not as a measured SLA.

## Featured market page

The site now includes `/featured/`, a timezone-aware market-focus page that:

- picks a regional session from the visitor timezone or `?exchange=...`
- shows a curated 10-major stock basket for that region from the local catalog
- links out to TradingView and Yahoo heatmaps for live stock-performance context
- loads CoinGecko live crypto movers and the CoinGecko heatmap widget client-side

Because the repo still ships static listing metadata rather than full end-of-day quote history, the
stock basket is curated by region and exchange focus, while the live ranking context comes from the
external heatmap sources.

### Major venue / index routes

| Venue | Benchmarks / flows | Primary PoP | Relay pattern | Indicative budget |
| --- | --- | --- | --- | --- |
| CME / Aurora | ES, NQ, RTY, YM, GC, SI, HG | Aurora I / CH2 | Aurora -> Chicago relay -> NY4/NY5 | sub-0.1 ms local, 0.3-0.9 ms metro, 8-10 ms to NJ |
| NASDAQ / NYSE / NYSE Arca / OPRA | QQQ, SPY, cash equities, ETFs, options | Carteret / Mahwah / Secaucus / NY4 | Venue edge -> NJ relay -> Chicago and London | sub-0.15 ms local, 0.2-1.1 ms metro, 8-10 ms to Chicago |
| LSE / ICE Europe / Euronext | FTSE, ICE energy, STOXX-linked flows | LD4 / Basildon / Slough | London edge -> LD4 relay -> Frankfurt and NY | sub-0.15 ms local, 0.3-1.2 ms metro, 3-5 ms to Frankfurt |
| Deutsche Boerse / Eurex | DAX, Euro Stoxx, Bund complex | FR2 / FR5 | Frankfurt edge -> Frankfurt relay -> LD4 and NY | sub-0.12 ms local, 0.2-0.8 ms metro, 3-5 ms to London |
| JPX / OSE | Nikkei 225, TOPIX, JGB-linked flows | TY3 / Tokyo metro | Tokyo edge -> Tokyo relay -> SG/HK | sub-0.12 ms local, 0.2-0.9 ms metro, 35-70 ms regional |
| HKEX / SGX | Hang Seng, CNH, SGX derivatives | HK1 / HK3 / SG1 | Local edge -> HK/SG relay -> Tokyo and London | sub-0.15 ms local, 0.3-1.0 ms metro, 30-40 ms HK<->SG |

### Relay points

- **Aurora / Chicago** for futures-first books and metals.
- **New Jersey / NY4-NY5** for US cash equity, ETF, and options aggregation.
- **London / LD4** for European fanout and transatlantic handoff.
- **Frankfurt** for Eurex/Xetra primaries or hot standby.
- **Tokyo + Singapore** as the regional APAC relay mesh.

### Live pipeline coverage

The architecture section now explicitly covers the full live-data chain:

1. **Venue ingress** with primary and secondary handoffs.
2. **Lossless capture** with timestamping and parallel hot hosts.
3. **Decode / normalize** for trades, books, status, and instrument metadata.
4. **Gap fill / reconciliation** for retransmit and replay continuity.
5. **Regional relay mesh** for Chicago, New Jersey, London, Frankfurt, Tokyo, and Singapore.
6. **Hot cache / serving plane** for session-aware stream delivery.
7. **Historical persistence** for raw and normalized archives.
8. **Client delivery** for live subscriptions, reconnect, and replay bootstrap.

For each stage, the page now lists:

- **Primary path**
- **Redundant path**
- **Data carried**
- **Critical junction**
- **Likely bottleneck**
- **Tech stack**

### Junction bottlenecks

The page now calls out the main join points where low-latency systems usually fail first:

- Venue demarcation
- Capture-to-parser handoff
- Relay fanout spine
- Gateway and entitlement plane
- Archive and replay contention

### Tech stack layers

The architecture section also breaks the plant down by stack layer:

- Time and clocking
- Network fabric
- Capture and feed handling
- Normalization and stream fabric
- Storage and replay
- Serving and client edge

### Server / system requirements

- **Capture edge:** 16-32 high-clock cores, 64-128 GB ECC, dual 25 GbE or 100 GbE NICs, NVMe-first scratch.
- **Relay / normalization:** 24-48 cores, 128-256 GB ECC, dual 25/100 GbE, 4-8 TB NVMe RAID1/10.
- **Strategy hot path:** 8-24 high-frequency cores, 64-128 GB ECC, 10/25 GbE, local NVMe cache.
- **Research / replay:** 32-64 cores, 128-512 GB ECC, 10/25 GbE, 8-32 TB NVMe or U.2 arrays.

Fast-path assumptions:

- Linux 6.x LTS with IRQ affinity and CPU isolation tuned.
- PTP or tightly disciplined clock sync.
- NIC hardware timestamping enabled.
- NVMe on the ingestion hot path.
- 25 GbE minimum east-west relay links, with 100 GbE where multi-venue fanout is shared.

## Local development

```bash
npm install --cache .npm-cache
npm run dev
```

The data-prep step runs automatically before `dev` and `build`.

## Build

```bash
npm run build
```

The production site is generated in `dist/`.

## GitHub Pages

The Astro config auto-detects the correct base path during GitHub Actions builds:

- user/org pages: `/`
- project pages: `/<repo-name>/`

If you need to override it manually, set `PUBLIC_BASE_PATH`.

The deployment workflow is in `.github/workflows/deploy.yml`.

## Data refresh

When the Train source CSV changes, rebuild the site:

```bash
npm run prepare:data
npm run build
```

## Source data

- `../../erika/artifacts/ticker_checklist.csv`
- `../../erika/artifacts/ticker_checklist_summary.md`

The directory currently focuses on listing metadata and coverage signals, not time-series charting.

### Attribution-safe enrichment policy

The catalog builder now passes through optional filing / headquarters / branch metadata when the
upstream CSV includes it. Supported output fields include:

- `lt` / `ll` / `lc` / `fs` — filing timestamp, filing location, filing coordinates, filing source
- `hq` / `hc` / `hs` — headquarters location, headquarters coordinates, headquarters source
- `br` / `bs` — branch locations and branch source

For a public static dataset, keep the enrichment stack on sources that are safe to redistribute:

- **SEC EDGAR** — public domain; use for US filer addresses, state of incorporation, and filing
  history proxies
- **GLEIF Golden Copy** — CC0; use for legal / headquarters addresses and LEI-linked entity data
- **Wikidata** — CC0; use for founding dates and headquarters coordinates when available
- **National open registries** (for example Companies House / OGL, BRREG / NLOD, INSEE / Etalab,
  PRH / CC-BY) — allowed with attribution

Avoid feeding the published catalog from sources that would impose share-alike or redistribution
restrictions unless the repository license and downstream expectations are updated accordingly:

- **OpenCorporates free tier** — ODbL/share-alike
- **OpenStreetMap hosted Nominatim bulk geocoding** — not allowed for bulk resolution; ODbL applies
- **Exchange reference feeds without explicit open terms** — redistribution is legally unclear

Practical limit: authoritative branch-office coverage is not realistically available for all ~56k
tickers from free redistributable sources, so branch data should remain optional and sparse unless a
licensed commercial source is added.

### OpenRegistry plugin + US listings

The [OpenRegistry Cursor plugin](https://cursor.directory/plugins/openregistry) documents
statutory registry fields (legal name, registered office, incorporation date, branches). The free
OpenRegistry **search API does not expose jurisdiction `US`** — US tickers are enriched from
**SEC EDGAR** (`data.sec.gov/submissions`) instead, which supplies the canonical legal name (for
example `Tesla, Inc.` for TSLA), business address, and CIK-linked registry metadata.

```bash
# Fetch SEC rows for specific tickers (writes public/data/enrichment/sources/sec-edgar.ndjson)
npm run enrichment:fetch -- --tickers TSLA,AAPL,MSFT --delay 0.2

US SEC rows set **statutory filing time** (`lt`) from the earliest registration-class
SEC acceptance timestamp (S-1 / 8-A12B / etc.), **filing venue** (`ll`) to the state
secretary-of-state office (not the issuer HQ street), and coordinates (`lc` / `hc`) via
the US Census geocoder when possible plus SOS/city fallbacks. Pass `--no-geocode` for
faster bulk runs.

# Or batch US exchange listings (respect SEC rate limits)
npm run enrichment:fetch -- --exchange NASDAQ --limit 200 --delay 0.25

# Merge sources → overlay → catalog
npm run enrichment:build
npm run prepare:data

# Batch listing profiles (identity / classification / quick-view fields) with resume state
npm run profiles:collect -- --exchange NASDAQ --limit 100 --delay 0.25
npm run profiles:collect -- --tickers TSLA,AAPL --delay 0.2
```

Non-US listings can use `--openregistry-only` or mixed mode when the catalog country maps to a
supported jurisdiction (GB, FR, IE, ES, NO, …). Install the MCP server from
`https://openregistry.sophymarine.com/mcp` for interactive profile lookups during editing.

### Build attribution-safe enrichment overlay

Use the enrichment builder to merge SEC EDGAR, GLEIF, Wikidata, and optional per-country registry
inputs into one deterministic overlay consumed by `build_catalog_data.py`. When
`public/data/enrichment/sources/sec-edgar.ndjson` or `openregistry.ndjson` exist, they are merged
automatically (no flags required).

```bash
npm run enrichment:build -- \
  --sec ./data/sec-edgar.ndjson \
  --gleif ./data/gleif.ndjson \
  --wikidata ./data/wikidata.ndjson \
  --registry ./data/companies-house.ndjson --registry-license OGL
```

Output is written to `public/data/enrichment/attribution-safe.json` and contains only
redistribution-safe fields (`ln`, `ls`, `lt`, `ll`, `lc`, `fs`, `hq`, `hc`, `hs`, `cd`, optional
`br` / `bs`, optional `registry`) plus per-field source and update metadata. During
`npm run prepare:data`, the catalog builder automatically applies this overlay when present.

## Snowflake coverage profiles (sharded + versioned)

Every catalog listing now also has a 5-axis snowflake coverage profile (Value, Future,
Past, Health, Dividends) modeled on `https://roi.kevencraftrituals.com/health.html`. The
profiles live under `public/data/health/`:

```
public/data/health/
├── manifest.json                # tiny (~42 KB) index: shards + patches + sha-256 etags
├── shards/v1/index.json         # ticker → shardId map
├── shards/v1/0000.json          # ~256 listings per shard (~600 KB)
├── shards/v1/0001.json
├── ...
└── patches/v1/<TICKER>.json     # per-listing overlays (small shims/blobs)
```

The browser loads only the `manifest.json` plus whichever shards or patches it actually
needs, caching them in `sessionStorage` keyed by their etag. When the research desk
flips a single check, only that 1–3 KB patch (or shard) is re-downloaded — never the
20 MB catalog.

### Iteration workflow

```bash
# 1. Scaffold an editable overlay for one ticker
python3 scripts/scaffold_health_patch.py AAPL

# 2. Edit public/data/health/patches/v1/AAPL.json
#    Flip check `state` from "na" to "pass"/"fail" and fill `detail`.

# 3. Promote the patch into the manifest (recomputes its etag)
npm run prepare:data
```

### Versioning API (`api.qbitos.ai`)

The Cloudflare Worker under `workers/api-qbitos-ai/` exposes the same data with edge
caching:

| Endpoint | Purpose |
| --- | --- |
| `GET /v1/health` | Worker liveness + Train Pages reachability |
| `GET /v1/coverage/manifest` | Snowflake manifest (shards + patches + etags) |
| `GET /v1/coverage/index` | Snowflake ticker → shard id map |
| `GET /v1/coverage/shard?id=NNNN` | Snowflake shard JSON (etag-cached, supports `If-None-Match`) |
| `GET /v1/coverage/listing?ticker=AAPL` | Snowflake profile (patch overlay if present, else shard entry) |
| `GET /v1/coverage/diff?since=<etag>` | Snowflake shards/patches changed since the caller's last manifest |
| `GET /v1/history/manifest` | 5y history manifest (per-ticker etags) |
| `GET /v1/history/listing?ticker=AAPL` | Per-ticker OHLCV series (`If-None-Match` → 304) |
| `GET /v1/history/diff?since=<etag>` | Tickers whose series file changed |
| `GET /v1/catalog.json` | Cached pass-through of the full catalog |

To point the browser at the API instead of static GitHub Pages, set
`window.__QBITOS_API_ORIGIN__ = 'https://api.qbitos.ai'` before the page scripts run.

Deploy:

```bash
cd workers/api-qbitos-ai
npm install
npx wrangler deploy
```

## US daily history (sharded + versioned, full available range)

Every US-listed ticker on `NASDAQ`, `NYSE`, `NYSEARCA`, `NYSEMKT`, `CBOE`, `AMEX`,
`BATS`, `OTC`, `OTCBB` (~21 K listings) can be backed by a daily OHLCV series stored
under:

```
public/data/history/
├── manifest.json                  # ticker index + sha-256 etags (small, fetched once)
└── series/v1/<TICKER>.json        # parallel-array OHLCV (~30 KB / 5y, ~250 KB / full history)
```

The format is parallel arrays (`d`, `o`, `h`, `l`, `c`, `v`) with `YYYYMMDD` integer
dates — gzip-friendly, and ECharts consumes it directly via `lttb` sampling. The
listing page (`/listing/?id=AAPL`) auto-renders a price line chart, a
[calendar-simple](https://echarts.apache.org/examples/en/editor.html?c=calendar-simple)
daily-return heatmap, a [flowGL-noise](https://echarts.apache.org/examples/en/editor.html?c=flowGL-noise&gl=1&theme=dark)
return-driven flow panel, and a snowflake radar plus check grid whenever history /
coverage data exists for that ticker. Metrics include total return, annualized return,
max drawdown, and average volume. The chart adapts to whatever span the file actually covers
(e.g. AAPL's full series goes back to 1980, IBM's to 1962).

Like the snowflake coverage system, only the small manifest is fetched up front; per-
ticker series files are loaded on demand and cached in `sessionStorage` keyed by their
sha-256 etag, so a single ticker's data refresh is one ~30–250 KB file — never the
full catalog.

### Lookback window

The fetcher defaults to **`--lookback max`**, which asks each upstream for the full
available history per ticker. You can shrink the window when bandwidth or storage
matters:

```
--lookback max         # default: full available history (1962+ for the oldest tickers)
--lookback 5y          # last 5 calendar years only
--lookback 10y         # last 10 calendar years only
--lookback 1825d       # last 1825 days
```

Each series file records both `lookbackYears` (numeric hint, `0` for max) and
`lookbackMode` (`'fixed' | 'max'`) so the listing-page UI can honestly label the span.

### Backfill workflows

Pick the path your environment can authenticate.

**A. yfinance (recommended for full backfill — handles Yahoo's auth crumbs):**

```bash
pip install yfinance
python3 scripts/fetch_us_history.py --source yfinance \
    --exchange NASDAQ,NYSE,NYSEARCA,NYSEMKT,CBOE \
    --lookback max
```

**B. Yahoo's keyless v8 chart endpoint (small batches; rate-limits aggressively):**

```bash
npm run history:fetch -- --tickers AAPL,MSFT,SPY,QQQ,NVDA --lookback max --delay 1.5
```

**C. Stooq with API key (US series back to ~1969):**

```bash
export STOOQ_APIKEY=<your-key>
npm run history:fetch -- --source stooq --exchange NASDAQ,NYSE --lookback max --delay 0.3
```

**D. Manual CSV import (any source — Polygon, Tiingo, your data lake, Yahoo CSV
download from the browser):**

```bash
npm run history:import -- --lookback max ./csvs/AAPL.csv ./csvs/MSFT.csv
# header columns auto-detected: Date, Open, High, Low, Close, Volume
```

After any backfill, regenerate the manifest:

```bash
npm run history:manifest      # or just run npm run prepare:data / npm run build
```

### Smoke test (charts + snowflake, no synthetic prices shipped)

Seed a ~25-year synthetic AAPL series and a demo snowflake patch with mixed
pass/fail states, then verify the build:

```bash
npm run smoke:viz:apply          # seed only (open /listing/?id=AAPL)
npm run smoke:viz                # seed + npm run check + npm run build
npm run smoke:viz:cleanup        # remove series + restore NA-only AAPL patch
```

Cleanup leaves `public/data/history/manifest.json` at 0 entries and does not commit
fake OHLCV.

### Filtering options

```
--exchange NASDAQ,NYSE      # comma-separated US exchanges
--tickers AAPL,MSFT,SPY     # explicit list
--limit 500                 # cap per run for sharded CI jobs
--skip 500                  # offset (parallel-shard across machines)
--max-age-days 7            # skip tickers refreshed within this window
--force                     # re-fetch even when fresh
--delay 1.5                 # seconds between requests
--lookback max              # full available history (default), or 5y / 10y / 1825d
```
