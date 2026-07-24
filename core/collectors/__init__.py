"""Contrato de coleta de dados brutos e registro de collectors por AssetType."""

from core.collectors.base import Collector, RawData
from core.collectors.registry import CollectorRegistry

__all__ = ["Collector", "RawData", "CollectorRegistry"]
