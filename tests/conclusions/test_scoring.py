import pytest

from conclusions.scoring import (
    _score_valuation,
    overall_label,
    score_fundamentalist,
    score_news_sentiment,
    score_technical,
)


def test_score_fundamentalist_petr4_like_without_price_is_favorable():
    """Sem `price`/`eps`, o critério de valuation fica ausente e o peso é
    redistribuído entre os demais (pl 15, pvp 20, dy 15, roe 10, debt 10).
    """
    data = {
        "pl": 5.202952,
        "pvp": 1.2246315,
        "dividend_yield": 9.07,
        "roe": 0.25601,
        "debt_to_equity": 83.269,
    }
    score, highlights = score_fundamentalist(data)

    assert score == 75.71
    assert len(highlights) == 3


def test_score_fundamentalist_petr4_like_with_valuation_included():
    """Com `price`/`eps` disponíveis, o critério de valuation (peso 30, o
    maior de todos) entra na composição ponderada.
    """
    data = {
        "pl": 5.202952,
        "pvp": 1.2246315,
        "dividend_yield": 9.07,
        "roe": 0.25601,
        "debt_to_equity": 83.269,
        "price": 38.5,
        "eps": 8.28,
    }
    score, highlights = score_fundamentalist(data)

    assert score == 83.0
    assert any("preço-teto" in h for h in highlights)


def test_score_fundamentalist_bad_indicators_is_negative():
    data = {"pl": -5, "pvp": 5, "dividend_yield": 0, "roe": -0.1, "debt_to_equity": 250}
    score, _ = score_fundamentalist(data)

    assert score < -20


def test_score_fundamentalist_partial_ignores_none():
    data = {"pl": 5.2, "pvp": None, "dividend_yield": None, "roe": None, "debt_to_equity": None}
    score, highlights = score_fundamentalist(data)

    assert score == 100.0
    assert len(highlights) == 1


def test_score_fundamentalist_all_none_is_absent():
    data = {"pl": None, "pvp": None, "dividend_yield": None, "roe": None, "debt_to_equity": None}
    assert score_fundamentalist(data) == (None, [])


@pytest.mark.parametrize(
    "dividend_yield,expected_score",
    [(10, 100.0), (7.5, 60.0), (6.3, 20.0), (5.7, -50.0), (3, -100.0)],
)
def test_score_valuation_bazin_bands(dividend_yield, expected_score):
    data = {"price": 100.0, "dividend_yield": dividend_yield}
    score, highlight = _score_valuation(data)

    assert score == expected_score
    assert "preço-teto" in highlight


def test_score_valuation_absent_without_price():
    """Sem `price`, nem Graham nem Bazin podem ser calculados — valuation
    fica ausente e não deve gerar highlight nem quebrar o score geral.
    """
    data = {"pl": 5.2, "dividend_yield": 8.0}
    score, highlights = score_fundamentalist(data)

    assert score is not None
    assert not any("preço-teto" in h for h in highlights)


def test_score_valuation_conservative_takes_the_lower_of_graham_and_bazin():
    # Graham dá ~76.53 e Bazin dá ~58.20 para estes dados -> o preço-teto
    # deve usar o menor dos dois (Bazin), não a média nem o maior (Graham).
    data = {"price": 38.5, "eps": 8.28, "pvp": 1.2246315, "dividend_yield": 9.07}
    score, highlight = _score_valuation(data)

    assert "58.20" in highlight
    assert "76.5" not in highlight
    assert score == 100.0


def test_score_technical_strong_positive():
    data = {"trend": "alta", "rsi_14": 25.0, "macd_histogram": 0.5}
    score, highlights = score_technical(data)

    assert score > 50
    assert len(highlights) == 3


def test_score_technical_strong_negative():
    data = {"trend": "baixa", "rsi_14": 85.0, "macd_histogram": -0.5}
    score, _ = score_technical(data)

    assert score < -50


def test_score_technical_all_none_is_absent():
    assert score_technical({}) == (None, [])


def test_score_news_sentiment_positive():
    data = {
        "score": 0.42,
        "positive_count": 3,
        "negative_count": 1,
        "neutral_count": 2,
        "articles_analyzed": 6,
    }
    score, highlights = score_news_sentiment(data)

    assert score == 42.0
    assert len(highlights) == 2


def test_score_news_sentiment_zero_articles_is_absent():
    data = {
        "score": 0.0,
        "positive_count": 0,
        "negative_count": 0,
        "neutral_count": 0,
        "articles_analyzed": 0,
    }
    assert score_news_sentiment(data) == (None, [])


@pytest.mark.parametrize(
    "score,expected",
    [
        (20, "favoravel"),
        (19.99, "neutro"),
        (-20, "desfavoravel"),
        (-19.99, "neutro"),
        (0, "neutro"),
    ],
)
def test_overall_label_thresholds(score, expected):
    assert overall_label(score) == expected
