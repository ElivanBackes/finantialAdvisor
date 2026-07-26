import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

from analysis_history.analysis_history_service import AnalysisHistoryService  # noqa: E402

st.title("📚 Histórico de Análises")
st.caption(
    "Todos os ativos já efetivamente analisados (com Recomendação gerada). "
    "Ativos apenas pesquisados em 'Buscar Ativo' não aparecem aqui."
)

_CATEGORY_TEXT = {
    "compra_forte": "🟢 Compra Forte",
    "comprar": "🟢 Comprar",
    "aguardar": "🟡 Aguardar",
    "manter": "🔵 Manter",
    "revisao_necessaria": "🔴 Revisão Necessária",
}

_SCORE_BANDS: dict[str, tuple[float, float] | None] = {
    "Todos": None,
    "Acima de 9": (9.0, float("inf")),
    "Entre 8 e 9": (8.0, 9.0),
    "Entre 7 e 8": (7.0, 8.0),
    "Abaixo de 7": (float("-inf"), 7.0),
}

_DY_BANDS: dict[str, tuple[float, float] | None] = {
    "Todos": None,
    "Acima de 10%": (10.0, float("inf")),
    "Entre 8% e 10%": (8.0, 10.0),
    "Abaixo de 8%": (float("-inf"), 8.0),
}

_PAGE_SIZE = 20


def _upside_badge(upside_pct) -> str:
    if pd.isna(upside_pct):
        return "-"
    if upside_pct > 20:
        return f"🟢 {upside_pct:+.1f}%"
    if upside_pct >= 10:
        return f"🟡 {upside_pct:+.1f}%"
    return f"🔴 {upside_pct:+.1f}%"


def _in_band(series: pd.Series, band: tuple[float, float] | None) -> pd.Series:
    if band is None:
        return pd.Series(True, index=series.index)
    low, high = band
    return series.notna() & (series > low) & (series <= high)


with st.spinner("Carregando histórico de análises..."):
    rows = AnalysisHistoryService().list_all()

if not rows:
    st.info(
        "Nenhum ativo analisado ainda. Gere uma Recomendação em "
        "'Conclusão e Recomendação' para que ele apareça aqui."
    )
else:
    df = pd.DataFrame(rows).sort_values("score_final", ascending=False, na_position="last")

    col_search, col_rec, col_score, col_dy = st.columns([2, 1, 1, 1])
    with col_search:
        search = st.text_input("🔎 Buscar por ticker ou empresa", value="")
    with col_rec:
        recommendation_filter = st.selectbox(
            "Recomendação",
            ["Todos", *_CATEGORY_TEXT.keys()],
            format_func=lambda k: "Todos" if k == "Todos" else _CATEGORY_TEXT[k],
        )
    with col_score:
        score_filter = st.selectbox("Score", list(_SCORE_BANDS.keys()))
    with col_dy:
        dy_filter = st.selectbox("Dividend Yield", list(_DY_BANDS.keys()))

    if search.strip():
        needle = search.strip().lower()
        df = df[
            df["ticker"].str.lower().str.contains(needle, na=False)
            | df["company_name"].str.lower().str.contains(needle, na=False)
        ]
    if recommendation_filter != "Todos":
        df = df[df["recommendation_category"] == recommendation_filter]
    df = df[_in_band(df["score_final"], _SCORE_BANDS[score_filter])]
    df = df[_in_band(df["dividend_yield_expected"], _DY_BANDS[dy_filter])]

    df = df.reset_index(drop=True)
    st.caption(f"{len(df)} ativo(s) encontrados.")

    if df.empty:
        st.info("Nenhum ativo corresponde aos filtros selecionados.")
    else:
        display_df = pd.DataFrame(
            {
                "Ranking": df.index + 1,
                "Ticker": df["ticker"],
                "Nome da Empresa": df["company_name"],
                "Score Final": df["score_final"].round(2),
                "DY Esperado (%)": df["dividend_yield_expected"].round(2),
                "Preço Atual (R$)": df["current_price"].round(2),
                "Preço Teto (R$)": df["ceiling_price"].round(2),
                "Potencial de Valorização": df["upside_pct"].apply(_upside_badge),
                "Recomendação": df["recommendation_category"].map(_CATEGORY_TEXT),
                "Data da Análise": df["analyzed_at"],
                "Última Atualização": df["updated_at"],
            }
        )

        total_pages = max(1, (len(display_df) - 1) // _PAGE_SIZE + 1)
        page = 1
        if total_pages > 1:
            page = st.number_input(
                "Página", min_value=1, max_value=total_pages, value=1, step=1
            )
        start = (page - 1) * _PAGE_SIZE
        st.dataframe(
            display_df.iloc[start : start + _PAGE_SIZE],
            use_container_width=True,
            hide_index=True,
        )
        st.caption(f"Página {page} de {total_pages} — clique nos cabeçalhos para ordenar.")

        st.divider()
        st.subheader("Reutilizar análise anterior")
        ticker_options = df["ticker"].tolist()
        chosen = st.selectbox("Selecione um ativo já analisado", ticker_options)
        if st.button("Carregar este ativo"):
            selected = df[df["ticker"] == chosen].iloc[0]
            st.session_state["current_asset_id"] = str(selected["asset_id"])
            st.session_state["current_asset_ticker"] = chosen
            st.success(
                f"Ativo '{chosen}' carregado — acesse as demais páginas para ver os "
                "dados sem precisar coletar de novo."
            )
