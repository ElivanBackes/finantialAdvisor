import requests

from config.settings import get_settings
from core.assets.asset import Asset
from core.assets.asset_type import AssetType
from core.collectors.base import RawData
from core.exceptions import CollectorError

_BASE_URL = "https://newsapi.org/v2/everything"


class NewsApiCollector:
    """Collector de notícias via NewsAPI (newsapi.org).

    Não é específico de uma categoria de ativo — registrado para
    AssetType.BR_STOCK no MVP, mas reutilizável por INTL_STOCK/CRYPTO no
    futuro sem mudanças.
    """

    source_name = "newsapi.org"
    supported_asset_types = {AssetType.BR_STOCK}

    def __init__(self, page_size: int = 20, timeout: float = 10.0) -> None:
        self._page_size = page_size
        self._timeout = timeout

    def fetch(self, asset: Asset) -> RawData:
        settings = get_settings()
        if not settings.newsapi_key:
            raise CollectorError(
                "newsapi.org: NEWSAPI_KEY ausente no .env — análise de notícias desabilitada."
            )

        query = self._build_query(asset)
        params = {
            "q": query,
            "language": "pt",
            "sortBy": "publishedAt",
            "pageSize": self._page_size,
            "apiKey": settings.newsapi_key,
        }
        try:
            response = requests.get(_BASE_URL, params=params, timeout=self._timeout)
            response.raise_for_status()
            body = response.json()
        except requests.RequestException as exc:
            raise CollectorError(
                f"newsapi.org: falha ao buscar notícias de '{asset.ticker}': {exc}"
            ) from exc

        if body.get("status") != "ok":
            raise CollectorError(f"newsapi.org: resposta inesperada: {body.get('message', body)}")

        articles = [
            {
                "title": article.get("title") or "",
                "description": article.get("description") or "",
                "source": (article.get("source") or {}).get("name", ""),
                "url": article.get("url", ""),
                "published_at": article.get("publishedAt", ""),
            }
            for article in body.get("articles", [])
        ]
        payload = {"ticker": asset.ticker, "query": query, "articles": articles}
        return RawData(source=self.source_name, payload=payload)

    @staticmethod
    def _build_query(asset: Asset) -> str:
        bare_ticker = asset.ticker.removesuffix(".SA")
        terms = {t for t in (asset.name.strip() if asset.name else "", bare_ticker) if t}
        return " OR ".join(terms) if terms else bare_ticker
