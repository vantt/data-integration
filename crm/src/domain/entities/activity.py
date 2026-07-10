"""CRM Activity domain entity — recorded touchpoints between staff and a party.

Pure dataclasses; no HTTP/DB adapter imports.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

# ---------------------------------------------------------------------------
# Activity type constants
# ---------------------------------------------------------------------------
ACTIVITY_TYPE_CALL = "call"
ACTIVITY_TYPE_NOTE = "note"
ACTIVITY_TYPE_VISIT = "visit"
ACTIVITY_TYPE_EMAIL = "email"
ACTIVITY_TYPE_CHAT = "chat"
ACTIVITY_TYPE_OTHER = "other"
VALID_ACTIVITY_TYPES = [
    ACTIVITY_TYPE_CALL,
    ACTIVITY_TYPE_NOTE,
    ACTIVITY_TYPE_VISIT,
    ACTIVITY_TYPE_EMAIL,
    ACTIVITY_TYPE_CHAT,
    ACTIVITY_TYPE_OTHER,
]

# ---------------------------------------------------------------------------
# Direction constants
# ---------------------------------------------------------------------------
DIRECTION_IN = "in"
DIRECTION_OUT = "out"

# ---------------------------------------------------------------------------
# contact_outcome constants (D2 — per channel enum)
# ---------------------------------------------------------------------------
CONTACT_OUTCOMES_CALL = [
    "answered", "no_answer", "busy", "wrong_number", "callback", "refused", "purchased",
]
CONTACT_OUTCOMES_MESSAGING = [
    "replied", "no_reply", "pending_reply", "refused", "blocked",
]
CONTACT_OUTCOMES_VISIT = ["met", "not_met"]

VALID_CONTACT_OUTCOMES: list[str] = list(
    dict.fromkeys(CONTACT_OUTCOMES_CALL + CONTACT_OUTCOMES_MESSAGING + CONTACT_OUTCOMES_VISIT)
)

CONTACT_OUTCOMES_BY_CHANNEL_TYPE: dict[str, list[str]] = {
    "call":  CONTACT_OUTCOMES_CALL,
    "zalo":  CONTACT_OUTCOMES_MESSAGING,
    "fb":    CONTACT_OUTCOMES_MESSAGING,
    "email": CONTACT_OUTCOMES_MESSAGING,
    "visit": CONTACT_OUTCOMES_VISIT,
}

# ---------------------------------------------------------------------------
# outcome_reason constants (D2 — nullable, required when refused)
# ---------------------------------------------------------------------------
VALID_OUTCOME_REASONS = [
    "budget", "timing", "product_fit", "competitor",
    "stock", "trust", "no_need", "other",
    # Cosmetics-retail specifics — distinct signals with distinct follow-up actions:
    # still_stocked: khách còn hàng chưa dùng hết → điều chỉnh chu kỳ gợi ý mua lại,
    #   khác 'timing' (bận/để sau, không nói gì về lượng hàng còn).
    # wait_promo: khách chờ khuyến mãi → trigger liên hệ lại khi có promo,
    #   khác 'budget' (không đủ ngân sách ở mọi mức giá).
    # irritation: tác dụng phụ (kích ứng da, khó chịu tiêu hóa, mệt...) → tín hiệu
    #   chất lượng cần escalate, không upsell cùng dòng sản phẩm; khác 'product_fit'
    #   (không đúng nhu cầu). UI label = "Tác dụng phụ" (enum value giữ nguyên
    #   'irritation' để tương thích dữ liệu cũ). Server requires a non-empty `body`
    #   when this reason is chosen (see ActivityService.log_activity).
    "still_stocked", "wait_promo", "irritation",
    # do_not_contact: khách yêu cầu KHÔNG liên hệ lại nữa — khác 'refused' (từ chối lần
    #   này, có thể gọi lại sau); dùng để loại vĩnh viễn khỏi action queue/outreach.
    #   Không nằm trong REASON_REQUIRED_OUTCOMES — chỉ chọn được khi outcome='refused'.
    "do_not_contact",
]
# Server enforces reason when contact_outcome is in this set
REASON_REQUIRED_OUTCOMES: set[str] = {"refused"}

# ---------------------------------------------------------------------------
# status constants (P1 — draft lifecycle, migration 0045)
# ---------------------------------------------------------------------------
# NULL in the DB is treated as ACTIVITY_STATUS_FINAL — every row written before
# migration 0045 predates the draft concept and is, by definition, already a
# finished record. Never write NULL for new rows; always one of these two.
ACTIVITY_STATUS_DRAFT = "draft"
ACTIVITY_STATUS_FINAL = "final"


# ---------------------------------------------------------------------------
# Entity
# ---------------------------------------------------------------------------

@dataclass
class Activity:
    """One recorded touchpoint between a staff member and a party."""
    activity_id: str            # UUID
    party_id: str               # FK → crm_party
    activity_type: str          # call|note|visit|email|chat|other
    occurred_at: str            # UTC ISO-8601
    created_at: str             # UTC ISO-8601
    direction: Optional[str] = None         # in|out — None when not applicable
    channel: Optional[str] = None           # phone|messenger|zalo|store|...
    subject: Optional[str] = None
    body: Optional[str] = None
    outcome: Optional[str] = None
    related_order_code: Optional[str] = None  # soft ref; order lives in warehouse
    staff_user_id: Optional[str] = None     # FK → crm_app_user (nullable)
    custom_fields: Optional[dict] = None   # structured metadata (JSON in DB)
    task_id: Optional[str] = None           # FK → crm_task (nullable) — links attempt to task
    channel_type: Optional[str] = None      # call|zalo|fb|email|visit|other — labels `channel` value
    contact_outcome: Optional[str] = None   # enum per D2; replaces free-text outcome for new rows
    outcome_reason: Optional[str] = None    # nullable; required when contact_outcome in REASON_REQUIRED_OUTCOMES
    # P1 — draft lifecycle (migration 0045). status=None is read as ACTIVITY_STATUS_FINAL
    # (legacy rows + every other log_activity() call site that never adopts a draft).
    status: Optional[str] = None            # draft|final|None(=final)
    started_at: Optional[str] = None        # UTC ISO-8601; set when a draft session begins
    finalize_at: Optional[str] = None       # UTC ISO-8601; set when finalize() runs
    contact_duration_s: Optional[int] = None  # finalize_at - started_at seconds; manual entry wins
