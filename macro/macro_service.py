from macro.bcb_client import get_exchange_rate_trend, get_latest_selic
from macro.oil_client import get_oil_price_trend

_MAX_ADJUSTMENT = 10.0


def _classify_sector(sector: str | None, industry: str | None) -> str | None:
    haystack = f"{sector or ''} {industry or ''}".lower()
    if "oil" in haystack or "gas" in haystack:
        return "oil_gas"
    if "bank" in haystack or "insurance" in haystack:
        return "financial"
    return None


def _pct_change(start: float, end: float) -> float:
    if start == 0:
        return 0.0
    return (end - start) / start * 100


class MacroService:
    """Ajuste de cenário macroeconômico setorial — conforme a
    especificação, atua como um pequeno ajuste na pontuação (bounded a
    ±10 pontos na escala -100..100), nunca como critério principal pesado.

    Cobre apenas os setores com fonte de dado gratuita e confiável:
    Petróleo/Gás (preço do Brent + câmbio, via BCB/yfinance) e
    Bancos/Seguros (Selic, via BCB). Demais setores retornam `None` (sem
    ajuste) em vez de uma heurística sem lastro em dado real.
    """

    def __init__(
        self,
        get_latest_selic=get_latest_selic,
        get_exchange_rate_trend=get_exchange_rate_trend,
        get_oil_price_trend=get_oil_price_trend,
    ) -> None:
        self._get_latest_selic = get_latest_selic
        self._get_exchange_rate_trend = get_exchange_rate_trend
        self._get_oil_price_trend = get_oil_price_trend

    def compute_adjustment(self, sector: str | None, industry: str | None) -> dict | None:
        category = _classify_sector(sector, industry)
        if category == "oil_gas":
            return self._oil_gas_adjustment()
        if category == "financial":
            return self._financial_adjustment()
        return None

    def _oil_gas_adjustment(self) -> dict | None:
        oil_trend = self._get_oil_price_trend()
        fx_trend = self._get_exchange_rate_trend()
        if oil_trend is None and fx_trend is None:
            return None

        adjustment = 0.0
        factors: list[str] = []

        if oil_trend is not None:
            oil_change = _pct_change(*oil_trend)
            if oil_change >= 5:
                adjustment += 5
                factors.append(
                    f"Petróleo (Brent) em alta ({oil_change:+.1f}% no período) "
                    "— cenário tende a favorecer o setor."
                )
            elif oil_change <= -5:
                adjustment -= 5
                factors.append(
                    f"Petróleo (Brent) em queda ({oil_change:+.1f}% no período) "
                    "— cenário tende a pressionar o setor."
                )

        if fx_trend is not None:
            fx_change = _pct_change(*fx_trend)
            if fx_change >= 3:
                adjustment += 3
                factors.append(
                    f"Real desvalorizado frente ao dólar ({fx_change:+.1f}%) "
                    "— tende a favorecer receita dolarizada do setor."
                )
            elif fx_change <= -3:
                adjustment -= 3
                factors.append(
                    f"Real valorizado frente ao dólar ({fx_change:+.1f}%) "
                    "— tende a reduzir receita dolarizada do setor."
                )

        if not factors:
            return None

        return {
            "sector_category": "petroleo_gas",
            "adjustment": max(-_MAX_ADJUSTMENT, min(_MAX_ADJUSTMENT, adjustment)),
            "factors": factors,
        }

    def _financial_adjustment(self) -> dict | None:
        selic = self._get_latest_selic()
        if selic is None:
            return None

        if selic >= 12:
            adjustment = 5.0
            text = f"Selic elevada ({selic:.2f}% a.a.) — tende a favorecer margens de bancos/seguradoras."
        elif selic < 7:
            adjustment = -5.0
            text = f"Selic baixa ({selic:.2f}% a.a.) — tende a pressionar margens de bancos/seguradoras."
        else:
            return None

        return {
            "sector_category": "bancos_seguros",
            "adjustment": adjustment,
            "factors": [text],
        }
