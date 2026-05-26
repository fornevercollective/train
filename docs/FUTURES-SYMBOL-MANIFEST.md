# Futures symbol manifest (Yahoo tape → outright genesis)

Yahoo [commodities](https://finance.yahoo.com/markets/commodities/) lists **continuous/front** symbols (`*=F`). Mood charts need **outright** CME symbols and verified `genesisUtc` in `public/data/futures-natal-config.json`.

## Manifest

`public/data/futures-symbol-manifest.csv` — one row per contract you care about.

| Column | Meaning |
|--------|---------|
| `yahoo` | Treemap / quotes tape symbol (`GC=F`) |
| `outright` | CME outright for genesis (`GCM26`) |
| `tv_symbol` | TradingView search (verify first 1m bar here) |
| `venue` | `comex` (Chicago natal) \| `nymex` (New York natal) |
| `status` | `verified` \| `pending` \| `skipped` |
| `first_volume_date` | YYYY-MM-DD when known |

## CME month letter (Jul 26 → `N26`, Jun 26 → `M26`)

`F G H J K M N Q U V X Z` → Jan … Dec.

## Workflow

1. Pick next `pending` row in the CSV.
2. On TradingView outright daily chart, find **first day with volume**.
3. **Tier A** — open **1m** on that day; if first bar is **22:00 UTC**, use that timestamp (`genesisMethod`: `first_trade_tick`).
4. **Tier B** — if you only have the date (or 1m confirms Globex open), set `genesisUtc` to `{firstVolumeDate}T22:00:00.000Z` with `genesisMethod`: `session_open_estimate` and `genesisSession`: `globex_open`.
5. Add JSON to `futures-natal-config.json`; set manifest `status` to `verified`.

### Globex / weekly renewal anchor (batch policy)

Evening open is **6:00 PM US Eastern** (Globex week open; Friday prints when a contract first lists on a Friday renewal). Same clock as **5:00 PM Central (CDT)** / **17:00 CT** in summer — **22:00 UTC** on the first real trade date.

| When | `genesisUtc` |
|------|----------------|
| First trade **6 PM ET**, date in **EDT** (roughly Mar–Nov) | `{date}T22:00:00.000Z` |
| First trade **6 PM ET**, date in **EST** (roughly Nov–Mar) | `{date}T23:00:00.000Z` |

**Friday listings:** Use the Friday when you see **6:00 PM Eastern** (e.g. MGCM2026 → 2024-06-14 18:00 ET on COMEX), not a later duplicate daily candle.

**Micros:** TV 1m may start months later; trust **Daily** left edge + 6 PM ET rule when 1m “go to date” jumps to 2026.

## Natal location

| Venue | `birthLocation` | When |
|-------|-----------------|------|
| COMEX / CME metals | Chicago (`America/Chicago`) | Default in JSON root |
| NYMEX energy | New York City (`America/New_York`) | Per-row override on `CL`, `NG`, `RB`, `BZ` |

## Micro contracts

`MGC`, `SIL` (and future micros) need their **own** first volume date — do not copy full-size genesis.

TradingView often has **no 1m history** back to the first daily bar on micro outrights. Use **Daily** (or Weekly), scroll to the leftmost candle, and take that date. If “Go to date” on 1m jumps to a recent month (e.g. Apr 2026 @ 22:00), that is the **start of the 1m feed**, not genesis — ignore it for birth dating.

## Already verified (in train JSON)

**COMEX (Chicago):** GCM26, MGCM26, SIN26, SILN26, PLN26, HGN26, PAM26

**NYMEX (NYC):** CLN26, NGN26, RBN26, BZN26

**Skipped:** HON26 (heating oil)

## Not in this metals/energy slice

Equity indices (`ES=F`, `NQ=F`), rates (`ZN=F`), ag (`ZC=F`), FX (`6E=F`) stay in app treemap tape until you add manifest rows.
