from collections import defaultdict

from core.assets.asset_type import AssetType
from core.collectors.base import Collector
from core.exceptions import UnsupportedAssetTypeError


class CollectorRegistry:
    """Mapeia AssetType -> lista de Collectors capazes de atendê-lo.

    Permite múltiplos collectors por AssetType (ex: yfinance e brapi.dev
    para BR_STOCK); a estratégia de fallback/agregação entre eles é decidida
    por quem consome o registry (Etapa 2), não aqui.
    """

    def __init__(self) -> None:
        self._collectors: dict[AssetType, list[Collector]] = defaultdict(list)

    def register(self, collector: Collector) -> None:
        for asset_type in collector.supported_asset_types:
            self._collectors[asset_type].append(collector)

    def get(self, asset_type: AssetType) -> list[Collector]:
        collectors = self._collectors.get(asset_type, [])
        if not collectors:
            raise UnsupportedAssetTypeError(
                f"Nenhum Collector registrado para AssetType={asset_type!r}"
            )
        return list(collectors)
