# Phase 05: New Finance Dashboards Roadmap

> **Status:** Backlog (parallel — không block các phase khác)
> **Owner:** Data Team + Analytics Design (skill)
> **Estimated:** 1-2 ngày/dashboard × 5 = ~2 tuần
> **Depends:** Phase 03 (Finance collection exists)
> **Blocks:** none

---

## Context Links

- Trigger scan: [phase-01](./phase-01-data-scan-discovery.md) §4
- Analytics design skill: `.skills/analytics-design/SKILL.md` (Phase 0-6)
- Metabase blueprint: `.skills/metabase-automation/SKILL.md` (Phase 7-10)

## Overview

3 mart P&L mới hôm nay nhưng 2 trong số đó (`fact_order_costs`, `fact_order_returns`) **chưa có dashboard**. Phase này định nghĩa 5 dashboard mới để serve Finance/CFO/Accounting audience.

## Key Insights

- Cost ledger (`fact_order_costs`) là long-format → ideal cho **explode-by-cost-type** visualization
- Returns (`fact_order_returns`) tách biệt khỏi orders → cho phép track liability theo recognition date
- Channel P&L hiện chỉ có comparison ở `Channel Profitability Monthly` (now in Analytics) — Finance cần **time series + variance**

## 5 Dashboard specs

### Spec 1 — Cost Ledger Analyzer [All]

| Field | Value |
|:---|:---|
| Priority | **P0** |
| Audience | CFO, Accounting Manager |
| Scope | scope_sales (all) |
| Collection | Finance |
| Mart source | `fact_order_costs` |
| Câu hỏi chính | "Tiền của tôi đi đâu? Breakdown các loại chi phí theo kênh." |

**Sections:**
- KPI row: Total Costs MTD, COGS %, Platform Fees %, Voucher Subsidy %
- Stacked bar: Cost composition by month (COGS / Platform Fees / Tax / Shipping / Voucher)
- Table: Top 20 channels by total cost với % breakdown
- Time series: Platform Fees ratio trend (last 6 months) — alert if > target
- Drill: Cost by SKU category for selected channel

**Blueprint file:** `docs/analytics-handbook/blueprints/finance_cost_ledger.md` (mới)

---

### Spec 2 — Return Impact Analysis [All]

| Field | Value |
|:---|:---|
| Priority | **P0** |
| Audience | CEO, CFO, Sales Ops Lead |
| Scope | scope_sales |
| Collection | Finance |
| Mart source | `fact_order_returns` |
| Câu hỏi chính | "Refund liability đang ở mức nào? Channel nào có return rate cao bất thường?" |

**Sections:**
- KPI row: Return Rate MTD, Refund Liability $, Average Days-to-Return, Top Reason
- Cohort table: Return rate by order_month × return_month (lag distribution)
- Channel ranking: Return rate by channel, sort DESC, flag > 5%
- Reason breakdown: Top 10 return reasons by revenue impact
- Trend: Daily return count last 90 days

**Blueprint file:** `docs/analytics-handbook/blueprints/finance_return_impact.md` (mới)

---

### Spec 3 — Channel P&L Deep Dive [Cross]

| Field | Value |
|:---|:---|
| Priority | **P1** |
| Audience | Finance Director, Sales Director |
| Scope | scope_sales (with channel breakdown) |
| Collection | Finance |
| Mart source | `fact_order_economics` + `int_misa_sales_lines` |
| Câu hỏi chính | "Kênh nào lỗ? Kênh nào lãi sau khi trừ hết phí platform?" |

**Sections:**
- Waterfall: Gross Revenue → Discounts → Net Revenue → COGS → Platform Fees → Net Profit
- Channel scorecard: 1 row/channel × cols (Net Rev, Gross Margin %, Net Margin %, Order Volume)
- Heatmap: Channel × Month, color = net margin %
- Variance: Actual vs prior period (WoW, MoM, YoY)
- Loss leader alert: Channel với net_margin < 0 → red flag

**Blueprint file:** `docs/analytics-handbook/blueprints/finance_channel_pl.md` (mới)

---

### Spec 4 — Product Cost-to-Margin Heatmap [Cross]

| Field | Value |
|:---|:---|
| Priority | **P1** |
| Audience | Merchandising Manager, Finance |
| Scope | scope_sales |
| Collection | Finance |
| Mart source | `int_misa_sales_lines` |
| Câu hỏi chính | "SKU nào margin tốt? SKU nào COGS variance cao bất thường?" |

**Sections:**
- Scatter: X=Revenue, Y=Margin %, size=Order count — bubble per SKU
- Top 50 table: SKU × Revenue × COGS × Margin % × COGS variance (vs avg)
- Margin distribution histogram
- COGS variance alert: SKU với COGS này tháng vs avg 3-month > 10% → flag
- Drill: SKU breakdown by channel

**Blueprint file:** `docs/analytics-handbook/blueprints/finance_product_cost_margin.md` (mới)

---

### Spec 5 — Accounting Reconciliation Cockpit [Internal]

| Field | Value |
|:---|:---|
| Priority | **P2** |
| Audience | Accounting Manager, CFO |
| Scope | All (recon = total picture) |
| Collection | Finance |
| Mart source | `fact_orders` + `recon_sapo_orders_daily` + `recon_misa_daily` |
| Câu hỏi chính | "Số Sapo, MISA, Shopee có khớp không? Exception ở đâu?" |

**Sections:**
- Status header: Sapo↔MISA last sync, MISA↔Shopee last sync, count of unmatched
- Exception table: Unmatched orders với reason (missing MISA invoice, fee mismatch, etc.)
- Drift trend: % unmatched per day last 30 days
- Reconciliation funnel: Total orders → Have MISA → Have COGS → Have margin
- Drill: Click exception → show full order + line items + invoice

**Blueprint file:** `docs/analytics-handbook/blueprints/finance_accounting_recon.md` (mới)

## Workflow per dashboard (theo Analytics Design skill)

1. **Phase 0:** Read mart schema + verify column availability
2. **Phase 1:** Create/update `docs/analytics-handbook/domains/finance.md` với new metrics
3. **Phase 2:** Create playbook `docs/analytics-handbook/playbooks/finance_<name>.md`
4. **Phase 3-5:** Design spec với composition table
5. **Phase 6:** Validate with stakeholder (CFO if available)
6. **Phase 7:** Create blueprint
7. **Phase 8:** Deploy via `deploy_from_markdown.js`
8. **Phase 9:** Smoke test trong Metabase UI
9. **Phase 10:** Add to validation script registry

## Todo List

- [ ] Verify CFO/Finance Director exists in team — chốt audience
- [ ] Schema check: confirm `fact_order_costs` columns ready (cost_type, cost_amount, currency)
- [ ] Schema check: confirm `fact_order_returns` columns ready (return_date, refund_amount, reason)
- [ ] Schema check: `recon_*` tables actually populated daily?
- [ ] **P0:** Cost Ledger Analyzer — domain → playbook → design → blueprint → deploy
- [ ] **P0:** Return Impact Analysis — same flow
- [ ] **P1:** Channel P&L Deep Dive
- [ ] **P1:** Product Cost-to-Margin Heatmap
- [ ] **P2:** Accounting Reconciliation Cockpit
- [ ] Update `collection_registry.yml` để liệt kê 5 dashboard mới trong Finance collection

## Success Criteria

- [ ] 5 blueprint files exist trong `docs/analytics-handbook/blueprints/finance_*.md`
- [ ] 5 dashboards deployed vào Finance collection
- [ ] Mỗi dashboard có suffix scope, description, audience documented
- [ ] CFO/Accounting có thể tự dùng không cần data team support

## Risk Assessment

| Risk | Mitigation |
|:---|:---|
| Mart mới (`fact_order_costs`, `fact_order_returns`) chưa stable | Validate sample data trước, có thể skip P0 nếu chưa ready |
| Audience CFO không exist trong team thực | Hỏi user trước khi build, có thể merge spec 3+4 nếu Finance team nhỏ |
| Recon tables không có signal | Replace Spec 5 với "Cost Reconciliation" dùng `fact_order_costs` |
| Performance: per-order P&L joins nặng | Pre-aggregate model nếu cần, dùng Metabase Model layer |

## Next Steps

→ Sau khi Phase 02-04 done, kick off P0 (Cost Ledger Analyzer) trước
→ Phase 06 cập nhật doc về Finance collection
