import pytest
from bson import ObjectId

from core.exceptions import RecommendationError
from recommendations.recommendation_service import DISCLAIMER, RecommendationService


class _FakeConclusionService:
    def __init__(self, conclusion: dict | None) -> None:
        self._conclusion = conclusion

    def get_latest_conclusion(self, asset_id):
        return self._conclusion


class _FakeRecommendationRepository:
    def __init__(self) -> None:
        self.inserted: list[dict] = []

    def insert(self, document: dict):
        document["_id"] = ObjectId()
        self.inserted.append(document)
        return document["_id"]

    def find_latest_by_asset(self, asset_id):
        return self.inserted[-1] if self.inserted else None


def _conclusion(label, breakdown, missing):
    return {
        "_id": ObjectId(),
        "overall_score": 50.0,
        "label": label,
        "missing_analyses": missing,
        "breakdown": breakdown,
    }


def test_build_recommendation_all_concordant_complete():
    conclusion = _conclusion(
        "favoravel",
        {
            "fundamentalist": {"sub_score": 60.0, "highlights": ["x"]},
            "technical": {"sub_score": 40.0, "highlights": ["y"]},
            "news_sentiment": {"sub_score": 25.0, "highlights": ["z"]},
        },
        [],
    )
    repo = _FakeRecommendationRepository()
    service = RecommendationService(
        conclusion_service=_FakeConclusionService(conclusion), recommendation_repository=repo
    )

    result = service.build_recommendation(ObjectId(), "PETR4.SA")

    assert result["category"] == "comprar"  # sub_score 60 -> 8.0 na escala 0-10
    assert result["fundamentalist_score_0_10"] == 8.0
    assert result["confidence"] == "alta"
    assert result["agreement"] == "concordante"
    assert result["disclaimer"] == DISCLAIMER
    assert len(repo.inserted) == 1


def test_build_recommendation_mixed_signals_downgrades_confidence():
    conclusion = _conclusion(
        "neutro",
        {
            "fundamentalist": {"sub_score": 60.0, "highlights": []},
            "technical": {"sub_score": -50.0, "highlights": []},
            "news_sentiment": {"sub_score": 10.0, "highlights": []},
        },
        [],
    )
    service = RecommendationService(
        conclusion_service=_FakeConclusionService(conclusion),
        recommendation_repository=_FakeRecommendationRepository(),
    )

    result = service.build_recommendation(ObjectId(), "PETR4.SA")

    assert result["agreement"] == "mista"
    assert result["confidence"] == "media"


def test_build_recommendation_missing_one_lowers_confidence():
    conclusion = _conclusion(
        "favoravel",
        {
            "fundamentalist": {"sub_score": 60.0, "highlights": []},
            "technical": {"sub_score": None, "highlights": []},
            "news_sentiment": {"sub_score": 40.0, "highlights": []},
        },
        ["technical"],
    )
    service = RecommendationService(
        conclusion_service=_FakeConclusionService(conclusion),
        recommendation_repository=_FakeRecommendationRepository(),
    )

    result = service.build_recommendation(ObjectId(), "PETR4.SA")

    assert result["agreement"] == "concordante"
    assert result["confidence"] == "media"


def test_build_recommendation_without_conclusion_raises():
    service = RecommendationService(
        conclusion_service=_FakeConclusionService(None),
        recommendation_repository=_FakeRecommendationRepository(),
    )

    with pytest.raises(RecommendationError):
        service.build_recommendation(ObjectId(), "PETR4.SA")


@pytest.mark.parametrize(
    "fundamentalist_sub_score,expected_category",
    [(80.0, "compra_forte"), (60.0, "comprar"), (30.0, "aguardar"), (0.0, "manter"), (-50.0, "revisao_necessaria")],
)
def test_build_recommendation_category_driven_by_fundamentalist_sub_score(
    fundamentalist_sub_score, expected_category
):
    """A categoria vem do sub-score fundamentalista (que já embute
    valuation), não do `label`/overall_score das 3 análises combinadas —
    técnica e notícias continuam informativas mas não decidem a categoria.
    """
    conclusion = _conclusion(
        "neutro",
        {
            "fundamentalist": {"sub_score": fundamentalist_sub_score, "highlights": []},
            "technical": {"sub_score": -80.0, "highlights": []},
            "news_sentiment": {"sub_score": -80.0, "highlights": []},
        },
        [],
    )
    service = RecommendationService(
        conclusion_service=_FakeConclusionService(conclusion),
        recommendation_repository=_FakeRecommendationRepository(),
    )

    result = service.build_recommendation(ObjectId(), "PETR4.SA")

    assert result["category"] == expected_category


def test_build_recommendation_missing_fundamentalist_is_revisao_necessaria():
    conclusion = _conclusion(
        "neutro",
        {
            "fundamentalist": {"sub_score": None, "highlights": []},
            "technical": {"sub_score": 60.0, "highlights": []},
            "news_sentiment": {"sub_score": 60.0, "highlights": []},
        },
        ["fundamentalist"],
    )
    service = RecommendationService(
        conclusion_service=_FakeConclusionService(conclusion),
        recommendation_repository=_FakeRecommendationRepository(),
    )

    result = service.build_recommendation(ObjectId(), "PETR4.SA")

    assert result["category"] == "revisao_necessaria"
    assert result["fundamentalist_score_0_10"] is None
