# Databricks notebook source
# MAGIC %md
# MAGIC # Market Caps Builder
# MAGIC
# MAGIC Refreshes `workspace.chartdata.market_caps` — one row per (symbol,
# MAGIC snapshot_date) holding the current market cap (`market_cap_basic`) of
# MAGIC every GICS-classified S&P 500 member, fetched from the TradingView
# MAGIC scanner. Each run appends a new dated snapshot; re-running on the same
# MAGIC day replaces that day's rows (idempotent). Consumers pick the latest
# MAGIC snapshot: `WHERE snapshot_date = (SELECT MAX(snapshot_date) FROM ...)`.
# MAGIC
# MAGIC **Universe source**: the GICS rows of `symbol_classifications`
# MAGIC (`taxonomy = 'gics'`) — the same table every downstream GICS consumer
# MAGIC (cache_industry_indexes, absorption_ratio) reads. Using the live
# MAGIC `get_sp500()` list instead let the two tables diverge (members like VEEV
# MAGIC were classified but got no cap), which silently dropped members from the
# MAGIC cap-weighted industry levels and clipped the aligned GICS calendar.
# MAGIC `get_sp500()` is only a fallback when the classifications table has no
# MAGIC gics rows yet.
# MAGIC
# MAGIC | Parameter | Value | Source |
# MAGIC |-----------|-------|--------|
# MAGIC | `table` | `workspace.chartdata.market_caps` | UC table |

# COMMAND ----------

# MAGIC %pip install -q websockets

# COMMAND ----------

import sys
from datetime import datetime, timezone

sys.path.insert(0, "/Workspace/Users/sl.ilya1987@gmail.com/pytvtools-core/src")

from pyspark.sql.types import StructType, StructField, StringType, DoubleType, DateType

from pytvtools_core.cache import _CATALOG, _SCHEMA
from pytvtools_core.watchlists import get_market_caps, get_sp500

OUTPUT_TABLE = f"{_CATALOG}.{_SCHEMA}.market_caps"
CLASS = f"{_CATALOG}.{_SCHEMA}.symbol_classifications"
print(f"Refreshing {OUTPUT_TABLE}")

# COMMAND ----------

# Universe of record: the gics rows of symbol_classifications (same source the
# downstream GICS chain reads). Fall back to the live S&P 500 list only when
# no gics classification rows exist yet.
import contextlib

with contextlib.suppress(Exception):
    cls_rows = spark.sql(
        f"SELECT DISTINCT symbol FROM {CLASS} WHERE taxonomy = 'gics'"
    ).collect()
    cls_symbols = [r["symbol"] for r in cls_rows]

if cls_symbols:
    members = cls_symbols
    print(f"Universe from symbol_classifications (gics): {len(members)} symbols")
else:
    members = list(get_sp500().symbols)
    print(f"Universe from get_sp500() fallback: {len(members)} symbols")

# get_market_caps() normalizes/resolves exchange-prefixed forms internally.
tickers = members
print(f"S&P 500 members: {len(tickers)}")

caps = get_market_caps(tickers)
print(f"Caps resolved: {len(caps)} / {len(tickers)}")

# COMMAND ----------

snapshot_date = datetime.now(timezone.utc).date()
rows = [
    {"symbol": sym, "market_cap": float(cap), "snapshot_date": snapshot_date}
    for sym, cap in caps.items()
]
if not rows:
    raise RuntimeError(
        f"no market caps resolved for {len(tickers)} tickers — aborting to "
        "protect today's existing snapshot"
    )

df = spark.createDataFrame(rows, schema=StructType([
    StructField("symbol", StringType(), False),
    StructField("market_cap", DoubleType(), False),
    StructField("snapshot_date", DateType(), False),
]))

# Same-day re-run is idempotent: drop today's snapshot, then append.
# Guard the DELETE — the table may not exist on the first run.
from pyspark.sql.utils import AnalysisException
try:
    spark.sql(f"DELETE FROM {OUTPUT_TABLE} WHERE snapshot_date = DATE '{snapshot_date}'")
except AnalysisException:
    pass

df.write.mode("append").saveAsTable(OUTPUT_TABLE)
print(f"Wrote {len(rows)} rows for {snapshot_date}")

# COMMAND ----------

spark.sql(
    f"SELECT snapshot_date, count(*) AS n, round(sum(market_cap)/1e12, 2) AS total_trillion "
    f"FROM {OUTPUT_TABLE} GROUP BY snapshot_date ORDER BY snapshot_date DESC LIMIT 5"
).show(truncate=False)
