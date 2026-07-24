from dataclasses import dataclass, field
from typing import Any

from core.assets.asset_type import AssetType


@dataclass(frozen=True)
class Asset:
    """Representação genérica de um ativo/passivo/investimento.

    Não contém nada específico de uma fonte de dados ou categoria concreta
    (ex: ações B3). Particularidades de cada categoria (ex: maturity_date de
    um título de renda fixa, ou o índice de um financiamento) vivem em
    `metadata`, para não exigir mudanças no core a cada novo AssetType.
    """

    ticker: str
    asset_type: AssetType
    name: str
    currency: str = "BRL"
    metadata: dict[str, Any] = field(default_factory=dict)
