# ADR-011: Dashboard archetypes (Pulse / Cockpit / Exploratory)

> **Trạng thái:** Accepted
> **Ngày:** 2026-03-31
> **Tham chiếu:** [`STRATEGY.md`](../../.skills/metabase-automation/STRATEGY.md), [`dashboard_design_patterns.md`](../analytics-handbook/guides/dashboard_design_patterns.md)

## Bối cảnh

Không phải dashboard nào cũng giống nhau. CEO cần nhìn tổng quan nhanh, Ops team cần drill-down chi tiết, Analyst cần exploration tool. Nếu không có pattern → dashboard trở thành "everything bagel" cố gắng phục vụ tất cả.

## Quyết định

Định nghĩa **3 dashboard archetypes** với layout và content rules riêng:

| Archetype | Audience | Đặc điểm | Layout |
|:---|:---|:---|:---|
| **Executive Pulse** | CEO, Founders | KPIs + trends, KHÔNG có tables | Scalar cards trên cùng, line/area charts bên dưới |
| **Operational Cockpit** | Managers, Ops | Bar charts + transaction tables | Summary row trên, breakdown charts giữa, detail tables dưới |
| **Exploratory Tool** | Analysts | Scatter plots, heavy filtering | Filters trên cùng, multi-dimensional charts, drill-through links |

## Lý do

1. **Mỗi audience có câu hỏi khác nhau:**
   - CEO: "Tuần này có ổn không?" → 5 KPI cards là đủ
   - Ops: "Đơn nào cần xử lý?" → cần bảng chi tiết
   - Analyst: "Tại sao metric X giảm?" → cần filter + explore

2. **Pattern-based design** đảm bảo consistency — mọi Pulse dashboard trông giống nhau
3. **Tránh dashboard bloat** — archetype rule giới hạn scope (Pulse không có tables = không bị feature creep)

## Hệ quả

- Mỗi blueprint phải declare archetype ở đầu file
- Blueprint template enforce layout rules theo archetype
- Dashboard mới phải fit vào 1 trong 3 archetypes (hoặc justify exception)

## Khi nào xem xét lại

- Xuất hiện use case không fit (ví dụ: embedded analytics cho external users) → thêm archetype mới
