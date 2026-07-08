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
        "vip":    BadgeDef("accent", "VIP — khách hàng giá trị đặc biệt cao"),
        "gold":   BadgeDef("good",   "GOLD — khách hàng giá trị cao"),
        "silver": BadgeDef("warn",   "SILVER — khách hàng giá trị trung bình"),
        "bronze": BadgeDef("",       "BRONZE — khách hàng mới hoặc giá trị cơ bản"),
    },
    "customer_status": {
        "active":   BadgeDef("good",  "Đang hoạt động — có giao dịch gần đây"),
        "at_risk":  BadgeDef("warn",  "Có nguy cơ rời bỏ — lâu chưa mua"),
        "churned":  BadgeDef("bad",   "Đã rời bỏ — không còn hoạt động"),
    },
    "purchase_signal": {
        "overdue":   BadgeDef("bad",  "Quá hạn mua lại theo dự đoán"),
        "due_soon":  BadgeDef("warn", "Sắp đến hạn mua lại"),
        "on_track":  BadgeDef("good", "Đang trong chu kỳ mua bình thường"),
    },
    "action_type": {
        "call_now":         BadgeDef("bad",    "Gọi ngay — khách có nguy cơ rời bỏ cao"),
        "reorder_overdue":  BadgeDef("bad",    "Đứt liệu trình — quá hạn dùng sản phẩm"),
        "reorder_nudge":    BadgeDef("warn",   "Nhắc tái đặt hàng — sắp đến hạn hết sản phẩm"),
        "reorder_preempt":  BadgeDef("warn",   "Đặt trước — trong vòng 7 ngày hết sản phẩm"),
        "progress_check":   BadgeDef("accent", "Hỏi thăm tiến độ — dùng được 12-16 ngày"),
        "usage_followup":   BadgeDef("accent", "Hỗ trợ trải nghiệm — dùng được 5-9 ngày"),
        "win_back":         BadgeDef("warn",   "Tái kích hoạt — đã lâu không mua"),
        "second_order":     BadgeDef("warn",   "Đẩy đơn 2 — mới mua lần đầu"),
        "high_cancel_risk": BadgeDef("bad",    "Tỷ lệ huỷ cao — cần xác nhận đơn"),
        "upsell":           BadgeDef("good",   "Upsell — tiềm năng nâng hạng"),
        "cross_sell":       BadgeDef("good",   "Cross-sell — đề xuất sản phẩm bổ sung"),
        "collect_feedback": BadgeDef("accent", "Thu thập phản hồi từ khách"),
        "manual_risk_review": BadgeDef("bad",  "Cần xác minh rủi ro — NV đã tự đánh giá, không phải hệ thống tự động"),
        "gift_to_purchase":   BadgeDef("accent", "Từng được tặng, chưa từng mua — hỏi cảm nhận, gợi ý mua chính"),
    },
    "customer_type": {
        "retail":    BadgeDef("",       "Khách lẻ"),
        "wholesale": BadgeDef("accent", "Khách buôn / B2B"),
        "partner":   BadgeDef("accent", "Đối tác"),
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
    "strategic_tier": {
        "live_core":        BadgeDef("good",   "KH sống — mua gần đây, giữ chân"),
        "second_order":     BadgeDef("warn",   "Mới — chưa có đơn-2, cần activation"),
        "dormant_valuable": BadgeDef("warn",   "Nguội gần (91-365 ngày) — win-back ưu tiên"),
        "lapsed_valuable":  BadgeDef("",       "Nguội xa (>365 ngày) — win-back thử"),
        "masked_repeat":    BadgeDef("accent", "Shopee ẩn, repeat — thu định danh"),
        "nonbuyer":         BadgeDef("",       "Chưa mua — nuôi lead"),
        "graveyard":        BadgeDef("bad",    "Nghĩa địa — suppress"),
    },
}


# Short VN label for the PRIMARY badge text (distinct from `hint`, the hover tooltip).
# Only action_type needs this today — worklist rows showed the raw mart code
# ("CALL_NOW") as the badge text, which the hint alone doesn't fix since hint is
# tooltip-only. Kept as a parallel dict (not a 3rd BadgeDef field) so the other
# domains don't need a label they don't use.
_ACTION_TYPE_SHORT_LABEL: dict[str, str] = {
    "call_now":         "Gọi ngay",
    "reorder_overdue":  "Đứt liệu trình",
    "reorder_nudge":    "Nhắc tái đặt",
    "reorder_preempt":  "Đặt trước",
    "progress_check":   "Hỏi tiến độ",
    "usage_followup":   "Hỗ trợ trải nghiệm",
    "win_back":         "Tái kích hoạt",
    "second_order":     "Đơn hàng 2",
    "high_cancel_risk": "Rủi ro huỷ",
    "upsell":           "Upsell",
    "cross_sell":       "Cross-sell",
    "collect_feedback": "Thu thập phản hồi",
    "manual_risk_review": "Cần xác minh",
    "gift_to_purchase": "Từng được tặng",
}


def bdg_lookup(domain: str, key: str) -> BadgeDef:
    """Return BadgeDef for domain+key; falls back to neutral on miss."""
    return _CATALOG.get(domain, {}).get((key or "").strip().lower(), _NEUTRAL)


def bdg_label(domain: str, key: str) -> str:
    """Short VN label for badge TEXT (not the hover tooltip — see bdg_hint).

    Only 'action_type' has short labels; other domains/unknown keys fall back to
    the raw key so existing badge text (order_status, payment_status, ...) is
    unaffected.
    """
    if domain == "action_type":
        return _ACTION_TYPE_SHORT_LABEL.get((key or "").strip().lower(), key or "")
    return key or ""


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
