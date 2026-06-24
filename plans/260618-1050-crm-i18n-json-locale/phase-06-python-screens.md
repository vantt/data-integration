# Phase 6 — Python Screen Files Migration

**Status:** Todo  
**Effort:** ~1h  
**Depends on:** Phase 1 (i18n.py)

## Overview

~20 hardcoded Vietnamese strings across 6 screen files — mostly error messages in `HTMLResponse` / `HTTPException`, plus geo region labels in `screen_customer_360.py`.

## Files and changes

### `screen_customer_360.py`

**Geo region labels** — `_geo_region()` returns display strings:
```python
# Before
def _geo_region(province: Optional[str]) -> str:
    if province in _GEO_HANOI:
        return "Hà Nội"
    if province in _GEO_MEKONG:
        return "Mekong"
    if province in _GEO_CENTRAL:
        return "Miền Trung"
    return "Khác"

# After
def _geo_region(province: Optional[str]) -> str:
    from adapters.inbound.web.i18n import t
    if not province:
        return ""
    if province in _GEO_HCMC:
        return t("geo.hcmc")
    if province in _GEO_HANOI:
        return t("geo.hanoi")
    if province in _GEO_MEKONG:
        return t("geo.mekong")
    if province in _GEO_CENTRAL:
        return t("geo.central")
    return t("geo.other")
```

Note: `_GEO_HCMC`, `_GEO_HANOI`, etc. sets are **input matchers** (province name variants from DB) — do NOT translate those, only translate the output label.

**Error responses:**
```python
# Before
return HTMLResponse("Không tìm thấy khách hàng", status_code=404)

# After
return HTMLResponse(t("error.customer_not_found"), status_code=404)
```

Apply to both 404 occurrences in this file.

---

### `screen_inbox.py`

```python
# 404
return HTMLResponse("Không tìm thấy hội thoại", status_code=404)
→ return HTMLResponse(t("error.conv_not_found"), status_code=404)

# Search hint (HTMX fragment)
return HTMLResponse('<div class="text-muted">Nhập tên hoặc SĐT để tìm...</div>')
→ return HTMLResponse(f'<div class="text-muted">{t("inbox.search_hint")}</div>')
```

---

### `screen_management.py`

```python
return HTMLResponse("Segment không tìm thấy", status_code=404)
→ return HTMLResponse(t("error.segment_not_found"), status_code=404)

return HTMLResponse("Chiến dịch không tìm thấy", status_code=404)
→ return HTMLResponse(t("error.campaign_not_found"), status_code=404)

return HTMLResponse("Không tìm thấy candidate", status_code=404)
→ return HTMLResponse(t("error.candidate_not_found"), status_code=404)

return HTMLResponse("xác nhận bắt buộc", status_code=400)
→ return HTMLResponse(t("error.confirm_required"), status_code=400)
```

---

### `screen_modals.py`

```python
raise HTTPException(status_code=500, detail=f"Lỗi tạo khách hàng: {exc}")
→ raise HTTPException(status_code=500, detail=f"{t('error.create_failed')}: {exc}")
```

---

### `screen_modals_party.py`

```python
return HTMLResponse("Không tìm thấy khách hàng", status_code=404)
→ return HTMLResponse(t("error.customer_not_found"), status_code=404)

return HTMLResponse("Không tìm thấy", status_code=404)
→ return HTMLResponse(t("error.not_found"), status_code=404)

return HTMLResponse("Không tìm thấy kênh liên lạc", status_code=404)
→ return HTMLResponse(t("error.contact_not_found"), status_code=404)

return HTMLResponse(f"Lỗi lưu tags: {exc}", status_code=500)
→ return HTMLResponse(f"{t('error.save_tags_failed')}: {exc}", status_code=500)
```

---

### `screen_worklist.py` + `screen_customer_list.py`

Check for any missed Vietnamese strings (32 total found across screen_*.py — most covered above).

## Import pattern

All screen files use local import inside function body to avoid circular at module load:

```python
from adapters.inbound.web.i18n import t
```

This is safe — `t()` reads from ContextVar which is set by middleware before handlers run.

## Add missing error key

Add `"error.not_found"` to locale files (generic fallback used in `screen_modals_party.py`):
```json
"error": {
  "not_found": "Không tìm thấy"   // vi
  "not_found": "Not found"          // en
}
```

## Verification

- Hit `/customers/nonexistent` → 404 response in correct language per cookie
- Search hint in inbox renders in correct language
- Geo region labels on C360 sidebar switch with language toggle
