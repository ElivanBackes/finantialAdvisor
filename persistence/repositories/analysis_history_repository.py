from datetime import datetime, timezone
from typing import Any

from bson import ObjectId

from config.mongo import get_database


class AnalysisHistoryRepository:
    """Resumo consultável de todas as análises já realizadas (coleção
    `analysis_history`), usado pela tela "Histórico de Análises".

    Como `AssetRepository`/`PositionRepository`, NÃO é append-only: cada
    ativo tem um único registro, atualizado (upsert) a cada nova
    recomendação gerada. O histórico completo e imutável de cada análise
    continua em `recommendations` (append-only) — esta coleção é apenas uma
    projeção "estado mais recente por ativo", otimizada para listar,
    ordenar e filtrar sem precisar agregar as outras coleções toda vez.
    """

    collection_name = "analysis_history"

    def __init__(self) -> None:
        self._collection = get_database()[self.collection_name]

    def upsert(self, asset_id: ObjectId, document: dict[str, Any]) -> ObjectId:
        now = datetime.now(timezone.utc)
        result = self._collection.find_one_and_update(
            {"asset_id": asset_id},
            {"$set": {**document, "updated_at": now}, "$setOnInsert": {"created_at": now}},
            upsert=True,
            return_document=True,
        )
        return result["_id"]

    def find_all(self) -> list[dict[str, Any]]:
        return list(self._collection.find({}))
