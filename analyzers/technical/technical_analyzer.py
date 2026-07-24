import pandas as pd

from core.analyzers.base import AnalysisResult, AnalysisType
from core.assets.asset import Asset
from core.collectors.base import RawData
from core.exceptions import AnalyzerError

_SMA_WINDOWS = (20, 50, 200)
_RSI_WINDOW = 14


class TechnicalAnalyzer:
    """Análise técnica: SMA 20/50/200, RSI(14) e MACD.

    Consome apenas RawData da fonte 'yfinance' — é a única que traz
    histórico OHLCV (brapi.dev só expõe cotação atual, sem série histórica).
    """

    analysis_type = AnalysisType.TECHNICAL

    def analyze(self, asset: Asset, raw_data: list[RawData]) -> AnalysisResult:
        yf_raw = next((rd for rd in raw_data if rd.source == "yfinance"), None)
        if yf_raw is None:
            raise AnalyzerError(
                f"TechnicalAnalyzer requer RawData de 'yfinance' para {asset.ticker}"
            )

        history = yf_raw.payload.get("history") or []
        if len(history) < 2:
            raise AnalyzerError(f"Histórico insuficiente para análise técnica de {asset.ticker}")

        df = pd.DataFrame(history)
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date").reset_index(drop=True)
        close = df["close"]

        sma = {
            f"sma_{w}": round(float(close.rolling(w).mean().iloc[-1]), 4)
            if len(close) >= w
            else None
            for w in _SMA_WINDOWS
        }
        rsi_value = self._rsi(close, _RSI_WINDOW)
        macd_line, signal_line, histogram = self._macd(close)

        last_price = float(close.iloc[-1])
        mid_term = sma.get("sma_50")
        if mid_term is None:
            trend = "indefinida"
        else:
            trend = "alta" if last_price > mid_term else "baixa"

        data = {
            "last_price": last_price,
            **sma,
            "rsi_14": rsi_value,
            "macd": macd_line,
            "macd_signal": signal_line,
            "macd_histogram": histogram,
            "trend": trend,
            "history_points": len(close),
        }
        return AnalysisResult(
            asset_ticker=asset.ticker,
            analysis_type=self.analysis_type,
            data=data,
            sources=[yf_raw.source],
        )

    @staticmethod
    def _rsi(close: pd.Series, window: int) -> float | None:
        if len(close) < window + 1:
            return None
        delta = close.diff()
        gain = delta.clip(lower=0).rolling(window).mean()
        loss = (-delta.clip(upper=0)).rolling(window).mean()
        last_gain = gain.iloc[-1]
        last_loss = loss.iloc[-1]
        if pd.isna(last_gain) or pd.isna(last_loss):
            return None
        if last_loss == 0:
            # Sem perdas na janela: RSI satura em 100 (só ganhos) ou fica
            # neutro em 50 (preço estável, sem ganhos nem perdas).
            return 100.0 if last_gain > 0 else 50.0
        rs = last_gain / last_loss
        rsi = 100 - (100 / (1 + rs))
        return round(float(rsi), 2)

    @staticmethod
    def _macd(close: pd.Series) -> tuple[float | None, float | None, float | None]:
        if len(close) < 26:
            return None, None, None
        ema_fast = close.ewm(span=12, adjust=False).mean()
        ema_slow = close.ewm(span=26, adjust=False).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=9, adjust=False).mean()
        histogram = macd_line - signal_line
        return (
            round(float(macd_line.iloc[-1]), 4),
            round(float(signal_line.iloc[-1]), 4),
            round(float(histogram.iloc[-1]), 4),
        )
