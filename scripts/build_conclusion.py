"""Gera/imprime uma conclusão (Etapa 3) a partir das análises já salvas no
Mongo, sem rodar coleta novamente.

Uso: python scripts/build_conclusion.py PETR4.SA
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from conclusions.conclusion_service import ConclusionService  # noqa: E402
from config.logging_setup import configure_logging  # noqa: E402
from core.exceptions import ConclusionError  # noqa: E402
from persistence.repositories.asset_repository import AssetRepository  # noqa: E402
from persistence.schemas.indexes import ensure_indexes  # noqa: E402


def _serialize(document: dict) -> dict:
    out = dict(document)
    out["_id"] = str(out["_id"])
    out["asset_id"] = str(out["asset_id"])
    out["analyzed_at"] = out["analyzed_at"].isoformat()
    if out.get("created_at"):
        out["created_at"] = out["created_at"].isoformat()
    out["based_on"] = {k: (str(v) if v else None) for k, v in out.get("based_on", {}).items()}
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
        conclusion = ConclusionService().build_conclusion(asset_doc["_id"], args.ticker)
    except ConclusionError as exc:
        print(f"Não foi possível gerar a conclusão: {exc}")
        return 1

    print(json.dumps(_serialize(conclusion), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
