from core.analyzers.base import Analyzer, AnalysisType
from core.exceptions import UnsupportedAssetTypeError


class AnalyzerRegistry:
    """Mapeia AnalysisType -> Analyzer responsável por produzi-lo."""

    def __init__(self) -> None:
        self._analyzers: dict[AnalysisType, Analyzer] = {}

    def register(self, analyzer: Analyzer) -> None:
        self._analyzers[analyzer.analysis_type] = analyzer

    def get(self, analysis_type: AnalysisType) -> Analyzer:
        analyzer = self._analyzers.get(analysis_type)
        if analyzer is None:
            raise UnsupportedAssetTypeError(
                f"Nenhum Analyzer registrado para AnalysisType={analysis_type!r}"
            )
        return analyzer
