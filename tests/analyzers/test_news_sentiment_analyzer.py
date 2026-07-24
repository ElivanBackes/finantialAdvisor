import pytest

from analyzers.sentiment.news_sentiment_analyzer import NewsSentimentAnalyzer
from core.analyzers.base import AnalysisType
from core.assets.asset import Asset
from core.assets.asset_type import AssetType
from core.collectors.base import RawData
from core.exceptions import AnalyzerError


def test_analyze_scores_mixed_articles():
    asset = Asset(ticker="PETR4.SA", asset_type=AssetType.BR_STOCK, name="Petrobras")
    articles = [
        {
            "title": "Petrobras registra lucro recorde e alta valorizacao",
            "description": "Resultado positivo supera expectativas",
        },
        {
            "title": "Petrobras enfrenta crise e queda no lucro",
            "description": "Prejuizo preocupa investidores",
        },
        {
            "title": "Petrobras anuncia nova reuniao de diretoria",
            "description": "Sem impacto relevante",
        },
    ]
    raw = RawData(source="newsapi.org", payload={"ticker": "PETR4.SA", "articles": articles})

    result = NewsSentimentAnalyzer().analyze(asset, [raw])

    assert result.analysis_type == AnalysisType.NEWS_SENTIMENT
    assert result.data["articles_analyzed"] == 3
    assert result.data["positive_count"] == 1
    assert result.data["negative_count"] == 1
    assert result.data["neutral_count"] == 1
    assert -1.0 <= result.data["score"] <= 1.0


def test_analyze_handles_no_articles():
    asset = Asset(ticker="PETR4.SA", asset_type=AssetType.BR_STOCK, name="Petrobras")
    raw = RawData(source="newsapi.org", payload={"ticker": "PETR4.SA", "articles": []})

    result = NewsSentimentAnalyzer().analyze(asset, [raw])

    assert result.data["score"] == 0.0
    assert result.data["articles_analyzed"] == 0


def test_analyze_raises_without_newsapi_source():
    asset = Asset(ticker="PETR4.SA", asset_type=AssetType.BR_STOCK, name="Petrobras")

    with pytest.raises(AnalyzerError):
        NewsSentimentAnalyzer().analyze(asset, [])
