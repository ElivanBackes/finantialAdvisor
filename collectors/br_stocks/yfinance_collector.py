import logging

import yfinance as yf

from core.assets.asset import Asset
from core.assets.asset_type import AssetType
from core.collectors.base import RawData
from core.exceptions import CollectorError

logger = logging.getLogger(__name__)

_RELEVANT_INFO_FIELDS = [
    "longName",
    "shortName",
    "sector",
    "industry",
    "currency",
    "currentPrice",
    "regularMarketPrice",
    "marketCap",
    "trailingPE",
    "forwardPE",
    "priceToBook",
    "dividendYield",
    "returnOnEquity",
    "debtToEquity",
    "trailingEps",
    "totalDebt",
    "totalCash",
    "payoutRatio",
    "freeCashflow",
    "enterpriseToEbitda",
    "earningsGrowth",
    "revenueGrowth",
    "ebit",
    "taxRateForCalcs",
    "investedCapital",
]

# Linhas dos DataFrames de demonstrativos do yfinance (`.financials` /
# `.balance_sheet`) usadas para calcular ROIC = EBIT x (1 - alíquota) /
# Invested Capital. Colunas vêm em ordem decrescente de data — usamos o
# valor mais recente não-nulo (nem todo período tem todas as linhas).
_FINANCIALS_ROW = "EBIT"
_TAX_RATE_ROW = "Tax Rate For Calcs"
_BALANCE_SHEET_ROW = "Invested Capital"


def _latest_non_null(df, row_label: str) -> float | None:
    if df is None or df.empty or row_label not in df.index:
        return None
    for value in df.loc[row_label]:
        if value is not None and value == value:  # descarta NaN sem exigir pandas
            return float(value)
    return None


class YFinanceCollector:
    """Collector de ações B3 via yfinance (AssetType.BR_STOCK).

    Tickers B3 usam sufixo ".SA" (ex: PETR4.SA). O payload retornado
    combina indicadores fundamentalistas (`info`) e histórico OHLCV
    (`history`), servindo de fonte compartilhada para FundamentalistAnalyzer
    e TechnicalAnalyzer.
    """

    source_name = "yfinance"
    supported_asset_types = {AssetType.BR_STOCK}

    def __init__(self, history_period: str = "1y", history_interval: str = "1d") -> None:
        self._history_period = history_period
        self._history_interval = history_interval

    def fetch(self, asset: Asset) -> RawData:
        try:
            ticker = yf.Ticker(asset.ticker)
            info = ticker.info or {}
            history_df = ticker.history(
                period=self._history_period, interval=self._history_interval
            )
        except Exception as exc:
            raise CollectorError(f"yfinance: falha ao buscar '{asset.ticker}': {exc}") from exc

        has_price = (
            info.get("regularMarketPrice") is not None or info.get("currentPrice") is not None
        )
        if not has_price and (history_df is None or history_df.empty):
            raise CollectorError(f"yfinance: ticker '{asset.ticker}' não encontrado ou sem dados")

        history = []
        if history_df is not None and not history_df.empty:
            for idx, row in history_df.iterrows():
                history.append(
                    {
                        "date": idx.isoformat(),
                        "open": float(row["Open"]),
                        "high": float(row["High"]),
                        "low": float(row["Low"]),
                        "close": float(row["Close"]),
                        "volume": int(row["Volume"]),
                    }
                )

        # Demonstrativos financeiros (ROIC) são chamadas extras e mais frágeis
        # que `.info` — isoladas para que uma falha aqui não derrube a coleta
        # do resto (info/history já validados acima).
        extra_info = dict(info)
        try:
            ebit = _latest_non_null(ticker.financials, _FINANCIALS_ROW)
            tax_rate = _latest_non_null(ticker.financials, _TAX_RATE_ROW)
            invested_capital = _latest_non_null(ticker.balance_sheet, _BALANCE_SHEET_ROW)
            if ebit is not None:
                extra_info["ebit"] = ebit
            if tax_rate is not None:
                extra_info["taxRateForCalcs"] = tax_rate
            if invested_capital is not None:
                extra_info["investedCapital"] = invested_capital
        except Exception:
            logger.warning(
                "yfinance: falha ao buscar demonstrativos financeiros (ROIC) para %s",
                asset.ticker,
            )

        payload = {
            "ticker": asset.ticker,
            "info": {
                k: extra_info.get(k) for k in _RELEVANT_INFO_FIELDS if extra_info.get(k) is not None
            },
            "history": history,
        }
        return RawData(source=self.source_name, payload=payload)
