# pytvtools-core — Agent Guide

Pure Python financial technical indicators and a WebSocket OHLCV data fetcher.

## Key files

| File | What |
|------|------|
| `src/pytvtools_core/indicators.py` | SMA, EMA, RSI, MACD, MFI, BBands, ATR, SRSI, SuperTrend, DSS, Market Cipher B |
| `src/pytvtools_core/watchlists.py` | `Watchlist` dataclass + predefined lists |
| `src/pytvtools_core/tvdata.py` | `TVData` — direct WebSocket OHLCV fetcher |

## Indicator convention

All functions accept `list[float]` (close-only) or `list[dict]` (OHLCV bars with `"close"` key).
Multi-column indicators return `dict[str, list[float | None]]`.
Volume-based indicators require full OHLCV dicts and raise `ValueError` on flat floats.

## Examples

```python
from pytvtools_core.indicators import rsi, macd
from pytvtools_core.tvdata import TVData

async with TVData() as d:
    bars = await d.get_ohlcv("NASDAQ:AAPL", "1D", 500)

closes = [b["close"] for b in bars]
rsi_vals = rsi(closes, period=14)
macd_vals = macd(closes, fast=12, slow=26, signal=9)
```

## Testing

```bash
pytest tests/ -v
```
