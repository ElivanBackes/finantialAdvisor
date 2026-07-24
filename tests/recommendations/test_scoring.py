import pytest

from recommendations.scoring import (
    action_from_label,
    classify_agreement,
    classify_confidence,
    classify_direction,
)


@pytest.mark.parametrize(
    "sub_score,expected",
    [(60.0, "positivo"), (0.0, "neutro"), (-60.0, "negativo"), (20, "positivo"), (-20, "negativo")],
)
def test_classify_direction(sub_score, expected):
    assert classify_direction(sub_score) == expected


@pytest.mark.parametrize(
    "label,expected",
    [("favoravel", "comprar"), ("neutro", "manter"), ("desfavoravel", "evitar")],
)
def test_action_from_label(label, expected):
    assert action_from_label(label) == expected


def test_classify_agreement_all_positive_is_concordante():
    breakdown = {
        "fundamentalist": {"sub_score": 60.0},
        "technical": {"sub_score": 40.0},
        "news_sentiment": {"sub_score": 25.0},
    }
    assert classify_agreement(breakdown) == "concordante"


def test_classify_agreement_mixed_signs_is_mista():
    breakdown = {
        "fundamentalist": {"sub_score": 60.0},
        "technical": {"sub_score": -40.0},
        "news_sentiment": {"sub_score": None},
    }
    assert classify_agreement(breakdown) == "mista"


def test_classify_agreement_all_neutral_is_neutra():
    breakdown = {
        "fundamentalist": {"sub_score": 5.0},
        "technical": {"sub_score": -5.0},
        "news_sentiment": {"sub_score": None},
    }
    assert classify_agreement(breakdown) == "neutra"


def test_classify_agreement_single_available_is_concordante_trivial():
    breakdown = {
        "fundamentalist": {"sub_score": 60.0},
        "technical": {"sub_score": None},
        "news_sentiment": {"sub_score": None},
    }
    assert classify_agreement(breakdown) == "concordante"


@pytest.mark.parametrize(
    "available_count,agreement,expected",
    [
        (3, "concordante", "alta"),
        (3, "mista", "media"),
        (3, "neutra", "media"),
        (2, "concordante", "media"),
        (2, "mista", "baixa"),
        (2, "neutra", "baixa"),
        (1, "concordante", "baixa"),
        (1, "neutra", "baixa"),
    ],
)
def test_classify_confidence_table(available_count, agreement, expected):
    assert classify_confidence(available_count, agreement) == expected
