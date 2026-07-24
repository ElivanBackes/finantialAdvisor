from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Protocol

from core.assets.asset import Asset
from core.collectors.base import RawData


class AnalysisType(str, Enum):
    """As 3 análises independentes que o sistema produz por ativo."""

    FUNDAMENTALIST = "fundamentalist"
    TECHNICAL = "technical"
    NEWS_SENTIMENT = "news_sentiment"


@dataclass(frozen=True)
class AnalysisResult:
    """Envelope uniforme de uma análise, independente do seu tipo.

    `data` contém o payload específico de cada análise (ex: indicadores
    fundamentalistas vs. indicadores técnicos vs. score de sentimento) — é o
    único campo que varia por AnalysisType. O envelope uniforme é o que
    permite a Etapa 3 (Conclusão) buscar as 3 análises mais recentes de um
    ativo de forma genérica, sem `if/else` por tipo.
    """

    asset_ticker: str
    analysis_type: AnalysisType
    data: dict[str, Any]
    sources: list[str] = field(default_factory=list)
    analyzed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class Analyzer(Protocol):
    """Contrato que toda análise concreta deve implementar.

    Implementações reais chegam na Etapa 2/3 (ex: analyzers/fundamentalist/).
    """

    analysis_type: AnalysisType

    def analyze(self, asset: Asset, raw_data: list[RawData]) -> AnalysisResult:
        """Transforma dados brutos coletados em um AnalysisResult."""
        ...
