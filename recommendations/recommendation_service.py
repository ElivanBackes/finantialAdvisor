import logging
from datetime import datetime, timezone

from bson import ObjectId

from conclusions.conclusion_service import ConclusionService
from core.exceptions import RecommendationError
from persistence.repositories.recommendation_repository import RecommendationRepository
from portfolio.portfolio_service import PortfolioService
from recommendations.scoring import (
    apply_allocation_adjustment,
    classify_agreement,
    classify_confidence,
    classify_recommendation,
)

logger = logging.getLogger(__name__)

DISCLAIMER = (
    "Esta recomendação é gerada automaticamente com base em dados públicos e "
    "não constitui aconselhamento financeiro profissional."
)

_AGREEMENT_TEXT = {
    "concordante": "Os sinais técnicos e de sentimento apontam na mesma direção do fundamentalista.",
    "mista": "Os sinais técnicos e de sentimento são conflitantes entre si.",
    "neutra": "Os sinais técnicos e de sentimento não indicam uma direção clara.",
}

_CONFIDENCE_TEXT = {
    "alta": "Confiança alta: todas as análises estão disponíveis e concordam entre si.",
    "media": "Confiança média: análises incompletas ou parcialmente divergentes.",
    "baixa": "Confiança baixa: poucas análises disponíveis e/ou sinais conflitantes.",
}

# Categorias da especificação de valuation (score 0-10 do sub-score
# fundamentalista, que já embute o critério de preço-teto/margem de segurança).
_CATEGORY_TEXT = {
    "compra_forte": "Compra Forte: excelente empresa negociando com grande margem de segurança.",
    "comprar": "Comprar: ativo atrativo, com potencial de valorização consistente.",
    "aguardar": (
        "Aguardar: empresa de qualidade, porém sem margem de segurança adequada "
        "ou com fatores conjunturais desfavoráveis."
    ),
    "manter": "Manter: sem novos aportes no momento; acompanhar evolução dos fundamentos.",
    "revisao_necessaria": (
        "Revisão Necessária: dados fundamentalistas insuficientes ou score muito "
        "baixo — avaliar deterioração dos fundamentos antes de decidir."
    ),
}


class RecommendationService:
    """Consome a última Conclusão já salva (não recalcula análises nem
    conclusão) e produz o veredito final acionável (Etapa 4).
    """

    def __init__(
        self,
        conclusion_service: ConclusionService | None = None,
        recommendation_repository: RecommendationRepository | None = None,
        portfolio_service: PortfolioService | None = None,
    ) -> None:
        self._conclusion_service = conclusion_service or ConclusionService()
        self._recommendation_repository = recommendation_repository or RecommendationRepository()
        self._portfolio_service = portfolio_service or PortfolioService()

    def get_latest_recommendation(self, asset_id: ObjectId) -> dict | None:
        return self._recommendation_repository.find_latest_by_asset(asset_id)

    def build_recommendation(self, asset_id: ObjectId, ticker: str) -> dict:
        """Busca a Conclusão mais recente já salva e deriva o veredito final.

        Levanta RecommendationError se não houver conclusão salva para o
        ativo (o usuário precisa gerar uma Conclusão primeiro).
        """
        logger.info("Iniciando build_recommendation para %s", ticker, extra={"ticker": ticker})

        conclusion = self._conclusion_service.get_latest_conclusion(asset_id)
        if conclusion is None:
            logger.warning(
                "Não há conclusão salva para %s", ticker, extra={"ticker": ticker}
            )
            raise RecommendationError(
                f"Não há conclusão salva para '{ticker}'. Gere uma Conclusão primeiro."
            )

        breakdown = conclusion["breakdown"]
        missing = conclusion["missing_analyses"]
        available_count = 3 - len(missing)

        agreement = classify_agreement(breakdown)
        confidence = classify_confidence(available_count, agreement)
        fundamentalist_sub_score = breakdown.get("fundamentalist", {}).get("sub_score")
        category, fundamentalist_score_0_10 = classify_recommendation(fundamentalist_sub_score)

        allocation = self._portfolio_service.compute_allocation(asset_id)
        allocation_status = allocation["status"] if allocation else None
        original_category = category
        category, adjusted_by_allocation = apply_allocation_adjustment(category, allocation_status)

        justification: list[str] = [_CATEGORY_TEXT[category]]
        if adjusted_by_allocation:
            justification.append(
                f"Categoria ajustada de '{_CATEGORY_TEXT[original_category]}' para 'Aguardar': "
                f"ativo em {allocation['current_allocation_pct']:.1f}% da carteira, acima da "
                f"meta de {allocation['target_allocation_pct']:.1f}% — priorizando outros ativos "
                "para evitar concentração."
            )
        justification.extend(breakdown.get("fundamentalist", {}).get("highlights", []))
        justification.append(_AGREEMENT_TEXT[agreement])
        justification.append(_CONFIDENCE_TEXT[confidence])
        if missing:
            justification.append(f"Análises ausentes na conclusão-base: {', '.join(missing)}.")

        document = {
            "asset_id": asset_id,
            "ticker": ticker,
            "analyzed_at": datetime.now(timezone.utc),
            "category": category,
            "fundamentalist_score_0_10": fundamentalist_score_0_10,
            "confidence": confidence,
            "agreement": agreement,
            "allocation": allocation,
            "justification": justification,
            "disclaimer": DISCLAIMER,
            "overall_score": conclusion["overall_score"],
            "label": conclusion["label"],
            "conclusion_id": conclusion["_id"],
            "missing_analyses": missing,
        }
        document["_id"] = self._recommendation_repository.insert(document)
        logger.info(
            "Recomendação gerada para %s: category=%s confidence=%s",
            ticker,
            category,
            confidence,
            extra={"ticker": ticker},
        )
        return document
