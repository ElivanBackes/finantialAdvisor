import pytest
from bson import ObjectId

from conclusions.conclusion_service import ConclusionService
from core.analyzers.base import AnalysisType
from core.exceptions import ConclusionError


class _FakeAssetService:
    def __init__(
        self, analyses: dict[AnalysisType, dict | None], history: list[dict] | None = None
    ) -> None:
        self._analyses = analyses
        self._history = history or []

    def get_latest_analyses(self, asset_id):
        return self._analyses

    def get_analysis_history(self, asset_id, analysis_type):
        return self._history


class _FakeConclusionRepository:
    def __init__(self) -> None:
        self.inserted: list[dict] = []

    def insert(self, document: dict):
        document["_id"] = ObjectId()
        self.inserted.append(document)
        return document["_id"]

    def find_latest_by_asset(self, asset_id):
        return self.inserted[-1] if self.inserted else None


_FUNDAMENTALIST_DOC = {
    "_id": ObjectId(),
    "data": {
        "pl": 5.202952,
        "pvp": 1.2246315,
        "dividend_yield": 9.07,
        "roe": 0.25601,
        "debt_to_equity": 83.269,
    },
}
_TECHNICAL_DOC = {
    "_id": ObjectId(),
    "data": {
        "last_price": 42.3,
        "sma_20": 39.902,
        "sma_50": 40.7135,
        "sma_200": 37.1773,
        "rsi_14": 77.45,
        "macd": 0.5881,
        "macd_signal": 0.1179,
        "macd_histogram": 0.4702,
        "trend": "alta",
        "history_points": 251,
    },
}
_NEWS_DOC = {
    "_id": ObjectId(),
    "data": {
        "score": 0.42,
        "positive_count": 3,
        "negative_count": 1,
        "neutral_count": 2,
        "articles_analyzed": 6,
    },
}


def test_build_conclusion_all_three_present():
    analyses = {
        AnalysisType.FUNDAMENTALIST: _FUNDAMENTALIST_DOC,
        AnalysisType.TECHNICAL: _TECHNICAL_DOC,
        AnalysisType.NEWS_SENTIMENT: _NEWS_DOC,
    }
    repo = _FakeConclusionRepository()
    service = ConclusionService(
        asset_service=_FakeAssetService(analyses), conclusion_repository=repo
    )

    result = service.build_conclusion(ObjectId(), "PETR4.SA")

    assert result["missing_analyses"] == []
    assert result["overall_score"] == 51.05
    assert result["label"] == "favoravel"
    assert result["based_on"]["fundamentalist_analysis_id"] == _FUNDAMENTALIST_DOC["_id"]
    assert result["based_on"]["technical_analysis_id"] == _TECHNICAL_DOC["_id"]
    assert result["based_on"]["news_sentiment_analysis_id"] == _NEWS_DOC["_id"]
    assert len(repo.inserted) == 1


def test_build_conclusion_missing_one_redistributes_weight():
    analyses = {
        AnalysisType.FUNDAMENTALIST: _FUNDAMENTALIST_DOC,
        AnalysisType.TECHNICAL: None,
        AnalysisType.NEWS_SENTIMENT: _NEWS_DOC,
    }
    repo = _FakeConclusionRepository()
    service = ConclusionService(
        asset_service=_FakeAssetService(analyses), conclusion_repository=repo
    )

    result = service.build_conclusion(ObjectId(), "PETR4.SA")

    assert result["missing_analyses"] == ["technical"]
    assert result["based_on"]["technical_analysis_id"] is None
    assert result["overall_score"] == round((84.47 + 42.0) / 2, 2)


def test_build_conclusion_injects_historical_multiple_averages():
    """Com >=3 análises fundamentalistas passadas (excluindo a atual), o
    sub-score fundamentalista deve refletir o critério de histórico de
    múltiplos — comprovado indiretamente comparando com/sem histórico.
    """
    current_doc = {"_id": ObjectId(), "data": {"pl": 12.0}}
    history_without_current = [
        {"_id": ObjectId(), "data": {"pl": 15.0}},
        {"_id": ObjectId(), "data": {"pl": 15.0}},
        {"_id": ObjectId(), "data": {"pl": 15.0}},
    ]
    analyses = {
        AnalysisType.FUNDAMENTALIST: current_doc,
        AnalysisType.TECHNICAL: None,
        AnalysisType.NEWS_SENTIMENT: None,
    }

    service_with_history = ConclusionService(
        asset_service=_FakeAssetService(
            analyses, history=[current_doc, *history_without_current]
        ),
        conclusion_repository=_FakeConclusionRepository(),
    )
    service_without_history = ConclusionService(
        asset_service=_FakeAssetService(analyses, history=[current_doc]),
        conclusion_repository=_FakeConclusionRepository(),
    )

    with_history = service_with_history.build_conclusion(ObjectId(), "AAA4.SA")
    without_history = service_without_history.build_conclusion(ObjectId(), "AAA4.SA")

    # P/L atual (12) abaixo da própria média histórica (15) -> critério de
    # histórico de múltiplos entra positivo, elevando o sub-score.
    assert with_history["breakdown"]["fundamentalist"]["sub_score"] > (
        without_history["breakdown"]["fundamentalist"]["sub_score"]
    )
    assert any(
        "própria média histórica" in h
        for h in with_history["breakdown"]["fundamentalist"]["highlights"]
    )


def test_build_conclusion_all_missing_raises():
    analyses = {
        AnalysisType.FUNDAMENTALIST: None,
        AnalysisType.TECHNICAL: None,
        AnalysisType.NEWS_SENTIMENT: None,
    }
    service = ConclusionService(
        asset_service=_FakeAssetService(analyses),
        conclusion_repository=_FakeConclusionRepository(),
    )

    with pytest.raises(ConclusionError):
        service.build_conclusion(ObjectId(), "PETR4.SA")


@pytest.mark.parametrize(
    "fixed_score,expected_label",
    [(60.0, "favoravel"), (0.0, "neutro"), (-60.0, "desfavoravel")],
)
def test_build_conclusion_label_thresholds(fixed_score, expected_label):
    dummy_doc = {"_id": ObjectId(), "data": {}}
    analyses = {
        AnalysisType.FUNDAMENTALIST: dummy_doc,
        AnalysisType.TECHNICAL: dummy_doc,
        AnalysisType.NEWS_SENTIMENT: dummy_doc,
    }
    fake_scorer = lambda data: (fixed_score, ["x"])  # noqa: E731
    scorers = {
        AnalysisType.FUNDAMENTALIST: fake_scorer,
        AnalysisType.TECHNICAL: fake_scorer,
        AnalysisType.NEWS_SENTIMENT: fake_scorer,
    }
    service = ConclusionService(
        asset_service=_FakeAssetService(analyses),
        conclusion_repository=_FakeConclusionRepository(),
        scorers=scorers,
    )

    result = service.build_conclusion(ObjectId(), "PETR4.SA")

    assert result["overall_score"] == fixed_score
    assert result["label"] == expected_label
