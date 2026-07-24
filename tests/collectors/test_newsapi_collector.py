import json
from pathlib import Path

import pytest

from collectors.news import newsapi_collector as module
from config.settings import get_settings
from core.assets.asset import Asset
from core.assets.asset_type import AssetType
from core.exceptions import CollectorError

_FIXTURES_DIR = Path(__file__).resolve().parents[1] / "fixtures"


class _FakeResponse:
    def __init__(self, json_body, status_code=200):
        self._json_body = json_body
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise module.requests.HTTPError(f"HTTP {self.status_code}")

    def json(self):
        return self._json_body


@pytest.fixture(autouse=True)
def _clear_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_fetch_returns_articles(monkeypatch):
    monkeypatch.setenv("NEWSAPI_KEY", "fake-key")
    body = json.loads((_FIXTURES_DIR / "newsapi_sample.json").read_text())

    def fake_get(url, params=None, timeout=None):
        return _FakeResponse(body)

    monkeypatch.setattr(module.requests, "get", fake_get)

    collector = module.NewsApiCollector()
    asset = Asset(ticker="PETR4.SA", asset_type=AssetType.BR_STOCK, name="Petrobras")

    raw = collector.fetch(asset)

    assert raw.source == "newsapi.org"
    assert len(raw.payload["articles"]) == len(body["articles"])


def test_fetch_raises_when_key_missing(monkeypatch):
    monkeypatch.setenv("NEWSAPI_KEY", "")

    collector = module.NewsApiCollector()
    asset = Asset(ticker="PETR4.SA", asset_type=AssetType.BR_STOCK, name="Petrobras")

    with pytest.raises(CollectorError):
        collector.fetch(asset)
