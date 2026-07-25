"""Funções puras: derivam categoria de recomendação, direção, concordância e
confiança a partir do breakdown de uma Conclusão já calculada. Sem I/O, sem
Mongo — a orquestração/persistência fica em
recommendations/recommendation_service.py.
"""

from conclusions.scoring import overall_label

_DIRECTION_MAP = {"favoravel": "positivo", "desfavoravel": "negativo", "neutro": "neutro"}
_CONFIDENCE_BASE_BY_AVAILABLE = {3: "alta", 2: "media", 1: "baixa", 0: "baixa"}
_DOWNGRADE = {"alta": "media", "media": "baixa", "baixa": "baixa"}

# Faixas de recomendação por score 0-10, derivado do sub-score fundamentalista
# (que já embute valuation/preço-teto) — não do overall_score das 3 análises,
# já que o modelo de valuation da especificação é orientado a fundamentos, não
# a sinais técnicos/sentimento de curto prazo.
_RECOMMENDATION_BANDS = [
    (9.0, "compra_forte"),
    (8.0, "comprar"),
    (6.5, "aguardar"),
    (5.0, "manter"),
]


def to_zero_ten_scale(score: float) -> float:
    """Converte um sub-score -100..100 para a escala 0-10 usada nas faixas
    de recomendação da especificação.
    """
    return round((score + 100) / 20, 2)


def apply_allocation_adjustment(category: str, allocation_status: str | None) -> tuple[str, bool]:
    """Estratégia de alocação de carteira (Etapa 4): só rebaixa uma
    recomendação já atrativa quando o ativo está acima da alocação-alvo,
    para evitar concentrar novos aportes em ativos sobreponderados. Nunca
    promove um ativo pouco atrativo por estar abaixo da meta — fundamentos
    sempre têm prioridade sobre alocação (princípio da especificação:
    "empresas excelentes podem não representar boas compras no momento",
    o inverso também vale: alocação não torna uma empresa fraca atrativa).

    Retorna (categoria_final, foi_ajustada).
    """
    if allocation_status == "acima" and category in ("compra_forte", "comprar"):
        return "aguardar", True
    return category, False


def classify_recommendation(fundamentalist_sub_score: float | None) -> tuple[str, float | None]:
    """Classifica em uma das 5 categorias da especificação a partir do
    sub-score fundamentalista (que já inclui o critério de valuation).

    Ausência do sub-score (nenhum dado fundamentalista disponível) é tratada
    como inconsistência de dados -> "revisao_necessaria", junto com scores
    muito baixos (< 5.0 na escala 0-10).
    """
    if fundamentalist_sub_score is None:
        return "revisao_necessaria", None

    score_0_10 = to_zero_ten_scale(fundamentalist_sub_score)
    for threshold, category in _RECOMMENDATION_BANDS:
        if score_0_10 >= threshold:
            return category, score_0_10
    return "revisao_necessaria", score_0_10


def classify_direction(sub_score: float) -> str:
    """Reaproveita os mesmos thresholds ±20 de conclusions.scoring.overall_label
    — sub-scores e overall_score estão na mesma escala -100..100 e são
    construídos da mesma forma (média de poucos indicadores discretos).
    """
    return _DIRECTION_MAP[overall_label(sub_score)]


def classify_agreement(breakdown: dict[str, dict]) -> str:
    directions = [
        classify_direction(entry["sub_score"])
        for entry in breakdown.values()
        if entry.get("sub_score") is not None
    ]
    non_neutral = {d for d in directions if d != "neutro"}
    if not non_neutral:
        return "neutra"
    if len(non_neutral) == 1:
        return "concordante"
    return "mista"


def classify_confidence(available_count: int, agreement: str) -> str:
    base = _CONFIDENCE_BASE_BY_AVAILABLE.get(available_count, "baixa")
    return base if agreement == "concordante" else _DOWNGRADE[base]
