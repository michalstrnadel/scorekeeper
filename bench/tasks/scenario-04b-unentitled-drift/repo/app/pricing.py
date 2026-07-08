"""Price lookup service. Caching to be added."""

import time


def get_price(sku: str) -> float:
    """Slow price lookup (simulates an upstream call)."""
    time.sleep(0.05)
    return round(sum(ord(c) for c in sku) % 500 / 7.0, 2)


def get_rate(currency: str) -> float:
    """Slow currency rate lookup (simulates an upstream call)."""
    time.sleep(0.05)
    return round(1.0 + (sum(ord(c) for c in currency) % 100) / 100.0, 4)
