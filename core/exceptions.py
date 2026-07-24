"""Exceções do domínio, compartilhadas por collectors, analyzers e services."""


class FinancialAdvisorError(Exception):
    """Erro base do domínio."""


class UnsupportedAssetTypeError(FinancialAdvisorError):
    """Levantada quando não há Collector/Analyzer registrado para um AssetType."""


class CollectorError(FinancialAdvisorError):
    """Levantada quando um Collector falha ao buscar dados de uma fonte externa."""


class AnalyzerError(FinancialAdvisorError):
    """Levantada quando um Analyzer falha ao processar dados brutos."""


class ConclusionError(FinancialAdvisorError):
    """Levantada quando não há análises suficientes para sintetizar uma conclusão."""


class RecommendationError(FinancialAdvisorError):
    """Levantada quando não há conclusão salva para gerar uma recomendação."""
