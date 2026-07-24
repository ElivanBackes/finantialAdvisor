import re
import unicodedata

from analyzers.sentiment.lexicon_ptbr import NEGATIVE_WORDS, POSITIVE_WORDS
from core.analyzers.base import AnalysisResult, AnalysisType
from core.assets.asset import Asset
from core.collectors.base import RawData
from core.exceptions import AnalyzerError

_TOKEN_RE = re.compile(r"[a-z]+")


def _normalize(text: str) -> str:
    nfkd = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def _tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(_normalize(text))


class NewsSentimentAnalyzer:
    """Análise de notícias/sentimento: score por léxico PT-BR simples."""

    analysis_type = AnalysisType.NEWS_SENTIMENT

    def analyze(self, asset: Asset, raw_data: list[RawData]) -> AnalysisResult:
        news_raw = next((rd for rd in raw_data if rd.source == "newsapi.org"), None)
        if news_raw is None:
            raise AnalyzerError(
                f"NewsSentimentAnalyzer requer RawData de 'newsapi.org' para {asset.ticker}"
            )

        articles = news_raw.payload.get("articles") or []
        if not articles:
            data = {
                "score": 0.0,
                "positive_count": 0,
                "negative_count": 0,
                "neutral_count": 0,
                "articles_analyzed": 0,
            }
            return AnalysisResult(
                asset_ticker=asset.ticker,
                analysis_type=self.analysis_type,
                data=data,
                sources=[news_raw.source],
            )

        scores: list[float] = []
        pos_n = neg_n = neu_n = 0
        for article in articles:
            tokens = _tokenize(f"{article.get('title', '')} {article.get('description', '')}")
            pos_hits = sum(1 for t in tokens if t in POSITIVE_WORDS)
            neg_hits = sum(1 for t in tokens if t in NEGATIVE_WORDS)

            if pos_hits == neg_hits == 0:
                scores.append(0.0)
                neu_n += 1
                continue

            article_score = (pos_hits - neg_hits) / (pos_hits + neg_hits)
            scores.append(article_score)
            if article_score > 0:
                pos_n += 1
            elif article_score < 0:
                neg_n += 1
            else:
                neu_n += 1

        data = {
            "score": round(sum(scores) / len(scores), 4),
            "positive_count": pos_n,
            "negative_count": neg_n,
            "neutral_count": neu_n,
            "articles_analyzed": len(articles),
        }
        return AnalysisResult(
            asset_ticker=asset.ticker,
            analysis_type=self.analysis_type,
            data=data,
            sources=[news_raw.source],
        )
