import pytest
from bson import ObjectId

from core.exceptions import PortfolioError
from portfolio.portfolio_service import PortfolioService


class _FakePositionRepository:
    def __init__(self) -> None:
        self._by_asset: dict[ObjectId, dict] = {}

    def get_by_asset(self, asset_id):
        return self._by_asset.get(asset_id)

    def find_all(self):
        return list(self._by_asset.values())

    def upsert(self, asset_id, ticker, quantity, avg_price, target_allocation_pct):
        doc = {
            "asset_id": asset_id,
            "ticker": ticker,
            "quantity": quantity,
            "avg_price": avg_price,
            "target_allocation_pct": target_allocation_pct,
        }
        self._by_asset[asset_id] = doc
        return ObjectId()

    def delete_by_asset(self, asset_id):
        self._by_asset.pop(asset_id, None)


class _FakeFundamentalistRepository:
    def __init__(self, prices: dict | None = None) -> None:
        self._prices = prices or {}

    def find_latest_by_asset(self, asset_id):
        price = self._prices.get(asset_id)
        if price is None:
            return None
        return {"data": {"price": price}}


def _service(prices: dict | None = None) -> tuple[PortfolioService, _FakePositionRepository]:
    positions = _FakePositionRepository()
    service = PortfolioService(
        position_repository=positions,
        fundamentalist_repository=_FakeFundamentalistRepository(prices),
    )
    return service, positions


def test_upsert_position_rejects_negative_quantity():
    service, _ = _service()
    with pytest.raises(PortfolioError):
        service.upsert_position(ObjectId(), "PETR4.SA", quantity=-1, avg_price=10, target_allocation_pct=20)


def test_upsert_position_rejects_negative_avg_price():
    service, _ = _service()
    with pytest.raises(PortfolioError):
        service.upsert_position(ObjectId(), "PETR4.SA", quantity=10, avg_price=-1, target_allocation_pct=20)


@pytest.mark.parametrize("target", [-1, 101])
def test_upsert_position_rejects_target_allocation_out_of_range(target):
    service, _ = _service()
    with pytest.raises(PortfolioError):
        service.upsert_position(ObjectId(), "PETR4.SA", quantity=10, avg_price=10, target_allocation_pct=target)


def test_upsert_position_valid_persists_and_is_retrievable():
    service, _ = _service()
    asset_id = ObjectId()

    service.upsert_position(asset_id, "PETR4.SA", quantity=10, avg_price=38.5, target_allocation_pct=20)

    position = service.get_position(asset_id)
    assert position["ticker"] == "PETR4.SA"
    assert position["quantity"] == 10
    assert position["target_allocation_pct"] == 20


def test_compute_allocation_returns_none_without_position():
    service, _ = _service()
    assert service.compute_allocation(ObjectId()) is None


def test_compute_allocation_uses_avg_price_fallback_when_no_analysis():
    service, _ = _service(prices={})
    asset_a, asset_b = ObjectId(), ObjectId()
    service.upsert_position(asset_a, "AAA4.SA", quantity=10, avg_price=100, target_allocation_pct=50)
    service.upsert_position(asset_b, "BBB4.SA", quantity=10, avg_price=100, target_allocation_pct=50)

    result = service.compute_allocation(asset_a)

    assert result["current_allocation_pct"] == 50.0
    assert result["status"] == "dentro"
    assert result["portfolio_value"] == 2000.0


def test_compute_allocation_prefers_latest_fundamentalist_price():
    asset_a, asset_b = ObjectId(), ObjectId()
    service, _ = _service(prices={asset_a: 150.0})
    service.upsert_position(asset_a, "AAA4.SA", quantity=10, avg_price=100, target_allocation_pct=50)
    service.upsert_position(asset_b, "BBB4.SA", quantity=10, avg_price=100, target_allocation_pct=50)

    result = service.compute_allocation(asset_a)

    # A vale 10*150=1500 (preço de análise), B vale 10*100=1000 (fallback) -> total 2500
    assert result["position_value"] == 1500.0
    assert result["portfolio_value"] == 2500.0
    assert result["current_allocation_pct"] == 60.0
    assert result["status"] == "acima"  # 60% > meta de 50%


def test_compute_allocation_status_abaixo():
    asset_a, asset_b = ObjectId(), ObjectId()
    service, _ = _service()
    service.upsert_position(asset_a, "AAA4.SA", quantity=10, avg_price=100, target_allocation_pct=60)
    service.upsert_position(asset_b, "BBB4.SA", quantity=10, avg_price=100, target_allocation_pct=40)

    result = service.compute_allocation(asset_a)

    assert result["current_allocation_pct"] == 50.0
    assert result["status"] == "abaixo"  # 50% < meta de 60%


def test_compute_allocation_none_when_portfolio_value_is_zero():
    service, _ = _service()
    asset_id = ObjectId()
    service.upsert_position(asset_id, "AAA4.SA", quantity=0, avg_price=100, target_allocation_pct=50)

    assert service.compute_allocation(asset_id) is None


def test_list_allocations_computes_all_positions():
    asset_a, asset_b = ObjectId(), ObjectId()
    service, _ = _service()
    service.upsert_position(asset_a, "AAA4.SA", quantity=10, avg_price=100, target_allocation_pct=60)
    service.upsert_position(asset_b, "BBB4.SA", quantity=10, avg_price=100, target_allocation_pct=40)

    rows = service.list_allocations()

    by_ticker = {row["ticker"]: row for row in rows}
    assert by_ticker["AAA4.SA"]["current_allocation_pct"] == 50.0
    assert by_ticker["AAA4.SA"]["status"] == "abaixo"
    assert by_ticker["BBB4.SA"]["status"] == "acima"


def test_remove_position():
    service, _ = _service()
    asset_id = ObjectId()
    service.upsert_position(asset_id, "AAA4.SA", quantity=10, avg_price=100, target_allocation_pct=50)

    service.remove_position(asset_id)

    assert service.get_position(asset_id) is None
