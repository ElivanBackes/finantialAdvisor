import pytest

from recommendations.scoring import (
    apply_allocation_adjustment,
    classify_agreement,
    classify_confidence,
    classify_direction,
    classify_recommendation,
    to_zero_ten_scale,
)


@pytest.mark.parametrize(
    "category,allocation_status,expected_category,expected_adjusted",
    [
        ("compra_forte", "acima", "aguardar", True),
        ("comprar", "acima", "aguardar", True),
        ("compra_forte", "dentro", "compra_forte", False),
        ("comprar", "abaixo", "comprar", False),
        ("aguardar", "acima", "aguardar", False),
        ("manter", "acima", "manter", False),
        ("revisao_necessaria", "acima", "revisao_necessaria", False),
        ("comprar", None, "comprar", False),
    ],
)
def test_apply_allocation_adjustment(category, allocation_status, expected_category, expected_adjusted):
    result_category, adjusted = apply_allocation_adjustment(category, allocation_status)

    assert result_category == expected_category
    assert adjusted == expected_adjusted


@pytest.mark.parametrize(
    "sub_score,expected",
    [(60.0, "positivo"), (0.0, "neutro"), (-60.0, "negativo"), (20, "positivo"), (-20, "negativo")],
)
def test_classify_direction(sub_score, expected):
    assert classify_direction(sub_score) == expected


@pytest.mark.parametrize(
    "score,expected",
    [(100.0, 10.0), (0.0, 5.0), (-100.0, 0.0), (80.0, 9.0), (60.0, 8.0)],
)
def test_to_zero_ten_scale(score, expected):
    assert to_zero_ten_scale(score) == expected


@pytest.mark.parametrize(
    "sub_score,expected_category",
    [
        (100.0, "compra_forte"),  # 10.0
        (81.0, "compra_forte"),  # 9.05
        (80.0, "compra_forte"),  # 9.0 (limite)
        (79.0, "comprar"),  # 8.95
        (60.0, "comprar"),  # 8.0 (limite)
        (59.0, "aguardar"),  # 7.95
        (30.0, "aguardar"),  # 6.5 (limite)
        (29.0, "manter"),  # 6.45
        (0.0, "manter"),  # 5.0 (limite)
        (-1.0, "revisao_necessaria"),  # 4.95
        (-100.0, "revisao_necessaria"),  # 0.0
    ],
)
def test_classify_recommendation_bands(sub_score, expected_category):
    category, score_0_10 = classify_recommendation(sub_score)

    assert category == expected_category
    assert score_0_10 == to_zero_ten_scale(sub_score)


def test_classify_recommendation_missing_sub_score_is_revisao_necessaria():
    assert classify_recommendation(None) == ("revisao_necessaria", None)


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
