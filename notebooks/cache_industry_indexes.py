# Databricks notebook source
# MAGIC %md
# MAGIC # Cap-Weighted Industry Index Builder (GICS level-3)
# MAGIC
# MAGIC Builds/refreshes `workspace.chartdata.cap_index_levels` — per-date
# MAGIC cap-weighted index level per GICS industry from S&P 500 members cached in
# MAGIC `ohlcv`, weighted by the latest `market_caps` snapshot (static as-of).
# MAGIC
# MAGIC | Parameter | Value | Source |
# MAGIC |-----------|-------|--------|
# MAGIC | `table` | `workspace.chartdata.cap_index_levels` | UC table |

# COMMAND ----------

# MAGIC %pip install -q websockets

# COMMAND ----------

import sys
sys.path.insert(0, "/Workspace/Users/sl.ilya1987@gmail.com/pytvtools-core/src")

from pyspark.sql.types import (
    StructType, StructField, StringType, DoubleType, IntegerType, LongType,
)

from pytvtools_core.cache import _CATALOG, _SCHEMA
from pytvtools_core.measures import cap_weighted_index

OUTPUT_TABLE = f"{_CATALOG}.{_SCHEMA}.cap_index_levels"
CLASS = f"{_CATALOG}.{_SCHEMA}.symbol_classifications"
CAPS = f"{_CATALOG}.{_SCHEMA}.market_caps"
OHLCV = f"{_CATALOG}.{_SCHEMA}.ohlcv"
print(f"Building {OUTPUT_TABLE}")

# COMMAND ----------

# GICS classification: symbol -> industry (exchange-prefixed symbols)
gics_rows = spark.sql(
    f"SELECT symbol, industry FROM {CLASS} WHERE taxonomy = 'gics'"
).collect()
member_industry = {r["symbol"]: r["industry"] for r in gics_rows}
print(f"GICS-classified members: {len(member_industry)}")

# Latest market-cap snapshot: symbol -> cap
caps_rows = spark.sql(
    f"SELECT symbol, market_cap FROM {CAPS} "
    f"WHERE snapshot_date = (SELECT MAX(snapshot_date) FROM {CAPS})"
).collect()
caps = {r["symbol"]: float(r["market_cap"]) for r in caps_rows}
print(f"Latest snapshot caps: {len(caps)}")

# Members that have both a GICS group AND ohlcv data AND a cap
symbols = sorted(set(member_industry) & set(caps))
print(f"Members with data + cap: {len(symbols)}")

# COMMAND ----------

import numpy as np
import pandas as pd


def load_closes(timeframe: str) -> "pd.DataFrame":
    """Pivot member closes: index=unix-ts, columns=symbol."""
    inlist = ", ".join(f"'{s}'" for s in symbols)
    rows = spark.sql(
        f"SELECT UNIX_TIMESTAMP(timestamp) AS ts, symbol, close "
        f"FROM {OHLCV} WHERE timeframe = '{timeframe}' AND symbol IN ({inlist}) "
        f"ORDER BY ts"
    ).collect()
    if not rows:
        raise RuntimeError(f"No ohlcv data for timeframe={timeframe}")
    df = pd.DataFrame(
        {"ts": int(r["ts"]), "symbol": r["symbol"], "close": float(r["close"])}
        for r in rows
    ).pivot(index="ts", columns="symbol", values="close").sort_index()
    df.columns = [str(c) for c in df.columns]
    return df


def build_industries(timeframe: str) -> list[dict]:
    closes = load_closes(timeframe)
    industries = sorted({member_industry[s] for s in symbols if s in closes.columns})
    out: list[dict] = []
    for ind in industries:
        cols = [s for s in symbols if s in closes.columns and member_industry[s] == ind]
        if not cols:
            continue
        mat = closes[cols].to_numpy(float)
        if not np.isfinite(mat).any():
            continue  # no cached data for this industry
        w = np.array([caps[s] for s in cols], dtype=float)
        levels = cap_weighted_index(mat, w)
        n_members = np.isfinite(mat).sum(axis=1)
        for ts, lvl, nm in zip(closes.index.to_numpy(), levels, n_members):
            if np.isfinite(lvl):
                out.append({
                    "symbol": ind, "timeframe": timeframe,
                    "timestamp": int(ts), "level": float(lvl), "n_members": int(nm),
                })
    return out

# COMMAND ----------

rows = build_industries("1D") + build_industries("1W")
print(f"Level rows: {len(rows)}")

df = spark.createDataFrame(rows, schema=StructType([
    StructField("symbol", StringType(), False),
    StructField("timeframe", StringType(), False),
    StructField("timestamp", LongType(), False),
    StructField("level", DoubleType(), False),
    StructField("n_members", IntegerType(), False),
]))
spark.sql(f"DROP TABLE IF EXISTS {OUTPUT_TABLE}")
df.write.mode("overwrite").saveAsTable(OUTPUT_TABLE)
print(f"Wrote {len(rows)} rows to {OUTPUT_TABLE}")

# COMMAND ----------

print(f"Per-timeframe industry count:")
spark.sql(
    f"SELECT timeframe, count(DISTINCT symbol) AS industries, count(*) AS rows "
    f"FROM {OUTPUT_TABLE} GROUP BY timeframe ORDER BY timeframe"
).show(truncate=False)