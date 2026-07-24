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

    assert result["action"] == "comprar"
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
    "label,expected_action",
    [("favoravel", "comprar"), ("neutro", "manter"), ("desfavoravel", "evitar")],
)
def test_build_recommendation_label_to_action_mapping(label, expected_action):
    conclusion = _conclusion(
        label,
        {
            "fundamentalist": {"sub_score": 0.0, "highlights": []},
            "technical": {"sub_score": 0.0, "highlights": []},
            "news_sentiment": {"sub_score": 0.0, "highlights": []},
        },
        [],
    )
    service = RecommendationService(
        conclusion_service=_FakeConclusionService(conclusion),
        recommendation_repository=_FakeRecommendationRepository(),
    )

    result = service.build_recommendation(ObjectId(), "PETR4.SA")

    assert result["action"] == expected_action
