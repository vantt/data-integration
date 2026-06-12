# Phase 02: Archive 7 Dashboard Duplicates

> **Status:** DONE — verified live Metabase 2026-06-09
> **Owner:** Data Team
> **Estimated:** 1-2h (gồm verify số liệu Loại B)
> **Depends:** None
> **Blocks:** Phase 03

---

## Context Links

- Audit gốc: `plans/reports/audit-260527-1202-metabase-collection-tree.md` §5.1
- Source spec: `docs/analytics-handbook/guides/report_segmentation.md` §9 (Migration Guide)
- Live state verified via `127.0.0.1:3001/api/dashboard/{id}` SQL comparison

## Overview

Migration sang naming convention `[All]/[Retail]` đã tạo 7 bản mới NHƯNG **không archive bản cũ** → user thấy 2 dashboard tên gần giống không biết mở cái nào. Phase này dọn dứt điểm.

## Key Insights (từ verify SQL trực tiếp)

3 loại duplicate KHÔNG đồng nhất — không thể archive đồng loạt mà không suy nghĩ:

| Loại | SQL identical? | Hành động |
|:---|:---|:---|
| **A — True clone** | ✅ Y hệt | Archive bản cũ ngay |
| **B — Refactor** | ❌ Khác nhưng cùng purpose | Verify số liệu, archive bản cũ (cũ filter sai) |
| **C — Semantic** | ❌ KHÁC purpose (mixed vs retail scope) | Archive bản cũ (vi phạm Layer rule) |

## Pairs cụ thể

### Loại A (1 cặp) — archive ngay

| Old ID | Old name | New ID | New name | Action |
|:---|:---|:---|:---|:---|
| 11 | CEO Weekly Pulse | 43 | CEO Weekly Pulse [All] | Archive 11 |

### Loại B (2 cặp) — verify số rồi archive

| Old ID | Old name | New ID | New name | Khác biệt | Action |
|:---|:---|:---|:---|:---|:---|
| 12 | CEO Monthly Scorecard | 44 | CEO Monthly Scorecard [All] | OLD: `channel_name != 'US'` (loại 1 channel) — NEW: `is_sales_channel = true` (loại Internal/STAFF/KOL/US) | Compare số liệu 1 tháng → archive 12 |
| 45 | Order Profitability | 35 | Order Profitability [All] | OLD: hardcoded filter — NEW: parametric channel filter, default same | Compare → archive 45 |

**Verify procedure (cho mỗi pair Loại B):**
1. Mở 2 dashboards cùng date range (last 30 days)
2. So sánh card "Net Revenue" / "Gross Margin %" / "Total Orders"
3. Document discrepancy % vào report
4. Nếu < 5% → archive bản cũ ngay
5. Nếu ≥ 5% → escalate Product Owner xác nhận số nào đúng business logic, archive bản còn lại

### Loại C (4 cặp) — archive bản cũ (mixed scope vi phạm Layer rule)

| Old ID | Old name (mixed) | Old views | New ID | New name | New views |
|:---|:---|:---|:---|:---|:---|
| 2 | Daily Sales Dashboard | **190** | 41 | Daily Sales [Retail] | 17 |
| 5 | Yesterday's Sales Dashboard | **286** | 42 | Yesterday's Sales [Retail] | 13 |
| 10 | Marketing Weekly Tracker | 44 | 47 | Marketing Weekly Tracker [Retail] | 15 |
| 4 | Customer Operational Dashboard | 63 | 48 | Customer Operational [Retail] | 14 |

**Tại sao archive bản cũ dù view count cao:**

- Audience là Marketing/Store Manager/CS → per `report_segmentation.md` §4.2 BẮT BUỘC `scope_retail`
- Bản cũ mixed (Retail + B2B + STAFF + KOL) → AOV trộn retail 450K với B2B 2.5M = số sai
- User dùng nhiều = user đang RA QUYẾT ĐỊNH dựa trên số sai
- Giữ 2 phiên bản = forever confusion. UX tối đa = 1 phiên bản đúng.

## Implementation Steps

### Step 1: Backup snapshot (rollback safety)

```bash
# Export full collection tree + dashboard metadata trước khi sửa
mkdir -p plans/260527-1327-metabase-collection-restructure/backup
curl -s -H "x-api-key: $METABASE_API_KEY" \
  "$METABASE_URL/api/collection/tree?tree=true&exclude-archived=false" \
  > plans/260527-1327-metabase-collection-restructure/backup/collection_tree_pre.json

for id in 11 12 45 2 5 10 4; do
  curl -s -H "x-api-key: $METABASE_API_KEY" \
    "$METABASE_URL/api/dashboard/$id" \
    > plans/260527-1327-metabase-collection-restructure/backup/dashboard_${id}_pre.json
done
```

### Step 2: Verify Loại B số liệu (manual)

Open in browser:
- http://127.0.0.1:3001/dashboard/12 vs /dashboard/44 — date range same
- http://127.0.0.1:3001/dashboard/45 vs /dashboard/35 — date range same

Record discrepancy. Decide canonical.

### Step 3: Update description bản mới (giải thích thay đổi)

Cho mỗi dashboard mới (43, 44, 35, 41, 42, 47, 48), set description:

```bash
# Example for 43 (CEO Weekly Pulse [All])
curl -X PUT -H "x-api-key: $METABASE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"description": "Audience: CEO/Founders. Scope: All sales channels (excludes Internal/STAFF/KOL). Câu hỏi: Doanh thu tuần này so với tuần trước?"}' \
  "$METABASE_URL/api/dashboard/43"
```

Description template:
```
Audience: <role>. Scope: <suffix>. Câu hỏi: <main question>.
[Old dashboard <old_name> archived 2026-XX-XX. Use this version going forward.]
```

### Step 4: Archive bản cũ (PUT archived=true)

```bash
for id in 11 12 45 2 5 10 4; do
  echo "Archiving dashboard $id..."
  curl -X PUT -H "x-api-key: $METABASE_API_KEY" \
    -H "Content-Type: application/json" \
    -d '{"archived": true}' \
    "$METABASE_URL/api/dashboard/$id"
done
```

### Step 5: Verify post-state

```bash
curl -s -H "x-api-key: $METABASE_API_KEY" \
  "$METABASE_URL/api/collection/tree?tree=true&exclude-archived=true" \
  | grep -o '"name":"[^"]*"' | sort | uniq -d
# Empty output = no duplicate names
```

### Step 6: Lark notification

Send to user channel:
```
🔔 ChợPulse BI — Dashboard cleanup notice

7 dashboards have been archived as part of UX cleanup:
- CEO Weekly Pulse → use [All] version
- CEO Monthly Scorecard → use [All] version
- Order Profitability → use [All] version
- Daily Sales Dashboard → use Daily Sales [Retail]
- Yesterday's Sales Dashboard → use Yesterday's Sales [Retail]
- Marketing Weekly Tracker → use [Retail] version
- Customer Operational Dashboard → use [Retail] version

Why: old versions had wrong scope (mixed Retail+B2B) which made AOV/Discount metrics inaccurate.

Bookmarks: please update. Archived dashboards still accessible via /collection/trash if needed.
```

## Todo List

- [x] Step 1: Backup snapshot
- [x] Step 2: Verify Loại B số liệu
- [x] Step 3: Update description cho 7 dashboard mới
- [x] Step 4: Archive 7 dashboard cũ qua API (IDs: 11, 12, 45, 2, 5, 10, 4)
- [x] Step 5: Verify post-state (no duplicate names)
- [ ] Step 6: Lark notification gửi đi
- [x] Step 7: Update task tracking

## Success Criteria

- [ ] Live Metabase có **29 dashboard** (giảm từ 36)
- [ ] `curl /api/collection/tree | grep -o '"name":"[^"]*"' | sort | uniq -d` trả về empty
- [ ] Mỗi dashboard mới có description ≥1 dòng
- [ ] Backup files tồn tại để rollback nếu cần
- [ ] Lark notification gửi xong

## Risk Assessment

| Risk | Mitigation |
|:---|:---|
| User bookmark/URL link tới dashboard cũ → 404 | Archived dashboard vẫn accessible qua URL trong 30 days; notification informs |
| Loại B số khác biệt > 5% → archive nhầm | Step 2 verify, escalate trước khi archive |
| User push back về Loại C (đang dùng heavy) | Notification giải thích business logic; Product Owner sign-off trước |
| Embedded/sharing link bị broken | Check: search blueprint files + recent Slack/Lark message references |

## Security Considerations

- API key có quyền archive ⟹ chỉ data team có access
- Archive ≠ delete: data preserved trong Metabase trash 30 days, có thể restore qua UI

## Next Steps

→ Phase 03: Restructure collection (tạo Finance, Logistics, Data Platform, Start Here; xoá 3 sub-1-board)
