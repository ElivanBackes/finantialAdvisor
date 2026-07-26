import pytest

from macro.macro_service import MacroService


def _service(selic=None, fx_trend=None, oil_trend=None) -> MacroService:
    return MacroService(
        get_latest_selic=lambda: selic,
        get_exchange_rate_trend=lambda: fx_trend,
        get_oil_price_trend=lambda: oil_trend,
    )


@pytest.mark.parametrize(
    "sector,industry",
    [("Energy", "Oil & Gas Integrated"), (None, "Oil & Gas E&P"), ("Oil and Gas", None)],
)
def test_oil_gas_sector_is_classified_and_uses_oil_and_fx_trend(sector, industry):
    service = _service(oil_trend=(80.0, 90.0), fx_trend=(5.0, 5.0))

    result = service.compute_adjustment(sector, industry)

    assert result["sector_category"] == "petroleo_gas"
    assert result["adjustment"] == 5.0  # só o petróleo subiu (+12.5%) -> +5
    assert len(result["factors"]) == 1


def test_oil_gas_combines_oil_and_fx_adjustments():
    # Petróleo em alta (+10%) e câmbio desvalorizado (+5%) -> +5 (petróleo) +3 (câmbio) = +8
    service = _service(oil_trend=(80.0, 88.0), fx_trend=(5.0, 5.25))

    result = service.compute_adjustment("Energy", "Oil & Gas Integrated")

    assert result["adjustment"] == 8.0
    assert len(result["factors"]) == 2


def test_oil_gas_returns_none_without_relevant_variation():
    service = _service(oil_trend=(80.0, 81.0), fx_trend=(5.0, 5.01))

    assert service.compute_adjustment("Energy", "Oil & Gas Integrated") is None


def test_oil_gas_returns_none_when_no_data_available():
    service = _service(oil_trend=None, fx_trend=None)

    assert service.compute_adjustment("Energy", "Oil & Gas Integrated") is None


@pytest.mark.parametrize(
    "sector,industry",
    [("Financial Services", "Banks - Regional"), (None, "Insurance - Diversified")],
)
def test_financial_sector_uses_selic(sector, industry):
    service = _service(selic=14.0)

    result = service.compute_adjustment(sector, industry)

    assert result["sector_category"] == "bancos_seguros"
    assert result["adjustment"] == 5.0


def test_financial_sector_low_selic_is_negative():
    service = _service(selic=5.0)

    result = service.compute_adjustment("Financial Services", "Banks - Regional")

    assert result["adjustment"] == -5.0


def test_financial_sector_moderate_selic_is_no_adjustment():
    service = _service(selic=9.0)

    assert service.compute_adjustment("Financial Services", "Banks - Regional") is None


def test_financial_sector_returns_none_without_selic_data():
    service = _service(selic=None)

    assert service.compute_adjustment("Financial Services", "Banks - Regional") is None


@pytest.mark.parametrize(
    "sector,industry",
    [("Utilities", "Utilities - Regulated Electric"), ("Industrials", "Conglomerates"), (None, None)],
)
def test_uncovered_sectors_return_none(sector, industry):
    service = _service(selic=14.0, oil_trend=(80.0, 120.0), fx_trend=(5.0, 6.0))

    assert service.compute_adjustment(sector, industry) is None
