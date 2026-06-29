"""Domain product catalog — core SKU registry for the CRM worklist filter.

Fine Japan 8 core SKUs. Each entry: (url_key, display_label).
Keyword matching per key uses loose substring logic — see matches_core_product().
"""
from __future__ import annotations


CORE_PRODUCTS: list[tuple[str, str]] = [
    ("cordyceps_vien",   "Cordyceps Viên"),
    ("cordyceps_plus",   "Cordyceps Plus"),
    ("fucoidan",         "Fucoidan"),
    ("collagen_plus",    "Collagen Plus"),
    ("collagen_swallow", "Collagen Swallow's Nest"),
    ("shark_cartilage",  "Shark Cartilage"),
    ("natto",            "Natto Kinase"),
    ("metabo",           "Metabo"),
]

CORE_PRODUCT_KEYS: frozenset[str] = frozenset(k for k, _ in CORE_PRODUCTS)


def matches_core_product(product_str: str, key: str) -> bool:
    """Return True if product_str belongs to the given core product key."""
    s = (product_str or "").lower()
    if key == "cordyceps_vien":
        return "cordyceps" in s and "plus" not in s
    if key == "cordyceps_plus":
        return "cordyceps plus" in s
    if key == "fucoidan":
        return "fucoidan" in s
    if key == "collagen_plus":
        return "collagen plus" in s
    if key == "collagen_swallow":
        return "swallow" in s
    if key == "shark_cartilage":
        return "shark" in s
    if key == "natto":
        return "natto" in s
    if key == "metabo":
        return "metabo" in s
    return False
