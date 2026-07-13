# Databricks notebook source
# MAGIC %md
# MAGIC # Market Data Cache Refresh
# MAGIC
# MAGIC Refreshes the UC market data cache for S&P 500 constituents (or a single symbol).
# MAGIC Run as a scheduled Databricks job or on-demand for ad-hoc refresh.
# MAGIC
# MAGIC | Parameter | Value | Source |
# MAGIC |-----------|-------|--------|
# MAGIC | `timeframe` | `"1D"`, `"1W"`, or `"1M"` | Job parameter |
# MAGIC | `symbol` | `"NASDAQ:AAPL"` (optional) | Omit for S&P 500 batch |
# MAGIC | `mode` | `"incremental"` or `"backfill"` | Use ``backfill`` for initial load (pagination), ``incremental`` for scheduled runs |
# MAGIC | `table` | `workspace.chartdata.ohlcv` | UC table |

# COMMAND ----------

# MAGIC %pip install -q websockets

# COMMAND ----------

import sys
sys.path.insert(0, "/Workspace/Users/sl.ilya1987@gmail.com/pytvtools-core/src")

import asyncio
from pytvtools_core.cache import MarketDataCache

dbutils.widgets.text("timeframe", "1D")
dbutils.widgets.text("symbol", "")
dbutils.widgets.text("mode", "incremental")

timeframe = dbutils.widgets.get("timeframe")
assert timeframe in ("1D", "1W", "1M"), f"Invalid timeframe: {timeframe}"

symbol = dbutils.widgets.get("symbol") or None
mode = dbutils.widgets.get("mode")
assert mode in ("incremental", "backfill"), f"Invalid mode: {mode}"

mode_label = f"single={symbol}" if symbol else "S&P 500 batch"
print(f"Refreshing cache: timeframe={timeframe}, mode={mode}, {mode_label}")

# COMMAND ----------

if symbol:
    symbols = [symbol]
else:
    from pytvtools_core.watchlists import get_sp500
    sp500 = get_sp500()
    symbols = sorted(sp500.symbols)
    print(f"S&P 500 constituents: {len(symbols)}")

# COMMAND ----------

# Initialize cache (spark mode = UC via Delta)
cache = MarketDataCache(mode="spark")

# COMMAND ----------

# Refresh in batches to avoid overwhelming the WebSocket connection
total_fetched = 0
total_inserted = 0

if mode == "backfill":
    # Paginated full history — slower per symbol but gets max data
    BATCH_SIZE = 1 if symbol else 10
    MAX_CONCURRENT = 1 if symbol else 2
    CHUNK_SIZE = 4000
    refresh_func = cache.refresh_multi_all
    refresh_kwargs = {"chunk_size": CHUNK_SIZE, "max_concurrent": MAX_CONCURRENT}
    print(f"Using paginated backfill: chunk_size={CHUNK_SIZE}, batch={BATCH_SIZE}, concurrency={MAX_CONCURRENT}")
else:
    # Incremental — fast, fetches only recent bars
    BATCH_SIZE = 1 if symbol else 25
    MAX_CONCURRENT = 1 if symbol else 2
    BARS_COUNT = 500 if symbol else 2000
    refresh_func = cache.refresh_multi
    refresh_kwargs = {"bars_count": BARS_COUNT, "max_concurrent": MAX_CONCURRENT}
    print(f"Using incremental refresh: bars_count={BARS_COUNT}, batch={BATCH_SIZE}, concurrency={MAX_CONCURRENT}")

for i in range(0, len(symbols), BATCH_SIZE):
    batch = symbols[i:i + BATCH_SIZE]
    print(f"Batch {i // BATCH_SIZE + 1}/{(len(symbols) + BATCH_SIZE - 1) // BATCH_SIZE}: "
          f"{batch[0]}…{batch[-1]}")

    result = await refresh_func(batch, [timeframe], **refresh_kwargs)

    for sym in batch:
        if sym in result and timeframe in result[sym]:
            r = result[sym][timeframe]
            total_fetched += r["fetched"]
            total_inserted += r["inserted"]

    print(f"  → fetched={total_fetched} inserted={total_inserted} (cumulative)")
    await asyncio.sleep(5)

# COMMAND ----------

print(f"Done. Total fetched: {total_fetched}, total inserted: {total_inserted}")

# Log latest timestamps for a few symbols to confirm
check_symbols = symbols[:5]
rows = cache.latest_timestamps(check_symbols, [timeframe])
for r in rows:
    print(f"  {r['symbol']}: last bar = {r['latest']}")
