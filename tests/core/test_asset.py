from core.assets.asset import Asset
from core.assets.asset_type import AssetType


def test_asset_defaults():
    asset = Asset(ticker="PETR4.SA", asset_type=AssetType.BR_STOCK, name="Petrobras PN")

    assert asset.currency == "BRL"
    assert asset.metadata == {}


def test_asset_metadata_is_escape_hatch():
    asset = Asset(
        ticker="TESOURO-SELIC-2029",
        asset_type=AssetType.FIXED_INCOME,
        name="Tesouro Selic 2029",
        metadata={"maturity_date": "2029-03-01", "index_rate": "SELIC"},
    )

    assert asset.metadata["index_rate"] == "SELIC"


def test_all_asset_types_are_valid_strings():
    for asset_type in AssetType:
        assert isinstance(asset_type.value, str)
