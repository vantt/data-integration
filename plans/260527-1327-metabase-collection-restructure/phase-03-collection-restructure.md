# Phase 03: Collection Tree Restructure

> **Status:** Pending
> **Owner:** Data Team
> **Estimated:** 30 phút (API ops) + 30 phút verify
> **Depends:** Phase 02 (archive done)
> **Blocks:** Phase 04

---

## Context Links

- Audit: `plans/reports/audit-260527-1202-metabase-collection-tree.md` §5
- P&L driver: [phase-01](./phase-01-data-scan-discovery.md)
- Doc gốc: `docs/analytics-handbook/collection_registry.yml`

## Overview

Tạo / xoá collection để khớp cấu trúc mục tiêu 6 top-level. Không di chuyển dashboard ở phase này (đó là Phase 04).

## Cấu trúc trước vs sau

### Trước (current live)

```
[7] Personal × 5
[2] Examples (sample)
[58] Tests
[46] Executive (10 boards)
[52] Marketing & Customers (9 boards)
[47] Operations (0 boards root)
    [60] B2B Operations
    [61] CrossBorder Operations  ← 1 board
    [48] Daily Monitoring
    [57] Order Management        ← 1 board
    [49] Periodic Reviews
    [59] Retail Operations       ← 1 board
```

### Sau

```
[NEW] 📍 Start Here              ← onboarding
[46]  Executive (trimmed)
[NEW] Finance                    ← P&L domain
[52]  Marketing & Customers
[47]  Operations
        [60] B2B Operations
        [48] Daily Monitoring
        [NEW] Logistics          ← move Logistics Ops Center
        [NEW] Data Platform      ← move Ingestion Health
        [49] Periodic Reviews
        (US CrossBorder Daily flat ở root /47/)
        (Order Detail flat ở Daily Monitoring)
[NEW] Analytics                  ← Layer 3
[58]  Tests (move ra ngoài / hide)
```

## Operations cần làm

### Tạo 5 collection mới

| Order | Name | Parent | Color | Description |
|:---|:---|:---|:---|:---|
| 1 | `📍 Start Here` | root | #0EA5E9 (blue) | Hướng dẫn cho user mới |
| 2 | `Finance` | root | #DC2626 (red) | P&L, profitability, cost analysis. Audience: CFO/FP&A/Accounting. |
| 3 | `Analytics` | root | #6366F1 (indigo) | Cross-segment deep-dives. Audience: Analysts. |
| 4 | `Logistics` | Operations (47) | #84BB4C inherit | Shipping & delivery ops. Audience: Logistics Manager. |
| 5 | `Data Platform` | Operations (47) | #6B7280 (gray) | Pipeline health, ingestion monitoring. Audience: Data Engineering. |

### Xoá 3 sub-collection 1-board (sau khi move board ra ở Phase 04)

| ID | Name | Reason |
|:---|:---|:---|
| 59 | Retail Operations | Chỉ 1 board (Promotion Analysis) → flatten lên parent |
| 61 | CrossBorder Operations | Chỉ 1 board (US CrossBorder Daily) → flatten |
| 57 | Order Management | Chỉ 1 board (Order Detail) → move sang Daily Monitoring |

### Move Tests collection

`[58] Tests` — dev artifact, end-user không cần thấy. Lựa chọn:
- (A) Move vào personal collection của Data Team owner
- (B) Archive (set archived=true)
- **(C — chọn)** Rename → `🔒 Internal / Tests`, place under root nhưng restrict permission `Data Team only`

Quyết định: chọn (C) — preserve test artifacts but hide from regular user view via permission.

## Implementation Steps

### Step 1: Create 5 new collections

```bash
# Helper: create collection
create_collection() {
  local name="$1" parent_id="$2" color="$3" desc="$4"
  local payload
  payload=$(jq -n --arg n "$name" --arg p "$parent_id" --arg c "$color" --arg d "$desc" \
    '{name:$n, parent_id:($p|tonumber? // null), color:$c, description:$d}')
  curl -X POST -H "x-api-key: $METABASE_API_KEY" \
    -H "Content-Type: application/json" \
    -d "$payload" \
    "$METABASE_URL/api/collection"
}

# Create in order
create_collection "📍 Start Here" "" "#0EA5E9" "Hướng dẫn cho user mới — start here if you're new to Metabase."
create_collection "Finance" "" "#DC2626" "P&L, profitability, cost analysis. Audience: CFO/FP&A/Accounting."
create_collection "Analytics" "" "#6366F1" "Cross-segment deep-dives. Audience: Analysts. Layer 3 per report_segmentation guide."
create_collection "Logistics" "47" "#84BB4C" "Shipping & delivery ops. Audience: Logistics Manager."
create_collection "Data Platform" "47" "#6B7280" "Pipeline health, ingestion monitoring. Audience: Data Engineering."
```

**Capture new IDs** từ response → cập nhật vào `phase-04-dashboard-relocation.md` trước khi chạy phase đó.

### Step 2: Restrict Tests collection permission

```bash
# Rename
curl -X PUT -H "x-api-key: $METABASE_API_KEY" \
  -d '{"name": "🔒 Internal / Tests"}' \
  "$METABASE_URL/api/collection/58"

# Restrict: only admin group can read
# Get current graph
curl -s -H "x-api-key: $METABASE_API_KEY" \
  "$METABASE_URL/api/collection/graph" > /tmp/coll_graph.json

# Manual edit /tmp/coll_graph.json: set group 1 (All Users) = "none" for collection 58
# Then PUT back:
curl -X PUT -H "x-api-key: $METABASE_API_KEY" \
  -H "Content-Type: application/json" \
  -d @/tmp/coll_graph.json \
  "$METABASE_URL/api/collection/graph"
```

### Step 3: Create "Welcome" dashboard trong Start Here

Minimal markdown card explaining structure (text card, no SQL needed):

```bash
# Create empty dashboard first
curl -X POST -H "x-api-key: $METABASE_API_KEY" \
  -d '{"name":"Welcome to ChợPulse BI", "collection_id":<START_HERE_ID>, "description":"Audience: All users. Câu hỏi: Tôi nên mở folder nào?"}' \
  "$METABASE_URL/api/dashboard"

# Then add text-only dashcard with content explaining 6 collections
# (Use Metabase UI for text card quickly, or API with dashcards endpoint)
```

Text card content (paste into UI):

```markdown
# ChợPulse BI — Where do I go?

| Role | Collection |
|:---|:---|
| 🏢 CEO / Founder | **Executive** |
| 💰 CFO / Accounting / FP&A | **Finance** |
| 📣 Marketing / CS | **Marketing & Customers** |
| 🏪 Store Manager / Sales Ops | **Operations > Daily Monitoring** or **Periodic Reviews** |
| 🤝 B2B Account Manager | **Operations > B2B Operations** |
| 📊 Analyst / Research | **Analytics** |
| 🚚 Logistics Manager | **Operations > Logistics** |
| 🛠️ Data Engineer | **Operations > Data Platform** |

**Naming convention:** Every dashboard has a scope suffix:
- `[All]` = all sales channels (CEO view)
- `[Retail]` = retail only (Marketing/CS/Store view)
- `[B2B]` = wholesale/partner only
- `[Cross]` = cross-segment comparison
- `[US]` = US CrossBorder fulfillment

See `docs/analytics-handbook/guides/report_segmentation.md` for full guide.
```

### Step 4: Verify

```bash
curl -s -H "x-api-key: $METABASE_API_KEY" "$METABASE_URL/api/collection/tree?tree=true" \
  | node -e '
let d="";process.stdin.on("data",c=>d+=c).on("end",()=>{
  function walk(items,depth=0){
    for (const c of items) {
      if (c.personal_owner_id||c.is_sample) continue;
      console.log("  ".repeat(depth)+"["+c.id+"] "+c.name);
      if (c.children) walk(c.children,depth+1);
    }
  }
  walk(JSON.parse(d));
})'
```

Expected output: 6 top-level (Start Here, Executive, Finance, Marketing & Customers, Operations, Analytics) + Tests (renamed).

## Todo List

- [ ] Step 1a: Create `📍 Start Here` collection
- [ ] Step 1b: Create `Finance` collection
- [ ] Step 1c: Create `Analytics` collection
- [ ] Step 1d: Create `Operations > Logistics` sub
- [ ] Step 1e: Create `Operations > Data Platform` sub
- [ ] Step 1f: Capture all new IDs vào file `new_collection_ids.txt`
- [ ] Step 2: Rename Tests + restrict permission
- [ ] Step 3: Create Welcome dashboard + text card
- [ ] Step 4: Verify tree post-state

## Success Criteria

- [ ] 6 top-level collection (loại Tests và Personal) hiển thị đúng thứ tự
- [ ] 5 sub-collection trong Operations (B2B, Daily Monitoring, Logistics, Data Platform, Periodic Reviews)
- [ ] Welcome dashboard tồn tại với text card explanation
- [ ] Tests collection vẫn tồn tại nhưng non-admin không thấy

## Risk Assessment

| Risk | Mitigation |
|:---|:---|
| Tạo collection xong nhưng quên save ID → phase 04 không biết move vào đâu | Step 1f bắt buộc, save vào file |
| Color hex không match Metabase palette | Test 1 cái trước, screenshot user confirm |
| Permission graph mis-edit → user mất quyền | Backup graph trước, validate JSON trước PUT |

## Next Steps

→ Phase 04: relocate 10+ dashboards vào homes mới
