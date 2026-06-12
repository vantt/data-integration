# Phase 04: Dashboard Relocation

> **Status:** DONE — verified live Metabase 2026-06-09
> **Owner:** Data Team
> **Estimated:** 1h (API ops + verify)
> **Depends:** Phase 02 + Phase 03
> **Blocks:** Phase 06

---

## Context Links

- Cấu trúc mục tiêu: [plan.md](./plan.md) §"Cấu trúc mục tiêu"
- Live dashboard list: live Metabase `127.0.0.1:3001`

## Overview

Move 13 dashboards về collection mới, áp suffix scope cho dashboard chưa có, merge 2 promotion dashboards trùng.

## Mapping moves

### Group A: Move sang Finance collection (NEW)

| ID | Dashboard | Hiện ở | Đích | Áp suffix? |
|:---|:---|:---|:---|:---|
| 34 | Finance P&L Dashboard | Executive (46) | Finance (NEW) | rename: `Finance P&L [All]` |
| 35 | Order Profitability [All] | Executive (46) | Finance (NEW) | đã có `[All]` |
| 36 | Product Profitability | Executive (46) | Finance (NEW) | rename: `Product Profitability [All]` |

### Group B: Move sang Analytics collection (NEW)

| ID | Dashboard | Hiện ở | Đích | Áp suffix? |
|:---|:---|:---|:---|:---|
| 33 | Channel Profitability Monthly | Executive (46) | Analytics (NEW) | rename: `Channel Profitability Monthly [Cross]` |
| 15 | Customer Intelligence Monthly | Marketing & Customers (52) | Analytics (NEW) | rename: `Customer Intelligence Monthly [Cross]` |
| (id?) | Product Performance | Periodic Reviews (49) | Analytics (NEW) | rename: `Product Performance [Cross]` |
| (id?) | Shopee Channel Economics | Periodic Reviews (49) | Analytics (NEW) | rename: `Shopee Channel Economics [Cross]` |

### Group C: Move sang Operations sub mới

| ID | Dashboard | Hiện ở | Đích | Áp suffix? |
|:---|:---|:---|:---|:---|
| 40 | Ingestion Health Monitor | Daily Monitoring (48) | Data Platform (NEW sub) | đã OK |
| 28 | Logistics Operations Center | Daily Monitoring (48) | Logistics (NEW sub) | rename: `Logistics Operations Center [All]` |

### Group D: Flatten 3 sub-1-board lên parent

| Dashboard ID | Hiện ở | Đích | Suffix |
|:---|:---|:---|:---|
| (Promotion Analysis [Retail]) | Retail Operations (59) | **Marketing & Customers (52) — merge với 29** | xem Group E |
| US CrossBorder Daily [US] | CrossBorder Operations (61) | Operations root (47) | đã có `[US]` |
| Order Detail | Order Management (57) | Daily Monitoring (48) | rename: `Order Detail [Retail]` |

### Group E: MERGE 2 Promotion dashboards (decision needed)

Hiện có:
- ID 29 `Promotion & Discount Analysis` ở Marketing & Customers (52) — mixed scope
- ID (?) `Promotion Analysis [Retail]` ở Retail Operations (59) — retail thuần

**Cùng audience (Marketing/Sales Ops), cùng purpose (promotion analysis), khác scope.**

Đề xuất: **Giữ `Promotion Analysis [Retail]` (ID retail), archive `Promotion & Discount Analysis` (ID 29 mixed)** — vi phạm scope rule.

Move `Promotion Analysis [Retail]` từ Retail Operations sang Marketing & Customers (52). Sau đó xoá Retail Operations.

### Group F: Áp suffix cho dashboard chưa có

Quét live → các dashboard sau đang **thiếu suffix**:

| ID | Hiện tại | Rename thành |
|:---|:---|:---|
| 14 | Customer Retention & Lifecycle | `Customer Retention & Lifecycle [Retail]` |
| 13 | Marketing Monthly Analysis | `Marketing Monthly Analysis [Retail]` |
| 37 | Marketing ROI | `Marketing ROI [Retail]` |
| 31 | Sales Monthly Business Review | `Sales Monthly Business Review [All]` |
| 26 | Order Listing | `Order Listing [Retail]` |
| 27 | Social Commerce Operations | `Social Commerce Operations [Retail]` |
| (id?) | Sales Ops Weekly Review | `Sales Ops Weekly Review [Retail]` |
| (id?) | Sales Ops Monthly Summary | `Sales Ops Monthly Summary [Retail]` |

(Cần query Periodic Reviews lấy id)

## Implementation Steps

### Step 0: Pre-flight check — capture all IDs

```bash
# Get fresh dashboard list per collection (post Phase 02 archive)
for cid in 46 52 47 48 49 60 NEW_FINANCE_ID NEW_ANALYTICS_ID NEW_LOGISTICS_ID NEW_DATA_PLATFORM_ID; do
  echo "=== Collection $cid ==="
  curl -s -H "x-api-key: $METABASE_API_KEY" \
    "$METABASE_URL/api/collection/$cid/items?models=dashboard&archived=false" \
    | node -e 'let d="";process.stdin.on("data",c=>d+=c).on("end",()=>{(JSON.parse(d).data||[]).forEach(x=>console.log(x.id+" | "+x.name))})'
done
```

Save output to `current_state_phase4.txt`.

### Step 1: Move dashboards (Group A → E)

```bash
# Helper: move dashboard to collection (and optionally rename)
move_dashboard() {
  local id="$1" target_cid="$2" new_name="$3"
  local payload
  if [ -n "$new_name" ]; then
    payload=$(jq -n --arg n "$new_name" --argjson c "$target_cid" '{collection_id:$c, name:$n}')
  else
    payload=$(jq -n --argjson c "$target_cid" '{collection_id:$c}')
  fi
  curl -X PUT -H "x-api-key: $METABASE_API_KEY" \
    -H "Content-Type: application/json" \
    -d "$payload" \
    "$METABASE_URL/api/dashboard/$id"
}

FINANCE_ID=$(cat new_collection_ids.txt | grep ^Finance | cut -d= -f2)
ANALYTICS_ID=$(cat new_collection_ids.txt | grep ^Analytics | cut -d= -f2)
LOGISTICS_ID=$(cat new_collection_ids.txt | grep ^Logistics | cut -d= -f2)
DATAPLATFORM_ID=$(cat new_collection_ids.txt | grep ^DataPlatform | cut -d= -f2)

# Group A: Finance
move_dashboard 34 $FINANCE_ID "Finance P&L [All]"
move_dashboard 35 $FINANCE_ID ""  # already named [All]
move_dashboard 36 $FINANCE_ID "Product Profitability [All]"

# Group B: Analytics
move_dashboard 33 $ANALYTICS_ID "Channel Profitability Monthly [Cross]"
move_dashboard 15 $ANALYTICS_ID "Customer Intelligence Monthly [Cross]"
# (Product Performance + Shopee Channel — fill IDs from Step 0)
move_dashboard PRODUCT_PERF_ID $ANALYTICS_ID "Product Performance [Cross]"
move_dashboard SHOPEE_ECON_ID $ANALYTICS_ID "Shopee Channel Economics [Cross]"

# Group C: Operations subs
move_dashboard 40 $DATAPLATFORM_ID ""
move_dashboard 28 $LOGISTICS_ID "Logistics Operations Center [All]"

# Group D: Flatten
# US CrossBorder → root Operations (id 47)
move_dashboard US_CROSSBORDER_ID 47 ""
# Order Detail → Daily Monitoring (id 48)
move_dashboard ORDER_DETAIL_ID 48 "Order Detail [Retail]"
# Promotion Analysis [Retail] → Marketing & Customers (52)
move_dashboard PROMOTION_RETAIL_ID 52 ""
```

### Step 2: Merge promotion — archive duplicate

```bash
# Archive Promotion & Discount Analysis (ID 29, mixed scope)
curl -X PUT -H "x-api-key: $METABASE_API_KEY" \
  -d '{"archived": true}' \
  "$METABASE_URL/api/dashboard/29"
```

### Step 3: Áp suffix cho Group F (rename only)

```bash
# Helper: rename only (preserve collection)
rename_dashboard() {
  curl -X PUT -H "x-api-key: $METABASE_API_KEY" \
    -H "Content-Type: application/json" \
    -d "$(jq -n --arg n "$2" '{name:$n}')" \
    "$METABASE_URL/api/dashboard/$1"
}

rename_dashboard 14 "Customer Retention & Lifecycle [Retail]"
rename_dashboard 13 "Marketing Monthly Analysis [Retail]"
rename_dashboard 37 "Marketing ROI [Retail]"
rename_dashboard 31 "Sales Monthly Business Review [All]"
rename_dashboard 26 "Order Listing [Retail]"
rename_dashboard 27 "Social Commerce Operations [Retail]"
rename_dashboard SALES_OPS_WEEKLY_ID "Sales Ops Weekly Review [Retail]"
rename_dashboard SALES_OPS_MONTHLY_ID "Sales Ops Monthly Summary [Retail]"
```

### Step 4: Delete 3 empty sub-collections

```bash
# After moves, these should be empty:
for cid in 57 59 61; do
  # Verify empty first
  count=$(curl -s -H "x-api-key: $METABASE_API_KEY" \
    "$METABASE_URL/api/collection/$cid/items?models=dashboard&archived=false" \
    | node -e 'let d="";process.stdin.on("data",c=>d+=c).on("end",()=>{console.log((JSON.parse(d).data||[]).length)})')
  if [ "$count" = "0" ]; then
    curl -X PUT -H "x-api-key: $METABASE_API_KEY" \
      -d '{"archived": true}' \
      "$METABASE_URL/api/collection/$cid"
    echo "Archived collection $cid"
  else
    echo "WARNING: Collection $cid still has $count dashboards — skip archive"
  fi
done
```

### Step 5: Add description for every moved dashboard

Template:
```
Audience: <role>. Scope: <suffix>. Câu hỏi: <main question>.
```

Cho mỗi dashboard, set description qua API (xem Phase 02 §Step 3 example).

### Step 6: Verify final tree

```bash
# Expected: 29 dashboards across 9 collections (6 top-level visible + 4 Operations subs)
curl -s -H "x-api-key: $METABASE_API_KEY" \
  "$METABASE_URL/api/collection/tree?tree=true&exclude-archived=true" \
  | <same parse script as phase 03>
```

## Todo List

- [x] Step 0: Capture current state with IDs
- [x] Step 1: Execute move operations (Finance, Analytics, Operations subs)
- [x] Step 2: Archive duplicate Promotion (ID 29)
- [x] Step 3: Execute rename operations (Group F — scope suffixes)
- [x] Step 4: Archive empty sub-collections (Order Management archived per commit 524e1e1)
- [x] Step 5: Set description cho dashboard relocated
- [x] Step 6: Verify final tree matches target
- [x] Step 7: Update task tracking

## Success Criteria

- [ ] Finance collection có 3 dashboards (P&L, Order Profit, Product Profit) — sẵn sàng nhận 5 new từ Phase 05
- [ ] Analytics có 4 dashboards (Customer Intel, Channel Profit, Product Perf, Shopee Econ)
- [ ] Operations > Data Platform có 1 (Ingestion Health) — accept để chờ thêm
- [ ] Operations > Logistics có 1 (Logistics Ops) — accept
- [ ] Operations > Daily Monitoring có 4-5 board RETAIL ONLY (không còn Ingestion/Logistics)
- [ ] 0 sub-collection có 1 dashboard ngoại trừ Logistics/Data Platform (mới, accept)
- [ ] 100% dashboards có suffix scope
- [ ] 100% dashboards có description

## Risk Assessment

| Risk | Mitigation |
|:---|:---|
| Move sai collection ID → dashboard mất tích | Step 0 capture IDs, dry-run với 1 dashboard test trước |
| User vào Slack báo "dashboard biến mất" | Phase 02 Lark notification đã giải thích; thêm 1 message khi xong Phase 04 |
| API rate limit khi gọi PUT loạt | Sleep 1s giữa mỗi call |
| `Promotion & Discount Analysis` (29) thực sự có user dùng | Check view_count trước khi archive, nếu > 50 escalate |

## Next Steps

→ Phase 05: Plan 5 new Finance dashboards
→ Phase 06: Update 5 docs với cấu trúc mới
