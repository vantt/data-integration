"""Vietnamese geography utilities — province → region mapping."""
from __future__ import annotations

from typing import Optional

_GEO_HCMC = frozenset({'Hồ Chí Minh', 'TP Hồ Chí Minh', 'TP. Hồ Chí Minh', 'HCM', 'Ho Chi Minh'})
_GEO_HANOI = frozenset({'Hà Nội', 'Ha Noi', 'Hanoi'})
_GEO_MEKONG = frozenset({
    'An Giang', 'Bạc Liêu', 'Bến Tre', 'Cà Mau', 'Cần Thơ',
    'Đồng Tháp', 'Hậu Giang', 'Kiên Giang', 'Long An', 'Sóc Trăng',
    'Tiền Giang', 'Trà Vinh', 'Vĩnh Long',
})
_GEO_CENTRAL = frozenset({
    'Đà Nẵng', 'Thừa Thiên Huế', 'Quảng Nam', 'Quảng Ngãi', 'Bình Định',
    'Phú Yên', 'Khánh Hòa', 'Ninh Thuận', 'Bình Thuận', 'Quảng Bình',
    'Quảng Trị', 'Hà Tĩnh', 'Nghệ An', 'Thanh Hóa',
})


def geo_region(province: Optional[str]) -> str:
    """Map a Vietnamese province name to a broad geographic region label."""
    if not province:
        return ""
    if province in _GEO_HCMC:
        return "HCMC"
    if province in _GEO_HANOI:
        return "Hà Nội"
    if province in _GEO_MEKONG:
        return "Mekong"
    if province in _GEO_CENTRAL:
        return "Miền Trung"
    return "Khác"
