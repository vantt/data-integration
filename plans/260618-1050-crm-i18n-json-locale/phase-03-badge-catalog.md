# Phase 3 — badge_catalog.py Migration

**Status:** Todo  
**Effort:** ~30min  
**Depends on:** Phase 1 (i18n.py), Phase 2 (locale files)

## Overview

`hint` field hiện là Vietnamese string hardcode. Đổi thành i18n key; `bdg_tip_filter` tự gọi `t()` — **templates không cần thay đổi**.

## Strategy

`badge_catalog` biết domain và key của mỗi badge → có thể tự construct i18n key:
```
domain="order_status", key="completed" → "badge.order_status.completed"
```

Thay vì đổi từng `hint` string trong catalog, ta thay đổi **hai hàm lookup** để auto-construct key và gọi `t()`.

## Changes to `badge_catalog.py`

### 1. Update `BadgeDef.hint` comment

```python
class BadgeDef(NamedTuple):
    css_mod: str  # 'good' | 'warn' | 'bad' | 'accent' | ''
    hint: str     # i18n key suffix, e.g. "completed" → resolved via badge.<domain>.<key>
```

Thực ra không cần đổi gì trong `BadgeDef` hay `_CATALOG` — hint string hiện tại trở thành dead data sau khi `bdg_hint` được override. Hoặc đơn giản hơn: xóa `hint` field ra khỏi catalog và để `bdg_hint` tự build key.

**Quyết định**: giữ nguyên `_CATALOG` (backward compat, không break), chỉ thay `bdg_hint`.

### 2. Replace `bdg_hint` function

```python
# Before
def bdg_hint(domain: str, key: str) -> str:
    """Vietnamese tooltip text for domain+key."""
    return bdg_lookup(domain, key).hint

# After
def bdg_hint(domain: str, key: str) -> str:
    """Localized tooltip text for domain+key via i18n."""
    from adapters.inbound.web.i18n import t  # local import avoids circular
    i18n_key = f"badge.{domain}.{(key or '').strip()}"
    result = t(i18n_key)
    # t() returns the key itself if not found — fall back to catalog hint
    if result == i18n_key:
        return bdg_lookup(domain, key).hint
    return result
```

### 3. `bdg_tip_filter` in `format_helpers.py` — no change needed

```python
def bdg_tip_filter(key: str, domain: str) -> str:
    return bdg_hint(domain, key)  # already calls updated bdg_hint
```

## Verification

```python
# With lang=vi
assert bdg_hint("order_status", "completed") == "Đơn đã hoàn tất"

# With lang=en  
assert bdg_hint("order_status", "completed") == "Order completed"

# Unknown key → falls back to catalog hint (Vietnamese)
assert bdg_hint("order_status", "unknown_key") == ""
```

## Notes

- Local import `from adapters.inbound.web.i18n import t` avoids circular import (i18n doesn't import badge_catalog)
- Fallback to `catalog.hint` ensures zero regression if a badge key is missing from locale files
- `complete` and `completed` are both in catalog as aliases → both need entries in locale JSON (or share same key via alias logic — simplest: both have entries)
