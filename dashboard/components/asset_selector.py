import streamlit as st

from core.assets.asset_type import AssetType


def asset_selector() -> tuple[str, AssetType]:
    """Widget reutilizável de busca/seleção de ativo (ticker + AssetType)."""
    ticker = st.text_input("Ticker do ativo (ex: PETR4.SA)", key="asset_selector_ticker")
    asset_type = st.selectbox(
        "Tipo de ativo",
        options=list(AssetType),
        format_func=lambda asset_type: asset_type.value,
        key="asset_selector_asset_type",
    )
    return ticker, asset_type
