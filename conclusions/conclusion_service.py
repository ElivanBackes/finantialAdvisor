import logging
from collections.abc import Callable
from datetime import datetime, timezone

from bson import ObjectId

from conclusions.scoring import (
    overall_label,
    score_fundamentalist,
    score_news_sentiment,
    score_technical,
)
from core.analyzers.base import AnalysisType
from core.exceptions import ConclusionError
from persistence.repositories.conclusion_repository import ConclusionRepository
from services.asset_service import AssetService

logger = logging.getLogger(__name__)

_SCORERS: dict[AnalysisType, Callable[[dict], tuple[float | None, list[str]]]] = {
    AnalysisType.FUNDAMENTALIST: score_fundamentalist,
    AnalysisType.TECHNICAL: score_technical,
    AnalysisType.NEWS_SENTIMENT: score_news_sentiment,
}

_ABSENCE_HIGHLIGHT: dict[AnalysisType, str] = {
    AnalysisType.FUNDAMENTALIST: "Nenhum indicador fundamentalista disponível.",
    AnalysisType.TECHNICAL: "Histórico insuficiente para indicadores técnicos.",
    AnalysisType.NEWS_SENTIMENT: "Nenhuma notícia recente encontrada para análise de sentimento.",
}

# Nº mínimo de análises fundamentalistas passadas (excluindo a atual) para
# considerar a média histórica de um múltiplo significativa o suficiente
# para pontuar "histórico dos múltiplos" — evita julgar "caro/barato frente
# ao próprio histórico" com 1-2 pontos de dado.
_MIN_HISTORY_POINTS = 3
_HISTORICAL_MULTIPLE_FIELDS = ("pl", "pvp", "ev_ebitda")


def _historical_multiple_averages(history: list[dict], current_id: ObjectId) -> dict[str, float]:
    values: dict[str, list[float]] = {field: [] for field in _HISTORICAL_MULTIPLE_FIELDS}
    for entry in history:
        if entry["_id"] == current_id:
            continue
        data = entry.get("data") or {}
        for field in _HISTORICAL_MULTIPLE_FIELDS:
            value = data.get(field)
            if value is not None:
                values[field].append(value)

    return {
        f"{field}_historical_avg": sum(points) / len(points)
        for field, points in values.items()
        if len(points) >= _MIN_HISTORY_POINTS
    }


class ConclusionService:
    """Sintetiza as 3 análises independentes mais recentes de um ativo em uma
    conclusão única (score ponderado -100..100 + rótulo de 3 faixas),
    persistida na coleção `conclusions` (append-only, como as análises).
    """

    def __init__(
        self,
        asset_service: AssetService | None = None,
        conclusion_repository: ConclusionRepository | None = None,
        scorers: dict[AnalysisType, Callable[[dict], tuple[float | None, list[str]]]]
        | None = None,
    ) -> None:
        self._asset_service = asset_service or AssetService()
        self._conclusion_repository = conclusion_repository or ConclusionRepository()
        self._scorers = scorers or _SCORERS

    def get_latest_conclusion(self, asset_id: ObjectId) -> dict | None:
        return self._conclusion_repository.find_latest_by_asset(asset_id)

    def build_conclusion(self, asset_id: ObjectId, ticker: str) -> dict:
        """Busca as análises mais recentes, calcula um sub-score -100..100 por
        análise disponível, combina por média igual-ponderada (peso = 1/n,
        n = nº de sub-scores disponíveis) e persiste + retorna o documento.

        Levanta ConclusionError se nenhuma das 3 análises produzir um
        sub-score utilizável (ex: ticker nunca coletado, ou as 3 análises
        falharam/estão vazias).
        """
        logger.info("Iniciando build_conclusion para %s", ticker, extra={"ticker": ticker})

        latest = self._asset_service.get_latest_analyses(asset_id)

        breakdown: dict[str, dict] = {}
        based_on: dict[str, ObjectId | None] = {}
        missing: list[str] = []
        available_scores: list[float] = []

        for analysis_type in AnalysisType:
            key = analysis_type.value
            doc = latest.get(analysis_type)
            sub_score: float | None = None
            highlights: list[str] = []

            if doc is not None:
                data = dict(doc.get("data") or {})
                if analysis_type == AnalysisType.FUNDAMENTALIST:
                    history = self._asset_service.get_analysis_history(asset_id, analysis_type)
                    data.update(_historical_multiple_averages(history, doc["_id"]))
                sub_score, highlights = self._scorers[analysis_type](data)

            if sub_score is None:
                breakdown[key] = {
                    "sub_score": None,
                    "highlights": [_ABSENCE_HIGHLIGHT[analysis_type]],
                }
                based_on[f"{key}_analysis_id"] = None
                missing.append(key)
                continue

            breakdown[key] = {"sub_score": round(sub_score, 2), "highlights": highlights}
            based_on[f"{key}_analysis_id"] = doc["_id"]
            available_scores.append(sub_score)

        if not available_scores:
            logger.warning(
                "Não há análises suficientes para gerar conclusão de %s",
                ticker,
                extra={"ticker": ticker},
            )
            raise ConclusionError(
                f"Não há análises suficientes para gerar uma conclusão de '{ticker}'. "
                "Rode 'Coletar e Analisar' primeiro."
            )

        overall_score = round(sum(available_scores) / len(available_scores), 2)
        label = overall_label(overall_score)

        document = {
            "asset_id": asset_id,
            "ticker": ticker,
            "analyzed_at": datetime.now(timezone.utc),
            "overall_score": overall_score,
            "label": label,
            "missing_analyses": missing,
            "breakdown": breakdown,
            "based_on": based_on,
        }
        document["_id"] = self._conclusion_repository.insert(document)
        logger.info(
            "Conclusão gerada para %s: score=%.2f label=%s",
            ticker,
            overall_score,
            label,
            extra={"ticker": ticker},
        )
        return document
