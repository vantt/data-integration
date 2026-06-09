# Handoff: Order Listing [All] Dashboard Bug Fixes

**Date:** 2026-06-07 | **Branch:** main | **Project:** D:\vantt\app\data-integration

---

## Context

Dashboard: **Metabase dashboard/26 — "Order Listing [All]"**
Blueprint: `docs/analytics-handbook/blueprints/order_listing.md`
Purpose: Reconciliation tool — compare BI order counts and revenue against Sapo Admin. `primary_scope: none` (shows ALL orders including CANCELLED, B2B, all channels).

**Metabase:** `http://127.0.0.1:3001` | API key in `.env.local` as `METABASE_API_KEY`
**Deploy cmd:** `set -a && source .env.local && node .skills/metabase-automation/scripts/deploy_from_markdown.js docs/analytics-handbook/blueprints/order_listing.md`

---

## Fixes Done in This Session (all committed, deployed)

| Commit | Fix |
|--------|-----|
| `d7bd3bb` | scope → none, title → "Order Listing [All]", removed all scope_sales filters |
| `3d28b87` | Deploy script: suppress false-positive "filter not mapped" warning for hardcoded-date cards |
| `7e489f8` | Cycle-indicator SQL: Today→"Hôm nay: DD/MM", Yesterday→"Hôm qua: DD/MM", By Date→"Ngày: {{date}}" |
| `cc704f0` | Revenue KPIs: add `AND status NOT IN ('CANCELLED', 'Voided')` — Sapo keeps non-zero amounts on cancelled orders |

### Revenue cards fixed (all 3 tabs × 4 cards = 12 updates)
Cards: **Net Revenue, Total Collected, Gross Revenue, Total Discount**  
Card IDs Today: 818, 819, 820, 821 | Yesterday: 830, 831, 832, 833 | By Date: 842, 843, 844, 845

### Cards intentionally NOT filtered by status
- **Total Orders** (817/829/841): COUNT all including CANCELLED — for order-count reconciliation
- **Cancelled Orders** (822/834/846): `status = 'CANCELLED'` — dedicated counter
- **Order Detail List** (828/840/852): shows all rows
- **Distribution cards** (Orders by Status, Payment Status, Channel): show full breakdown

---

## Current Dashboard State (verified)

| Tab | Rendering | Cycle-indicator | Revenue KPIs | Notes |
|-----|-----------|----------------|--------------|-------|
| Today | ✅ works | "Hôm nay: DD/MM/YYYY" | Exclude CANCELLED ✅ | Uses `current_date` hardcoded, no `{{date}}` |
| Yesterday | ✅ works | "Hôm qua: DD/MM/YYYY" | Exclude CANCELLED ✅ | Hardcoded `current_date - 1 day` |
| By Date | ✅ works | "Ngày: DD/MM/YYYY" | Exclude CANCELLED ✅ | Uses `{{date}}` wired to dashboard filter |

---

## Key Technical Notes

### Why Today tab uses `current_date`, not `{{date}}`
Dashboard has one `date/single` parameter with `default: "today"`. Today/Yesterday tabs use hardcoded predicates; only By Date tab uses `{{date}}` template tag wired via `parameter_mappings`. Do NOT add `{{date}}` to Today/Yesterday cards — it will break rendering (no parameter mapping).

### Why revenue uses explicit status filter, not `scope_sales`
`scope_sales = is_sales_channel AND status NOT IN ('CANCELLED', 'Voided')`. The reconciliation dashboard needs all channels → can't use `scope_sales`. Use explicit `AND status NOT IN ('CANCELLED', 'Voided')` on revenue-aggregate cards only.

### Sapo behaviour
Sapo does NOT zero `total_amount` / `total_collected` when an order is cancelled. `fact_orders` inherits the face value. Revenue SUM must filter by status.

---

## Investigation Status (2026-06-09)

Items 1–4 verified addressed in blueprint SQL (agent scan 2026-06-09):

| # | Card | Status |
|---|------|--------|
| 1 | Returns (823/835/847) | ✅ SQL found in blueprint — uses LEFT JOIN to fact_order_returns, returns 0 correctly |
| 2 | Flagged Orders (827/839/851) | ✅ Anomaly detection SQL present in blueprint |
| 3 | Orders by Channel (826/838/850) | ✅ JOINs dim_channels.channel_name — displays names |
| 4 | Order Detail List (828/840/852) | ✅ All columns + order link in blueprint |
| 5 | DoD arrows on KPI scalars | ⚠️ Previous column wiring not found in blueprint — needs investigation |
| 6 | By Date "Chu kỳ báo cáo" (1937) | ✅ Uses {{date}} + parameter_mappings per blueprint |
| 7 | Data Freshness (1088/1089/1090) | ⚠️ Cards not found/verified in blueprint — needs investigation |

**Remaining:** Items 5 (DoD arrows) and 7 (Data Freshness cards 1088–1090) not confirmed in blueprint. Investigate live cards directly via API.

---

## Files Modified This Session

- `docs/analytics-handbook/blueprints/order_listing.md` — blueprint (source of truth)
- `.skills/metabase-automation/scripts/deploy_from_markdown.js` — deploy script fix
- `.skills/data-pipeline/references/lessons-learned.md` — L112–L115

---

## How to Check a Card's SQL

```bash
API_KEY="mb_buAQN9X7jRNYeum74PRgIJIirdmXM9hy2IDLDJtAmmA="
curl -s -H "x-api-key: $API_KEY" http://127.0.0.1:3001/api/card/<ID> | python3 -c "
import json,sys; d=json.load(sys.stdin)
stages=d.get('dataset_query',{}).get('stages',[])
print(stages[0].get('native','') if stages else '')
"
```

## How to Re-Deploy Blueprint

```bash
cd D:/vantt/app/data-integration
set -a && source .env.local
node .skills/metabase-automation/scripts/deploy_from_markdown.js docs/analytics-handbook/blueprints/order_listing.md
```
