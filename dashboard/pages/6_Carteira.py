import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402
from bson import ObjectId  # noqa: E402

from core.exceptions import PortfolioError  # noqa: E402
from portfolio.portfolio_service import PortfolioService  # noqa: E402

st.title("💼 Carteira")
st.caption(
    "Registre quantas ações você possui e a alocação-alvo de cada ativo. A "
    "recomendação (página 'Conclusão e Recomendação') passa a considerar isso: "
    "ativos já acima da meta têm a categoria rebaixada para 'Aguardar', para "
    "evitar concentrar novos aportes onde a carteira já está sobreponderada."
)

service = PortfolioService()

asset_id_str = st.session_state.get("current_asset_id")
ticker = st.session_state.get("current_asset_ticker")

st.subheader("Posição do ativo selecionado")

if not asset_id_str:
    st.warning("Nenhum ativo selecionado. Vá para a página 'Buscar Ativo' primeiro.")
else:
    asset_id = ObjectId(asset_id_str)
    existing = service.get_position(asset_id)

    with st.form("position_form"):
        quantity = st.number_input(
            "Quantidade possuída",
            min_value=0.0,
            value=float(existing["quantity"]) if existing else 0.0,
            step=1.0,
        )
        avg_price = st.number_input(
            "Preço médio de compra (R$)",
            min_value=0.0,
            value=float(existing["avg_price"]) if existing else 0.0,
            step=0.01,
        )
        target_allocation_pct = st.number_input(
            "Alocação-alvo na carteira (%)",
            min_value=0.0,
            max_value=100.0,
            value=float(existing["target_allocation_pct"]) if existing else 0.0,
            step=1.0,
        )
        submitted = st.form_submit_button("Salvar Posição")

    if submitted:
        try:
            service.upsert_position(
                asset_id=asset_id,
                ticker=ticker,
                quantity=quantity,
                avg_price=avg_price,
                target_allocation_pct=target_allocation_pct,
            )
        except PortfolioError as exc:
            st.error(str(exc))
        else:
            st.success(f"Posição de '{ticker}' salva.")
            existing = service.get_position(asset_id)

    if existing and st.button("Remover posição deste ativo"):
        service.remove_position(asset_id)
        st.success(f"Posição de '{ticker}' removida.")
        existing = None

    if existing:
        allocation = service.compute_allocation(asset_id)
        if allocation is None:
            st.info(
                "Alocação atual ainda não pode ser calculada (cadastre posições "
                "com quantidade e preço em pelo menos um ativo)."
            )
        else:
            st.metric(
                f"Alocação atual de {ticker}",
                f"{allocation['current_allocation_pct']:.1f}%",
                delta=f"meta: {allocation['target_allocation_pct']:.1f}%",
            )
            st.caption(
                f"Status: {allocation['status']} — valor da posição "
                f"R$ {allocation['position_value']:.2f} de R$ {allocation['portfolio_value']:.2f} "
                "na carteira."
            )

st.divider()
st.subheader("Visão geral da carteira")

rows = service.list_allocations()
if not rows:
    st.info("Nenhuma posição cadastrada ainda.")
else:
    df = pd.DataFrame(
        [
            {
                "Ticker": row["ticker"],
                "Quantidade": row["quantity"],
                "Preço médio": row["avg_price"],
                "Valor atual": row["value"],
                "Alocação atual (%)": row["current_allocation_pct"],
                "Meta (%)": row["target_allocation_pct"],
                "Status": row["status"],
            }
            for row in rows
        ]
    )
    st.dataframe(df, use_container_width=True)
