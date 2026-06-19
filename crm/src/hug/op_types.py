"""Hug op_type metadata — shared label / print-badge definitions.

op_type is a mint-time batch property of a physical sticker: it records WHERE
the tem is applied (inside a parcel, on a loyalty card, on a flyer, …). It is
stored per hug_token row and is never embedded in the opaque token/QR.

Both the mint form (screen_hug_mint) and the QR label sheet (hug_qr_print) need
to render op_type for humans, so the single source of truth lives here.

Each op_type carries:
  - label : full Vietnamese name shown in the form + on the printed sheet header
  - code  : 1-char marker printed on every individual sticker (survives B&W
            printing and label cutting — the unambiguous fallback)
  - color : dot color for fast visual sorting of loose stickers (degrades
            gracefully to the code if printed in grayscale)
"""
from __future__ import annotations

# Ordered: the first key is the default selection in the mint form.
OP_TYPES: dict[str, dict[str, str]] = {
    "package_insert": {"label": "Trong kiện hàng (mặc định)", "code": "P", "color": "#2563eb"},
    "loyalty_card":   {"label": "Thẻ thành viên",             "code": "L", "color": "#16a34a"},
    "winback_flyer":  {"label": "Tờ rơi mời mua lại",         "code": "W", "color": "#d97706"},
    "receipt":        {"label": "Hóa đơn",                    "code": "R", "color": "#64748b"},
    "acquire":        {"label": "Phát lẻ / chưa gắn khách",   "code": "A", "color": "#9333ea"},
}

# Fallback for an unknown/legacy op_type so printing never crashes.
_UNKNOWN = {"label": "Không rõ", "code": "?", "color": "#475569"}


def op_meta(op_type: str | None) -> dict[str, str]:
    """Return {label, code, color} for an op_type, with a safe fallback."""
    return OP_TYPES.get(op_type or "", _UNKNOWN)


def op_label(op_type: str | None) -> str:
    """Full Vietnamese label for an op_type."""
    return op_meta(op_type)["label"]


# {op_type: vietnamese_label} — convenience map for the mint form <select>.
OP_LABELS: dict[str, str] = {k: v["label"] for k, v in OP_TYPES.items()}
