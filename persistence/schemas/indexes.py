from pymongo.database import Database

from config.mongo import get_database

_ANALYSIS_COLLECTIONS = [
    "fundamentalist_analysis",
    "technical_analysis",
    "news_sentiment_analysis",
    "conclusions",
    "recommendations",
]


def ensure_indexes(db: Database | None = None) -> list[str]:
    """Cria (de forma idempotente) os índices necessários. Retorna os nomes criados/confirmados."""
    database = db if db is not None else get_database()
    created: list[str] = []

    created.append(database["assets"].create_index("ticker", unique=True))

    for collection_name in _ANALYSIS_COLLECTIONS:
        created.append(
            database[collection_name].create_index(
                [("asset_id", 1), ("analyzed_at", -1)]
            )
        )

    created.append(database["raw_data"].create_index([("ticker", 1), ("fetched_at", -1)]))

    return created
