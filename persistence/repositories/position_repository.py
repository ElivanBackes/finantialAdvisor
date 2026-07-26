from datetime import datetime, timezone
from typing import Any

from bson import ObjectId

from config.mongo import get_database


class PositionRepository:
    """Posições da carteira do usuário (coleção `positions`).

    Como `AssetRepository`, NÃO é append-only: cada ativo tem uma única
    posição, atualizada quando quantidade/preço médio/meta de alocação
    mudam — ao contrário das coleções de análise, que preservam histórico.
    """

    collection_name = "positions"

    def __init__(self) -> None:
        self._collection = get_database()[self.collection_name]

    def get_by_asset(self, asset_id: ObjectId) -> dict[str, Any] | None:
        return self._collection.find_one({"asset_id": asset_id})

    def find_all(self) -> list[dict[str, Any]]:
        return list(self._collection.find({}))

    def upsert(
        self,
        asset_id: ObjectId,
        ticker: str,
        quantity: float,
        avg_price: float,
        target_allocation_pct: float,
    ) -> ObjectId:
        now = datetime.now(timezone.utc)
        result = self._collection.find_one_and_update(
            {"asset_id": asset_id},
            {
                "$set": {
                    "ticker": ticker,
                    "quantity": quantity,
                    "avg_price": avg_price,
                    "target_allocation_pct": target_allocation_pct,
                    "updated_at": now,
                },
                "$setOnInsert": {"created_at": now},
            },
            upsert=True,
            return_document=True,
        )
        return result["_id"]

    def delete_by_asset(self, asset_id: ObjectId) -> None:
        self._collection.delete_one({"asset_id": asset_id})
