import logging
from datetime import datetime, timezone

from bson import ObjectId

from conclusions.conclusion_service import ConclusionService
from core.exceptions import RecommendationError
from persistence.repositories.recommendation_repository import RecommendationRepository
from recommendations.scoring import action_from_label, classify_agreement, classify_confidence

logger = logging.getLogger(__name__)

DISCLAIMER = (
    "Esta recomendação é gerada automaticamente com base em dados públicos e "
    "não constitui aconselhamento financeiro profissional."
)

_AGREEMENT_TEXT = {
    "concordante": "Os sinais disponíveis apontam na mesma direção.",
    "mista": "Os sinais disponíveis são conflitantes entre si.",
    "neutra": "Os sinais disponíveis não indicam uma direção clara.",
}

_CONFIDENCE_TEXT = {
    "alta": "Confiança alta: todas as análises estão disponíveis e concordam entre si.",
    "media": "Confiança média: análises incompletas ou parcialmente divergentes.",
    "baixa": "Confiança baixa: poucas análises disponíveis e/ou sinais conflitantes.",
}


class RecommendationService:
    """Consome a última Conclusão já salva (não recalcula análises nem
    conclusão) e produz o veredito final acionável (Etapa 4).
    """

    def __init__(
        self,
        conclusion_service: ConclusionService | None = None,
        recommendation_repository: RecommendationRepository | None = None,
    ) -> None:
        self._conclusion_service = conclusion_service or ConclusionService()
        self._recommendation_repository = recommendation_repository or RecommendationRepository()

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
        action = action_from_label(conclusion["label"])

        justification: list[str] = []
        for entry in breakdown.values():
            justification.extend(entry.get("highlights", []))
        justification.append(_AGREEMENT_TEXT[agreement])
        justification.append(_CONFIDENCE_TEXT[confidence])
        if missing:
            justification.append(f"Análises ausentes na conclusão-base: {', '.join(missing)}.")

        document = {
            "asset_id": asset_id,
            "ticker": ticker,
            "analyzed_at": datetime.now(timezone.utc),
            "action": action,
            "confidence": confidence,
            "agreement": agreement,
            "justification": justification,
            "disclaimer": DISCLAIMER,
            "overall_score": conclusion["overall_score"],
            "label": conclusion["label"],
            "conclusion_id": conclusion["_id"],
            "missing_analyses": missing,
        }
        document["_id"] = self._recommendation_repository.insert(document)
        logger.info(
            "Recomendação gerada para %s: action=%s confidence=%s",
            ticker,
            action,
            confidence,
            extra={"ticker": ticker},
        )
        return document
