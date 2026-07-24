import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

from persistence.repositories.log_repository import LogRepository  # noqa: E402

st.title("📜 Logs")
st.caption(
    "Registros persistidos no MongoDB (coleção `logs`, TTL de 30 dias) — "
    "captura tudo a partir de INFO, independente de onde o app foi iniciado."
)

_LEVEL_OPTIONS = ["Todos", "INFO", "WARNING", "ERROR"]
_LIMIT = 200

col1, col2 = st.columns(2)
with col1:
    level_choice = st.selectbox("Nível", _LEVEL_OPTIONS)
with col2:
    ticker_filter = st.text_input("Ticker (opcional, ex: PETR4.SA)", value="")

level = None if level_choice == "Todos" else level_choice
ticker = ticker_filter.strip() or None

logs = LogRepository().find_recent(limit=_LIMIT, level=level, ticker=ticker)

if not logs:
    st.info("Nenhum log encontrado para os filtros selecionados.")
else:
    df = pd.DataFrame(
        [
            {
                "timestamp": doc.get("timestamp"),
                "level": doc.get("level"),
                "logger": doc.get("logger"),
                "ticker": doc.get("ticker"),
                "message": doc.get("message"),
                "exception": doc.get("exception"),
            }
            for doc in logs
        ]
    )
    st.caption(f"{len(df)} registro(s) — máximo {_LIMIT} mais recentes.")
    st.dataframe(df, use_container_width=True)
