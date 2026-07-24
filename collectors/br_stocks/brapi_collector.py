import requests

from config.settings import get_settings
from core.assets.asset import Asset
from core.assets.asset_type import AssetType
from core.collectors.base import RawData
from core.exceptions import CollectorError

_BASE_URL = "https://brapi.dev/api/quote/{ticker}"


class BrapiCollector:
    """Collector de ações B3 via brapi.dev (AssetType.BR_STOCK).

    Fonte alternativa/complementar ao YFinanceCollector. A brapi.dev passou
    a exigir token de autenticação em toda requisição (confirmado
    empiricamente: até o endpoint de cotação simples, sem `fundamental`/
    `modules`, retorna 401 "Token de autenticação não fornecido" sem
    token) — não funciona mais sem BRAPI_API_TOKEN configurado, ao
    contrário do que se assumia originalmente.

    Pede só a cotação simples (sem `fundamental`/`modules`): os módulos
    `defaultKeyStatistics`/`financialData` exigem plano pago (confirmado
    empiricamente: token válido do plano gratuito recebe 403
    "MODULES_NOT_AVAILABLE" ao pedi-los) e nem são necessários — os campos
    que `FundamentalistAnalyzer` usa daqui (`priceEarnings`,
    `regularMarketPrice`, `marketCap`) já vêm na cotação simples.
    """

    source_name = "brapi.dev"
    supported_asset_types = {AssetType.BR_STOCK}

    def __init__(self, timeout: float = 10.0) -> None:
        self._timeout = timeout

    def fetch(self, asset: Asset) -> RawData:
        settings = get_settings()
        if not settings.brapi_api_token:
            raise CollectorError(
                "brapi.dev: BRAPI_API_TOKEN ausente no .env — a brapi.dev passou a exigir "
                "token de autenticação em toda requisição. Obtenha um token gratuito em "
                "https://brapi.dev e configure BRAPI_API_TOKEN para habilitar esta fonte."
            )

        bare_ticker = asset.ticker.removesuffix(".SA")
        params = {"token": settings.brapi_api_token}

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
