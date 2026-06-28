"""hug.py — domain entities for the Hug token lifecycle.

HugToken  — physical sticker tracking from mint → bind → push.
HugCampaign — campaign configuration record (core fields only).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class HugToken:
    """Domain representation of a hug_token row.

    token is the only required field (the PK).  All other fields may be absent
    depending on lifecycle stage (printed tokens have no order_code/bound_at).
    """

    token: str
    customer_id: Optional[str] = None
    op_type: Optional[str] = None
    order_code: Optional[str] = None
    channel: Optional[str] = None
    ship_date: Optional[str] = None
    sku: Optional[str] = None
    campaign_hint: Optional[str] = None
    is_gift: int = 0
    status: str = "printed"
    batch_id: Optional[str] = None
    pushed_at: Optional[str] = None
    created_at: Optional[str] = None
    bound_at: Optional[str] = None


@dataclass
class HugCampaign:
    """Domain representation of a crm_hug_campaign row (core fields).

    Optional fields default to None; callers set what they know at creation time.
    """

    campaign_id: str
    name: str
    status: str = "active"
    destination_type: Optional[str] = None
    destination_url: Optional[str] = None
    targeting: Optional[str] = None   # JSON string stored in DB
    offer: Optional[str] = None       # maps to offer_ref column in the schema
