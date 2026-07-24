from typing import Any

from persistence.repositories.base_repository import BaseRepository


class LogRepository(BaseRepository):
    """Coleção `logs`: registros de logging.LogRecord persistidos pelo
    MongoLogHandler (config/logging_setup.py). Append-only, com TTL de 30
    dias (persistence/schemas/indexes.py) — não precisa de limpeza manual.
    """

    collection_name = "logs"

    def find_recent(
        self, limit: int = 200, level: str | None = None, ticker: str | None = None
    ) -> list[dict[str, Any]]:
        query: dict[str, Any] = {}
        if level:
            query["level"] = level
        if ticker:
            query["ticker"] = ticker
        cursor = self._collection.find(query).sort("timestamp", -1).limit(limit)
        return list(cursor)
