"""Server-side price list. The checkout charges these prices; a client-sent amount is ignored."""

PRICES: dict[str, float] = {
    "NMB-P8-128": 899.0,
    "NMB-P8-256": 999.0,
    "NMB-A5-64": 399.0,
}


def price_for(sku: str) -> float | None:
    return PRICES.get(sku)
