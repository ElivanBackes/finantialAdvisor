import json
from unittest.mock import MagicMock, patch

from macro.bcb_client import get_exchange_rate_trend, get_latest_selic


def _fake_response(payload: list[dict]):
    response = MagicMock()
    response.read.return_value = json.dumps(payload).encode()
    response.__enter__.return_value = response
    response.__exit__.return_value = False
    return response


@patch("macro.bcb_client.urllib.request.urlopen")
def test_get_latest_selic_returns_latest_value(mock_urlopen):
    mock_urlopen.return_value = _fake_response([{"data": "05/08/2026", "valor": "14.25"}])

    assert get_latest_selic() == 14.25


@patch("macro.bcb_client.urllib.request.urlopen")
def test_get_latest_selic_returns_none_on_failure(mock_urlopen):
    mock_urlopen.side_effect = RuntimeError("boom")

    assert get_latest_selic() is None


@patch("macro.bcb_client.urllib.request.urlopen")
def test_get_exchange_rate_trend_returns_start_and_end(mock_urlopen):
    mock_urlopen.return_value = _fake_response(
        [{"data": "20/07/2026", "valor": "5.0894"}, {"data": "24/07/2026", "valor": "5.20"}]
    )

    assert get_exchange_rate_trend() == (5.0894, 5.20)


@patch("macro.bcb_client.urllib.request.urlopen")
def test_get_exchange_rate_trend_returns_none_with_insufficient_data(mock_urlopen):
    mock_urlopen.return_value = _fake_response([{"data": "24/07/2026", "valor": "5.20"}])

    assert get_exchange_rate_trend() is None


@patch("macro.bcb_client.urllib.request.urlopen")
def test_get_exchange_rate_trend_returns_none_on_failure(mock_urlopen):
    mock_urlopen.side_effect = RuntimeError("boom")

    assert get_exchange_rate_trend() is None
