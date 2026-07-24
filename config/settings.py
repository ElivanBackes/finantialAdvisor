import os
from dataclasses import dataclass
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    mongo_uri: str
    mongo_db_name: str
    brapi_api_token: str
    newsapi_key: str
    log_level: str


@lru_cache
def get_settings() -> Settings:
    """Carrega as configurações do ambiente (.env) uma única vez por processo."""
    return Settings(
        mongo_uri=os.getenv("MONGO_URI", "mongodb://localhost:27017"),
        mongo_db_name=os.getenv("MONGO_DB_NAME", "financial_advisor"),
        brapi_api_token=os.getenv("BRAPI_API_TOKEN", ""),
        newsapi_key=os.getenv("NEWSAPI_KEY", ""),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
    )
