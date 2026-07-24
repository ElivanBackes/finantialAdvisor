import pytest

from core.analyzers.base import AnalysisResult, AnalysisType
from core.analyzers.registry import AnalyzerRegistry
from core.assets.asset import Asset
from core.assets.asset_type import AssetType
from core.collectors.base import RawData
from core.collectors.registry import CollectorRegistry
from core.exceptions import UnsupportedAssetTypeError


class _FakeCollector:
    source_name = "fake-source"
    supported_asset_types = {AssetType.BR_STOCK}

    def fetch(self, asset: Asset) -> RawData:
        return RawData(source=self.source_name, payload={"ticker": asset.ticker})


class _FakeAnalyzer:
    analysis_type = AnalysisType.FUNDAMENTALIST

    def analyze(self, asset: Asset, raw_data: list[RawData]) -> AnalysisResult:
        return AnalysisResult(
            asset_ticker=asset.ticker, analysis_type=self.analysis_type, data={}
        )


def test_collector_registry_registers_and_returns():
    registry = CollectorRegistry()
    collector = _FakeCollector()

    registry.register(collector)

    assert registry.get(AssetType.BR_STOCK) == [collector]


def test_collector_registry_raises_for_unregistered_type():
    registry = CollectorRegistry()

    with pytest.raises(UnsupportedAssetTypeError):
        registry.get(AssetType.CRYPTO)


def test_analyzer_registry_registers_and_returns():
    registry = AnalyzerRegistry()
    analyzer = _FakeAnalyzer()

    registry.register(analyzer)

    assert registry.get(AnalysisType.FUNDAMENTALIST) is analyzer


def test_analyzer_registry_raises_for_unregistered_type():
    registry = AnalyzerRegistry()

    with pytest.raises(UnsupportedAssetTypeError):
        registry.get(AnalysisType.TECHNICAL)
