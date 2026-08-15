"""Tests for symbols.py — ticker normalization and resolution."""

import io
import json
import urllib.error
from unittest import mock

import pytest

from pytvtools_core.symbols import normalize_symbol, resolve_symbols


@pytest.fixture(autouse=True)
def _clear_resolve_cache():
    """Clear the module-level resolve/sweep caches between tests.

    ``resolve_symbols`` caches results in ``pytvtools_core.symbols`` module
    globals for the process lifetime; without clearing, tests observe stale
    cached mappings (e.g. ``test_cache_reuses_results`` would see 0 network
    calls and the sweep-fallback test would short-circuit on a cached hit).
    """
    import pytvtools_core.symbols as _sym
    _sym._resolve_cache.clear()
    _sym._sweep_cache.clear()
    yield


class TestNormalizeSymbol:
    def test_dash_to_dot(self):
        assert normalize_symbol("BRK-B") == "BRK.B"

    def test_underscore_to_dot(self):
        assert normalize_symbol("BRK_B") == "BRK.B"

    def test_dot_unchanged(self):
        assert normalize_symbol("BRK.B") == "BRK.B"

    def test_prefixed_dash(self):
        assert normalize_symbol("NYSE:BRK-B") == "NYSE:BRK.B"

    def test_prefixed_plain_unchanged(self):
        assert normalize_symbol("NASDAQ:AAPL") == "NASDAQ:AAPL"


_SYM_URL_PREFIX = "https://symbol-search.tradingview.com/symbol_search/v3/?text="


class TestResolveSymbols:
    @staticmethod
    def _respond(symbols):
        return io.BytesIO(json.dumps(
            {"symbols_remaining": 0, "symbols": symbols}).encode())

    def test_passes_through_prefixed(self):
        with mock.patch("urllib.request.urlopen",
                        side_effect=lambda *a, **k: self._respond([])):
            out = resolve_symbols(["NASDAQ:AAPL", "NYSE:BRK.B"])
        assert out == {
            "NASDAQ:AAPL": "NASDAQ:AAPL",
            "NYSE:BRK.B": "NYSE:BRK.B",
        }

    def test_resolves_bare_via_symbol_search(self):
        seen = []

        def _open(req, timeout=None):
            seen.append(req.full_url)
            query = req.full_url.split("text=")[1].split("&")[0]
            if query == "AAPL":
                return self._respond([
                    {"symbol": "AAPL", "description": "Apple Inc.",
                     "type": "stock", "exchange": "NASDAQ"},
                ])
            if query == "BRK.B":
                return self._respond([
                    {"symbol": "BRK.B", "description": "Berkshire",
                     "type": "stock", "exchange": "NYSE"},
                ])
            return self._respond([])

        with mock.patch("urllib.request.urlopen", side_effect=_open):
            out = resolve_symbols(["AAPL", "BRK.B"])
        assert out == {"AAPL": "NASDAQ:AAPL", "BRK.B": "NYSE:BRK.B"}
        assert len(seen) == 2

    def test_nyse_arca_maps_to_amex(self):
        def _open(req, timeout=None):
            return self._respond([
                {"symbol": "XLK", "description": "SPDR Tech",
                 "type": "fund", "exchange": "NYSE Arca"},
            ])

        with mock.patch("urllib.request.urlopen", side_effect=_open):
            out = resolve_symbols(["XLK"])
        assert out == {"XLK": "AMEX:XLK"}

    def test_prefers_us_exchange_over_foreign(self):
        def _open(req, timeout=None):
            return self._respond([
                {"symbol": "RIO", "description": "Rio Tinto",
                 "type": "dr", "exchange": "NYSE"},
                {"symbol": "RIO", "description": "Rio Tinto ASX",
                 "type": "stock", "exchange": "ASX"},
            ])

        with mock.patch("urllib.request.urlopen", side_effect=_open):
            out = resolve_symbols(["RIO"])
        assert out == {"RIO": "NYSE:RIO"}

    def test_dash_form_input_resolves(self):
        def _open(req, timeout=None):
            return self._respond([
                {"symbol": "BRK.B", "description": "Berkshire",
                 "type": "stock", "exchange": "NYSE"},
            ])

        with mock.patch("urllib.request.urlopen", side_effect=_open):
            out = resolve_symbols(["BRK-B"])
        assert out == {"BRK-B": "NYSE:BRK.B"}

    def test_unresolvable_ticker_omitted(self):
        def _open(req, timeout=None):
            return self._respond([])

        with mock.patch("urllib.request.urlopen", side_effect=_open):
            out = resolve_symbols(["ZZZZ", "NASDAQ:AAPL"])
        assert out == {"NASDAQ:AAPL": "NASDAQ:AAPL"}

    def test_cache_reuses_results(self):
        calls = []

        def _open(req, timeout=None):
            calls.append(req.full_url)
            return self._respond([
                {"symbol": "AAPL", "description": "Apple",
                 "type": "stock", "exchange": "NASDAQ"},
            ])

        with mock.patch("urllib.request.urlopen", side_effect=_open):
            first = resolve_symbols(["AAPL"])
            second = resolve_symbols(["AAPL"])
        assert first == {"AAPL": "NASDAQ:AAPL"}
        assert second == {"AAPL": "NASDAQ:AAPL"}
        assert len(calls) == 1

    def test_falls_back_to_screen_sweep_on_symbol_search_error(self):
        import pytvtools_core.symbols as sym
        sweep_map = {"AAPL": "NASDAQ:AAPL"}

        def _open(req, timeout=None):
            raise urllib.error.HTTPError(req.full_url, 500, "boom", {}, None)

        with mock.patch("urllib.request.urlopen", side_effect=_open), \
             mock.patch.object(sym, "_sweep_map",
                               wraps=sym._sweep_map) as mock_sweep:
            mock_sweep.return_value = sweep_map
            out = resolve_symbols(["AAPL"])
        assert out == {"AAPL": "NASDAQ:AAPL"}

    def test_raises_when_all_fail_and_sweep_empty(self):
        import pytvtools_core.symbols as sym

        def _open(req, timeout=None):
            raise urllib.error.URLError("no network")

        with mock.patch("urllib.request.urlopen", side_effect=_open), \
             mock.patch.object(sym, "_sweep_map", return_value={}):
            out = resolve_symbols(["ZZZZ"])
        assert out == {}
