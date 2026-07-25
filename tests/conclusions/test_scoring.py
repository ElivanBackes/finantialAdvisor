import pytest

from conclusions.scoring import (
    _score_dividend_yield,
    _score_ev_ebitda,
    _score_fcf_yield,
    _score_growth,
    _score_valuation,
    overall_label,
    score_fundamentalist,
    score_news_sentiment,
    score_technical,
)


def test_score_fundamentalist_petr4_like_without_price_is_favorable():
    """Sem `price`/`eps`/payout/fcf/ev_ebitda/growth, só pl/pvp/dy/roe/debt
    estão disponíveis — o peso dos demais critérios é redistribuído entre
    eles.
    """
    data = {
        "pl": 5.202952,
        "pvp": 1.2246315,
        "dividend_yield": 9.07,
        "roe": 0.25601,
        "debt_to_equity": 83.269,
    }
    score, highlights = score_fundamentalist(data)

    assert score == 82.22
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

    assert score == 89.33
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


@pytest.mark.parametrize(
    "earnings_growth,revenue_growth,expected_score",
    [
        (-0.30, None, -100.0),
        (-0.10, None, -50.0),
        (0.02, None, 0.0),
        (0.10, None, 50.0),
        (0.25, None, 80.0),
        (0.40, None, 100.0),
        (0.10, 0.20, 80.0),  # média (15%) -> banda "bom crescimento"
    ],
)
def test_score_growth_bands(earnings_growth, revenue_growth, expected_score):
    score, highlight = _score_growth(earnings_growth, revenue_growth)

    assert score == expected_score
    assert highlight is not None


def test_score_growth_absent_without_any_data():
    assert _score_growth(None, None) == (None, None)


@pytest.mark.parametrize(
    "fcf,market_cap,expected_score",
    [(-100, 1000, -100.0), (20, 1000, 20.0), (50, 1000, 50.0), (80, 1000, 80.0), (150, 1000, 100.0)],
)
def test_score_fcf_yield_bands(fcf, market_cap, expected_score):
    score, highlight = _score_fcf_yield(fcf, market_cap)

    assert score == expected_score
    assert highlight is not None


def test_score_fcf_yield_absent_without_market_cap():
    assert _score_fcf_yield(100.0, None) == (None, None)


@pytest.mark.parametrize(
    "ev_ebitda,expected_score",
    [(-1, -100.0), (3, 90.0), (6, 60.0), (10, 0.0), (15, -50.0), (25, -100.0)],
)
def test_score_ev_ebitda_bands(ev_ebitda, expected_score):
    score, highlight = _score_ev_ebitda(ev_ebitda)

    assert score == expected_score
    assert highlight is not None


def test_score_ev_ebitda_absent_without_data():
    assert _score_ev_ebitda(None) == (None, None)


@pytest.mark.parametrize(
    "payout_ratio,expected_score",
    [
        (0.31, 100.0),  # payout saudável, sem penalidade
        (0.70, 85.0),
        (0.95, 60.0),
        (1.5, 35.0),
        (None, 100.0),  # payout desconhecido, sem penalidade
        (-0.2, 50.0),  # payout negativo, penalidade forte
    ],
)
def test_score_dividend_yield_payout_penalty(payout_ratio, expected_score):
    score, highlight = _score_dividend_yield(9.07, payout_ratio)

    assert score == expected_score
    if payout_ratio is not None and not (0 <= payout_ratio * 100 <= 60):
        assert "Payout" in highlight


def test_score_dividend_yield_no_payout_penalty_when_no_dividend():
    """DY <= 0 não paga dividendo — payout não deve alterar o score nem
    entrar na mensagem.
    """
    score, highlight = _score_dividend_yield(0.0, payout_ratio=2.0)

    assert score == 0.0
    assert "Payout" not in highlight


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
