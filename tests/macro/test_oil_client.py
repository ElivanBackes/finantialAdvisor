from unittest.mock import MagicMock, patch

import pandas as pd

from macro.oil_client import get_oil_price_trend


def _fake_history_df(closes: list[float]) -> pd.DataFrame:
    return pd.DataFrame({"Close": closes})


@patch("macro.oil_client.yf.Ticker")
def test_get_oil_price_trend_returns_start_and_end(mock_ticker_cls):
    mock_ticker = MagicMock()
    mock_ticker.history.return_value = _fake_history_df([80.0, 82.0, 85.0])
    mock_ticker_cls.return_value = mock_ticker

    assert get_oil_price_trend() == (80.0, 85.0)


@patch("macro.oil_client.yf.Ticker")
def test_get_oil_price_trend_returns_none_with_empty_history(mock_ticker_cls):
    mock_ticker = MagicMock()
    mock_ticker.history.return_value = pd.DataFrame()
    mock_ticker_cls.return_value = mock_ticker

    assert get_oil_price_trend() is None


@patch("macro.oil_client.yf.Ticker")
def test_get_oil_price_trend_returns_none_on_failure(mock_ticker_cls):
    mock_ticker_cls.side_effect = RuntimeError("boom")

    assert get_oil_price_trend() is None
