# pytvtools-core

Your favorite indicators now easily accessible in Python.

Pure Python implementations of common financial technical indicators — SMA, EMA, RSI, MACD, MFI, Bollinger Bands, ATR, Stochastic RSI, SuperTrend, DSS, and Market Cipher B. Also includes a fast WebSocket OHLCV data fetcher.

## Install

```bash
pip install pytvtools-core
```

Or from source:

```bash
pip install -e .
```

## Quick start

```python
from pytvtools_core.indicators import rsi, sma, macd

closes = [44.34, 44.09, 44.15, 43.61, 44.33, 44.83, 45.10, 45.42,
          45.84, 46.08, 45.89, 46.03, 45.61, 46.28, 46.28, 46.00]

rsi_vals = rsi(closes, period=14)
sma_vals = sma(closes, period=5)
macd_vals = macd(closes, fast=12, slow=26, signal=9)
```

## Fetching data

```python
from pytvtools_core.tvdata import TVData

async with TVData() as d:
    bars = await d.get_ohlcv("NASDAQ:AAPL", "1D", 500)
    summary = await d.get_ohlcv("BINANCE:BTCUSDT", "1D", 500, summary=True)
```

## All indicators

| Function | Returns | Notes |
|----------|---------|-------|
| `sma(data, period)` | `list[float\|None]` | Simple Moving Average |
| `ema(data, period)` | `list[float\|None]` | Exponential Moving Average |
| `rsi(data, period)` | `list[float\|None]` | Wilder's RSI |
| `mfi(data, period)` | `list[float\|None]` | Requires OHLCV dicts with volume |
| `atr(data, period)` | `list[float\|None]` | Average True Range |
| `macd(data, fast, slow, signal)` | `dict` | macd, signal, histogram |
| `bbands(data, period, stddev)` | `dict` | upper, basis, lower |
| `srsi(data, period, smooth_k, smooth_d)` | `dict` | k, d |
| `supertrend(data, period, multiplier)` | `dict` | up_trend, down_trend |
| `dss(data, pds, ema_len, trigger_len)` | `dict` | dss, trigger |
| `market_cipher_b(data, channel_length, average_length)` | `dict` | wt1, wt2, wt1_minus_wt2 |

## Testing

```bash
pytest tests/ -v
```
