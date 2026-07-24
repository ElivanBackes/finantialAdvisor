"""Funções puras: derivam ação, direção, concordância e confiança a partir
do breakdown/label de uma Conclusão já calculada. Sem I/O, sem Mongo — a
orquestração/persistência fica em recommendations/recommendation_service.py.
"""

from conclusions.scoring import overall_label

_ACTION_BY_LABEL = {"favoravel": "comprar", "neutro": "manter", "desfavoravel": "evitar"}
_DIRECTION_MAP = {"favoravel": "positivo", "desfavoravel": "negativo", "neutro": "neutro"}
_CONFIDENCE_BASE_BY_AVAILABLE = {3: "alta", 2: "media", 1: "baixa", 0: "baixa"}
_DOWNGRADE = {"alta": "media", "media": "baixa", "baixa": "baixa"}


def action_from_label(label: str) -> str:
    return _ACTION_BY_LABEL[label]


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
