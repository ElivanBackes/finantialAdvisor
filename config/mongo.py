from functools import lru_cache

from pymongo import MongoClient
from pymongo.database import Database

from config.settings import get_settings


@lru_cache
def get_mongo_client() -> MongoClient:
    """Cliente Mongo cacheado por processo — evita abrir conexão nova a cada chamada."""
    settings = get_settings()
    return MongoClient(settings.mongo_uri)


def get_database() -> Database:
    settings = get_settings()
    return get_mongo_client()[settings.mongo_db_name]
