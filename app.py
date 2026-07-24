import streamlit as st

from config.logging_setup import configure_logging
from config.mongo import get_database
from persistence.schemas.indexes import ensure_indexes

configure_logging()

st.set_page_config(page_title="Financial Advisor", page_icon="💰", layout="wide")

pages = [
    st.Page("dashboard/pages/1_Buscar_Ativo.py", title="Buscar Ativo", icon="🔎"),
    st.Page(
        "dashboard/pages/2_Analise_Fundamentalista.py",
        title="Análise Fundamentalista",
        icon="📊",
    ),
    st.Page("dashboard/pages/3_Analise_Tecnica.py", title="Análise Técnica", icon="📈"),
    st.Page("dashboard/pages/4_Noticias_Sentimento.py", title="Notícias/Sentimento", icon="📰"),
    st.Page(
        "dashboard/pages/5_Conclusao_Recomendacao.py",
        title="Conclusão e Recomendação",
        icon="🧭",
    ),
    st.Page("dashboard/pages/6_Logs.py", title="Logs", icon="📜"),
]

with st.sidebar:
    st.title("💰 Financial Advisor")
    try:
        get_database().client.admin.command("ping")
        ensure_indexes()
        st.success("MongoDB conectado")
    except Exception as exc:  # noqa: BLE001 — feedback de conectividade na sidebar
        st.error(f"MongoDB indisponível: {exc}")

navigation = st.navigation(pages)
navigation.run()
