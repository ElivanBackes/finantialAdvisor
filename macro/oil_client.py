import logging

import yfinance as yf

logger = logging.getLogger(__name__)

_BRENT_TICKER = "BZ=F"  # Futuro de petróleo Brent, já disponível via yfinance


def get_oil_price_trend(period: str = "3mo") -> tuple[float, float] | None:
    """(preço mais antigo, preço mais recente) do petróleo Brent no
    período informado — usado para medir a tendência do preço
    internacional do petróleo, fator relevante para o setor de óleo e gás.
    `None` se a busca falhar ou não houver histórico suficiente.
    """
    try:
        history = yf.Ticker(_BRENT_TICKER).history(period=period, interval="1d")
    except Exception:
        logger.warning("yfinance: falha ao buscar preço do petróleo (%s)", _BRENT_TICKER)
        return None

    if history is None or history.empty or len(history) < 2:
        return None
    return float(history["Close"].iloc[0]), float(history["Close"].iloc[-1])
