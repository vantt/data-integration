# Phase 02 — S14 Collect: Health Domain Chips + Context Text

**Depends on:** Phase 01 (health_domain tags seeded)

## Context

S14 collect region hiện show: Zalo, Email, Birthday, fix-invalid-contact, skin_type chip (Phase 06). Cần thêm 2 rows health. `skin_type` vẫn giữ — là health_domain='da' precursor, không xoá.

Cơ chế collect hiện tại: `script.data_gaps[]` drives which rows show; inline POST → `_s14_collect_row.html` fragment swap.

## Files to modify

- `crm/templates/call_cockpit.html` (hoặc `_s14_collect_region.html`) — thêm 2 row blocks
- `crm/templates/fragments/_s14_collect_row.html` — extend để handle `health_domain` chip type
- `crm/views/call_cockpit.py` — context builder: thêm health gap detection
- `crm/routes/customers.py` (hoặc `crm/views/inline_endpoints.py`) — thêm `POST /customers/{id}/tags/inline`

## Requirements

### Row 1 — Health domains (multi-chip select)

**Condition shown:** party chưa có bất kỳ `crm_party_tag` nào với `category='health_domain'`

```
• Lĩnh vực sức khỏe
  [Tim mạch] [Hô hấp] [Miễn dịch] [Xương khớp]
  [Tiêu hóa] [Thần kinh/Ngủ] [Năng lượng] [Da]
                                              [Lưu ✓]
```

Chips render từ `crm_tag WHERE category='health_domain' AND is_archived=false`, ordered by usage count desc.

**POST** `POST /customers/{id}/tags/inline`
```json
{ "tag_names": ["tim-mach", "ho-hap"], "category": "health_domain", "source": "crm_user" }
```
Server: lookup tag_id by name, upsert `crm_party_tag(party_id, tag_id, source='crm_user', tagged_by=current_user)`.

**Response:** `_s14_collect_row.html` với `saved=True` → swap thành `✓ Tim mạch, Hô hấp`

### Row 2 — Health context free text

**Condition shown:** `party.custom.health_context_raw` null hoặc rỗng

```
• Ghi chú sức khỏe  [huyết áp cao, hay mệt...    ] [+]
                     ↑ maxlength=200, placeholder gợi ý
```

**POST** `POST /customers/{id}/custom-field-inline` (endpoint đã có từ Phase 06)
```json
{ "field": "health_context_raw", "value": "huyết áp cao, hay mệt" }
```

**Response:** existing `_s14_collect_row.html` với `saved=True` (2s toast).

### Gap detection trong context builder

```python
# crm/views/call_cockpit.py — trong _build_collect_gaps()
health_domain_tags = [t for t in party_tags if t.category == 'health_domain']
if not health_domain_tags:
    gaps.append({"type": "health_domain", "label": "Lĩnh vực sức khỏe"})

if not party.custom.get("health_context_raw"):
    gaps.append({"type": "health_context", "label": "Ghi chú sức khỏe"})
```

### POST /customers/{id}/tags/inline (endpoint mới)

```python
@router.post("/customers/{party_id}/tags/inline")
def inline_tag_assign(party_id, body: InlineTagBody, user=Depends(current_user)):
    # Whitelist: chỉ chấp nhận category trong INLINE_ALLOWED_CATEGORIES
    INLINE_ALLOWED_CATEGORIES = {"health_domain", "health_concern"}
    tags = crm_tag.filter(name__in=body.tag_names, category=body.category)
    for tag in tags:
        crm_party_tag.upsert(party_id=party_id, tag_id=tag.id,
                              source="crm_user", tagged_by=user.id)
    return render_fragment("_s14_collect_row.html", saved=True, tags=tags)
```

Whitelist category tránh rep gán tùy tiện tag nhạy cảm (risk, vip_tier) từ S14.

## S14 spec update

Thêm vào `Implementation Notes (Phase XX)` trong `S14-call-mode-cockpit.md`:
- 2 collect rows mới: `health_domain` (multi-chip) và `health_context` (text)
- Endpoint mới: `POST /customers/{id}/tags/inline`
- Whitelist categories cho inline: `health_domain`, `health_concern`

## Validation

- S14 collect hiện health chip row khi party không có health_domain tags
- Click nhiều chips → highlight → [Lưu] → row swap "✓ Tim mạch, Hô hấp"
- Sau lưu, row ẩn (gap cleared, không re-render toàn panel)
- Text row hiện khi `health_context_raw` trống; sau POST → toast 2s → row ẩn
- `skin_type` row vẫn hoạt động bình thường (không regression)
- POST với category ngoài whitelist → 400 Bad Request
