import pytest

from analyzers.fundamentalist.fundamentalist_analyzer import FundamentalistAnalyzer
from core.analyzers.base import AnalysisType
from core.assets.asset import Asset
from core.assets.asset_type import AssetType
from core.collectors.base import RawData
from core.exceptions import AnalyzerError


def test_analyze_prefers_yfinance_over_brapi():
    asset = Asset(ticker="PETR4.SA", asset_type=AssetType.BR_STOCK, name="Petrobras")
    yf_raw = RawData(
        source="yfinance",
        payload={
            "info": {
                "trailingPE": 5.2,
                "priceToBook": 1.3,
                "dividendYield": 0.12,
                "returnOnEquity": 0.35,
                "marketCap": 500000000000,
                "currentPrice": 38.5,
            }
        },
    )
    brapi_raw = RawData(
        source="brapi.dev",
        payload={
            "quote": {
                "priceEarnings": 5.0,
                "regularMarketPrice": 38.4,
                "marketCap": 499000000000,
            }
        },
    )

    result = FundamentalistAnalyzer().analyze(asset, [yf_raw, brapi_raw])

    assert result.analysis_type == AnalysisType.FUNDAMENTALIST
    assert result.data["pl"] == 5.2
    assert result.data["field_sources"]["pl"] == "yfinance"
    assert result.data["debt_to_equity"] is None
    assert set(result.sources) == {"yfinance", "brapi.dev"}


def test_analyze_falls_back_to_brapi_when_yfinance_missing_field():
    asset = Asset(ticker="PETR4.SA", asset_type=AssetType.BR_STOCK, name="Petrobras")
    yf_raw = RawData(source="yfinance", payload={"info": {}})
    brapi_raw = RawData(
        source="brapi.dev",
        payload={"quote": {"priceEarnings": 5.0, "regularMarketPrice": 38.4}},
    )

    result = FundamentalistAnalyzer().analyze(asset, [yf_raw, brapi_raw])

    assert result.data["pl"] == 5.0
    assert result.data["field_sources"]["pl"] == "brapi.dev"


def test_analyze_maps_eps_from_yfinance_trailing_eps():
    asset = Asset(ticker="PETR4.SA", asset_type=AssetType.BR_STOCK, name="Petrobras")
    yf_raw = RawData(source="yfinance", payload={"info": {"trailingEps": 8.28}})

    result = FundamentalistAnalyzer().analyze(asset, [yf_raw])

    assert result.data["eps"] == 8.28
    assert result.data["field_sources"]["eps"] == "yfinance"


def test_analyze_raises_when_no_data():
    asset = Asset(ticker="PETR4.SA", asset_type=AssetType.BR_STOCK, name="Petrobras")

    with pytest.raises(AnalyzerError):
        FundamentalistAnalyzer().analyze(asset, [])
