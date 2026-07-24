import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import streamlit as st  # noqa: E402

from core.analyzers.base import AnalysisType  # noqa: E402
from dashboard.components.asset_selector import asset_selector  # noqa: E402
from services.asset_service import AssetService  # noqa: E402

_LABELS = {
    AnalysisType.FUNDAMENTALIST: "Fundamentalista",
    AnalysisType.TECHNICAL: "Técnica",
    AnalysisType.NEWS_SENTIMENT: "Notícias/Sentimento",
}

st.title("🔎 Buscar Ativo")
st.caption("Cadastra o ativo e roda a coleta de dados + as 3 análises (Etapa 2).")

ticker, asset_type = asset_selector()

if st.button("Buscar / Cadastrar"):
    if not ticker:
        st.warning("Informe um ticker.")
    else:
        service = AssetService()
        asset_id = service.get_or_create_asset(ticker=ticker, asset_type=asset_type)
        st.session_state["current_asset_id"] = str(asset_id)
        st.session_state["current_asset_ticker"] = ticker
        st.session_state["current_asset_type"] = asset_type
        st.success(f"Ativo '{ticker}' pronto (asset_id={asset_id}).")

if "current_asset_ticker" in st.session_state:
    st.info(f"Ativo selecionado atualmente: {st.session_state['current_asset_ticker']}")

    if st.button("Coletar e Analisar"):
        service = AssetService()
        with st.spinner("Coletando dados e rodando as 3 análises..."):
            results = service.collect_and_analyze(
                ticker=st.session_state["current_asset_ticker"],
                asset_type=st.session_state["current_asset_type"],
            )
        for analysis_type, result in results.items():
            label = _LABELS[analysis_type]
            if result is not None:
                st.success(f"✅ {label} ok")
            else:
                st.warning(f"⚠️ {label} falhou — confira logs / chaves no .env")
