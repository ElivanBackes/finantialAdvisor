import logging

from bson import ObjectId

from core.exceptions import PortfolioError
from persistence.repositories.fundamentalist_repository import FundamentalistRepository
from persistence.repositories.position_repository import PositionRepository

logger = logging.getLogger(__name__)


class PortfolioService:
    """Gerencia as posições da carteira do usuário e calcula a alocação
    atual (valor da posição / valor total da carteira) frente à meta.

    Registrar uma posição é opcional: ativos sem posição cadastrada
    simplesmente não recebem o ajuste de alocação na recomendação (Etapa 4).
    """

    def __init__(
        self,
        position_repository: PositionRepository | None = None,
        fundamentalist_repository: FundamentalistRepository | None = None,
    ) -> None:
        self._position_repository = position_repository or PositionRepository()
        self._fundamentalist_repository = fundamentalist_repository or FundamentalistRepository()

    def get_position(self, asset_id: ObjectId) -> dict | None:
        return self._position_repository.get_by_asset(asset_id)

    def upsert_position(
        self,
        asset_id: ObjectId,
        ticker: str,
        quantity: float,
        avg_price: float,
        target_allocation_pct: float,
    ) -> ObjectId:
        if quantity < 0:
            raise PortfolioError("Quantidade não pode ser negativa.")
        if avg_price < 0:
            raise PortfolioError("Preço médio não pode ser negativo.")
        if not 0 <= target_allocation_pct <= 100:
            raise PortfolioError("Alocação-alvo deve estar entre 0 e 100%.")

        position_id = self._position_repository.upsert(
            asset_id=asset_id,
            ticker=ticker,
            quantity=quantity,
            avg_price=avg_price,
            target_allocation_pct=target_allocation_pct,
        )
        logger.info("Posição registrada para %s", ticker, extra={"ticker": ticker})
        return position_id

    def remove_position(self, asset_id: ObjectId) -> None:
        self._position_repository.delete_by_asset(asset_id)

    def _current_price(self, asset_id: ObjectId, avg_price_fallback: float) -> float:
        """Usa o preço mais recente da análise fundamentalista; cai para o
        preço médio de compra se o ativo ainda não foi coletado/analisado.
        """
        doc = self._fundamentalist_repository.find_latest_by_asset(asset_id)
        price = (doc or {}).get("data", {}).get("price")
        return price if price is not None else avg_price_fallback

    def _values_by_asset(self) -> tuple[dict[ObjectId, float], float]:
        """Valor atual (quantidade x preço) de cada posição e o total da
        carteira — base compartilhada por `compute_allocation` e
        `list_allocations`.
        """
        values: dict[ObjectId, float] = {}
        total_value = 0.0
        for entry in self._position_repository.find_all():
            price = self._current_price(entry["asset_id"], entry["avg_price"])
            value = entry["quantity"] * price
            values[entry["asset_id"]] = value
            total_value += value
        return values, total_value

    @staticmethod
    def _status(current_pct: float, target_pct: float) -> str:
        if current_pct > target_pct:
            return "acima"
        if current_pct < target_pct:
            return "abaixo"
        return "dentro"

    def compute_allocation(self, asset_id: ObjectId) -> dict | None:
        """Retorna a alocação atual do ativo frente à meta, ou `None` se o
        ativo não tem posição registrada (feature opt-in) ou se a carteira
        não tem valor total positivo (ex: todas as posições zeradas).
        """
        position = self.get_position(asset_id)
        if position is None:
            return None

        values, total_value = self._values_by_asset()
        if total_value <= 0:
            return None

        this_value = values[asset_id]
        current_pct = this_value / total_value * 100
        target_pct = position["target_allocation_pct"]

        return {
            "current_allocation_pct": round(current_pct, 2),
            "target_allocation_pct": target_pct,
            "status": self._status(current_pct, target_pct),
            "position_value": round(this_value, 2),
            "portfolio_value": round(total_value, 2),
        }

    def list_allocations(self) -> list[dict]:
        """Lista todas as posições com a alocação atual calculada, para a
        visão geral da carteira no dashboard.
        """
        values, total_value = self._values_by_asset()
        result = []
        for entry in self._position_repository.find_all():
            value = values[entry["asset_id"]]
            current_pct = (value / total_value * 100) if total_value > 0 else 0.0
            target_pct = entry["target_allocation_pct"]
            result.append(
                {
                    "asset_id": entry["asset_id"],
                    "ticker": entry["ticker"],
                    "quantity": entry["quantity"],
                    "avg_price": entry["avg_price"],
                    "target_allocation_pct": target_pct,
                    "value": round(value, 2),
                    "current_allocation_pct": round(current_pct, 2),
                    "status": self._status(current_pct, target_pct) if total_value > 0 else "indefinido",
                }
            )
        return result
