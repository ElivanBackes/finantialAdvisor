from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Protocol

from core.assets.asset import Asset
from core.assets.asset_type import AssetType


@dataclass(frozen=True)
class RawData:
    """Payload bruto retornado por um Collector, antes de qualquer análise."""

    source: str
    payload: dict[str, Any]
    fetched_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class Collector(Protocol):
    """Contrato que toda fonte de dados concreta deve implementar.

    Implementações reais chegam na Etapa 2 (ex: collectors/br_stocks/).
    """

    source_name: str
    supported_asset_types: set[AssetType]

    def fetch(self, asset: Asset) -> RawData:
        """Busca dados brutos de `asset` na fonte representada por este Collector."""
        ...
