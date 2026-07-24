import requests

from config.settings import get_settings
from core.assets.asset import Asset
from core.assets.asset_type import AssetType
from core.collectors.base import RawData
from core.exceptions import CollectorError

_BASE_URL = "https://brapi.dev/api/quote/{ticker}"


class BrapiCollector:
    """Collector de ações B3 via brapi.dev (AssetType.BR_STOCK).

    Fonte alternativa/complementar ao YFinanceCollector — funciona sem
    BRAPI_API_TOKEN (com rate limit menor); usa o token do .env se presente.
    """

    source_name = "brapi.dev"
    supported_asset_types = {AssetType.BR_STOCK}

    def __init__(self, timeout: float = 10.0) -> None:
        self._timeout = timeout

    def fetch(self, asset: Asset) -> RawData:
        bare_ticker = asset.ticker.removesuffix(".SA")
        settings = get_settings()
        params = {"fundamental": "true", "modules": "defaultKeyStatistics,financialData"}
        if settings.brapi_api_token:
            params["token"] = settings.brapi_api_token

        try:
            response = requests.get(
                _BASE_URL.format(ticker=bare_ticker), params=params, timeout=self._timeout
            )
            response.raise_for_status()
            body = response.json()
        except requests.RequestException as exc:
            raise CollectorError(f"brapi.dev: falha ao buscar '{asset.ticker}': {exc}") from exc

        results = body.get("results") or []
        if not results:
            raise CollectorError(
                f"brapi.dev: ticker '{asset.ticker}' sem resultados "
                f"({body.get('message', 'sem detalhes')})"
            )

        payload = {"ticker": asset.ticker, "quote": results[0]}
        return RawData(source=self.source_name, payload=payload)
