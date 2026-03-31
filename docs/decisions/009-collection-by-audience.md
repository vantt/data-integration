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
