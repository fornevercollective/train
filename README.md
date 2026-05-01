# Erika Market Directory

This project turns the Erika market dataset into a static directory site designed for GitHub
Pages. It behaves like a searchable catalog, with a landing page for discovery and a dedicated
profile view for individual listings.

## Architecture

- **Astro static site** for presentation and page generation
- **Python build step** that reads `../../erika/artifacts/ticker_checklist.csv`
- **Static JSON catalog** served from `public/data/catalog.json`
- **Server-rendered summary data** written to `src/generated/catalog-meta.json`

The site does not require a runtime backend. Search and filtering happen in the browser against
the generated JSON catalog.

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

When the Erika source CSV changes, rebuild the site:

```bash
npm run prepare:data
npm run build
```

## Source data

- `../../erika/artifacts/ticker_checklist.csv`
- `../../erika/artifacts/ticker_checklist_summary.md`

The directory currently focuses on listing metadata and coverage signals, not time-series charting.
