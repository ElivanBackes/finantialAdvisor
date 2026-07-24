from datetime import datetime, timezone
from typing import Any

from bson import ObjectId

from config.mongo import get_database
from core.assets.asset import Asset


class AssetRepository:
    """Catálogo de identidade dos ativos já pesquisados (coleção `assets`).

    Diferente das coleções de análise, esta NÃO é append-only: um mesmo
    ticker tem um único documento, atualizado quando seus metadados mudam.
    """

    collection_name = "assets"

    def __init__(self) -> None:
        self._collection = get_database()[self.collection_name]

    def get_by_ticker(self, ticker: str) -> dict[str, Any] | None:
        return self._collection.find_one({"ticker": ticker})

    def upsert(self, asset: Asset) -> ObjectId:
        now = datetime.now(timezone.utc)
        result = self._collection.find_one_and_update(
            {"ticker": asset.ticker},
            {
                "$set": {
                    "asset_type": asset.asset_type.value,
                    "name": asset.name,
                    "currency": asset.currency,
                    "metadata": asset.metadata,
                    "updated_at": now,
                },
                "$setOnInsert": {"created_at": now},
            },
            upsert=True,
            return_document=True,
        )
        return result["_id"]
