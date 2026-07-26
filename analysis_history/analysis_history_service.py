from bson import ObjectId

from conclusions.scoring import compute_ceiling_price, normalize_percent
from persistence.repositories.analysis_history_repository import AnalysisHistoryRepository


class AnalysisHistoryService:
    """Mantém o resumo "Histórico de Análises": um snapshot consultável do
    estado mais recente de cada ativo já efetivamente analisado (com
    Recomendação gerada) — não confundir com `recommendations`, que guarda
    o histórico completo/imutável de cada veredito ao longo do tempo.

    `record()` é chamado ao final de `RecommendationService.build_recommendation`,
    então só existe registro aqui para ativos que passaram pelo pipeline
    completo (coleta -> análises -> conclusão -> recomendação) — ativos
    apenas cadastrados em "Buscar Ativo" não aparecem.
    """

    def __init__(self, repository: AnalysisHistoryRepository | None = None) -> None:
        self._repository = repository or AnalysisHistoryRepository()

    def record(
        self,
        asset_id: ObjectId,
        ticker: str,
        company_name: str,
        recommendation: dict,
        fundamentalist_data: dict,
    ) -> None:
        price = fundamentalist_data.get("price")
        ceiling_price = compute_ceiling_price(fundamentalist_data)
        upside_pct = None
        if price is not None and price > 0 and ceiling_price is not None:
            upside_pct = round((ceiling_price - price) / price * 100, 2)

        dividend_yield = fundamentalist_data.get("dividend_yield")
        dividend_yield_pct = normalize_percent(dividend_yield) if dividend_yield is not None else None

        document = {
            "ticker": ticker,
            "company_name": company_name,
            "score_final": recommendation.get("fundamentalist_score_0_10"),
            "dividend_yield_expected": dividend_yield_pct,
            "current_price": price,
            "ceiling_price": ceiling_price,
            "upside_pct": upside_pct,
            "recommendation_category": recommendation.get("category"),
            "justification": recommendation.get("justification", []),
            "analyzed_at": recommendation.get("analyzed_at"),
        }
        self._repository.upsert(asset_id, document)

    def list_all(self) -> list[dict]:
        return self._repository.find_all()
