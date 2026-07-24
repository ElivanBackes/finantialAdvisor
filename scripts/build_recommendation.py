"""Gera/imprime uma recomendação (Etapa 4) a partir da última Conclusão já
salva no Mongo, sem regerar a Conclusão.

Uso: python scripts/build_recommendation.py PETR4.SA
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config.logging_setup import configure_logging  # noqa: E402
from core.exceptions import RecommendationError  # noqa: E402
from persistence.repositories.asset_repository import AssetRepository  # noqa: E402
from persistence.schemas.indexes import ensure_indexes  # noqa: E402
from recommendations.recommendation_service import RecommendationService  # noqa: E402


def _serialize(document: dict) -> dict:
    out = dict(document)
    out["_id"] = str(out["_id"])
    out["asset_id"] = str(out["asset_id"])
    out["conclusion_id"] = str(out["conclusion_id"])
    out["analyzed_at"] = out["analyzed_at"].isoformat()
    if out.get("created_at"):
        out["created_at"] = out["created_at"].isoformat()
    return out


def main() -> int:
    configure_logging()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ticker", help="Ticker B3 com sufixo .SA, ex: PETR4.SA")
    args = parser.parse_args()

    ensure_indexes()
    asset_doc = AssetRepository().get_by_ticker(args.ticker)
    if asset_doc is None:
        print(f"Ativo '{args.ticker}' não encontrado. Rode 'Buscar / Cadastrar' primeiro.")
        return 1

    try:
        recommendation = RecommendationService().build_recommendation(
            asset_doc["_id"], args.ticker
        )
    except RecommendationError as exc:
        print(f"Não foi possível gerar a recomendação: {exc}")
        return 1

    print(json.dumps(_serialize(recommendation), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
