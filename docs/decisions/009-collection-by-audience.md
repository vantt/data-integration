# ADR-009: Collection tổ chức theo audience, không theo chủ đề

> **Trạng thái:** Accepted
> **Ngày:** 2026-03-31
> **Tham chiếu:** [`collection_organization.md`](../analytics-handbook/guides/collection_organization.md)

## Bối cảnh

Metabase collections có thể tổ chức theo nhiều chiều: chủ đề (Sales, Finance), tần suất (Daily, Weekly), loại report, hoặc audience. Cần chọn 1 chiều chính.

## Quyết định

**Tổ chức theo audience (người dùng chính):**

| Collection | Ai mở? | Dashboards |
|:---|:---|:---|
| Executive | CEO, Founders | Weekly Pulse, Monthly Scorecard, Sales Executive |
| Marketing & Customers | Marketing Manager | Weekly Tracker, Monthly Analysis, Customer Ops |
| Operations > Daily Monitoring | Store Managers | Daily Sales, Yesterday's Sales, Today/Yesterday Orders |
| Operations > Periodic Reviews | Sales Ops Lead | Weekly Review, Monthly Summary |

Tần suất (daily/weekly/monthly) nằm trong **tên dashboard**, không trong tên collection.

## Lý do

| Cách tổ chức | Vấn đề |
|:---|:---|
| Theo chủ đề (Sales, Finance) | Marketing Manager cần mở 2-3 collections |
| Theo tần suất (Daily, Weekly) | CEO thấy lẫn dashboard của Ops trong "Weekly" |
| Theo audience | Mỗi người mở 1 collection → thấy đúng dashboards của mình |

**Quy tắc gộp/tách:**
- Gộp khi cùng người dùng (Executive + Sales Analytics → Executive, vì CEO cũng là Sales Director)
- Tách khi khác workflow (Daily Monitoring vs. Periodic Reviews dù cùng Ops team)
- Sub-collection khi > 8 dashboards trong 1 collection

## Hệ quả

- Khi team scale → cần tách collection (ví dụ: Customer Success tách khỏi Marketing)
- Mỗi dashboard mới phải trả lời "ai sẽ mở?" trước khi chọn collection
- Collection registry (`collection_registry.yml`) là source of truth cho mapping

## Khi nào xem xét lại

- Team > 15 người dùng Metabase → xem decision tree trong collection_organization.md
- Xuất hiện domain mới (Finance, Logistics) có audience riêng biệt

---

## Amendments

### 2026-05-27 — Expansion từ 3 lên 6 top-level

**Trigger:** Audit `plans/reports/audit-260527-1202-metabase-collection-tree.md` phát hiện:
- 7 cặp dashboard duplicate (migration `[All]/[Retail]` dở dang, không archive bản cũ)
- Drift spec↔live: 6 collection paths trong blueprints không đăng ký
- 3 sub-collection chỉ 1 dashboard (vi phạm chính guideline)
- Audience mismatch: Ingestion Health (Data team) + Logistics Operations (Logistics Manager) lẫn trong Daily Monitoring (Store Manager)
- 3 mart P&L mới (`fact_order_economics`, `fact_order_costs`, `fact_order_returns`) — 2 chưa có dashboard

**Thay đổi cấu trúc:**

| Trước (3 top) | Sau (6 top) |
|:---|:---|
| Executive, Marketing & Customers, Operations | + 📍 Start Here, + Finance, + Analytics |

**Thay đổi sub trong Operations:**
- Thêm: `Logistics` (audience: Logistics Manager), `Data Platform` (audience: Data Engineering)
- Xoá (gộp lên parent): `Retail Operations`, `CrossBorder Operations`, `Order Management` (chỉ 1 board)

**Nguyên tắc ADR-009 vẫn giữ nguyên:**
- Organize by AUDIENCE, không theo cadence
- Cadence trong dashboard name
- Gộp khi cùng audience, tách khi khác
- Max 2 levels deep

**Bổ sung policy mới:**
- **Scope suffix bắt buộc:** Mọi dashboard có `[All]/[Retail]/[B2B]/[Cross]/[US]/[Internal]`
- **Archive policy:** Blueprint frontmatter `aliases:` → deploy script auto-archive bản cũ (chống tái phát 7 duplicates)
- **Validation script:** CI check `collection_registry.yml` ↔ live Metabase ↔ blueprints
- **Description bắt buộc:** Mỗi dashboard ≥1 dòng "Audience / Scope / Câu hỏi"

**Root cause của drift trước đây:**
1. Migration `[All]/[Retail]` không có archive policy → duplicate đẻ ra
2. Deploy script tự tạo collection lạ khi blueprint dùng tên chưa đăng ký
3. Không có CI check spec↔live → drift im lặng

**Implementation:** xem [plans/260527-1327-metabase-collection-restructure/](../../plans/260527-1327-metabase-collection-restructure/)

### 2026-05-27 — Tách `Operations > US CrossBorder` thành sub-collection riêng

**Trigger:** US CrossBorder dashboard trước đây đặt trực tiếp ở root `Operations`. Sau khi add weekly + monthly tabs, dashboard này đủ scope để cần collection riêng.

**Thay đổi:**
- Tạo `Operations > US CrossBorder` (ID: 97) — audience: US Operations / Sales Ops Lead
- Move dashboard `US CrossBorder Daily [US]` (ID: 51) và 25 questions vào đây
- Archive collection tạm `CrossBorder Operations` (ID: 96) — empty sau khi move

**Lý do:** Audience của US CrossBorder (export arrangement ops) khác biệt với Store Managers (Daily Monitoring) và Sales Ops Lead (Periodic Reviews). Tách sub-collection giúp phân quyền và navigation rõ ràng hơn.

**Blueprint cập nhật:** `blueprints/us_crossborder_operations.md` → `Collection: Operations > US CrossBorder`
