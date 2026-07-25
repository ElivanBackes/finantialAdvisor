import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import streamlit as st  # noqa: E402
from bson import ObjectId  # noqa: E402

from conclusions.conclusion_service import ConclusionService  # noqa: E402
from core.exceptions import ConclusionError, RecommendationError  # noqa: E402
from recommendations.recommendation_service import RecommendationService  # noqa: E402

_LABEL_TEXT = {"favoravel": "Favorável", "neutro": "Neutro", "desfavoravel": "Desfavorável"}
_LABEL_STYLE = {"favoravel": st.success, "neutro": st.warning, "desfavoravel": st.error}
_ANALYSIS_DISPLAY = {
    "fundamentalist": "Fundamentalista",
    "technical": "Técnica",
    "news_sentiment": "Notícias/Sentimento",
}
_CATEGORY_TEXT = {
    "compra_forte": "Compra Forte",
    "comprar": "Comprar",
    "aguardar": "Aguardar",
    "manter": "Manter",
    "revisao_necessaria": "Revisão Necessária",
}
_CATEGORY_STYLE = {
    "compra_forte": st.success,
    "comprar": st.success,
    "aguardar": st.warning,
    "manter": st.warning,
    "revisao_necessaria": st.error,
}
_CONFIDENCE_TEXT = {"alta": "Alta", "media": "Média", "baixa": "Baixa"}
_AGREEMENT_TEXT = {"concordante": "Concordante", "mista": "Mista", "neutra": "Neutra"}

st.title("🧭 Conclusão e Recomendação")

asset_id_str = st.session_state.get("current_asset_id")
ticker = st.session_state.get("current_asset_ticker")


def _md_escape(text: str) -> str:
    """Escapa `$` para o Streamlit não interpretar como delimitador de LaTeX
    (ex: "R$ 42.21 ... R$ 64.93" vira fórmula matemática sem isso).
    """
    return text.replace("$", "\\$")


def _render(conclusion: dict) -> None:
    style_fn = _LABEL_STYLE.get(conclusion["label"], st.info)
    style_fn(
        f"Conclusão: {_LABEL_TEXT.get(conclusion['label'], conclusion['label'])} "
        f"(score {conclusion['overall_score']:+.1f})"
    )
    if conclusion["missing_analyses"]:
        faltantes = ", ".join(
            _ANALYSIS_DISPLAY.get(m, m) for m in conclusion["missing_analyses"]
        )
        st.warning(f"Conclusão parcial — análises ausentes: {faltantes}")
    for key, label in _ANALYSIS_DISPLAY.items():
        entry = conclusion["breakdown"].get(key) or {}
        st.subheader(label)
        sub_score = entry.get("sub_score")
        st.write(f"Sub-score: {sub_score:+.1f}" if sub_score is not None else "Ausente.")
        for highlight in entry.get("highlights", []):
            st.write(f"- {_md_escape(highlight)}")
    st.caption(f"Gerado em {conclusion['analyzed_at']}")


def _render_recommendation(recommendation: dict) -> None:
    category = recommendation.get("category")
    if category is None:
        st.info(
            "A última recomendação salva para este ativo usa um formato antigo "
            "(anterior às 5 categorias de valuation). Gere uma nova recomendação."
        )
        return
    score_0_10 = recommendation.get("fundamentalist_score_0_10")
    style_fn = _CATEGORY_STYLE.get(category, st.info)
    score_text = f" (nota {score_0_10:.1f}/10)" if score_0_10 is not None else ""
    style_fn(
        f"Recomendação: {_CATEGORY_TEXT.get(category, category)}{score_text} "
        f"(confiança {_CONFIDENCE_TEXT.get(recommendation['confidence'], recommendation['confidence'])}, "
        f"concordância {_AGREEMENT_TEXT.get(recommendation['agreement'], recommendation['agreement'])})"
    )
    st.write("Justificativa:")
    for item in recommendation["justification"]:
        st.write(f"- {_md_escape(item)}")
    st.caption(recommendation["disclaimer"])
    st.caption(f"Gerado em {recommendation['analyzed_at']}")


if not asset_id_str:
    st.warning("Nenhum ativo selecionado. Vá para a página 'Buscar Ativo' primeiro.")
else:
    asset_id = ObjectId(asset_id_str)
    service = ConclusionService()

    existing = service.get_latest_conclusion(asset_id)
    if existing is not None:
        st.info("Última conclusão salva para este ativo:")
        _render(existing)
    else:
        st.info("Ainda não há conclusão gerada para este ativo.")

    if st.button("Gerar Conclusão"):
        with st.spinner("Sintetizando as 3 análises..."):
            try:
                conclusion = service.build_conclusion(asset_id, ticker)
            except ConclusionError as exc:
                st.error(str(exc))
            else:
                st.success("Conclusão gerada com sucesso.")
                _render(conclusion)

    st.divider()
    st.subheader("Recomendação")

    recommendation_service = RecommendationService()
    existing_recommendation = recommendation_service.get_latest_recommendation(asset_id)
    if existing_recommendation is not None:
        st.info("Última recomendação salva para este ativo:")
        _render_recommendation(existing_recommendation)
    else:
        st.info("Ainda não há recomendação gerada para este ativo.")

    if st.button("Gerar Recomendação"):
        with st.spinner("Calculando veredito final..."):
            try:
                recommendation = recommendation_service.build_recommendation(asset_id, ticker)
            except RecommendationError as exc:
                st.error(str(exc))
            else:
                st.success("Recomendação gerada com sucesso.")
                _render_recommendation(recommendation)
