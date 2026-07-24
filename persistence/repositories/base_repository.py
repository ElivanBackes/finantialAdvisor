from datetime import datetime, timezone
from typing import Any

from bson import ObjectId
from pymongo.collection import Collection

from config.mongo import get_database


class BaseRepository:
    """CRUD genérico sobre uma collection MongoDB.

    As coleções de análise (`fundamentalist_analysis`, `technical_analysis`,
    `news_sentiment_analysis`) são append-only por design: cada análise nova
    é um `insert`, nunca um `update` — isso preserva o histórico ao longo do
    tempo, já que dados de mercado mudam constantemente.
    """

    collection_name: str

    def __init__(self) -> None:
        self._collection: Collection = get_database()[self.collection_name]

    def insert(self, document: dict[str, Any]) -> ObjectId:
        document.setdefault("created_at", datetime.now(timezone.utc))
        result = self._collection.insert_one(document)
        return result.inserted_id

    def find_latest_by_asset(self, asset_id: ObjectId) -> dict[str, Any] | None:
        return self._collection.find_one(
            {"asset_id": asset_id}, sort=[("analyzed_at", -1)]
        )

    def find_all_by_asset(self, asset_id: ObjectId) -> list[dict[str, Any]]:
        cursor = self._collection.find({"asset_id": asset_id}).sort("analyzed_at", -1)
        return list(cursor)
