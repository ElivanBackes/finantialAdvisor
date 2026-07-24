from bson import ObjectId

from core.analyzers.base import AnalysisResult, AnalysisType
from core.analyzers.registry import AnalyzerRegistry
from core.assets.asset import Asset
from core.assets.asset_type import AssetType
from core.collectors.base import RawData
from core.collectors.registry import CollectorRegistry
from core.exceptions import AnalyzerError, CollectorError
from services.asset_service import AssetService


class _FakeAssetRepository:
    def __init__(self) -> None:
        self._docs: dict[str, dict] = {}

    def get_by_ticker(self, ticker: str):
        return self._docs.get(ticker)

    def upsert(self, asset: Asset):
        existing = self._docs.get(asset.ticker)
        asset_id = existing["_id"] if existing else ObjectId()
        self._docs[asset.ticker] = {
            "_id": asset_id,
            "ticker": asset.ticker,
            "asset_type": asset.asset_type.value,
            "name": asset.name,
        }
        return asset_id


class _FakeRawDataRepository:
    def __init__(self) -> None:
        self.inserted: list[dict] = []

    def insert(self, document: dict):
        document["_id"] = ObjectId()
        self.inserted.append(document)
        return document["_id"]


def _make_repo_cls():
    class _Repo:
        inserted: list[dict] = []

        def insert(self, document: dict):
            self.inserted.append(document)
            return ObjectId()

        def find_latest_by_asset(self, asset_id):
            return self.inserted[-1] if self.inserted else None

    return _Repo


class _StubCollector:
    def __init__(self, source_name: str, should_fail: bool = False) -> None:
        self.source_name = source_name
        self.supported_asset_types = {AssetType.BR_STOCK}
        self._should_fail = should_fail

    def fetch(self, asset: Asset) -> RawData:
        if self._should_fail:
            raise CollectorError(f"{self.source_name} indisponível")
        return RawData(source=self.source_name, payload={"ticker": asset.ticker})


class _StubAnalyzer:
    def __init__(self, analysis_type: AnalysisType, should_fail: bool = False) -> None:
        self.analysis_type = analysis_type
        self._should_fail = should_fail

    def analyze(self, asset: Asset, raw_data: list[RawData]) -> AnalysisResult:
        if self._should_fail:
            raise AnalyzerError(f"{self.analysis_type.value} indisponível")
        return AnalysisResult(
            asset_ticker=asset.ticker,
            analysis_type=self.analysis_type,
            data={"sources_seen": [rd.source for rd in raw_data]},
            sources=[rd.source for rd in raw_data],
        )


def _build_service(collectors, analyzers, analysis_repos):
    collector_registry = CollectorRegistry()
    for collector in collectors:
        collector_registry.register(collector)

    analyzer_registry = AnalyzerRegistry()
    for analyzer in analyzers:
        analyzer_registry.register(analyzer)

    return AssetService(
        asset_repository=_FakeAssetRepository(),
        raw_data_repository=_FakeRawDataRepository(),
        collector_registry=collector_registry,
        analyzer_registry=analyzer_registry,
        analysis_repositories=analysis_repos,
    )


def test_collect_and_analyze_happy_path():
    fundamentalist_repo = _make_repo_cls()
    technical_repo = _make_repo_cls()
    news_repo = _make_repo_cls()

    service = _build_service(
        collectors=[_StubCollector("yfinance"), _StubCollector("newsapi.org")],
        analyzers=[
            _StubAnalyzer(AnalysisType.FUNDAMENTALIST),
            _StubAnalyzer(AnalysisType.TECHNICAL),
            _StubAnalyzer(AnalysisType.NEWS_SENTIMENT),
        ],
        analysis_repos={
            AnalysisType.FUNDAMENTALIST: fundamentalist_repo,
            AnalysisType.TECHNICAL: technical_repo,
            AnalysisType.NEWS_SENTIMENT: news_repo,
        },
    )

    results = service.collect_and_analyze("PETR4.SA", AssetType.BR_STOCK, name="Petrobras")

    assert results[AnalysisType.FUNDAMENTALIST] is not None
    assert results[AnalysisType.TECHNICAL] is not None
    assert results[AnalysisType.NEWS_SENTIMENT] is not None
    assert len(fundamentalist_repo.inserted) == 1
    assert len(technical_repo.inserted) == 1
    assert len(news_repo.inserted) == 1


def test_collect_and_analyze_isolates_collector_failure():
    fundamentalist_repo = _make_repo_cls()
    technical_repo = _make_repo_cls()
    news_repo = _make_repo_cls()

    service = _build_service(
        collectors=[_StubCollector("yfinance"), _StubCollector("newsapi.org", should_fail=True)],
        analyzers=[
            _StubAnalyzer(AnalysisType.FUNDAMENTALIST),
            _StubAnalyzer(AnalysisType.TECHNICAL),
            _StubAnalyzer(AnalysisType.NEWS_SENTIMENT),
        ],
        analysis_repos={
            AnalysisType.FUNDAMENTALIST: fundamentalist_repo,
            AnalysisType.TECHNICAL: technical_repo,
            AnalysisType.NEWS_SENTIMENT: news_repo,
        },
    )

    results = service.collect_and_analyze("PETR4.SA", AssetType.BR_STOCK, name="Petrobras")

    assert results[AnalysisType.FUNDAMENTALIST] is not None
    assert results[AnalysisType.TECHNICAL] is not None
    assert results[AnalysisType.NEWS_SENTIMENT] is None
    assert len(news_repo.inserted) == 0


def test_collect_and_analyze_isolates_analyzer_failure():
    fundamentalist_repo = _make_repo_cls()
    technical_repo = _make_repo_cls()
    news_repo = _make_repo_cls()

    service = _build_service(
        collectors=[_StubCollector("yfinance"), _StubCollector("newsapi.org")],
        analyzers=[
            _StubAnalyzer(AnalysisType.FUNDAMENTALIST),
            _StubAnalyzer(AnalysisType.TECHNICAL),
            _StubAnalyzer(AnalysisType.NEWS_SENTIMENT, should_fail=True),
        ],
        analysis_repos={
            AnalysisType.FUNDAMENTALIST: fundamentalist_repo,
            AnalysisType.TECHNICAL: technical_repo,
            AnalysisType.NEWS_SENTIMENT: news_repo,
        },
    )

    results = service.collect_and_analyze("PETR4.SA", AssetType.BR_STOCK, name="Petrobras")

    assert results[AnalysisType.NEWS_SENTIMENT] is None
    assert len(news_repo.inserted) == 0
    assert results[AnalysisType.FUNDAMENTALIST] is not None
    assert len(fundamentalist_repo.inserted) == 1
