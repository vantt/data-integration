# Phases — chi tiết

> Nguồn số liệu: [enriched-data report](../260604-1125-retail-reactivation/02-understand/enriched-data-margin-and-activation-signals.md).
> DB query: `app_data/data_lake/serving/standalone/sapo_export_latest.duckdb` (read_only).

---

## P0 — RUN action queue (Ops, S, làm NGAY)

**Mục tiêu:** biến 1,156tr value-at-stake đang nằm im thành outreach thật.

**Steps:**
1. Export 2 call-list từ `mart_customer_action_queue` (filter `phone IS NOT NULL`):
   - **Hot/timing (142 khách, 653tr):** `next_purchase_signal IN ('OVERDUE','DUE_SOON')`.
   - **Reactivation mine (61 khách, 992tr):** `value_group IN ('VALUE_VIP','VALUE_GOLD','VALUE_SILVER') AND customer_status IN ('At Risk','Churned')`.
2. Sort theo `value_at_stake DESC`, gắn `action_rationale` + `product_affinity` (gợi ý SKU nhắc).
3. Giao CSKH (high-touch gọi/Zalo VIP-GOLD) + Sales (REORDER_NUDGE). Bronze lỗ → **bỏ qua** high-touch.
4. **Track song song:** thu phone tại điểm bán (gỡ bottleneck 56% no-phone). **Không có Zalo OA** → no-phone = không tiếp cận được; chỉ chạy 44% có phone.

**Files:** không sửa code. Dùng skill `/manage-metabase-resources` hoặc query export CSV.
**Acceptance:** call-list bàn giao + ≥1 vòng outreach 142 khách trong 7 ngày. Log kết quả → `../260604-1125-retail-reactivation/06-execute/execution-log.md`.

---

## P1 — Mart customer contribution-margin (Mart, M)

**Mục tiêu:** `value_group` hiện thuần revenue → không margin-gate được. Cần margin theo customer.

**✅ Overhead đã verify (2026-06-11):** 98% overhead chia ∝ net_revenue (revenue-weighted) → fully-loaded phạt đơn to, "VIP/GOLD lỗ" là artifact. **Quyết định: customer view dùng `contribution margin`, KHÔNG fully-loaded.** Model: `int_order_overhead_allocation` + `int_overhead_pool_monthly`.

**Steps:**
1. Định nghĩa contribution margin per order = `gross_profit − chi phí trực tiếp` (phí sàn `shopee_platform_fees`, ship; KHÔNG trừ `allocated_overhead`). Dùng cột sẵn trong `fact_order_economics`: `gross_profit`, `channel_net_profit` (= sau phí sàn) — kiểm tra `channel_net_profit` có đúng = contribution không, nếu có thì tái dùng (DRY).
2. Thêm intermediate: aggregate `fact_order_economics` theo `customer_key` (qua `fact_orders.order_id`) → `lifetime_gross_profit`, `lifetime_contribution_margin`, `avg_order_margin_pct`, `has_cogs_coverage_pct`, `is_margin_negative` (theo contribution, không fully-loaded).
3. Surface vào `dim_customers` (hoặc mart phụ `mart_customer_economics`) — quyết theo độ nặng incremental.
4. QA: reconcile tổng contribution với `fact_order_economics` aggregate; check coverage `has_cogs` (~65%) — flag khách thiếu COGS.

**Files (sửa trực tiếp, không tạo enhanced-copy):**
- đọc: `transformation/models/marts/.../fact_order_economics.sql` + model overhead
- tạo/sửa: `transformation/models/marts/core/intermediate/int_customer_economics.sql` (mới) → join vào `dim_customers.sql`
- `schema.yml` + column descriptions
**Acceptance:** contribution-margin theo customer queryable; overhead method ghi rõ trong schema; coverage caveat documented. Restart `data_platform` (manifest reload) sau khi thêm node.

---

## P2 — Fix retention waterfall survivorship (Mart/model, M) — song song P1

**Mục tiêu:** `mart_customer_status_snapshot_monthly` dùng `last_order_date` hiện tại → thổi ACTIVE ~9× tháng đáy, giấu churn 2025. Thay bằng point-in-time.

**Steps:**
1. Tạo `mart_retention_waterfall_monthly` — grain `(snapshot_month, status)`, tính as-of từ `fact_orders` (SQL chuẩn ở [retention-leak §3.2](../260604-1125-retail-reactivation/02-understand/retention-leak.md)). Biến thể có `value_group`/`product_affinity`/`channel_preference` để bóc churn theo phân khúc.
2. Giữ model snapshot cũ cho thuộc tính khách, **gắn cảnh báo trong `schema.yml`: ngừng dùng cột `status` cho biểu đồ xu hướng.**
3. QA: ACTIVE 2025-05 phải ~7 (không phải 71).

**Files:** `transformation/models/marts/.../mart_retention_waterfall_monthly.sql` (mới) + `schema.yml`.
**Acceptance:** waterfall point-in-time khớp số chẩn đoán; cảnh báo gắn vào model cũ. Restart `data_platform`.

---

## P3a — Repoint customer_retention_dashboard (Dashboard extend, S) — chờ P2

**Steps:** sửa blueprint `docs/analytics-handbook/blueprints/customer_retention_dashboard.md` → card retention/cohort trỏ `mart_retention_waterfall_monthly`. Thêm card one-time-rate & M1-repeat. Redeploy qua `/deploy-metabase-blueprint` (KHÔNG patch tay — memory: manual edits diverge from blueprint).
**Acceptance:** dashboard hiện đường ACTIVE/AT_RISK/CHURNED point-in-time + heatmap cohort không còn ru ngủ.

---

## P3b — customer_action_queue + contactable + margin flag (Dashboard extend, S) — chờ P1

**Steps:** sửa blueprint `customer_action_queue.md` → thêm cột `is_contactable` (**phone-only**, không Zalo) + `lifetime_contribution_margin`/`is_margin_negative` (từ P1, theo contribution). Filter mặc định: ẩn `is_margin_negative` khỏi high-touch + chỉ hiện `is_contactable=true`. Redeploy qua skill.
**Acceptance:** CSKH thấy ngay ai contactable + ai lãi/lỗ trước khi gọi.

---

## P4 — Retail Activation Cockpit (Dashboard new, L, TÙY CHỌN) — chờ P1+P2

**Mục tiêu:** cross chưa tồn tại = **contribution-margin theo segment × tín hiệu activation × retention-by-channel**. Marketing-owned (khác finance_channel_pl: customer-grain, audience marketing).

**Steps:**
1. Design spec qua skill `analytics-design` (Phase 0-6): tabs gợi ý — (a) Activation Now (queue + timing + margin flag), (b) Channel: retention × margin (Shopee lỗ+giữ kém vs owned lãi+giữ tốt → quyết migrate), (c) Discount-dependency × margin.
2. Blueprint qua `create-metabase-blueprint` (Phase 7-10) → deploy.
**Acceptance:** marketing dùng để quyết channel-gate + offer redesign. **Status: BUILD (đã chốt trong scope 2026-06-11).**

---

## Effort tổng & thứ tự đề xuất
`P0 (ngay)` → `P1 ∥ P2 (song song)` → `P3a ∥ P3b` → `P4 (review rồi quyết)`.
S=nửa ngày–1 ngày, M=2–3 ngày, L=4–6 ngày (gồm design+deploy).

## Decisions (chốt 2026-06-11)
1. ✅ Overhead = revenue-weighted → customer view dùng **contribution margin**, không fully-loaded.
2. ✅ Không Zalo OA → contactable = phone-only; 56% no-phone không tiếp cận được.
3. ✅ P4 Cockpit = BUILD (trong scope).

## Remaining open questions
- REORDER_NUDGE drop 66% (62→21) — kiểm tra logic queue khi làm P3b (đổi tiêu chí hay recency shift thật?).
