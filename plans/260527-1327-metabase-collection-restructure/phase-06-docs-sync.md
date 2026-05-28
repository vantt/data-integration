# Phase 06: Documentation Sync

> **Status:** Pending
> **Owner:** Data Team + docs-manager
> **Estimated:** 1-2h
> **Depends:** Phase 03 + 04 (live state đã đúng)
> **Blocks:** Phase 07

---

## Context Links

- 5 doc gốc cần update:
  1. `docs/analytics-handbook/collection_registry.yml`
  2. `docs/analytics-handbook/guides/collection_organization.md`
  3. `docs/analytics-handbook/guides/report_segmentation.md`
  4. `docs/analytics-handbook/AGENTS.md`
  5. `docs/decisions/009-collection-by-audience.md` (ADR-009)
- 30 blueprint files cần normalize header

## Overview

Đồng bộ 5 doc gốc + 30 blueprint headers với cấu trúc mới sau Phase 03/04. Quyết định cứng: **CÓ `Analytics` collection + CÓ `Finance` collection** (6 top-level).

## File 1: `collection_registry.yml`

### Replace nội dung

Cấu trúc mới full registry:

```yaml
collections:

  # ---------------------------------------------------------------------------
  # 📍 START HERE — Onboarding (NEW)
  # All users
  # ---------------------------------------------------------------------------
  - name: "📍 Start Here"
    description: "Onboarding cho user mới. Where do I go?"
    audience: [All]
    color: "#0EA5E9"
    dashboards:
      - Welcome to ChợPulse BI

  # ---------------------------------------------------------------------------
  # EXECUTIVE — "Công ty đang thế nào?"
  # CEO, Co-Founders, Board (strategic only)
  # ---------------------------------------------------------------------------
  - name: Executive
    description: "Strategic dashboards for leadership."
    audience: [CEO, Co-Founders, Board]
    color: "#7C3AED"
    dashboards:
      - "CEO Weekly Pulse [All]"
      - "CEO Monthly Scorecard [All]"
      - "Sales Monthly Business Review [All]"

  # ---------------------------------------------------------------------------
  # FINANCE — "Tiền của tôi đi đâu?" (NEW)
  # CFO, FP&A, Accounting Manager
  # ---------------------------------------------------------------------------
  - name: Finance
    description: "P&L, profitability, cost ledger, reconciliation."
    audience: [CFO, FP&A, Accounting Manager, Finance Director]
    color: "#DC2626"
    dashboards:
      - "Finance P&L [All]"
      - "Order Profitability [All]"
      - "Product Profitability [All]"
      # Roadmap (Phase 05):
      # - Cost Ledger Analyzer [All]
      # - Return Impact Analysis [All]
      # - Channel P&L Deep Dive [Cross]
      # - Product Cost-to-Margin Heatmap [Cross]
      # - Accounting Reconciliation Cockpit [Internal]

  # ---------------------------------------------------------------------------
  # MARKETING & CUSTOMERS — "Kênh/Khách thế nào?"
  # ---------------------------------------------------------------------------
  - name: Marketing & Customers
    description: "Channel performance, customer acquisition, retention, promotion."
    audience: [Marketing Manager, Brand Manager, CMO, Customer Success]
    color: "#F9A825"
    dashboards:
      - "Marketing Weekly Tracker [Retail]"
      - "Marketing Monthly Analysis [Retail]"
      - "Marketing ROI [Retail]"
      - "Customer Operational [Retail]"
      - "Customer Retention & Lifecycle [Retail]"
      - "Promotion Analysis [Retail]"

  # ---------------------------------------------------------------------------
  # OPERATIONS — "Hôm nay cần làm gì?"
  # ---------------------------------------------------------------------------
  - name: Operations
    description: "Daily/weekly operational dashboards by line of business."
    audience: [Store Managers, Sales Operators, B2B Account Manager, Logistics Manager, Data Engineering]
    color: "#84BB4C"
    dashboards:
      - "US CrossBorder Daily [US]"
    children:

      - name: Daily Monitoring
        description: "Real-time và yesterday's retail dashboards. Multiple times/day."
        audience: [Store Managers]
        dashboards:
          - "Daily Sales [Retail]"
          - "Yesterday's Sales [Retail]"
          - "Order Listing [Retail]"
          - "Order Detail [Retail]"
          - "Social Commerce Operations [Retail]"

      - name: Periodic Reviews
        description: "Weekly và monthly retail ops summaries."
        audience: [Sales Ops Lead]
        dashboards:
          - "Sales Ops Weekly Review [Retail]"
          - "Sales Ops Monthly Summary [Retail]"

      - name: B2B Operations
        description: "B2B sales tracking."
        audience: [B2B Account Manager]
        dashboards:
          - "B2B Daily Sales [B2B]"
          - "B2B Orders Tracking [B2B]"

      - name: Logistics  # NEW
        description: "Shipping & delivery operations."
        audience: [Logistics Manager]
        dashboards:
          - "Logistics Operations Center [All]"

      - name: Data Platform  # NEW
        description: "Pipeline health, ingestion monitoring."
        audience: [Data Engineering]
        dashboards:
          - Ingestion Health Monitor

  # ---------------------------------------------------------------------------
  # ANALYTICS — "So sánh segment / deep-dive?" (NEW, Layer 3)
  # Analysts, Leadership doing deep analysis
  # ---------------------------------------------------------------------------
  - name: Analytics
    description: "Cross-segment deep-dives, research-grade analysis (Layer 3)."
    audience: [Analyst, Leadership]
    color: "#6366F1"
    dashboards:
      - "Customer Intelligence Monthly [Cross]"
      - "Channel Profitability Monthly [Cross]"
      - "Product Performance [Cross]"
      - "Shopee Channel Economics [Cross]"
```

### Update LOOKUP TABLE phần dưới

```yaml
# | Audience                          | Collection Path                |
# |-----------------------------------|--------------------------------|
# | All (onboarding)                  | 📍 Start Here                  |
# | CEO / Board                       | Executive                      |
# | CFO / Accounting / FP&A           | Finance                        |
# | Marketing Manager / CMO           | Marketing & Customers          |
# | Customer Success                  | Marketing & Customers          |
# | Store Manager                     | Operations > Daily Monitoring  |
# | Sales Ops Lead                    | Operations > Periodic Reviews  |
# | B2B Account Manager               | Operations > B2B Operations    |
# | Logistics Manager                 | Operations > Logistics         |
# | Data Engineering                  | Operations > Data Platform     |
# | Analyst (cross-segment research)  | Analytics                      |
```

## File 2: `guides/collection_organization.md`

### Changes

1. **§3 Cấu trúc hiện tại** — replace ASCII tree với 6 top-level mới
2. **§3 table** — thêm Finance + Logistics + Data Platform + Start Here rows
3. **§6 "Khi nào cần thay đổi"** — thêm row "Đã tách 2026-05-27: Finance khỏi Executive khi P&L mart explode"
4. **Header date** → update to 2026-05-27

## File 3: `guides/report_segmentation.md`

### Changes

1. **§6 Collection Structure** — replace với tree mới (6 top-level)
2. **§9 Migration Guide** — đánh dấu DONE cho tất cả rows, archive guide này hoặc move sang historical section
3. **Header date** → 2026-05-27
4. Thêm note: "Analytics collection ✅ created 2026-05-27 (was proposed but missing previously)"

## File 4: `AGENTS.md`

### Changes

1. **Section "Collection Governance"** §"Collection Architecture (3 Collections)" → **"6 Collections"**
2. Update ASCII tree với 6 top-level
3. **§"Collection Placement Workflow"** decision table → thêm Finance + Logistics + Data Platform rows
4. **§"When to Split"** — thêm note "Finance + Logistics + Data Platform đã tách out 2026-05-27"

## File 5: `decisions/009-collection-by-audience.md`

### Changes

1. Status: Accepted (giữ nguyên)
2. Thêm section **"Amendments"** ở cuối:

```markdown
## Amendments

### 2026-05-27 — Expansion từ 3 lên 6 top-level

**Trigger:** Audit phát hiện drift + 3 P&L mart mới (`fact_order_economics`, `fact_order_costs`, `fact_order_returns`).

**Thay đổi:**
- Thêm `Finance` (CFO/FP&A audience — driven by P&L data explosion)
- Thêm `Analytics` (Layer 3 cross-segment, đã proposed nhưng chưa create)
- Thêm `📍 Start Here` (onboarding)
- Thêm 2 sub trong Operations: `Logistics` + `Data Platform`

**Nguyên tắc giữ nguyên:** Vẫn organize by audience. Cadence vẫn trong dashboard name.

**Drift root cause:** Không có archive policy khi migration → để 7 cặp duplicate tồn tại 1 tháng. Validation script sẽ chống tái phát (xem [phase-07](../../plans/260527-1327-metabase-collection-restructure/phase-07-validation-rollout.md)).
```

## File 6: Blueprint headers normalize (30 files)

### Standard format

```markdown
# 📘 Blueprint: <Dashboard Name>

**Playbook**: [Link](../playbooks/<name>.md)

> **Target Collection:** `<Collection Path>`
> **Role:** <Audience>
> **Archetype:** <Pattern>
> **Database:** <DB name>  # if non-default

## 📂 Collection: <Parent> > <Child>
```

### Cases cần fix

1. **Header style inconsistency:**
   - 2 files dùng `## Collection:` (no emoji): `ceo_weekly_pulse.md`, `sales_ops_weekly_review.md`, `sales_ops_monthly_summary.md`
   - Normalize hết về `## 📂 Collection:`

2. **Backtick path:**
   - `order_listing.md` dùng `` `Operations` > `Daily Monitoring` `` (2 backticks)
   - Normalize: `Operations > Daily Monitoring` (no backticks)

3. **Missing `> **Target Collection:**` header:**
   - ~20 blueprints không có quote line
   - Add line consistent với `## 📂 Collection:`

4. **Path updates do move:**
   - `finance_pl.md`: `Executive` → `Finance`
   - `order_profitability.md`, `order_profitability_all.md`: `Executive` → `Finance`
   - `product_profitability.md`: `Executive` → `Finance`
   - `channel_profitability_monthly.md`: `Executive` → `Analytics`
   - `customer_intelligence_monthly.md`: `Marketing & Customers` → `Analytics`
   - `product_performance.md`: `Operations > Periodic Reviews` → `Analytics`
   - `shopee_channel_economics.md`: `Operations > Periodic Reviews` → `Analytics`
   - `sales_promotion_analysis.md`: `Operations > Retail Operations` → `Marketing & Customers`
   - `customer_support_social_commerce.md`: `Operations > Daily Monitoring` → keep (correct now)
   - `ingestion_health.md`: `Operations > Daily Monitoring` → `Operations > Data Platform`
   - `logistics_operations.md`: `Operations > Daily Monitoring` → `Operations > Logistics`
   - `us_crossborder_operations.md`: `Operations > CrossBorder Operations` → `Operations`
   - `order_detail.md`: `Operations > Order Management` → `Operations > Daily Monitoring`

## Implementation Steps

### Step 1: Update `collection_registry.yml` (full replace)

Use Write tool với nội dung trên.

### Step 2: Edit 4 markdown docs

Targeted Edit operations for sections listed above. Không full rewrite — preserve untouched sections.

### Step 3: Bulk fix 30 blueprints

```bash
# Find files with old format
grep -rln "^## Collection:" docs/analytics-handbook/blueprints/ | while read f; do
  sed -i 's|^## Collection:|## 📂 Collection:|' "$f"
done

# Find files with backtick path
grep -rln "Operations\` > \`Daily Monitoring" docs/analytics-handbook/blueprints/
# Manual fix với Edit tool
```

For collection path updates, use Edit per file (13 files affected).

### Step 4: Verify blueprint↔registry alignment

```bash
# Should return 0 — no unregistered collection paths
grep -h "^## 📂 Collection:" docs/analytics-handbook/blueprints/*.md \
  | sort -u \
  | while read line; do
      path="${line#*: }"
      if ! grep -q "$path" docs/analytics-handbook/collection_registry.yml; then
        echo "DRIFT: $path"
      fi
    done
```

## Todo List

- [ ] Step 1: Write new `collection_registry.yml`
- [ ] Step 2a: Edit `collection_organization.md` §3 + §6
- [ ] Step 2b: Edit `report_segmentation.md` §6 + §9
- [ ] Step 2c: Edit `AGENTS.md` Collection Governance section
- [ ] Step 2d: Edit ADR-009 add Amendments
- [ ] Step 3a: Normalize 30 blueprint headers (sed for `## Collection:`)
- [ ] Step 3b: Fix 13 blueprint collection paths (per move table)
- [ ] Step 3c: Add `> **Target Collection:**` line to ~20 blueprints missing it
- [ ] Step 4: Run drift verification — must return 0

## Success Criteria

- [ ] 5 doc gốc nhất quán về Cấu trúc 6 top-level
- [ ] 30 blueprint files dùng cùng header format
- [ ] `grep` blueprint Collection paths khớp 100% với registry
- [ ] ADR-009 có ghi nhận amendment
- [ ] Mỗi doc có date update 2026-05-27

## Risk Assessment

| Risk | Mitigation |
|:---|:---|
| sed replace có pattern không match → file bị skip | Run `grep -L` after sed để find non-matched |
| Edit blueprint nhưng quên rerun deploy → live state mismatch | Phase 04 đã move qua API, doc chỉ là update record |
| Quên file → drift quay lại | Phase 07 validation script will catch |

## Next Steps

→ Phase 07: Build validation script + rollout communication
