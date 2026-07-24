from enum import Enum


class AssetType(str, Enum):
    """Categorias de ativo/passivo suportadas (ou planejadas) pelo sistema.

    MVP (Etapa 2) cobre apenas BR_STOCK. Os demais valores já existem para
    que o core não precise ser alterado quando essas categorias forem
    implementadas.
    """

    BR_STOCK = "br_stock"
    INTL_STOCK = "intl_stock"
    ETF = "etf"
    CRYPTO = "crypto"
    FIXED_INCOME = "fixed_income"
    LIABILITY = "liability"
