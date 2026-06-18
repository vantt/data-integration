"""Centralized badge color and tooltip catalog for CRM web UI.

Single source of truth for all business-domain badge styling.
Templates use bdg_cls / bdg_tip Jinja2 filters; Python helpers use bdg_lookup.

css_mod values map directly to CSS class suffixes:
  'good'   → bdg--good   (green)
  'warn'   → bdg--warn   (amber)
  'bad'    → bdg--bad    (red)
  'accent' → bdg--accent (accent/purple)
  ''       → bdg         (neutral, no modifier)
"""
from __future__ import annotations

from typing import NamedTuple


class BadgeDef(NamedTuple):
    css_mod: str  # 'good' | 'warn' | 'bad' | 'accent' | ''
    hint: str     # Vietnamese tooltip text shown via data-tooltip


_NEUTRAL = BadgeDef("", "")

_CATALOG: dict[str, dict[str, BadgeDef]] = {
    "order_status": {
        "completed":  BadgeDef("good",   "Đơn đã hoàn tất"),
        "complete":   BadgeDef("good",   "Đơn đã hoàn tất"),
        "finalized":  BadgeDef("good",   "Đơn đã chốt"),
        "processing": BadgeDef("warn",   "Đang xử lý"),
        "confirmed":  BadgeDef("warn",   "Đã xác nhận, chờ xuất kho"),
        "pending":    BadgeDef("warn",   "Chờ xác nhận"),
        "draft":      BadgeDef("",       "Nháp — chưa xác nhận"),
        "archived":   BadgeDef("",       "Lưu trữ"),
        "cancelled":  BadgeDef("bad",    "Đã hủy"),
        "canceled":   BadgeDef("bad",    "Đã hủy"),
        "returned":   BadgeDef("bad",    "Đã hoàn trả"),
        "voided":     BadgeDef("bad",    "Vô hiệu"),
    },
    "payment_status": {
        "paid":       BadgeDef("good",   "Đã thanh toán đủ"),
        "partial":    BadgeDef("warn",   "Thanh toán một phần"),
        "unpaid":     BadgeDef("warn",   "Chưa thanh toán"),
        "refunded":   BadgeDef("bad",    "Đã hoàn tiền"),
        "voided":     BadgeDef("bad",    "Giao dịch bị hủy"),
    },
    "fulfillment_status": {
        "delivered":  BadgeDef("good",   "Đã giao hàng thành công"),
        "received":   BadgeDef("good",   "Đã nhận hàng"),
        "packed":     BadgeDef("warn",   "Đã đóng gói, chờ lấy hàng"),
        "shipping":   BadgeDef("warn",   "Đang vận chuyển"),
        "unshipped":  BadgeDef("warn",   "Chưa xuất kho"),
        "returned":   BadgeDef("bad",    "Hàng bị hoàn trả"),
        "restocked":  BadgeDef("bad",    "Hàng hoàn kho"),
        "cancelled":  BadgeDef("bad",    "Vận chuyển bị hủy"),
        "canceled":   BadgeDef("bad",    "Vận chuyển bị hủy"),
    },
    "value_group": {
        "VIP":    BadgeDef("accent", "VIP — khách hàng giá trị đặc biệt cao"),
        "GOLD":   BadgeDef("good",   "GOLD — khách hàng giá trị cao"),
        "SILVER": BadgeDef("warn",   "SILVER — khách hàng giá trị trung bình"),
        "BRONZE": BadgeDef("",       "BRONZE — khách hàng mới hoặc giá trị cơ bản"),
    },
    "customer_status": {
        "active":   BadgeDef("good",  "Đang hoạt động — có giao dịch gần đây"),
        "at_risk":  BadgeDef("warn",  "Có nguy cơ rời bỏ — lâu chưa mua"),
        "churned":  BadgeDef("bad",   "Đã rời bỏ — không còn hoạt động"),
    },
    "purchase_signal": {
        "OVERDUE":   BadgeDef("bad",  "Quá hạn mua lại theo dự đoán"),
        "DUE_SOON":  BadgeDef("warn", "Sắp đến hạn mua lại"),
        "ON_TRACK":  BadgeDef("good", "Đang trong chu kỳ mua bình thường"),
    },
    "action_type": {
        "CALL_NOW":         BadgeDef("bad",    "Gọi ngay — khách có nguy cơ rời bỏ cao"),
        "REORDER_NUDGE":    BadgeDef("warn",   "Nhắc tái đặt hàng — sắp đến chu kỳ"),
        "WIN_BACK":         BadgeDef("warn",   "Tái kích hoạt — đã lâu không mua"),
        "UPSELL":           BadgeDef("good",   "Upsell — tiềm năng nâng hạng"),
        "CROSS_SELL":       BadgeDef("good",   "Cross-sell — đề xuất sản phẩm bổ sung"),
        "COLLECT_FEEDBACK": BadgeDef("accent", "Thu thập phản hồi từ khách"),
    },
    "customer_type": {
        "RETAIL":    BadgeDef("",       "Khách lẻ"),
        "WHOLESALE": BadgeDef("accent", "Khách buôn / B2B"),
        "PARTNER":   BadgeDef("accent", "Đối tác"),
    },
    "party_status": {
        "active":   BadgeDef("good",  "Hồ sơ đang hoạt động"),
        "inactive": BadgeDef("",      "Hồ sơ không hoạt động"),
        "at_risk":  BadgeDef("warn",  "Có nguy cơ rời bỏ"),
        "churned":  BadgeDef("bad",   "Đã rời bỏ"),
        "merged":   BadgeDef("",      "Đã gộp vào hồ sơ khác"),
    },
    "task_status": {
        "open":      BadgeDef("",      "Chưa bắt đầu"),
        "doing":     BadgeDef("warn",  "Đang thực hiện"),
        "done":      BadgeDef("good",  "Đã hoàn thành"),
        "cancelled": BadgeDef("bad",   "Đã hủy"),
    },
    "conv_status": {
        "open":    BadgeDef("warn",  "Đang mở — chờ phản hồi"),
        "closed":  BadgeDef("good",  "Đã đóng"),
        "pending": BadgeDef("",      "Chờ xử lý"),
    },
    "campaign_status": {
        "draft":     BadgeDef("",       "Nháp"),
        "active":    BadgeDef("good",   "Đang chạy"),
        "completed": BadgeDef("accent", "Đã hoàn thành"),
        "paused":    BadgeDef("warn",   "Tạm dừng"),
        "archived":  BadgeDef("bad",    "Đã lưu trữ"),
    },
    "campaign_target": {
        "pending":   BadgeDef("",       "Chờ gửi"),
        "sent":      BadgeDef("warn",   "Đã gửi"),
        "responded": BadgeDef("accent", "Đã phản hồi"),
        "converted": BadgeDef("good",   "Đã chuyển đổi"),
        "opted_out": BadgeDef("bad",    "Đã từ chối"),
    },
}


def bdg_lookup(domain: str, key: str) -> BadgeDef:
    """Return BadgeDef for domain+key; falls back to neutral on miss."""
    return _CATALOG.get(domain, {}).get((key or "").strip(), _NEUTRAL)


def bdg_mod_cls(domain: str, key: str) -> str:
    """Modifier-only class string: 'bdg--good' | '' (for templates using 'bdg {{ mod }}')."""
    mod = bdg_lookup(domain, key).css_mod
    return f"bdg--{mod}" if mod else ""


def bdg_full_cls(domain: str, key: str) -> str:
    """Full class string: 'bdg bdg--good' | 'bdg' (neutral)."""
    mod = bdg_lookup(domain, key).css_mod
    return f"bdg bdg--{mod}" if mod else "bdg"


def bdg_hint(domain: str, key: str) -> str:
    """Vietnamese tooltip text for domain+key."""
    return bdg_lookup(domain, key).hint
