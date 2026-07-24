"""Roda coleta + as 3 análises contra as APIs reais (fora do Streamlit).

Uso: python scripts/collect_and_analyze.py PETR4.SA [--name "Petrobras"]
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config.logging_setup import configure_logging  # noqa: E402
from core.analyzers.base import AnalysisResult, AnalysisType  # noqa: E402
from core.assets.asset_type import AssetType  # noqa: E402
from persistence.schemas.indexes import ensure_indexes  # noqa: E402
from services.asset_service import AssetService  # noqa: E402


def _serialize(result: AnalysisResult | None) -> dict | None:
    if result is None:
        return None
    return {
        "analysis_type": result.analysis_type.value,
        "data": result.data,
        "sources": result.sources,
        "analyzed_at": result.analyzed_at.isoformat(),
    }


def main() -> int:
    configure_logging()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ticker", help="Ticker B3 com sufixo .SA, ex: PETR4.SA")
    parser.add_argument("--name", default="", help="Nome do ativo (opcional)")
    args = parser.parse_args()

    ensure_indexes()
    results = AssetService().collect_and_analyze(
        ticker=args.ticker, asset_type=AssetType.BR_STOCK, name=args.name
    )

    exit_code = 0
    for analysis_type in AnalysisType:
        result = results.get(analysis_type)
        print(f"\n=== {analysis_type.value} ===")
        if result is None:
            print("FALHOU (ver logs acima / conferir .env)")
            exit_code = 1
        else:
            print(json.dumps(_serialize(result), indent=2, ensure_ascii=False))

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
