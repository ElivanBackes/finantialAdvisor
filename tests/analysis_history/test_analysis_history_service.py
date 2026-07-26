from datetime import datetime, timezone

import pytest
from bson import ObjectId

from analysis_history.analysis_history_service import AnalysisHistoryService


class _FakeAnalysisHistoryRepository:
    def __init__(self) -> None:
        self.upserted: list[tuple] = []
        self._rows: list[dict] = []

    def upsert(self, asset_id, document):
        self.upserted.append((asset_id, document))
        self._rows.append({"asset_id": asset_id, **document})
        return ObjectId()

    def find_all(self):
        return self._rows


def _recommendation(**overrides):
    base = {
        "fundamentalist_score_0_10": 8.5,
        "category": "comprar",
        "justification": ["Comprar: ativo atrativo."],
        "analyzed_at": datetime(2026, 7, 26, tzinfo=timezone.utc),
    }
    base.update(overrides)
    return base


def test_record_computes_ceiling_price_and_upside():
    repo = _FakeAnalysisHistoryRepository()
    service = AnalysisHistoryService(repository=repo)
    asset_id = ObjectId()
    fundamentalist_data = {"price": 38.5, "eps": 8.28, "pvp": 1.2246315, "dividend_yield": 9.07}

    service.record(asset_id, "PETR4.SA", "Petrobras", _recommendation(), fundamentalist_data)

    assert len(repo.upserted) == 1
    stored_asset_id, document = repo.upserted[0]
    assert stored_asset_id == asset_id
    assert document["ticker"] == "PETR4.SA"
    assert document["company_name"] == "Petrobras"
    assert document["score_final"] == 8.5
    assert document["current_price"] == 38.5
    assert document["dividend_yield_expected"] == 9.07
    assert document["ceiling_price"] == 58.19916666666667
    # upside = (58.199... - 38.5) / 38.5 * 100 ~= 51.2%
    assert document["upside_pct"] == 51.17
    assert document["recommendation_category"] == "comprar"
    assert document["justification"] == ["Comprar: ativo atrativo."]


def test_record_normalizes_fractional_dividend_yield():
    """yfinance às vezes retorna dividend_yield como fração (0.0923), às
    vezes já em percentual (9.23) — o histórico deve sempre armazenar em
    percentual, senão os filtros de faixa de DY na tela ficam incoerentes.
    """
    repo = _FakeAnalysisHistoryRepository()
    service = AnalysisHistoryService(repository=repo)

    service.record(
        ObjectId(), "PETR4.SA", "Petrobras", _recommendation(), {"price": 42.21, "dividend_yield": 0.0923}
    )

    _, document = repo.upserted[0]
    assert document["dividend_yield_expected"] == pytest.approx(9.23)


def test_record_handles_missing_ceiling_price():
    repo = _FakeAnalysisHistoryRepository()
    service = AnalysisHistoryService(repository=repo)

    service.record(ObjectId(), "XYZ4.SA", "Empresa XYZ", _recommendation(), {"price": 10.0})

    _, document = repo.upserted[0]
    assert document["ceiling_price"] is None
    assert document["upside_pct"] is None


def test_record_handles_missing_price():
    repo = _FakeAnalysisHistoryRepository()
    service = AnalysisHistoryService(repository=repo)

    service.record(ObjectId(), "XYZ4.SA", "Empresa XYZ", _recommendation(), {})

    _, document = repo.upserted[0]
    assert document["current_price"] is None
    assert document["ceiling_price"] is None
    assert document["upside_pct"] is None


def test_list_all_delegates_to_repository():
    repo = _FakeAnalysisHistoryRepository()
    service = AnalysisHistoryService(repository=repo)
    service.record(ObjectId(), "AAA4.SA", "Empresa AAA", _recommendation(), {"price": 10.0})

    rows = service.list_all()

    assert len(rows) == 1
    assert rows[0]["ticker"] == "AAA4.SA"
