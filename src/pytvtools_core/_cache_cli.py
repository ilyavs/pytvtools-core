"""
CLI for ``pytvtools-cache`` — cache market data from TradingView.

Usage::

    # Refresh local parquet cache
    pytvtools-cache refresh --symbols NASDAQ:AAPL BINANCE:BTCUSDT --timeframes 1D 60

    # Refresh via Databricks SDK
    pytvtools-cache refresh --mode sdk --warehouse-id ... --symbols NASDAQ:AAPL

    # Check cache status
    pytvtools-cache status

    # Dump cached bars as JSON
    pytvtools-cache dump --symbol NASDAQ:AAPL --timeframe 1D
"""
from __future__ import annotations

import argparse
import asyncio
import json

from pytvtools_core.cache import MarketDataCache


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Cache market data from TradingView.")
    p.add_argument("--mode", default="local", choices=["local", "sdk"], help="Storage mode")
    p.add_argument("--cache-dir", default="data/market_cache", help="Local cache directory")
    p.add_argument("--warehouse-id", help="SQL warehouse ID (sdk mode)")
    p.add_argument("--profile", default="DEFAULT", help="Databricks CLI profile")

    sub = p.add_subparsers(dest="command", required=True)

    refresh = sub.add_parser("refresh", help="Fetch and cache bars")
    refresh.add_argument("--symbols", nargs="+", required=True)
    refresh.add_argument("--timeframes", nargs="+", required=True)
    refresh.add_argument("--bars", type=int, default=1500)

    status = sub.add_parser("status", help="Show cached timestamp per symbol/tf")
    status.add_argument("--symbols", nargs="+")
    status.add_argument("--timeframes", nargs="+")

    dump = sub.add_parser("dump", help="Dump cached bars as JSON")
    dump.add_argument("--symbol", required=True)
    dump.add_argument("--timeframe", required=True)
    dump.add_argument("--since", type=float)
    dump.add_argument("--until", type=float)
    dump.add_argument("--pretty", action="store_true")

    return p


async def _run() -> None:
    args = _parser().parse_args()

    cache = MarketDataCache(
        mode=args.mode,
        cache_dir=args.cache_dir,
        warehouse_id=args.warehouse_id,
        profile=args.profile,
    )

    if args.command == "refresh":
        result = await cache.refresh_multi(args.symbols, args.timeframes, args.bars)
        for sym, tfs in result.items():
            for tf, counts in tfs.items():
                print(f"{sym} {tf}: fetched={counts['fetched']} inserted={counts['inserted']}")

    elif args.command == "status":
        rows = cache.latest_timestamps(args.symbols, args.timeframes)
        if not rows:
            print("No cached data found.")
            return
        for r in rows:
            print(f"{r['symbol']} {r['timeframe']}: last bar at {r['latest']}")

    elif args.command == "dump":
        rows = cache.query(args.symbol, args.timeframe, args.since, args.until)
        indent = 2 if args.pretty else None
        print(json.dumps(rows, indent=indent, default=str))


def main() -> None:
    asyncio.run(_run())


if __name__ == "__main__":
    main()
