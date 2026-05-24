#!/usr/bin/env python3
"""
Fetch CoinGecko market data → public/data/crypto-members/

Categories are coarse buckets (large cap, layer-1, defi, etc.) for treemap browse.
Requires network. Rate-limit friendly (single markets call + category map).

  python3 scripts/build-crypto-members.py
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from collections import defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "public" / "data" / "crypto-members"
USER_AGENT = "RitualROI-TrainCryptoFetch/1.0 (kevencraftrituals/train)"

# CoinGecko id → Yahoo-style symbol for quote prefetch (BTC-USD)
YAHOO_SYMBOL = {
    "bitcoin": "BTC-USD",
    "ethereum": "ETH-USD",
    "solana": "SOL-USD",
    "binancecoin": "BNB-USD",
    "ripple": "XRP-USD",
    "cardano": "ADA-USD",
    "dogecoin": "DOGE-USD",
    "tron": "TRX-USD",
    "chainlink": "LINK-USD",
    "avalanche-2": "AVAX-USD",
    "polkadot": "DOT-USD",
    "litecoin": "LTC-USD",
    "uniswap": "UNI-USD",
    "stellar": "XLM-USD",
    "near": "NEAR-USD",
    "internet-computer": "ICP-USD",
    "ethereum-classic": "ETC-USD",
    "filecoin": "FIL-USD",
    "cosmos": "ATOM-USD",
    "algorand": "ALGO-USD",
}

CATEGORY_RULES: list[tuple[str, str, tuple[str, ...]]] = [
    ("large-cap", "Large cap", ("bitcoin", "ethereum", "binancecoin", "ripple", "solana", "cardano", "dogecoin", "tron")),
    ("layer-1", "Layer 1", ("polkadot", "avalanche-2", "near", "cosmos", "algorand", "litecoin", "ethereum-classic")),
    ("defi", "DeFi", ("chainlink", "uniswap", "internet-computer", "filecoin")),
    ("other-majors", "Other majors", ()),
]


def fetch_json(url: str) -> object:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=90) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main() -> None:
    url = (
        "https://api.coingecko.com/api/v3/coins/markets"
        "?vs_currency=usd&order=market_cap_desc&per_page=100&page=1&sparkline=false&price_change_percentage=24h"
    )
    try:
        markets = fetch_json(url)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
        raise SystemExit(f"CoinGecko fetch failed: {e}") from e

    if not isinstance(markets, list):
        raise SystemExit("Unexpected CoinGecko response")

    by_id = {str(m.get("id") or ""): m for m in markets if m.get("id")}
    assigned: set[str] = set()
    updated = date.today().isoformat()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    index_categories = []

    def add_category(cat_id: str, label: str, coin_ids: tuple[str, ...]) -> None:
        rows = []
        for cid in coin_ids:
            m = by_id.get(cid)
            if not m:
                continue
            assigned.add(cid)
            mc = float(m.get("market_cap") or 0)
            sym = YAHOO_SYMBOL.get(cid) or f"{str(m.get('symbol') or cid).upper()}-USD"
            rows.append(
                {
                    "id": cid,
                    "sy": sym,
                    "cgId": cid,
                    "name": str(m.get("name") or cid),
                    "marketCap": mc,
                    "change24hPct": m.get("price_change_percentage_24h"),
                }
            )
        if not rows:
            return
        rows.sort(key=lambda r: -(r.get("marketCap") or 0))
        total_mc = sum(r.get("marketCap") or 0 for r in rows) or 1
        for r in rows:
            r["weight"] = round(100 * (r.get("marketCap") or 0) / total_mc, 4)
        doc = {
            "categoryId": cat_id,
            "categoryLabel": label,
            "updated": updated,
            "count": len(rows),
            "tickers": rows,
        }
        path = OUT_DIR / f"{cat_id}.json"
        path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        index_categories.append(
            {"categoryId": cat_id, "categoryLabel": label, "file": path.name, "count": len(rows)}
        )

    for cat_id, label, ids in CATEGORY_RULES:
        add_category(cat_id, label, ids)

    # Remaining top coins → other-majors
    rest = []
    for m in markets:
        cid = str(m.get("id") or "")
        if not cid or cid in assigned:
            continue
        mc = float(m.get("market_cap") or 0)
        if mc < 1e9:
            continue
        sym = YAHOO_SYMBOL.get(cid) or f"{str(m.get('symbol') or cid).upper()}-USD"
        rest.append(
            {
                "id": cid,
                "sy": sym,
                "cgId": cid,
                "name": str(m.get("name") or cid),
                "marketCap": mc,
                "change24hPct": m.get("price_change_percentage_24h"),
                "weight": 0,
            }
        )
    rest.sort(key=lambda r: -(r.get("marketCap") or 0))
    rest = rest[:24]
    if rest:
        total_mc = sum(r.get("marketCap") or 0 for r in rest) or 1
        for r in rest:
            r["weight"] = round(100 * (r.get("marketCap") or 0) / total_mc, 4)
        doc = {
            "categoryId": "other-majors",
            "categoryLabel": "Other majors",
            "updated": updated,
            "count": len(rest),
            "tickers": rest,
        }
        path = OUT_DIR / "other-majors.json"
        path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        index_categories.append(
            {"categoryId": "other-majors", "categoryLabel": "Other majors", "file": path.name, "count": len(rest)}
        )

    index = {
        "updated": updated,
        "source": "coingecko_markets_v3",
        "categories": index_categories,
    }
    (OUT_DIR / "index.json").write_text(json.dumps(index, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(index_categories)} crypto categories to {OUT_DIR}")
    time.sleep(0.2)


if __name__ == "__main__":
    main()
