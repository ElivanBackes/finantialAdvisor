"""Contrato de análise, tipos de análise e registro de analyzers por tipo."""

from core.analyzers.base import Analyzer, AnalysisResult, AnalysisType
from core.analyzers.registry import AnalyzerRegistry

__all__ = ["Analyzer", "AnalysisResult", "AnalysisType", "AnalyzerRegistry"]
