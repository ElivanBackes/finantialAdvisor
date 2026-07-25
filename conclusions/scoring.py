"""Funções puras de scoring: transformam o `data` de cada AnalysisResult em
um sub-score -100..100 + highlights textuais. Sem I/O, sem Mongo — toda a
orquestração/persistência fica em conclusions/conclusion_service.py.
"""

import math


def _normalize_percent(value: float) -> float:
    """Heurística empírica (yfinance é inconsistente entre campos):
    se |value| <= 1, trata como fração e multiplica por 100 (ex: 0.256 -> 25.6);
    se |value| > 1, assume que já está em formato percentual (ex: 9.07 -> 9.07).
    Não é uma verdade absoluta — é uma aproximação best-effort para o MVP.
    """
    return value * 100 if abs(value) <= 1 else value


# --- Indicadores fundamentalistas -------------------------------------------------


def _score_pl(pl: float | None) -> tuple[float | None, str | None]:
    if pl is None:
        return None, None
    if pl <= 0:
        return -100.0, "P/L negativo ou nulo (empresa com prejuízo)."
    if pl <= 4:
        return 40.0, "P/L muito baixo (pode indicar subavaliação, mas também distorção contábil)."
    if pl <= 10:
        return 100.0, "P/L em faixa considerada barata/saudável."
    if pl <= 15:
        return 60.0, "P/L razoável."
    if pl <= 25:
        return 0.0, "P/L neutro (mercado precifica crescimento)."
    if pl <= 40:
        return -50.0, "P/L elevado (ação cara)."
    return -100.0, "P/L muito elevado (ação muito cara)."


def _score_pvp(pvp: float | None) -> tuple[float | None, str | None]:
    if pvp is None:
        return None, None
    if pvp <= 0:
        return -100.0, "P/VP negativo (patrimônio líquido negativo, sinal grave)."
    if pvp < 1:
        return 100.0, "P/VP abaixo de 1 (negociada abaixo do valor patrimonial)."
    if pvp < 2:
        return 40.0, "P/VP razoável, entre o valor patrimonial e a faixa cara."
    if pvp < 3:
        return -40.0, "P/VP começando a ficar caro."
    return -100.0, "P/VP igual ou acima de 3 (considerado caro)."


def _score_dividend_yield(dy: float | None) -> tuple[float | None, str | None]:
    if dy is None:
        return None, None
    dy_pct = _normalize_percent(dy)
    if dy_pct <= 0:
        return 0.0, "Sem distribuição de dividendos (não é necessariamente ruim)."
    if dy_pct < 3:
        return 30.0, f"Dividend yield baixo (~{dy_pct:.2f}%)."
    if dy_pct < 6:
        return 65.0, f"Dividend yield moderado (~{dy_pct:.2f}%)."
    if dy_pct < 9:
        return 90.0, f"Dividend yield bom (~{dy_pct:.2f}%)."
    return 100.0, f"Dividend yield de {dy_pct:.2f}% é considerado forte."


def _score_roe(roe: float | None) -> tuple[float | None, str | None]:
    if roe is None:
        return None, None
    roe_pct = _normalize_percent(roe)
    if roe_pct < 0:
        return -100.0, f"ROE negativo ({roe_pct:.2f}%), patrimônio sendo corroído."
    if roe_pct < 5:
        return -20.0, f"ROE fraco ({roe_pct:.2f}%)."
    if roe_pct < 10:
        return 20.0, f"ROE abaixo da média ({roe_pct:.2f}%)."
    if roe_pct < 15:
        return 50.0, f"ROE razoável ({roe_pct:.2f}%)."
    if roe_pct < 20:
        return 75.0, f"ROE bom ({roe_pct:.2f}%)."
    return 100.0, f"ROE de {roe_pct:.2f}% é considerado forte."


def _score_debt_to_equity(d2e: float | None) -> tuple[float | None, str | None]:
    if d2e is None:
        return None, None
    if d2e < 0:
        return -100.0, "Dívida/Patrimônio negativa (patrimônio líquido negativo)."
    if d2e < 50:
        return 100.0, f"Baixo endividamento ({d2e:.2f}%)."
    if d2e < 100:
        return 50.0, f"Endividamento moderado ({d2e:.2f}%)."
    if d2e < 150:
        return 0.0, f"Endividamento elevado ({d2e:.2f}%)."
    if d2e < 200:
        return -50.0, f"Endividamento alto ({d2e:.2f}%)."
    return -100.0, f"Endividamento muito alto ({d2e:.2f}%)."


def _fair_value_graham(eps: float | None, vpa: float | None) -> float | None:
    """Fórmula de Graham: valor justo = sqrt(22.5 x LPA x VPA). Só válida com
    lucro e patrimônio líquido positivos (empresa deficitária não tem
    "valor justo" bem definido por essa fórmula).
    """
    if eps is None or vpa is None or eps <= 0 or vpa <= 0:
        return None
    return math.sqrt(22.5 * eps * vpa)


def _ceiling_price_bazin(dpa: float | None) -> float | None:
    """Método de Bazin: preço-teto = DPA / 6%. Assume 6% como yield mínimo
    aceitável — heurística clássica, não calibrada por setor.
    """
    if dpa is None or dpa <= 0:
        return None
    return dpa / 0.06


def _score_valuation(data: dict) -> tuple[float | None, str | None]:
    """Preço-teto conservador = menor valor entre Graham e Bazin (quando
    ambos disponíveis). Pontua pela margem de segurança entre o preço atual
    e esse preço-teto — critério de maior peso no score fundamentalista,
    por ser o fator dominante segundo a especificação de valuation.
    """
    price = data.get("price")
    if price is None or price <= 0:
        return None, None

    pvp = data.get("pvp")
    vpa = price / pvp if pvp and pvp > 0 else None
    dividend_yield = data.get("dividend_yield")
    dpa = price * (_normalize_percent(dividend_yield) / 100) if dividend_yield is not None else None

    candidates = [
        v
        for v in (_fair_value_graham(data.get("eps"), vpa), _ceiling_price_bazin(dpa))
        if v is not None
    ]
    if not candidates:
        return None, None

    preco_teto = min(candidates)
    margem = (preco_teto - price) / price * 100

    if margem >= 30:
        return 100.0, (
            f"Preço R$ {price:.2f} com {margem:.1f}% de margem de segurança "
            f"em relação ao preço-teto estimado (R$ {preco_teto:.2f})."
        )
    if margem >= 15:
        return 60.0, (
            f"Preço R$ {price:.2f} com margem de segurança adequada "
            f"({margem:.1f}%) frente ao preço-teto (R$ {preco_teto:.2f})."
        )
    if margem >= 0:
        return 20.0, (
            f"Preço R$ {price:.2f} próximo do preço-teto (R$ {preco_teto:.2f}) "
            "— margem de segurança reduzida."
        )
    if margem >= -15:
        return -50.0, (
            f"Preço R$ {price:.2f} está {abs(margem):.1f}% acima do preço-teto "
            f"(R$ {preco_teto:.2f}) — reduz a atratividade para novos aportes."
        )
    return -100.0, (
        f"Preço R$ {price:.2f} está {abs(margem):.1f}% acima do preço-teto "
        f"(R$ {preco_teto:.2f}) — margem de segurança negativa."
    )


# Pesos do score fundamentalista (Fase 1 da especificação de valuation).
# Valuation assume o peso de maior importância (30%, dominante segundo a
# spec); PL e PVP seguem como proxy de "histórico de múltiplos" até que
# ROIC/FCF/payout/EV-EBITDA/crescimento sejam incorporados (Fase 2).
_FUNDAMENTALIST_WEIGHTS = {
    "valuation": 30,
    "dividend_yield": 15,
    "pl": 15,
    "pvp": 20,
    "roe": 10,
    "debt_to_equity": 10,
}


def score_fundamentalist(data: dict) -> tuple[float | None, list[str]]:
    scored = {
        "valuation": _score_valuation(data),
        "pl": _score_pl(data.get("pl")),
        "pvp": _score_pvp(data.get("pvp")),
        "dividend_yield": _score_dividend_yield(data.get("dividend_yield")),
        "roe": _score_roe(data.get("roe")),
        "debt_to_equity": _score_debt_to_equity(data.get("debt_to_equity")),
    }
    available = {key: pair for key, pair in scored.items() if pair[0] is not None}
    if not available:
        return None, []

    total_weight = sum(_FUNDAMENTALIST_WEIGHTS[key] for key in available)
    weighted_sum = sum(_FUNDAMENTALIST_WEIGHTS[key] * pair[0] for key, pair in available.items())
    sub_score = round(weighted_sum / total_weight, 2)

    top_highlights = sorted(available.values(), key=lambda pair: -abs(pair[0]))[:3]
    return sub_score, [text for _, text in top_highlights]


# --- Indicadores técnicos ----------------------------------------------------------


def _score_trend(trend: str | None) -> tuple[float | None, str | None]:
    if trend == "alta":
        return 100.0, "Tendência de alta."
    if trend == "baixa":
        return -100.0, "Tendência de baixa."
    if trend == "indefinida":
        return 0.0, "Tendência indefinida (histórico curto)."
    return None, None


def _score_rsi(rsi: float | None) -> tuple[float | None, str | None]:
    if rsi is None:
        return None, None
    if rsi <= 30:
        score = 60 + (30 - rsi) / 30 * 40
        estado = "sobrevendido"
    elif rsi >= 70:
        score = -60 - (min(rsi, 100) - 70) / 30 * 40
        estado = "sobrecomprado"
    else:
        score = (50 - rsi) / 20 * 60
        estado = "neutro"
    return round(score, 2), f"RSI(14) em {rsi:.2f} — {estado}."


def _score_macd_histogram(hist: float | None) -> tuple[float | None, str | None]:
    if hist is None:
        return None, None
    if hist > 0:
        return 50.0, "MACD histograma positivo (sinal bullish)."
    if hist < 0:
        return -50.0, "MACD histograma negativo (sinal bearish)."
    return 0.0, "MACD histograma neutro."


def score_technical(data: dict) -> tuple[float | None, list[str]]:
    pairs = [
        _score_trend(data.get("trend")),
        _score_rsi(data.get("rsi_14")),
        _score_macd_histogram(data.get("macd_histogram")),
    ]
    available = [(score, text) for score, text in pairs if score is not None]
    if not available:
        return None, []

    sub_score = round(sum(score for score, _ in available) / len(available), 2)
    top_highlights = sorted(available, key=lambda pair: -abs(pair[0]))[:3]
    return sub_score, [text for _, text in top_highlights]


# --- Notícias / sentimento ----------------------------------------------------------


def score_news_sentiment(data: dict) -> tuple[float | None, list[str]]:
    articles = data.get("articles_analyzed", 0)
    if not articles:
        # Ausência de notícias reais não é um sinal neutro — é falta de dado.
        return None, []

    score = data.get("score")
    if score is None:
        return None, []

    sub_score = round(max(-100.0, min(100.0, score * 100)), 2)
    tom = "positivo" if score > 0 else "negativo" if score < 0 else "neutro"
    highlights = [
        f"Sentimento de notícias {tom} (score {score:+.2f}) com base em {articles} artigo(s).",
        f"{data.get('positive_count', 0)} positiva(s), {data.get('negative_count', 0)} negativa(s), "
        f"{data.get('neutral_count', 0)} neutra(s).",
    ]
    return sub_score, highlights


# --- Rótulo geral --------------------------------------------------------------------


def overall_label(score: float) -> str:
    """Zona neutra de 40 pontos (20% do range para cada lado): evita que
    ruído de poucos indicadores/análises baste para definir o rótulo, já
    que o score vem de poucas fontes discretas (3 análises, cada uma com
    poucos indicadores), não de uma amostra estatisticamente grande.
    """
    if score >= 20:
        return "favoravel"
    if score <= -20:
        return "desfavoravel"
    return "neutro"
