import logging

from bson import ObjectId

from core.analyzers.base import AnalysisResult, AnalysisType
from core.analyzers.registry import AnalyzerRegistry
from core.assets.asset import Asset
from core.assets.asset_type import AssetType
from core.collectors.base import RawData
from core.collectors.registry import CollectorRegistry
from core.exceptions import FinancialAdvisorError
from persistence.repositories.asset_repository import AssetRepository
from persistence.repositories.fundamentalist_repository import FundamentalistRepository
from persistence.repositories.news_sentiment_repository import NewsSentimentRepository
from persistence.repositories.raw_data_repository import RawDataRepository
from persistence.repositories.technical_repository import TechnicalRepository
from services.bootstrap import build_analyzer_registry, build_collector_registry

logger = logging.getLogger(__name__)

_ANALYSIS_REPOSITORIES = {
    AnalysisType.FUNDAMENTALIST: FundamentalistRepository,
    AnalysisType.TECHNICAL: TechnicalRepository,
    AnalysisType.NEWS_SENTIMENT: NewsSentimentRepository,
}

# Quais fontes (RawData.source) cada AnalysisType recebe.
_ANALYZER_SOURCE_FILTER: dict[AnalysisType, set[str]] = {
    AnalysisType.FUNDAMENTALIST: {"yfinance", "brapi.dev"},
    AnalysisType.TECHNICAL: {"yfinance"},
    AnalysisType.NEWS_SENTIMENT: {"newsapi.org"},
}


class AssetService:
    """Fachada de orquestração consumida pelo dashboard Streamlit.

    A partir da Etapa 2, `collect_and_analyze` orquestra
    collectors -> analyzers -> repositories de fato.
    """

    def __init__(
        self,
        asset_repository: AssetRepository | None = None,
        raw_data_repository: RawDataRepository | None = None,
        collector_registry: CollectorRegistry | None = None,
        analyzer_registry: AnalyzerRegistry | None = None,
        analysis_repositories: dict[AnalysisType, type] | None = None,
    ) -> None:
        self._asset_repository = asset_repository or AssetRepository()
        self._raw_data_repository = raw_data_repository or RawDataRepository()
        self._collector_registry = collector_registry or build_collector_registry()
        self._analyzer_registry = analyzer_registry or build_analyzer_registry()
        self._analysis_repositories = analysis_repositories or _ANALYSIS_REPOSITORIES

    def get_or_create_asset(self, ticker: str, asset_type: AssetType, name: str = "") -> ObjectId:
        existing = self._asset_repository.get_by_ticker(ticker)
        if existing is not None:
            return existing["_id"]

        asset = Asset(ticker=ticker, asset_type=asset_type, name=name or ticker)
        return self._asset_repository.upsert(asset)

    def get_latest_analyses(self, asset_id: ObjectId) -> dict[AnalysisType, dict | None]:
        """Retorna a análise mais recente de cada tipo (ou None, se ainda não coletada)."""
        return {
            analysis_type: repository_cls().find_latest_by_asset(asset_id)
            for analysis_type, repository_cls in _ANALYSIS_REPOSITORIES.items()
        }

    def collect_and_analyze(
        self, ticker: str, asset_type: AssetType, name: str = ""
    ) -> dict[AnalysisType, AnalysisResult | None]:
        """Coleta dados de todas as fontes registradas e roda as 3 análises.

        Falhas de um collector ou analyzer são isoladas: uma fonte
        indisponível (ex: NEWSAPI_KEY ausente) não impede as demais análises
        de serem calculadas e persistidas. O tipo correspondente recebe
        `None` no retorno quando a análise não pôde ser produzida.
        """
        asset_id = self.get_or_create_asset(ticker=ticker, asset_type=asset_type, name=name)
        asset_doc = self._asset_repository.get_by_ticker(ticker)
        asset = Asset(ticker=ticker, asset_type=asset_type, name=asset_doc.get("name", ticker))

        raw_by_source: dict[str, RawData] = {}
        raw_ids_by_source: dict[str, ObjectId] = {}
        for collector in self._collector_registry.get(asset_type):
            try:
                raw = collector.fetch(asset)
            except FinancialAdvisorError as exc:
                logger.warning(
                    "Collector '%s' falhou para %s: %s", collector.source_name, ticker, exc
                )
                continue
            except Exception:
                logger.exception(
                    "Collector '%s' falhou inesperadamente para %s", collector.source_name, ticker
                )
                continue

            raw_by_source[raw.source] = raw
            raw_ids_by_source[raw.source] = self._raw_data_repository.insert(
                {
                    "asset_id": asset_id,
                    "ticker": ticker,
                    "source": raw.source,
                    "payload": raw.payload,
                    "fetched_at": raw.fetched_at,
                }
            )

        results: dict[AnalysisType, AnalysisResult | None] = {}
        for analysis_type in AnalysisType:
            allowed = _ANALYZER_SOURCE_FILTER.get(analysis_type, set())
            relevant = [rd for src, rd in raw_by_source.items() if src in allowed]
            if not relevant:
                logger.warning(
                    "Sem RawData para %s (%s) — análise pulada", analysis_type.value, ticker
                )
                results[analysis_type] = None
                continue

            try:
                analyzer = self._analyzer_registry.get(analysis_type)
                result = analyzer.analyze(asset, relevant)
            except FinancialAdvisorError as exc:
                logger.warning(
                    "Analyzer '%s' falhou para %s: %s", analysis_type.value, ticker, exc
                )
                results[analysis_type] = None
                continue
            except Exception:
                logger.exception(
                    "Analyzer '%s' falhou inesperadamente para %s", analysis_type.value, ticker
                )
                results[analysis_type] = None
                continue

            repository_cls = self._analysis_repositories[analysis_type]
            repository_cls().insert(
                {
                    "asset_id": asset_id,
                    "ticker": ticker,
                    "analyzed_at": result.analyzed_at,
                    "sources": result.sources,
                    "data": result.data,
                    "raw_data_refs": [raw_ids_by_source[rd.source] for rd in relevant],
                }
            )
            results[analysis_type] = result

        return results
