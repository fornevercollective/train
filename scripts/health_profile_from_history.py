"""Build SnowflakeProfileV1 scores from daily OHLCV (no external fundamentals API)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
SERIES_DIR = ROOT / "public" / "data" / "history" / "series" / "v1"
SCHEMA_VERSION = 1

AXES: tuple[tuple[str, str, list[tuple[str, str]]], ...] = (
    (
        "value",
        "Value",
        [
            ("price-vs-fair", "Trading below estimated fair value"),
            ("price-vs-peers", "Price-to-earnings vs peers"),
        ],
    ),
    (
        "future",
        "Future",
        [
            ("eps-growth-fwd", "Forecast EPS growth above market"),
            ("revenue-growth-fwd", "Forecast revenue growth above market"),
            ("roe-forecast", "Forecast return on equity"),
        ],
    ),
    (
        "past",
        "Past",
        [
            ("eps-growth-5y", "EPS growth over the past 5 years"),
            ("revenue-growth-5y", "Revenue growth over the past 5 years"),
            ("eps-acceleration-1y", "EPS growth accelerating last 12 months"),
        ],
    ),
    (
        "health",
        "Health",
        [
            ("debt-to-equity", "Debt-to-equity ratio in safe range"),
            ("operating-cashflow", "Operating cashflow covers debt"),
            ("interest-coverage", "Interest coverage ratio healthy"),
        ],
    ),
    (
        "dividends",
        "Dividends",
        [
            ("dividend-yield", "Dividend yield is above market average"),
            ("payout-ratio", "Payout ratio is sustainable"),
            ("dividend-growth", "Dividend growth is positive"),
        ],
    ),
)


@dataclass
class HistoryMetrics:
    rows: int
    ret_1y_pct: float
    ret_6m_pct: float
    ret_3m_pct: float
    ret_5y_pct: float
    ann_vol_pct: float
    max_drawdown_pct: float
    win_rate_pct: float
    volume_trend: float
    last_close: float


def _safe_filename(ticker_id: str) -> str:
    return "".join(ch if ch.isalnum() or ch in "._-" else "-" for ch in ticker_id) + ".json"


def history_path_for_record(record: dict[str, Any]) -> Path:
    return SERIES_DIR / _safe_filename(str(record.get("id") or ""))


def load_history_series(record: dict[str, Any]) -> dict[str, Any] | None:
    path = history_path_for_record(record)
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if int(payload.get("rows") or 0) < 22:
            return None
        return payload
    except (json.JSONDecodeError, TypeError, ValueError):
        return None


def compute_metrics(series: dict[str, Any]) -> HistoryMetrics | None:
    closes = series.get("c")
    volumes = series.get("v")
    if not isinstance(closes, list) or len(closes) < 22:
        return None

    n = len(closes)

    def close_at(offset_from_end: int) -> float:
        idx = max(0, n - 1 - offset_from_end)
        return float(closes[idx] or 0)

    def total_return(days: int) -> float:
        if n <= days:
            a, b = float(closes[0]), float(closes[-1])
        else:
            a, b = close_at(days), close_at(0)
        if a <= 0:
            return 0.0
        return (b / a - 1) * 100

    returns: list[float] = []
    wins = 0
    for i in range(1, n):
        a, b = float(closes[i - 1]), float(closes[i])
        if a <= 0 or b <= 0:
            continue
        r = (b / a - 1) * 100
        returns.append(r)
        if r > 0:
            wins += 1

    mean = sum(returns) / max(len(returns), 1)
    var = sum((r - mean) ** 2 for r in returns) / max(len(returns), 1)
    ann_vol = (var**0.5) * (252**0.5)

    peak = float(closes[0])
    max_dd = 0.0
    for c in closes:
        c = float(c)
        if c > peak:
            peak = c
        dd = (c - peak) / peak if peak else 0
        if dd < max_dd:
            max_dd = dd

    vol_tail = volumes[-63:] if isinstance(volumes, list) and len(volumes) >= 63 else volumes or []
    vol_recent = vol_tail[-21:] if len(vol_tail) >= 21 else vol_tail
    avg_vol = sum(vol_tail) / max(len(vol_tail), 1) if vol_tail else 1
    recent_avg = sum(vol_recent) / max(len(vol_recent), 1) if vol_recent else avg_vol

    return HistoryMetrics(
        rows=n,
        ret_1y_pct=total_return(252),
        ret_6m_pct=total_return(126),
        ret_3m_pct=total_return(63),
        ret_5y_pct=total_return(min(252 * 5, n - 1)),
        ann_vol_pct=ann_vol,
        max_drawdown_pct=max_dd * 100,
        win_rate_pct=(wins / max(len(returns), 1)) * 100,
        volume_trend=recent_avg / max(avg_vol, 1),
        last_close=float(closes[-1]),
    )


def _check_state(check_id: str, m: HistoryMetrics) -> tuple[str, str]:
    """Return (state, detail) for one check id."""

    if check_id == "price-vs-fair":
        # Proxy: negative 6m return suggests price fell vs prior fair-value window.
        if m.ret_6m_pct < -5:
            return "pass", f"6m return {m.ret_6m_pct:+.1f}% (below recent trend)"
        if m.ret_6m_pct > 15:
            return "fail", f"6m return {m.ret_6m_pct:+.1f}% (extended vs window)"
        return "na", f"6m return {m.ret_6m_pct:+.1f}% — no fair-value model"

    if check_id == "price-vs-peers":
        if m.ann_vol_pct < 35:
            return "pass", f"Ann. vol {m.ann_vol_pct:.1f}% vs high-vol peers"
        return "fail", f"Ann. vol {m.ann_vol_pct:.1f}% elevated vs typical large-cap"

    if check_id == "eps-growth-fwd":
        return "na", "Requires forecast EPS feed (FMP/EDGAR)"

    if check_id == "revenue-growth-fwd":
        if m.ret_6m_pct > 8:
            return "pass", f"6m price return {m.ret_6m_pct:+.1f}% (momentum proxy)"
        if m.ret_6m_pct < -8:
            return "fail", f"6m price return {m.ret_6m_pct:+.1f}%"
        return "na", f"6m return {m.ret_6m_pct:+.1f}% — revenue forecast unavailable"

    if check_id == "roe-forecast":
        return "na", "Requires ROE forecast feed"

    if check_id == "eps-growth-5y":
        if m.ret_5y_pct > 20:
            return "pass", f"~5y window return {m.ret_5y_pct:+.1f}%"
        if m.ret_5y_pct < -10:
            return "fail", f"~5y window return {m.ret_5y_pct:+.1f}%"
        return "na", f"~5y return {m.ret_5y_pct:+.1f}% — EPS series unavailable"

    if check_id == "revenue-growth-5y":
        if m.ret_5y_pct > 10:
            return "pass", f"~5y window return {m.ret_5y_pct:+.1f}% (revenue proxy)"
        if m.ret_5y_pct < 0:
            return "fail", f"~5y window return {m.ret_5y_pct:+.1f}%"
        return "na", f"~5y return {m.ret_5y_pct:+.1f}%"

    if check_id == "eps-acceleration-1y":
        if m.ret_3m_pct > m.ret_1y_pct / 4:
            return "pass", f"3m {m.ret_3m_pct:+.1f}% vs 1y {m.ret_1y_pct:+.1f}%"
        return "fail", f"3m {m.ret_3m_pct:+.1f}% vs 1y {m.ret_1y_pct:+.1f}%"

    if check_id == "debt-to-equity":
        if m.max_drawdown_pct > -25:
            return "pass", f"Max drawdown {m.max_drawdown_pct:.1f}% (stability proxy)"
        return "fail", f"Max drawdown {m.max_drawdown_pct:.1f}%"

    if check_id == "operating-cashflow":
        if m.volume_trend > 0.85 and m.ret_6m_pct > -15:
            return "pass", f"Volume trend {m.volume_trend:.2f}× avg"
        return "na", "Cashflow statement not in OHLCV shim"

    if check_id == "interest-coverage":
        if m.ann_vol_pct < 50 and m.win_rate_pct > 45:
            return "pass", f"Win rate {m.win_rate_pct:.0f}% · vol {m.ann_vol_pct:.1f}%"
        return "fail", f"Win rate {m.win_rate_pct:.0f}% · vol {m.ann_vol_pct:.1f}%"

    if check_id == "dividend-yield":
        return "na", "Dividend history not in OHLCV shim"

    if check_id == "payout-ratio":
        return "na", "Payout ratio requires fundamentals feed"

    if check_id == "dividend-growth":
        if m.ret_1y_pct > 0 and m.win_rate_pct > 50:
            return "pass", f"1y return {m.ret_1y_pct:+.1f}% with {m.win_rate_pct:.0f}% up days"
        return "na", "Dividend events not in OHLCV shim"

    return "na", "Unmapped check"


def build_scored_profile(record: dict[str, Any], series: dict[str, Any]) -> dict[str, Any]:
    metrics = compute_metrics(series)
    if not metrics:
        return skeletal_profile(record)

    now = datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    axes_out = []
    for name, label, checks in AXES:
        check_rows = []
        passed = 0
        for check_id, check_label in checks:
            state, detail = _check_state(check_id, metrics)
            if state == "pass":
                passed += 1
            check_rows.append(
                {"id": check_id, "label": check_label, "detail": detail, "state": state}
            )
        axes_out.append(
            {
                "name": name,
                "label": label,
                "scoreLabel": f"{passed}/{len(checks)}",
                "passed": passed,
                "total": len(checks),
                "checks": check_rows,
            }
        )

    return {
        "schemaVersion": SCHEMA_VERSION,
        "ticker": record["id"],
        "displayName": record.get("nm") or record.get("ln") or record["id"],
        "asOfISO": str(series.get("asOfISO") or now),
        "sourceNotes": [
            "OHLCV-derived scores from public/data/history/ (health_profile_from_history.py)",
            f"{metrics.rows} daily bars · source {series.get('source', 'unknown')}",
        ],
        "axes": axes_out,
    }


def skeletal_profile(record: dict[str, Any]) -> dict[str, Any]:
    axes = []
    for name, label, checks in AXES:
        axes.append(
            {
                "name": name,
                "label": label,
                "scoreLabel": f"0/{len(checks)}",
                "passed": 0,
                "total": len(checks),
                "checks": [
                    {
                        "id": check_id,
                        "label": check_label,
                        "detail": "Awaiting OHLCV backfill (npm run database:history).",
                        "state": "na",
                    }
                    for check_id, check_label in checks
                ],
            }
        )
    return {
        "schemaVersion": SCHEMA_VERSION,
        "ticker": record["id"],
        "displayName": record.get("nm") or record.get("ln") or record["id"],
        "asOfISO": "1970-01-01T00:00:00Z",
        "sourceNotes": [
            "Skeleton scaffold; run database:backfill to add OHLCV + scored checks.",
        ],
        "axes": axes,
    }


def profile_for_record(record: dict[str, Any]) -> dict[str, Any]:
    series = load_history_series(record)
    if series:
        return build_scored_profile(record, series)
    return skeletal_profile(record)
