import pandas as pd
import pytest

from collectors.br_stocks import yfinance_collector as module
from core.assets.asset import Asset
from core.assets.asset_type import AssetType
from core.exceptions import CollectorError


class _FakeTicker:
    def __init__(self, info, history_df, financials=None, balance_sheet=None):
        self.info = info
        self._history_df = history_df
        self.financials = financials if financials is not None else pd.DataFrame()
        self.balance_sheet = balance_sheet if balance_sheet is not None else pd.DataFrame()

    def history(self, period=None, interval=None):
        return self._history_df


class _FakeTickerFinancialsRaise(_FakeTicker):
    """Simula uma falha ao acessar `.financials` (ex: dado indisponível para
    o ticker) — deve ser isolada, sem derrubar a coleta de info/history.
    """

    @property
    def financials(self):
        raise RuntimeError("financials indisponível")

    @financials.setter
    def financials(self, value):
        pass


def _history_df(n=5):
    dates = pd.date_range("2026-01-01", periods=n, freq="D")
    return pd.DataFrame(
        {
            "Open": [10.0 + i for i in range(n)],
            "High": [10.5 + i for i in range(n)],
            "Low": [9.5 + i for i in range(n)],
            "Close": [10.2 + i for i in range(n)],
            "Volume": [1000 + i for i in range(n)],
        },
        index=dates,
    )


def test_fetch_returns_raw_data_with_info_and_history(monkeypatch):
    info = {"currentPrice": 38.5, "trailingPE": 5.2, "unused_field": "x"}
    fake_ticker = _FakeTicker(info=info, history_df=_history_df())
    monkeypatch.setattr(module.yf, "Ticker", lambda ticker: fake_ticker)

    collector = module.YFinanceCollector()
    asset = Asset(ticker="PETR4.SA", asset_type=AssetType.BR_STOCK, name="Petrobras")

    raw = collector.fetch(asset)

    assert raw.source == "yfinance"
    assert raw.payload["info"]["currentPrice"] == 38.5
    assert raw.payload["info"]["trailingPE"] == 5.2
    assert "unused_field" not in raw.payload["info"]
    assert len(raw.payload["history"]) == 5
    assert raw.payload["history"][0]["close"] == 10.2


def test_fetch_includes_roic_fields_from_financials_and_balance_sheet(monkeypatch):
    info = {"currentPrice": 38.5}
    financials = pd.DataFrame(
        {"2025-12-31": [169257967200.0, 0.264042]}, index=["EBIT", "Tax Rate For Calcs"]
    )
    balance_sheet = pd.DataFrame({"2025-12-31": [558911275200.0]}, index=["Invested Capital"])
    fake_ticker = _FakeTicker(
        info=info, history_df=_history_df(), financials=financials, balance_sheet=balance_sheet
    )
    monkeypatch.setattr(module.yf, "Ticker", lambda ticker: fake_ticker)

    collector = module.YFinanceCollector()
    asset = Asset(ticker="PETR4.SA", asset_type=AssetType.BR_STOCK, name="Petrobras")

    raw = collector.fetch(asset)

    assert raw.payload["info"]["ebit"] == 169257967200.0
    assert raw.payload["info"]["taxRateForCalcs"] == pytest.approx(0.264042)
    assert raw.payload["info"]["investedCapital"] == 558911275200.0


def test_fetch_skips_roic_fields_when_rows_missing(monkeypatch):
    fake_ticker = _FakeTicker(info={"currentPrice": 38.5}, history_df=_history_df())
    monkeypatch.setattr(module.yf, "Ticker", lambda ticker: fake_ticker)

    raw = module.YFinanceCollector().fetch(
        Asset(ticker="PETR4.SA", asset_type=AssetType.BR_STOCK, name="Petrobras")
    )

    assert "ebit" not in raw.payload["info"]
    assert "taxRateForCalcs" not in raw.payload["info"]
    assert "investedCapital" not in raw.payload["info"]


def test_fetch_isolates_financials_failure_without_breaking_collection(monkeypatch):
    fake_ticker = _FakeTickerFinancialsRaise(info={"currentPrice": 38.5}, history_df=_history_df())
    monkeypatch.setattr(module.yf, "Ticker", lambda ticker: fake_ticker)

    raw = module.YFinanceCollector().fetch(
        Asset(ticker="PETR4.SA", asset_type=AssetType.BR_STOCK, name="Petrobras")
    )

    assert raw.payload["info"]["currentPrice"] == 38.5
    assert "ebit" not in raw.payload["info"]


def test_fetch_raises_collector_error_when_no_data(monkeypatch):
    fake_ticker = _FakeTicker(info={}, history_df=pd.DataFrame())
    monkeypatch.setattr(module.yf, "Ticker", lambda ticker: fake_ticker)

    collector = module.YFinanceCollector()
    asset = Asset(ticker="INEXISTENTE.SA", asset_type=AssetType.BR_STOCK, name="Inexistente")

    with pytest.raises(CollectorError):
        collector.fetch(asset)


def test_fetch_wraps_unexpected_exception(monkeypatch):
    def _raise_ticker(ticker):
        raise RuntimeError("boom")

    monkeypatch.setattr(module.yf, "Ticker", _raise_ticker)

    collector = module.YFinanceCollector()
    asset = Asset(ticker="PETR4.SA", asset_type=AssetType.BR_STOCK, name="Petrobras")

    with pytest.raises(CollectorError):
        collector.fetch(asset)
