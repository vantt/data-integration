"""approach_script_regen_state.py — Regen-guard cho luồng auto-gen (phase 05).

Tránh gọi provider lại cho khách vừa có script "đủ mới". Ngưỡng tiered theo
next_purchase_signal (không dùng lifecycle_stage — lifecycle_stage=NEW không
đáng tin, xem memory project_lifecycle_stage_new_unreliable):
  - OVERDUE/DUE_SOON (tình huống đổi nhanh)  → 14 ngày
  - còn lại (VIP/GOLD ổn định)               → 30 ngày

State chỉ được cập nhật khi auto-load THÀNH CÔNG (script đang chờ duyệt tay
trong approach_out/ không tính là "đã sinh" cho mục đích regen-guard).
"""
from __future__ import annotations

import json
import logging
from datetime import date
from pathlib import Path

log = logging.getLogger(__name__)

_URGENT_SIGNALS = {"OVERDUE", "DUE_SOON"}
_URGENT_REGEN_DAYS = 14
_DEFAULT_REGEN_DAYS = 30


def regen_after_days_for(customer: dict, override: int | None) -> int:
    """Ngưỡng regen (ngày) cho 1 khách; override ép flat N khi truyền (vd test)."""
    if override is not None:
        return override
    signal = customer.get("next_purchase_signal")
    return _URGENT_REGEN_DAYS if signal in _URGENT_SIGNALS else _DEFAULT_REGEN_DAYS


def load_state(path: Path) -> dict[str, str]:
    """{customer_id (str): last_loaded_at ISO date}; {} nếu file thiếu/hỏng."""
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError) as exc:
        log.warning("regen_state: không đọc được %s (%s) — coi như rỗng", path, exc)
        return {}


def save_state(path: Path, state: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def should_skip(customer: dict, state: dict[str, str], override: int | None, today: date) -> bool:
    """True nếu customer đã load gần đây hơn ngưỡng regen (bỏ qua, không sinh lại)."""
    last = state.get(str(customer["customer_id"]))
    if not last:
        return False
    try:
        last_date = date.fromisoformat(last[:10])
    except ValueError:
        return False
    threshold = regen_after_days_for(customer, override)
    return (today - last_date).days < threshold
