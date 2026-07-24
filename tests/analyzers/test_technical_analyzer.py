import pandas as pd
import pytest

from analyzers.technical.technical_analyzer import TechnicalAnalyzer
from core.assets.asset import Asset
from core.assets.asset_type import AssetType
from core.collectors.base import RawData
from core.exceptions import AnalyzerError


def _make_history(n=30, start_price=10.0, step=0.5):
    history = []
    for i in range(n):
        date = pd.Timestamp("2026-01-01") + pd.Timedelta(days=i)
        price = start_price + i * step
        history.append(
            {
                "date": date.isoformat(),
                "open": price - 0.1,
                "high": price + 0.2,
                "low": price - 0.2,
                "close": price,
                "volume": 1000 + i,
            }
        )
    return history


def test_analyze_computes_sma_rsi_macd():
    history = _make_history(n=30)
    raw = RawData(source="yfinance", payload={"info": {}, "history": history})
    asset = Asset(ticker="PETR4.SA", asset_type=AssetType.BR_STOCK, name="Petrobras")

    result = TechnicalAnalyzer().analyze(asset, [raw])

    close = pd.Series([h["close"] for h in history])
    expected_sma_20 = round(float(close.rolling(20).mean().iloc[-1]), 4)

    assert result.data["sma_20"] == expected_sma_20
    assert result.data["sma_200"] is None
    assert result.data["last_price"] == history[-1]["close"]
    assert result.data["trend"] in {"alta", "baixa", "indefinida"}
    assert result.data["history_points"] == 30
    assert result.data["rsi_14"] > 50  # série estritamente crescente


def test_analyze_raises_when_insufficient_history():
    raw = RawData(
        source="yfinance",
        payload={
            "info": {},
            "history": [
                {"date": "2026-01-01", "open": 10, "high": 10, "low": 10, "close": 10.0, "volume": 1}
            ],
        },
    )
    asset = Asset(ticker="PETR4.SA", asset_type=AssetType.BR_STOCK, name="Petrobras")

    with pytest.raises(AnalyzerError):
        TechnicalAnalyzer().analyze(asset, [raw])


def test_analyze_raises_when_no_yfinance_source():
    asset = Asset(ticker="PETR4.SA", asset_type=AssetType.BR_STOCK, name="Petrobras")

    with pytest.raises(AnalyzerError):
        TechnicalAnalyzer().analyze(asset, [])
