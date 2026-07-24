"""Verifica se o ambiente está pronto: conexão Mongo + índices criados.

Uso: python scripts/check_setup.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config.logging_setup import configure_logging  # noqa: E402
from config.mongo import get_database  # noqa: E402
from persistence.schemas.indexes import ensure_indexes  # noqa: E402


def main() -> int:
    configure_logging()
    try:
        db = get_database()
        db.client.admin.command("ping")
    except Exception as exc:  # noqa: BLE001
        print(f"[FALHA] Não foi possível conectar ao MongoDB: {exc}")
        return 1

    print(f"[OK] Conectado ao MongoDB (banco: {db.name})")

    created = ensure_indexes(db)
    print(f"[OK] {len(created)} índices confirmados/criados: {created}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
