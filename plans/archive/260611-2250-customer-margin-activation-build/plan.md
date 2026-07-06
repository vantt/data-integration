---
title: "Customer Margin + Activation — Build Plan (5 việc)"
created: 2026-06-11
status: done
# (updated 2026-06-24: all phases P0-P4 + P3a/P3b-mart/P3b-dash completed by 2026-06-12; dashboards #14/#99/#102 live; one open framing decision on Tab B margin — untouched by 260623 audit)
parent: ../260604-1125-retail-reactivation/plan.md
source: ../260604-1125-retail-reactivation/02-understand/enriched-data-margin-and-activation-signals.md
---

# Customer Margin + Activation — Phasing 5 việc

> Từ re-evaluate customer domain trên dữ liệu mới (margin thật + shipment + P3 refresh).
> Nguyên tắc: **RUN trước, BUILD sau.** Đòn bẩy lớn nhất = chạy queue đang nằm im + thêm trục margin
> vào customer-grain. Channel-margin ĐÃ có (`finance_channel_pl`) → không build lại (DRY).

## Dependency graph

```
P0 RUN queue ─────────────────────────────────► (revenue ngay, 0 build, độc lập)

P1 verify overhead ─► mart customer contribution-margin ─┬─► P3b action_queue +margin flag
                                                         └─► P4 Retail Activation Cockpit
P2 fix retention waterfall (survivorship) ───────────────┬─► P3a customer_retention repoint
                                                         └─► P4 (tab retention)
```
P1 và P2 chạy **song song**. P3/P4 chờ P1+P2.

## Phases

| Phase | Việc | Type | Effort | Status | Chặn bởi |
|---|---|---|---|---|---|
| **P0** | RUN `mart_customer_action_queue` → dùng dashboard 99 | Ops | S | ✅ usable (dashboard 99) | — |
| **P1** | mart customer contribution-margin (`int_customer_economics` + dim_customers cols) | Mart | M | ✅ DONE+verified | — |
| **P2** | `mart_retention_waterfall_monthly` (point-in-time) | Mart/model | M | ✅ DONE+verified | — |
| **P3b-mart** | action_queue widen (DUE_SOON/SILVER At-Risk) + is_contactable + margin flags | Mart | S | ✅ DONE+verified | P1 |
| **P3a** | Repoint dashboard #14 retention trend → waterfall (card 2224) | Dashboard | S | ✅ DONE+verified | P2 |
| **P3b-dash** | dashboard #99: +filters contactable/next_purchase_signal, +REORDER_PREEMPT scalar, +margin cols | Dashboard | S | ✅ DONE+verified | P3b-mart |
| **P4** | NEW "Retail Activation Cockpit" → dashboard #102 (3 tabs, 28 cards) | Dashboard new | L | ✅ DONE (1 decision open) | P1, P2 |

> **Dashboards DONE 2026-06-12.** #14 retention waterfall trend; #99 enriched; #102 cockpit (https://bi.lan.fwg.vn/dashboard/102).
> **OPEN DECISION (Tab B margin framing):** cockpit dùng `channel_net_margin_pct` (Shopee +13-27%, contribution — nhất quán quyết định overhead). Headline cũ "Shopee lỗ" dùng `fully_loaded` (artifact). Shopee yếu nhất mọi metric + retention kém → migrate; nhưng KHÔNG nói "lỗ" trên contribution. Chờ user chốt framing.

> **Data layer DONE 2026-06-12 00:35 ICT** — materialized via real Dagster run (RUN_SUCCESS, dbt PASS, 0 ERROR), verified in olap.duckdb: dim retail 1231 có margin / 887 âm; waterfall ACTIVE 2025-05=3 (model cũ thổi 50); action_queue cột mới populate.
> **Lesson:** thêm cột vào `dim_customers` (incremental) cần **one-time `dbt build --full-refresh`** (Dagster dbt asset hardcode `dbt build`, không có full_refresh flag → chạy dbt trực tiếp trong container, retry lock). `int_customer_economics` đổi incremental→table (watermark `metric_calculated_at` sai).

Chi tiết từng phase → [phases.md](./phases.md).

## Sequencing rationale

1. **P0 ngay hôm nay** — 653tr (142 khách due/overdue) + 992tr (61 SILVER/GOLD/VIP churn) đang tuột theo ngày. Zero engineering. Không chờ gì.
2. **P1+P2 song song** — 2 prereq độc lập, unblock toàn bộ phần dashboard. P1 phải mở bằng **verify overhead** (gỡ câu hỏi VIP/GOLD lỗ thật hay artifact) trước khi chốt logic margin.
3. **P3a/P3b** — extend rẻ, làm ngay sau prereq tương ứng.
4. **P4 cuối + tùy chọn** — chỉ build nếu sau P3 thấy 2 dashboard extend chưa đủ kể câu chuyện margin-gate cho marketing. Có thể HOÃN.

## KPI / definition of done (link)

- Targets gốc: [../260604-1125-retail-reactivation/06-execute/kpi.md](../260604-1125-retail-reactivation/06-execute/kpi.md)
- P0 success: call-list giao CSKH + ≥1 vòng outreach 142 khách trong tuần.
- P1 success: cột contribution-margin theo customer queryable; overhead method documented.
- P2 success: waterfall point-in-time thay cột `status` cũ; ACTIVE không còn phồng ~9×.
- P3/P4 success: dashboard deploy + margin lens hiển thị; marketing dùng để quyết channel-gate.

## Risks

| Risk | Mitigation |
|---|---|
| ~~Overhead alloc sai~~ ✅ RESOLVED: revenue-weighted phạt đơn to | Customer view dùng contribution margin, không fully-loaded (xem Decision #1) |
| 56% no-phone, KHÔNG có Zalo fallback → không tiếp cận được qua CRM | P0 chỉ chạy 44% có phone; phone-capture tại điểm bán = track sống còn |
| P4 Cockpit trùng finance dashboards | Giữ Cockpit ở customer-grain + marketing audience; channel P&L vẫn ở finance (DRY) |

## Decisions (chốt 2026-06-11)
1. **Overhead = revenue-weighted (98% pool chia ∝ net_revenue)** → fully-loaded phạt đơn to ⇒ "VIP/GOLD lỗ" là ARTIFACT (gross margin VIP cao nhất 57%, overhead TB 11.1tr > gross profit 7.2tr). **Customer view dùng `contribution margin` = gross profit − phí trực tiếp (phí sàn/ship), KHÔNG fully-loaded.** Shopee-lỗ vẫn THẬT (phí sàn là chi phí trực tiếp). → đã gỡ chặn P1. Verify: [verify-overhead-allocation-finding.md](./verify-overhead-allocation-finding.md).
2. **Không có Zalo OA** → contactable = **phone-only**, 56% no-phone = **không tiếp cận được qua CRM** (không fallback). P0/P3b thu hẹp về 44% có phone; phone-capture tại điểm bán là track sống còn (không còn "Zalo OA" trong mitigation).
3. **P4 Cockpit = BUILD** (trong scope).
