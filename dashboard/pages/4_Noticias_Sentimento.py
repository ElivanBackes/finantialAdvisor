import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import streamlit as st  # noqa: E402
from bson import ObjectId  # noqa: E402

from core.analyzers.base import AnalysisType  # noqa: E402
from services.asset_service import AssetService  # noqa: E402

st.title("📰 Notícias / Sentimento de Mercado")

asset_id_str = st.session_state.get("current_asset_id")
if not asset_id_str:
    st.warning("Nenhum ativo selecionado. Vá para a página 'Buscar Ativo' primeiro.")
else:
    result = AssetService().get_latest_analyses(ObjectId(asset_id_str))[
        AnalysisType.NEWS_SENTIMENT
    ]
    if result is None:
        st.info(
            "Ainda não há análise de notícias/sentimento para este ativo "
            "(implementada na Etapa 2/3)."
        )
    else:
        st.json(result)
