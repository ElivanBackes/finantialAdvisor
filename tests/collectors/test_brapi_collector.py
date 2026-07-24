import json
from pathlib import Path

import pytest

from collectors.br_stocks import brapi_collector as module
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


def test_fetch_returns_raw_data(monkeypatch):
    body = json.loads((_FIXTURES_DIR / "brapi_petr4_sample.json").read_text())

    def fake_get(url, params=None, timeout=None):
        return _FakeResponse(body)

    monkeypatch.setattr(module.requests, "get", fake_get)

    collector = module.BrapiCollector()
    asset = Asset(ticker="PETR4.SA", asset_type=AssetType.BR_STOCK, name="Petrobras")

    raw = collector.fetch(asset)

    assert raw.source == "brapi.dev"
    assert raw.payload["quote"]["symbol"] == "PETR4"


def test_fetch_raises_when_no_results(monkeypatch):
    def fake_get(url, params=None, timeout=None):
        return _FakeResponse({"results": [], "message": "not found"})

    monkeypatch.setattr(module.requests, "get", fake_get)

    collector = module.BrapiCollector()
    asset = Asset(ticker="INEXISTENTE.SA", asset_type=AssetType.BR_STOCK, name="Inexistente")

    with pytest.raises(CollectorError):
        collector.fetch(asset)
