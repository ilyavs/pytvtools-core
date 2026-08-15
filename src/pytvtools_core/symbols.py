"""Ticker normalization and bare -> exchange-prefixed resolution.

TradingView's scanner only resolves exchange-prefixed tickers
(``NASDAQ:AAPL``, ``NYSE:BRK.B``); bare tickers return zero results.  This
module is the single place that converts user-facing ticker forms (bare,
dash-form ``BRK-B``, underscore ``BRK_B``) into the canonical prefixed form
every stored source (watchlists, UC tables, caches) uses.
"""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

logger = logging.getLogger(__name__)

_SYM_SEARCH_URL = (
    "https://symbol-search.tradingview.com/symbol_search/v3/"
    "?text={text}&lang=en&domain=production"
)

_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)

# symbol-search exchange name -> scanner prefix
_EXCHANGE_MAP: dict[str, str] = {"NYSE Arca": "AMEX"}

# exchanges with a stable scanner prefix, preferred for US listings
_US_EXCHANGES: tuple[str, ...] = ("NYSE", "NASDAQ", "AMEX")

# bare normalized ticker -> "EXCHANGE:TICKER", process lifetime
_resolve_cache: dict[str, str] = {}


def normalize_symbol(sym: str) -> str:
    """Dash/underscore in the ticker portion -> dot; prefix preserved."""
    if ":" in sym:
        prefix, ticker = sym.split(":", 1)
        return f"{prefix}:{ticker.replace('-', '.').replace('_', '.')}"
    return sym.replace("-", ".").replace("_", ".")


def _get_json(url: str, timeout: float) -> dict[str, Any]:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": _UA, "Referer": "https://www.tradingview.com/"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def _best_hit(ticker: str, symbols: list[dict[str, Any]]) -> str | None:
    """Pick the best ``EXCHANGE:SYMBOL`` for a ticker from symbol-search rows.

    Priority: exact normalized symbol match, then US exchange, then
    instrument type (stock > fund/dr), then shorter exchange name.
    Returns None when there are no rows.
    """
    norm = normalize_symbol(ticker)

    def exact(row: dict[str, Any]) -> bool:
        return normalize_symbol(str(row.get("symbol", ""))) == norm

    pool = [r for r in symbols if exact(r)] or list(symbols)
    if not pool:
        return None

    def key(row: dict[str, Any]) -> tuple[int, int, int, int]:
        exch = _EXCHANGE_MAP.get(row.get("exchange", ""), row.get("exchange", ""))
        type_rank = 1 if row.get("type") == "stock" else (
            0 if row.get("type") in ("fund", "dr") else -1
        )
        return (
            1 if exch in _US_EXCHANGES else 0,
            type_rank,
            0 if exch in _US_EXCHANGES else 1,
            -len(str(row.get("exchange", ""))),
        )

    best = max(pool, key=key)
    exch = _EXCHANGE_MAP.get(str(best.get("exchange", "")), str(best.get("exchange", "")))
    return f"{exch}:{best['symbol']}"


def _symbol_search(ticker: str, timeout: float) -> str | None:
    url = _SYM_SEARCH_URL.format(text=urllib.parse.quote(ticker))
    data = _get_json(url, timeout)
    return _best_hit(ticker, data.get("symbols", []))


# ---------------------------------------------------------------------------
#  Scanner screen() sweep fallback (Databricks-proven resolution path)
# ---------------------------------------------------------------------------

_sweep_cache: dict[tuple[str, tuple[str, ...]], dict[str, str]] = {}


def _sweep_map(
    market: str,
    exchanges: tuple[str, ...] = ("NYSE", "NASDAQ", "AMEX"),
) -> dict[str, str]:
    """bare -> prefixed map built from one scanner screen() per exchange."""
    from pytvtools_core.watchlists import screen

    key = (market, exchanges)
    if key in _sweep_cache:
        return _sweep_cache[key]
    out: dict[str, str] = {}
    for exch in exchanges:
        rows, _ = screen(market=market, exchange=exch)
        for r in rows:
            sym = str(r["symbol"])
            bare = sym.split(":", 1)[1] if ":" in sym else sym
            out[normalize_symbol(bare)] = sym
    _sweep_cache[key] = out
    return out


# ---------------------------------------------------------------------------
#  Public API
# ---------------------------------------------------------------------------

def resolve_symbols(
    tickers: list[str],
    market: str = "america",
    timeout: float = 30.0,
) -> dict[str, str]:
    """Resolve bare/dash/underscore tickers to ``EXCHANGE:TICKER``.

    Already-prefixed inputs pass through unchanged.  Bare inputs are resolved
    via symbol-search v3 (preferred US listing); if symbol-search fails or
    finds nothing, a scanner ``screen()`` sweep per exchange is used as a
    fallback.  Unresolvable tickers are omitted from the result.  Results are
    cached per normalized ticker for the process lifetime.

    Returns ``{input: "EXCHANGE:TICKER"}`` keyed by the exact input string.
    """
    out: dict[str, str] = {}
    missing: list[str] = []
    for sym in tickers:
        if ":" in sym:
            out[sym] = sym
            continue
        cached = _resolve_cache.get(normalize_symbol(sym))
        if cached is not None:
            out[sym] = cached
        else:
            missing.append(sym)

    if not missing:
        return out

    for sym in missing:
        resolved: str | None = None
        try:
            resolved = _symbol_search(normalize_symbol(sym), timeout)
        except (urllib.error.HTTPError, urllib.error.URLError) as exc:
            logger.warning("symbol-search failed for %s (%s); trying sweep", sym, exc)
        if resolved is None:
            try:
                resolved = _sweep_map(market).get(normalize_symbol(sym))
            except Exception as exc:  # noqa: BLE001 — mirror screen()'s failure mode
                logger.warning("screen sweep failed for %s (%s)", sym, exc)
        if resolved is not None:
            _resolve_cache[normalize_symbol(sym)] = resolved
            out[sym] = resolved
        else:
            logger.warning("unresolvable ticker: %s", sym)
    return out
