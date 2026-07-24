from typing import Any

from persistence.repositories.base_repository import BaseRepository


class RawDataRepository(BaseRepository):
    """Coleção `raw_data`: payload bruto retornado por cada Collector.fetch().

    Reaproveita `insert`/`find_all_by_asset` de BaseRepository (documentos
    inseridos aqui incluem `asset_id`). O índice principal da coleção é
    `{ticker:1, fetched_at:-1}` (persistence/schemas/indexes.py), por isso a
    consulta idiomática é por ticker+source, não por asset_id.
    """

    collection_name = "raw_data"

    def find_recent_by_ticker_and_source(
        self, ticker: str, source: str, limit: int = 1
    ) -> list[dict[str, Any]]:
        cursor = (
            self._collection.find({"ticker": ticker, "source": source})
            .sort("fetched_at", -1)
            .limit(limit)
        )
        return list(cursor)
