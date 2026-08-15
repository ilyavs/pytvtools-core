"""Predefined watchlist library — object-oriented, extensible.

All watchlists are frozen ``Watchlist`` instances with a ``name`` and
immutable ``symbols`` tuple.  Use them directly with ``Collector``::

    from pytvtools_core.watchlists import SPDR_SECTORS
    from pytvtools import Collector, CollectorConfig

    config = CollectorConfig(
        symbols=list(SPDR_SECTORS),
        timeframes=["1D", "60"],
        actions=["ohlcv"],
    )
"""

from __future__ import annotations

import dataclasses
import json
import urllib.error
import urllib.request
from typing import Iterator

from pytvtools_core.symbols import resolve_symbols

_SCANNER_URL = "https://scanner.tradingview.com/{market}/scan"
_PAGE_SIZE = 100


@dataclasses.dataclass(frozen=True)
class Watchlist:
    """A named collection of trading symbols.

    Parameters
    ----------
    name : str
        Human-readable label.
    symbols : tuple[str, ...]
        Ticker symbols as exchange-prefixed strings (``"NYSE:BRK.B"``,
        ``"AMEX:XLK"``).  No bare tickers.
    """

    name: str
    symbols: tuple[str, ...]

    # -- convenience -------------------------------------------------------

    def __len__(self) -> int:
        return len(self.symbols)

    def __iter__(self) -> Iterator[str]:
        return iter(self.symbols)

    def __getitem__(self, index: int) -> str:
        return self.symbols[index]

    def __contains__(self, symbol: str) -> bool:
        return symbol in self.symbols

    def __repr__(self) -> str:
        return f"Watchlist({self.name!r}, n={len(self.symbols)})"


# ---------------------------------------------------------------------------
# SPDR Select Sector (S&P 500 sectors — market-cap weighted)
# ---------------------------------------------------------------------------

SPDR_SECTORS = Watchlist(
    name="SPDR S&P 500 Select Sectors",
    symbols=(
        "AMEX:XLK",   # Technology
        "AMEX:XLC",   # Communication Services
        "AMEX:XLY",   # Consumer Discretionary
        "AMEX:XLP",   # Consumer Staples
        "AMEX:XLE",   # Energy
        "AMEX:XLF",   # Financials
        "AMEX:XLV",   # Health Care
        "AMEX:XLI",   # Industrials
        "AMEX:XLB",   # Materials
        "AMEX:XLRE",  # Real Estate
        "AMEX:XLU",   # Utilities
    ),
)

SPDR_SECTORS_CORE = Watchlist(
    name="SPDR S&P 500 Select Sectors — original 9 (no XLC/XLRE)",
    symbols=(
        "AMEX:XLK",   # Technology
        "AMEX:XLY",   # Consumer Discretionary
        "AMEX:XLP",   # Consumer Staples
        "AMEX:XLE",   # Energy
        "AMEX:XLF",   # Financials
        "AMEX:XLV",   # Health Care
        "AMEX:XLI",   # Industrials
        "AMEX:XLB",   # Materials
        "AMEX:XLU",   # Utilities
    ),
)

# ---------------------------------------------------------------------------
# SPDR Industry ETFs (sub-sector / modified equal-weight)
# ---------------------------------------------------------------------------

SPDR_INDUSTRIES = Watchlist(
    name="SPDR Industry ETFs",
    symbols=(
        "AMEX:XBI",   # Biotech
        "AMEX:XPH",   # Pharmaceuticals
        "AMEX:XHS",   # Health Care Services
        "AMEX:XHE",   # Health Care Equipment
        "AMEX:XAR",   # Aerospace & Defense
        "AMEX:XHB",   # Homebuilders
        "AMEX:XRT",   # Retail
        "AMEX:XOP",   # Oil & Gas Exploration & Production
        "AMEX:XES",   # Oil & Gas Equipment & Services
        "AMEX:XME",   # Metals & Mining
        "AMEX:XSD",   # Semiconductor
        "AMEX:XSW",   # Software & Services
        "AMEX:XTL",   # Telecom
        "AMEX:XNTK",  # NYSE Technology
        "AMEX:XITK",  # FactSet Innovative Technology
        "AMEX:KBE",   # Banking
        "AMEX:KRE",   # Regional Banking
        "AMEX:SLX",   # Steel
        "LSE:XWEB",   # Internet (US listing delisted; LSE fund only)
    ),
)

# ---------------------------------------------------------------------------
# Combined
# ---------------------------------------------------------------------------

SPDR_ALL = Watchlist(
    name="All SPDR Sector & Industry ETFs",
    symbols=SPDR_SECTORS.symbols + SPDR_INDUSTRIES.symbols,
)

# ---------------------------------------------------------------------------
# S&P 500 constituents (lazy-loaded from Wikipedia)
# ---------------------------------------------------------------------------

_SP500_CACHE: Watchlist | None = None


def get_sp500(*, force_refetch: bool = False) -> Watchlist:
    """Return the current S&P 500 constituents.

    Fetches from Wikipedia on first call (or when ``force_refetch=True``).
    Falls back to a static snapshot if the HTTP request fails.

    Result is cached in memory for the lifetime of the process.
    """
    global _SP500_CACHE
    if _SP500_CACHE is not None and not force_refetch:
        return _SP500_CACHE

    try:
        import pandas as pd
        url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
        tables = pd.read_html(url)
        df = tables[0]
        bare = tuple(str(s).replace(".", "-") for s in df["Symbol"].tolist())
        resolved = resolve_symbols(list(bare))
        symbols = tuple(resolved[t] for t in bare if t in resolved)
        _SP500_CACHE = Watchlist(name="S&P 500", symbols=symbols)
    except Exception:
        _SP500_CACHE = _SP500_STATIC

    return _SP500_CACHE


# Exchange-prefixed S&P 500 constituent tickers (bare/dash forms resolved
# via symbol-search / scanner sweep; delisted or renamed members dropped).
_SP500_TICKERS = (
    "NYSE:A", "NASDAQ:AAPL", "NYSE:ABBV", "NASDAQ:ABNB", "NYSE:ABT", "NASDAQ:ACGL", "NYSE:ACN", "NASDAQ:ADBE", "NASDAQ:ADI", "NYSE:ADM",
    "NASDAQ:ADP", "NASDAQ:ADSK", "NYSE:AEE", "NASDAQ:AEP", "NYSE:AES", "NYSE:AFG", "NYSE:AFL", "NYSE:AGCO", "NYSE:AIG", "NYSE:AIZ",
    "NYSE:AJG", "NASDAQ:AKAM", "NYSE:ALB", "NASDAQ:ALGN", "NYSE:ALL", "NYSE:ALLE", "NASDAQ:AMAT", "NYSE:AMCR", "NASDAQ:AMD", "NYSE:AME",
    "NASDAQ:AMGN", "NYSE:AMH", "NYSE:AMP", "NYSE:AMT", "NASDAQ:AMZN", "NYSE:ANET", "NYSE:AON", "NYSE:AOS", "NASDAQ:APA", "NYSE:APD",
    "NYSE:APO", "NASDAQ:APP", "NYSE:APTV", "NYSE:ARE", "NYSE:ATO", "NYSE:AVB", "NASDAQ:AVGO", "NYSE:AVY", "NYSE:AWK", "NASDAQ:AXON",
    "NYSE:AXP", "NYSE:AZO", "NYSE:BA", "NYSE:BAC", "NYSE:BALL", "NYSE:BAX", "NYSE:BBY", "NYSE:BDX", "NYSE:BEN", "NYSE:BF.B",
    "NYSE:BG", "NASDAQ:BIIB", "NYSE:BIO", "NASDAQ:BKNG", "NASDAQ:BKR", "NYSE:BLK", "NYSE:BMY", "NYSE:BR", "NYSE:BRK.B", "NYSE:BRO",
    "NYSE:BSX", "NYSE:BWA", "NYSE:BXP", "NYSE:C", "NYSE:CAG", "NYSE:CAH", "NYSE:CARR", "NYSE:CAT", "NYSE:CB", "NYSE:CBRE",
    "NYSE:CCL", "NASDAQ:CDNS", "NASDAQ:CDW", "NYSE:CE", "NASDAQ:CEG", "NYSE:CF", "NYSE:CFG", "NYSE:CHD", "NASDAQ:CHRW", "NASDAQ:CHTR",
    "NYSE:CI", "NASDAQ:CINF", "NYSE:CL", "NYSE:CLX", "NASDAQ:CMCSA", "NASDAQ:CME", "NYSE:CMG", "NYSE:CMI", "NYSE:CMS", "NYSE:CNC",
    "NYSE:CNP", "NYSE:COF", "NASDAQ:COIN", "NASDAQ:COO", "NYSE:COP", "NYSE:COR", "NASDAQ:COST", "NYSE:COTY", "NASDAQ:CPB", "NASDAQ:CPRT",
    "NYSE:CPT", "NYSE:CRL", "NYSE:CRM", "NASDAQ:CRWD", "NASDAQ:CSCO", "NASDAQ:CSGP", "NASDAQ:CSX", "NASDAQ:CTAS", "NASDAQ:CTSH", "NYSE:CTVA",
    "NYSE:CVS", "NYSE:CVX", "NASDAQ:CZR", "NYSE:D", "NYSE:DAL", "NYSE:DD", "NYSE:DE", "NYSE:DECK", "NYSE:DELL", "NYSE:DG",
    "NYSE:DGX", "NYSE:DHI", "NYSE:DHR", "NYSE:DIS", "NYSE:DLR", "NASDAQ:DLTR", "NYSE:DOV", "NYSE:DOW", "NASDAQ:DPZ", "NYSE:DRI",
    "NASDAQ:DRVN", "NYSE:DVA", "NYSE:DVN", "NASDAQ:DXCM", "NASDAQ:EBAY", "NYSE:ECL", "NYSE:ED", "NYSE:EFX", "NYSE:EG", "NYSE:EIX",
    "NYSE:EL", "NYSE:ELS", "NYSE:EMN", "NYSE:EMR", "NASDAQ:ENPH", "NYSE:EOG", "NYSE:EPAM", "NASDAQ:EQIX", "NYSE:EQR", "NYSE:EQT",
    "NASDAQ:ERIE", "NYSE:ES", "NYSE:ESS", "NYSE:ETN", "NYSE:ETR", "NYSE:ETSY", "NASDAQ:EVRG", "NYSE:EW", "NASDAQ:EXC", "NYSE:EXPD",
    "NYSE:EXR", "NYSE:F", "NASDAQ:FANG", "NASDAQ:FAST", "NYSE:FCX", "NYSE:FDS", "NYSE:FDX", "NYSE:FE", "NASDAQ:FFIV", "NYSE:FICO",
    "NYSE:FIS", "NYSE:FITB", "NYSE:FMC", "NASDAQ:FOX", "NASDAQ:FOXA", "NYSE:FRT", "NASDAQ:FSLR", "NASDAQ:FTNT", "NYSE:FTV", "NYSE:GD",
    "NYSE:GE", "NASDAQ:GEHC", "NASDAQ:GEN", "NASDAQ:GILD", "NYSE:GIS", "NYSE:GL", "NYSE:GLW", "NYSE:GM", "NYSE:GNRC", "NYSE:GOLD",
    "NASDAQ:GOOG", "NASDAQ:GOOGL", "NYSE:GPC", "NYSE:GPN", "NYSE:GRMN", "NYSE:GS", "NYSE:GWW", "NYSE:HAL", "NASDAQ:HAS", "NASDAQ:HBAN",
    "NYSE:HCA", "NYSE:HD", "NYSE:HIG", "NYSE:HII", "NYSE:HLT", "NASDAQ:HON", "NYSE:HPE", "NYSE:HPQ", "NYSE:HRL", "NASDAQ:HSIC",
    "NASDAQ:HST", "NYSE:HSY", "NYSE:HUBB", "NYSE:HUM", "NYSE:HWM", "NYSE:IBM", "NYSE:ICE", "NASDAQ:IDXX", "NYSE:IEX", "NYSE:IFF",
    "NASDAQ:ILMN", "NASDAQ:INCY", "NASDAQ:INTC", "NASDAQ:INTU", "NYSE:INVH", "NYSE:IOT", "NYSE:IP", "NYSE:IQV", "NYSE:IR", "NYSE:IRM",
    "NASDAQ:ISRG", "NYSE:IT", "NYSE:ITW", "NYSE:IVZ", "NYSE:J", "NASDAQ:JBHT", "NYSE:JBL", "NYSE:JCI", "NASDAQ:JKHY", "NYSE:JNJ",
    "NYSE:JPM", "NASDAQ:KDP", "NYSE:KEY", "NYSE:KEYS", "NASDAQ:KHC", "NYSE:KIM", "NYSE:KKR", "NASDAQ:KLAC", "NASDAQ:KMB", "NYSE:KMI",
    "NYSE:KMX", "NYSE:KO", "NYSE:KR", "NYSE:L", "NYSE:LDOS", "NYSE:LEN", "NYSE:LH", "NYSE:LHX", "NASDAQ:LIN", "NASDAQ:LKQ",
    "NYSE:LLY", "NYSE:LMT", "NASDAQ:LNT", "NYSE:LOW", "NASDAQ:LPLA", "NASDAQ:LRCX", "NASDAQ:LULU", "NYSE:LUV", "NYSE:LVS", "NYSE:LW",
    "NYSE:LYB", "NYSE:LYV", "NYSE:M", "NYSE:MA", "NYSE:MAA", "NASDAQ:MANH", "NASDAQ:MAR", "NYSE:MAS", "NYSE:MCD", "NASDAQ:MCHP",
    "NYSE:MCK", "NYSE:MCO", "NASDAQ:MDLZ", "NYSE:MDT", "NYSE:MET", "NASDAQ:META", "NYSE:MGM", "NYSE:MHK", "NYSE:MKC", "NASDAQ:MKTX",
    "NYSE:MLM", "NYSE:MMM", "NASDAQ:MNST", "NYSE:MO", "NYSE:MOH", "NYSE:MOS", "NYSE:MPC", "NASDAQ:MPWR", "NYSE:MRK", "NASDAQ:MRNA",
    "NYSE:MS", "NYSE:MSCI", "NASDAQ:MSFT", "NYSE:MSI", "NASDAQ:MSTR", "NYSE:MTB", "NASDAQ:MTCH", "NYSE:MTD", "NASDAQ:MU", "NYSE:NCLH",
    "NASDAQ:NDAQ", "NASDAQ:NDSN", "NYSE:NEE", "NYSE:NEM", "NYSE:NET", "NASDAQ:NFLX", "NYSE:NI", "NYSE:NKE", "NYSE:NOC", "NYSE:NOW",
    "NYSE:NRG", "NYSE:NSC", "NASDAQ:NTAP", "NASDAQ:NTRS", "NYSE:NUE", "NASDAQ:NVDA", "NYSE:NVR", "NASDAQ:NWS", "NASDAQ:NWSA", "NASDAQ:NXPI",
    "NYSE:O", "NASDAQ:ODFL", "NYSE:OKE", "NYSE:OMC", "NASDAQ:ON", "NYSE:ORCL", "NASDAQ:ORLY", "NYSE:OTIS", "NYSE:OXY", "NASDAQ:PANW",
    "NASDAQ:PARA", "NYSE:PAYC", "NASDAQ:PAYX", "NASDAQ:PCAR", "NYSE:PCG", "NYSE:PEG", "NASDAQ:PEP", "NYSE:PFE", "NASDAQ:PFG", "NYSE:PG",
    "NYSE:PGR", "NYSE:PH", "NYSE:PHM", "NYSE:PKG", "NYSE:PLD", "NASDAQ:PLTR", "NYSE:PM", "NYSE:PNC", "NYSE:PNR", "NYSE:PNW",
    "NASDAQ:PODD", "NASDAQ:POOL", "NYSE:PPG", "NYSE:PPL", "NYSE:PRU", "NYSE:PSA", "NYSE:PSX", "NASDAQ:PTC", "NYSE:PWR", "NASDAQ:PYPL",
    "NASDAQ:QCOM", "NASDAQ:QRVO", "NYSE:RCL", "NASDAQ:REGN", "NYSE:RF", "NYSE:RJF", "NYSE:RL", "NYSE:RMD", "NYSE:ROK", "NASDAQ:ROKU",
    "NYSE:ROL", "NASDAQ:ROP", "NASDAQ:ROST", "NYSE:RS", "NYSE:RSG", "NYSE:RTX", "NYSE:RVTY", "NYSE:S", "NASDAQ:SBAC", "NASDAQ:SBUX",
    "NYSE:SCHW", "NYSE:SCI", "NYSE:SHW", "NASDAQ:SIRI", "NYSE:SJM", "NYSE:SLB", "NYSE:SLG", "NASDAQ:SMCI", "NYSE:SNA", "NYSE:SNOW",
    "NASDAQ:SNPS", "NYSE:SO", "NYSE:SOLV", "NYSE:SPG", "NYSE:SPGI", "NYSE:SRE", "NYSE:STE", "NASDAQ:STLD", "NYSE:STT", "NASDAQ:STX",
    "NYSE:STZ", "NYSE:SWK", "NASDAQ:SWKS", "NYSE:SYF", "NYSE:SYK", "NYSE:SYY", "NYSE:T", "NYSE:TAP", "NYSE:TDG", "NYSE:TDY",
    "NASDAQ:TECH", "NYSE:TEL", "NASDAQ:TER", "NYSE:TFC", "NYSE:TFX", "NYSE:TGT", "NYSE:TJX", "NYSE:TMO", "NASDAQ:TMUS", "NYSE:TPR",
    "NYSE:TRGP", "NASDAQ:TRMB", "NASDAQ:TROW", "NYSE:TRV", "NASDAQ:TSCO", "NASDAQ:TSLA", "NYSE:TSN", "NYSE:TT", "NASDAQ:TTD", "NASDAQ:TTWO",
    "NASDAQ:TXN", "NYSE:TXT", "NYSE:TYL", "NASDAQ:UAL", "NYSE:UBER", "NYSE:UDR", "NYSE:UHS", "NASDAQ:ULTA", "NYSE:UNH", "NYSE:UNM",
    "NYSE:UNP", "NYSE:UPS", "NYSE:URI", "NYSE:USB", "NYSE:V", "NYSE:VICI", "NYSE:VLO", "NYSE:VLTO", "NYSE:VMC", "NASDAQ:VRSK",
    "NASDAQ:VRSN", "NYSE:VRT", "NASDAQ:VRTX", "NYSE:VST", "NYSE:VTR", "NASDAQ:VTRS", "NYSE:VZ", "NYSE:WAB", "NYSE:WAT", "NASDAQ:WBD",
    "NASDAQ:WDAY", "NASDAQ:WDC", "NYSE:WEC", "NYSE:WELL", "NYSE:WFC", "NYSE:WHR", "NYSE:WM", "NYSE:WMB", "NASDAQ:WMT", "NYSE:WRB",
    "NYSE:WSM", "NYSE:WST", "NASDAQ:WTW", "NYSE:WY", "NASDAQ:WYNN", "NASDAQ:XEL", "NYSE:XOM", "NYSE:XYL", "NYSE:YUM", "NYSE:ZBH",
    "NASDAQ:ZBRA", "NASDAQ:ZION", "NYSE:ZTS",
)

_SP500_STATIC = Watchlist(
    name="S&P 500 (static snapshot)",
    symbols=_SP500_TICKERS,
)

# ---------------------------------------------------------------------------
# Crypto
# ---------------------------------------------------------------------------

CRYPTO = Watchlist(
    name="Top Crypto",
    symbols=(
        "BITSTAMP:BTCUSD",
        "BITSTAMP:ETHUSD",
    ),
)

# ---------------------------------------------------------------------------
# Metals & Miners
# ---------------------------------------------------------------------------

METALS_MINERS = Watchlist(
    name="Metals & Miners",
    symbols=(
        # Precious spot
        "OANDA:XAUUSD", "TVC:GOLD", "OANDA:XAGUSD", "TVC:SILVER",
        "OANDA:XPTUSD", "TVC:PLATINUM", "OANDA:XPDUSD", "TVC:PALLADIUM",
        "OANDA:XCUUSD", "CAPITALCOM:COPPER",
        # Gold miners ETF
        "AMEX:GDX", "AMEX:GDXJ",
        # Silver miners ETF
        "AMEX:SIL", "AMEX:SILJ",
        # Gold ETFs
        "AMEX:GLD", "AMEX:IAU",
        # Platinum/Palladium
        "AMEX:PPLT", "AMEX:PALL", "AMEX:PLG",
        # Copper
        "AMEX:COPX", "AMEX:CPER", "LSE:COPA",
        # Individual miners
        "NYSE:NEM", "NYSE:FCX", "NYSE:SCCO", "NYSE:AA", "NYSE:RIO",
        "NYSE:BHP", "NYSE:HBM", "NYSE:TECK", "NYSE:VALE",
    ),
)

# ---------------------------------------------------------------------------
# Index Futures
# ---------------------------------------------------------------------------

INDEX_FUTURES = Watchlist(
    name="Index Futures",
    symbols=(
        "CME_MINI:ES1!",
        "CME_MINI:NQ1!",
        "CBOT_MINI:YM1!",
        "CME_MINI:RTY1!",
        "EUREX:FDAX1!",
        "EUREX:FESX1!",
    ),
)

# ---------------------------------------------------------------------------
# Index CFDs
# ---------------------------------------------------------------------------

INDEX_CFDS = Watchlist(
    name="Index CFDs",
    symbols=(
        "SPCFD:SPX",
        "TVC:NDQ",
        "TVC:DJI",
        "TVC:RUT",
        "TVC:DAX",
        "TVC:UKX",
        "EURONEXT:PX1",
        "TVC:NI225",
        "TVC:HSI",
        "TVC:VIX",
    ),
)

# ---------------------------------------------------------------------------
# Index ETFs
# ---------------------------------------------------------------------------

INDEX_ETFS = Watchlist(
    name="Index ETFs",
    symbols=(
        "AMEX:SPY",
        "NASDAQ:QQQ",
        "AMEX:IWM",
        "AMEX:DIA",
        "AMEX:VTI",
        "CBOE:MAGS",
    ),
)

# ---------------------------------------------------------------------------
# Bonds
# ---------------------------------------------------------------------------

BONDS = Watchlist(
    name="Bonds",
    symbols=(
        "TVC:US10Y",
        "TVC:US02Y",
        "TVC:US03M",
        "TVC:TNX",
        "CBOT:TN1!",
        "CBOT:ZT1!",
        "NASDAQ:TLT",
    ),
)

# ---------------------------------------------------------------------------
# Oil
# ---------------------------------------------------------------------------

OIL = Watchlist(
    name="Oil",
    symbols=(
        "TVC:USOIL",
        "TVC:UKOIL",
        "NYMEX:CL1!",
        "OANDA:WTICOUSD",
        "OANDA:BCOUSD",
    ),
)

# ---------------------------------------------------------------------------
# Uranium & Strategic Commodities
# ---------------------------------------------------------------------------

URANIUM_STRATEGIC = Watchlist(
    name="Uranium & Strategic Commodities",
    symbols=(
        "AMEX:URA",
        "AMEX:URNM",
        "AMEX:UEC",
        "NASDAQ:NNE",
        "NASDAQ:USAR",
        "NASDAQ:AREC",
        "NASDAQ:CRML",
        "NYSE:AMR",
        "NYSE:CCJ",
        "AMEX:DNN",
        "NYSE:NXE",
        "AMEX:GLO",
        "NASDAQ:EU",
        "AMEX:URG",
        "AMEX:REMX",
        "NYSE:MP",
        "NASDAQ:NB",
        "NASDAQ:NIKL",
        "ASX:LYC",
        "AMEX:SLX",
        "OTC:AMLIF",
        "NASDAQ:CENX",
    ),
)

# ---------------------------------------------------------------------------
# Registry — map name → Watchlist for job lookup
# ---------------------------------------------------------------------------

WATCHLISTS: dict[str, Watchlist] = {
    "SPDR_SECTORS": SPDR_SECTORS,
    "SPDR_SECTORS_CORE": SPDR_SECTORS_CORE,
    "SPDR_INDUSTRIES": SPDR_INDUSTRIES,
    "SPDR_ALL": SPDR_ALL,
    "CRYPTO": CRYPTO,
    "METALS_MINERS": METALS_MINERS,
    "INDEX_FUTURES": INDEX_FUTURES,
    "INDEX_CFDS": INDEX_CFDS,
    "INDEX_ETFS": INDEX_ETFS,
    "BONDS": BONDS,
    "OIL": OIL,
    "URANIUM_STRATEGIC": URANIUM_STRATEGIC,
}

PINK_LIST_WATCHLISTS: dict[str, Watchlist] = {
    "METALS_MINERS": METALS_MINERS,
    "INDEX_FUTURES": INDEX_FUTURES,
    "INDEX_CFDS": INDEX_CFDS,
    "INDEX_ETFS": INDEX_ETFS,
    "BONDS": BONDS,
    "OIL": OIL,
    "URANIUM_STRATEGIC": URANIUM_STRATEGIC,
}

def get_watchlist(name: str) -> Watchlist:
    """Look up a watchlist by name constant."""
    if name not in WATCHLISTS:
        raise KeyError(f"Unknown watchlist: {name}. Choices: {', '.join(sorted(WATCHLISTS))}")
    return WATCHLISTS[name]


def registry_rows(sp500: Watchlist | None = None) -> list[dict[str, str]]:
    """Build one (symbol, watchlist, source) entry per symbol per watchlist.

    Static ``WATCHLISTS`` entries get ``source="watchlist"``; the S&P 500 gets
    ``source="sp500"`` with ``watchlist="SP500"``.  Pass ``sp500`` explicitly
    to avoid the network/pandas load of ``get_sp500()`` (used in Databricks).
    """
    wl = sp500 if sp500 is not None else get_sp500()
    rows: list[dict[str, str]] = []
    for name, watch in WATCHLISTS.items():
        for sym in watch.symbols:
            rows.append({"symbol": sym, "watchlist": name, "source": "watchlist"})
    for sym in wl.symbols:
        rows.append({"symbol": sym, "watchlist": "SP500", "source": "sp500"})
    return rows


def screen(
    market: str = "america",
    exchange: str | None = None,
    types: tuple[str, ...] = ("stock",),
    columns: tuple[str, ...] = ("name",),
    page_size: int = _PAGE_SIZE,
    timeout: float = 30.0,
    sort_by: str | None = "name",
) -> tuple[list[dict[str, object]], int]:
    """Query TradingView's stock-screener endpoint.

    Returns ``(rows, total_count)`` where each row is a dict, e.g.
    ``{"symbol": "NYSE:A", "name": "A", "close": 145.97}``.  Paginates
    internally through the full result set.  A stable sort (default
    ``"name"``) is required for correct pagination — TradingView's default
    order is unstable across page requests, which causes duplicate/missing
    symbols.  ``sort_by=None`` disables the sort only for callers who
    know the server returns a stable order.

    Parameters
    ----------
    market : str
        Scanner market, e.g. ``"america"``, ``"crypto"``, ``"forex"``.
    exchange : str | None
        If given, only return symbols from this exchange (e.g. ``"NYSE"``,
        ``"NASDAQ"``, ``"AMEX"``).  None returns every market symbol.
    types : tuple[str, ...]
        Instrument types to include, e.g. ``("stock",)``.
    columns : tuple[str, ...]
        Screen columns to fetch per row, e.g. ``("name", "close")``.  The
        symbol itself is always present as the ``"symbol"`` key.
    timeout : float
        Seconds to wait for the server response.
    sort_by : str | None
        Column to sort results by (default ``"name"``, ascending) — required
        for correct pagination.  ``None`` omits the sort entirely.
    """
    rows: list[dict[str, object]] = []
    total: int | None = None
    offset = 0
    while True:
        payload: dict[str, object] = {
            "symbols": {"query": {"types": list(types)}},
            "columns": list(columns),
        }
        if sort_by:
            payload["sort"] = {"sortBy": sort_by, "sortOrder": "asc"}
        payload["range"] = [offset, offset + page_size]
        if exchange:
            payload["filter"] = [
                {"left": "exchange", "operation": "equal", "right": exchange}
            ]

        body = json.dumps(payload).encode()
        req = urllib.request.Request(
            _SCANNER_URL.format(market=market),
            data=body,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 "
                "Safari/537.36",
                "Referer": "https://www.tradingview.com/screener/",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode())
        except urllib.error.HTTPError as err:
            reason = f": {err.reason}" if err.reason else ""
            raise RuntimeError(
                f"screen({market!r}) failed: HTTP {err.code}{reason}"
            ) from err
        except urllib.error.URLError as err:
            raise RuntimeError(f"screen({market!r}) failed: {err.reason}") from err

        total = int(data["totalCount"])
        batch = data.get("data", [])
        for item in batch:
            row: dict[str, object] = {"symbol": item["s"]}
            row.update(zip(columns, item.get("d", [])))
            rows.append(row)
        if not batch or offset + page_size >= total:
            break
        offset += page_size
    return rows, total


def get_market_caps(
    symbols: list[str],
    market: str = "america",
    timeout: float = 30.0,
) -> dict[str, float]:
    """Market caps for an explicit ticker list via the scanner.

    Accepts prefixed (``"NYSE:BRK.B"``), dash (``"BRK-B"``), dot
    (``"BRK.B"``), or underscore (``"BRK_B"``) forms; bare/dash/underscore
    inputs are resolved to exchange-prefixed form via ``resolve_symbols()``
    before POSTing.  Returns ``{symbol: cap}`` keyed by the scanner's
    returned (prefixed) symbol.  Members whose cap is null (delisted /
    non-tradable) are omitted.

    Parameters
    ----------
    symbols : list[str]
        Explicit ticker list, e.g. ``["AAPL", "BRK.B"]``.
    market : str
        Scanner market, e.g. ``"america"``.
    timeout : float
        Seconds to wait for the server response.
    """
    resolved = resolve_symbols(list(symbols), market=market, timeout=timeout)
    prefixed = [resolved[s] for s in symbols if s in resolved]

    caps: dict[str, float] = {}
    chunk_size = 500  # keep each POST modest; the scanner accepts large lists
    for i in range(0, len(prefixed), chunk_size):
        chunk = prefixed[i : i + chunk_size]
        payload: dict[str, object] = {
            "symbols": {"tickers": list(chunk)},
            "columns": ["market_cap_basic"],
            "range": [0, len(chunk)],
        }
        body = json.dumps(payload).encode()
        req = urllib.request.Request(
            _SCANNER_URL.format(market=market),
            data=body,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 "
                "Safari/537.36",
                "Referer": "https://www.tradingview.com/screener/",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode())
        except urllib.error.HTTPError as err:
            reason = f": {err.reason}" if err.reason else ""
            raise RuntimeError(
                f"get_market_caps({len(symbols)} symbols) failed: HTTP {err.code}{reason}"
            ) from err
        except urllib.error.URLError as err:
            raise RuntimeError(
                f"get_market_caps({len(symbols)} symbols) failed: {err.reason}"
            ) from err

        for item in data.get("data", []):
            values = item.get("d") or []
            cap = values[0] if values else None
            if cap is not None:
                caps[str(item["s"])] = float(cap)
    return caps


US_STOCK_EXCHANGES: tuple[str, ...] = ("NYSE", "NASDAQ", "AMEX")

_US_STOCKS_CACHE: Watchlist | None = None


def us_stock_rows(
    market: str = "america",
    exchanges: tuple[str, ...] = US_STOCK_EXCHANGES,
) -> list[dict[str, str]]:
    """One (symbol, US_STOCKS, screen) entry per listed US stock.

    Queries the TradingView scanner per exchange and unions the results.
    Symbols are already exchange-prefixed (``NYSE:A``), matching the
    format the cache/refresh path consumes.
    """
    rows: list[dict[str, str]] = []
    for exch in exchanges:
        screen_rows, _ = screen(market=market, exchange=exch)
        for r in screen_rows:
            rows.append({
                "symbol": str(r["symbol"]),
                "watchlist": "US_STOCKS",
                "source": "screen",
            })
    return rows


def get_us_stocks(*, force_refetch: bool = False) -> Watchlist:
    """Return a Watchlist of all listed US stocks (mirrors get_sp500).

    Cached in memory for process lifetime.  Raises on failure — unlike
    S&P 500 there is no static fallback snapshot for the whole market.
    """
    global _US_STOCKS_CACHE
    if _US_STOCKS_CACHE is not None and not force_refetch:
        return _US_STOCKS_CACHE
    symbols = tuple(r["symbol"] for r in us_stock_rows())
    _US_STOCKS_CACHE = Watchlist(name="US Stocks", symbols=symbols)
    return _US_STOCKS_CACHE
