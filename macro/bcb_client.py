import json
import logging
import urllib.request

logger = logging.getLogger(__name__)

_BCB_SGS_URL = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados/ultimos/{n}?formato=json"
_SELIC_SERIES = 432  # Meta Selic definida pelo Copom (% a.a.)
_EXCHANGE_RATE_SERIES = 1  # Dólar comercial venda (R$)


def _fetch_series(series_code: int, last_n: int, timeout: float = 10.0) -> list[dict] | None:
    url = _BCB_SGS_URL.format(codigo=series_code, n=last_n)
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:  # noqa: S310 — URL fixa do BCB
            return json.loads(response.read().decode())
    except Exception:
        logger.warning("BCB (série %s): falha ao buscar dados", series_code)
        return None


def get_latest_selic() -> float | None:
    """Meta Selic mais recente (% a.a.). `None` se a API do BCB estiver
    indisponível — a chamada isola essa falha, não deve derrubar a
    recomendação (mesmo princípio dos collectors de mercado).
    """
    data = _fetch_series(_SELIC_SERIES, last_n=1)
    if not data:
        return None
    return float(data[-1]["valor"])


def get_exchange_rate_trend(days: int = 20) -> tuple[float, float] | None:
    """(valor mais antigo, valor mais recente) do dólar comercial de venda
    nos últimos `days` dias úteis — usado para medir se o real está se
    desvalorizando (tende a favorecer receita dolarizada, ex: petróleo) ou
    se valorizando frente ao dólar. `None` se a API estiver indisponível ou
    não houver pontos suficientes.

    O endpoint `/dados/ultimos/N` da série 1 (dólar comercial) do BCB/SGS
    responde 400 Bad Request para N > ~20 (validado empiricamente) — ao
    contrário de séries mensais/de baixa frequência como a Selic, que
    aceitam N maiores. 20 dias úteis (~1 mês) é o maior período seguro.
    """
    data = _fetch_series(_EXCHANGE_RATE_SERIES, last_n=days)
    if not data or len(data) < 2:
        return None
    return float(data[0]["valor"]), float(data[-1]["valor"])
