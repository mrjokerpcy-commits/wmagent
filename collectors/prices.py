"""
Market Prices Collector
- Yahoo Finance: stocks, ETFs, commodities, forex
- Binance WebSocket: crypto real-time
"""

import httpx
import json
import asyncio
import websockets
from datetime import datetime, timezone
from typing import Callable


YAHOO_FINANCE_URL = "https://query1.finance.yahoo.com/v8/finance/chart"

# Key assets to track
TRACKED_ASSETS = {
    "equities": ["SPY", "QQQ", "AAPL", "NVDA", "TSM"],
    "commodities": ["CL=F", "GC=F", "NG=F", "ZW=F"],  # oil, gold, gas, wheat
    "forex": ["EURUSD=X", "JPY=X", "DX-Y.NYB"],        # EUR/USD, USD/JPY, DXY
    "crypto": ["BTC-USD", "ETH-USD"],
    "rates": ["^TNX", "^TYX"],                           # 10Y, 30Y Treasury
    "volatility": ["^VIX"],
}


async def fetch_price(symbol: str) -> dict | None:
    """Fetch current price + 1d change for a symbol via Yahoo Finance."""
    async with httpx.AsyncClient(timeout=15) as client:
        try:
            resp = await client.get(
                f"{YAHOO_FINANCE_URL}/{symbol}",
                params={"interval": "1m", "range": "1d"},
                headers={"User-Agent": "Mozilla/5.0"},
            )
            resp.raise_for_status()
            data = resp.json()
            result = data["chart"]["result"][0]
            meta = result["meta"]
            return {
                "symbol": symbol,
                "price": meta.get("regularMarketPrice"),
                "prev_close": meta.get("previousClose") or meta.get("chartPreviousClose"),
                "change_pct": _calc_change(
                    meta.get("regularMarketPrice"),
                    meta.get("previousClose") or meta.get("chartPreviousClose"),
                ),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        except Exception:
            return None


async def fetch_all_prices() -> dict[str, dict]:
    """Fetch all tracked assets concurrently."""
    all_symbols = [s for group in TRACKED_ASSETS.values() for s in group]
    tasks = [fetch_price(symbol) for symbol in all_symbols]
    results = await asyncio.gather(*tasks)
    return {r["symbol"]: r for r in results if r}


async def binance_websocket(
    symbols: list[str],
    on_price: Callable[[dict], None],
):
    """
    Stream real-time crypto prices from Binance.
    symbols: ["btcusdt", "ethusdt"]
    """
    streams = "/".join(f"{s.lower()}@trade" for s in symbols)
    url = f"wss://stream.binance.com:9443/stream?streams={streams}"

    async with websockets.connect(url) as ws:
        async for msg in ws:
            data = json.loads(msg)
            trade = data.get("data", {})
            on_price({
                "symbol": trade.get("s"),
                "price": float(trade.get("p", 0)),
                "quantity": float(trade.get("q", 0)),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })


def _calc_change(current: float | None, prev: float | None) -> float | None:
    if not current or not prev or prev == 0:
        return None
    return round((current - prev) / prev * 100, 4)
