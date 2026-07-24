from analyzers.fundamentalist.fundamentalist_analyzer import FundamentalistAnalyzer
from analyzers.sentiment.news_sentiment_analyzer import NewsSentimentAnalyzer
from analyzers.technical.technical_analyzer import TechnicalAnalyzer
from collectors.br_stocks.brapi_collector import BrapiCollector
from collectors.br_stocks.yfinance_collector import YFinanceCollector
from collectors.news.newsapi_collector import NewsApiCollector
from core.analyzers.registry import AnalyzerRegistry
from core.collectors.registry import CollectorRegistry


def build_collector_registry() -> CollectorRegistry:
    registry = CollectorRegistry()
    registry.register(YFinanceCollector())
    registry.register(BrapiCollector())
    registry.register(NewsApiCollector())
    return registry


def build_analyzer_registry() -> AnalyzerRegistry:
    registry = AnalyzerRegistry()
    registry.register(FundamentalistAnalyzer())
    registry.register(TechnicalAnalyzer())
    registry.register(NewsSentimentAnalyzer())
    return registry
