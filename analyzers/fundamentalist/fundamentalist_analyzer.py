from core.analyzers.base import AnalysisResult, AnalysisType
from core.assets.asset import Asset
from core.collectors.base import RawData
from core.exceptions import AnalyzerError

_YF_FIELD_MAP = {
    "pl": "trailingPE",
    "pvp": "priceToBook",
    "dividend_yield": "dividendYield",
    "roe": "returnOnEquity",
    "debt_to_equity": "debtToEquity",
    "market_cap": "marketCap",
    "price": "currentPrice",
}

# Nomes de campo do brapi.dev (modules=defaultKeyStatistics,financialData).
# Cobertura parcial: brapi só é usado como fallback quando yfinance não tem o dado.
_BRAPI_FIELD_MAP = {
    "pl": "priceEarnings",
    "price": "regularMarketPrice",
    "market_cap": "marketCap",
}


class FundamentalistAnalyzer:
    """Análise fundamentalista: P/L, P/VP, Dividend Yield, ROE, endividamento.

    Prefere dados do yfinance; usa brapi.dev como fallback por campo quando
    o yfinance não trouxer o indicador.
    """

    analysis_type = AnalysisType.FUNDAMENTALIST

    def analyze(self, asset: Asset, raw_data: list[RawData]) -> AnalysisResult:
        by_source = {rd.source: rd.payload for rd in raw_data}
        yf_info = (by_source.get("yfinance") or {}).get("info", {})
        brapi_quote = (by_source.get("brapi.dev") or {}).get("quote", {})

        if not yf_info and not brapi_quote:
            raise AnalyzerError(f"Sem dados fundamentalistas disponíveis para {asset.ticker}")

        indicators: dict[str, float | None] = {}
        field_sources: dict[str, str] = {}
        for field, yf_key in _YF_FIELD_MAP.items():
            value = yf_info.get(yf_key)
            if value is not None:
                indicators[field] = value
                field_sources[field] = "yfinance"
                continue

            brapi_key = _BRAPI_FIELD_MAP.get(field)
            value = brapi_quote.get(brapi_key) if brapi_key else None
            indicators[field] = value
            if value is not None:
                field_sources[field] = "brapi.dev"

        sources_used = sorted({rd.source for rd in raw_data})
        return AnalysisResult(
            asset_ticker=asset.ticker,
            analysis_type=self.analysis_type,
            data={**indicators, "field_sources": field_sources},
            sources=sources_used,
        )
