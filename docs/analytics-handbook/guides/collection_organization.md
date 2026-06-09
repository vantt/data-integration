# Hướng dẫn Tổ chức Collection trong Metabase

> **Dành cho:** Tất cả người dùng Metabase, AI Agents tạo dashboard
> **Cập nhật:** 2026-05-27 (restructure: 6 top-level + Finance + Analytics + sub Logistics/Data Platform)
> **Bảo trì:** Data Team
> **Tham chiếu kỹ thuật:** [`collection_registry.yml`](../collection_registry.yml)
> **Lịch sử quyết định:** [`decisions/009-collection-by-audience.md`](../../decisions/009-collection-by-audience.md)
> **Xem thêm:** [Report Segmentation Guide](./report_segmentation.md) — Phân lớp báo cáo theo scope
> **Migration:** [plans/260527-1327-metabase-collection-restructure/](../../../plans/260527-1327-metabase-collection-restructure/)

## 1. Vấn đề

Khi tạo dashboard mới, câu hỏi đầu tiên luôn là: "Đặt ở collection nào?"

Nếu không có quy tắc, mỗi người sẽ tự đặt theo cách riêng:
- Người A tạo "Weekly Reports" chứa cả báo cáo của CEO lẫn Marketing
- Người B tạo "Sales Analytics" chỉ vì dashboard liên quan đến sales
- Người C tạo "Monthly Reports" bên cạnh "Weekly Reports"

Kết quả: sidebar Metabase phình to, không ai biết cái nào ở đâu, dashboard dần bị bỏ quên vì người dùng không tìm được.

---

## 2. Nguyên tắc cốt lõi

### Tổ chức theo NGƯỜI DÙNG, không theo chủ đề hay tần suất

Cách sai phổ biến:

| Cách tổ chức | Vấn đề |
|:---|:---|
| Theo **chủ đề** (Sales, Finance, Logistics) | Marketing Manager cần xem cả Sales lẫn Customer → phải mở 2-3 collection |
| Theo **tần suất** (Daily, Weekly, Monthly) | CEO mở "Weekly Reports" thấy lẫn dashboard của Ops team → không biết cái nào dành cho mình |
| Theo **loại report** (KPIs, Tables, Charts) | Vô nghĩa với người dùng — họ không nghĩ theo loại biểu đồ |

**Cách đúng: Tổ chức theo người dùng (audience).**

Mỗi collection trả lời cho MỘT nhóm người, MỘT câu hỏi chính:

```
📁 Executive               → CEO mở lên, thấy ĐÚNG 3 dashboards cần thiết
📁 Marketing & Customers   → Marketing Manager mở lên, thấy ĐÚNG kênh + khách hàng
📁 Operations              → Ops team mở lên, thấy ĐÚNG dashboard vận hành hàng ngày
```

Người dùng không cần nhớ tên dashboard. Họ chỉ cần mở collection của mình → mọi thứ liên quan đều ở đó.

### Tần suất nằm trong TÊN dashboard, không trong tên collection

- Đúng: Collection `Executive` chứa `CEO Weekly Pulse` và `CEO Monthly Scorecard`
- Sai: Collection `Weekly Reports` chứa dashboard của 3 đối tượng khác nhau

Tần suất (daily/weekly/monthly) là thuộc tính của dashboard, không phải lý do tạo collection.

---

## 3. Cấu trúc hiện tại

> **Thay đổi 2026-05-27:** Restructure lên **6 top-level**. Thêm `Finance` (driven by P&L mart explosion), `Analytics` (Layer 3 — formally created), `📍 Start Here` (onboarding), sub `Operations > Logistics` + `Operations > Data Platform` (audience fix), `Operations > US CrossBorder` (CrossBorder scope tách riêng). Xoá 3 sub-1-board (Retail Ops, CrossBorder Ops, Order Management).

```text
                          ┌────────────────────────────────┐
                          │        Metabase Root            │
                          └─┬──────┬──────┬──────┬──────┬──┘
                            │      │      │      │      │
        ┌───────────────────┼──────┼──────┼──────┼──────┼─────────┐
        │                   │      │      │      │      │         │
  ┌─────┴──────┐  ┌────────┴┐  ┌──┴───┐  │  ┌──┴────┐  │  ┌─────┴────┐
  │📍 Start    │  │Executive│  │Finance│ │  │Mkt &  │  │  │Analytics │
  │   Here     │  │  [L1]   │  │ [L1.5]│ │  │Customer│  │  │   [L3]   │
  │  [All]     │  │ 3 brd   │  │ 3 brd │ │  │[L2-Ret]│  │  │  4 brd   │
  └────────────┘  └─────────┘  └───────┘ │  │ 6 brd  │  │  └──────────┘
                                          │  └────────┘  │
                                     ┌────┴────┐         │
                                     │Operations│        │
                                     │   [L2]   │        │
                                     │   1 brd  │        │
                                     │   root   │        │
                                     └────┬─────┘
      ┌──────────┬──────────┬──────────┬──┴─────┬──────────┬──────────┐
      │          │          │          │        │          │          │
┌─────┴────┐ ┌───┴───┐ ┌───┴────┐ ┌───┴────┐ ┌─┴──────┐ ┌─┴───────┐
│  Daily   │ │Periodic│ │  B2B  │ │   US   │ │Logistics│ │  Data   │
│Monitoring│ │Reviews │ │  Ops  │ │CrossBor│ │  (NEW)  │ │Platform │
│ [Retail] │ │[Retail]│ │ [B2B] │ │ [US]   │ │ [All]   │ │  (NEW)  │
│  5 brd   │ │ 2 brd  │ │ 2 brd │ │  1 brd │ │  1 brd  │ │ 1 brd   │
└──────────┘ └────────┘ └───────┘ └────────┘ └─────────┘ └─────────┘
```

Danh sách đầy đủ audience, dashboard, và lookup table → xem [`collection_registry.yml`](../collection_registry.yml).

---

## 4. Tại sao gộp, không tách?

### Executive gộp Sales Analytics

| Trước | Sau |
|:---|:---|
| `Executive` (2 dashboards) + `Sales Analytics` (1 dashboard) | `Executive` (3 dashboards) |

**Lý do:** Trong công ty nhỏ, CEO cũng chính là Sales Director (hoặc report trực tiếp). Không có lý do bắt 1 người mở 2 collection. Sales Executive Dashboard và CEO Monthly Scorecard phục vụ cùng mục đích: nhìn tổng quan doanh thu.

### Marketing gộp Customer Analytics

| Trước | Sau |
|:---|:---|
| `Marketing` (2 dashboards) + `Customer Analytics` (1 dashboard) | `Marketing & Customers` (3 dashboards) |

**Lý do:** Marketing Manager khi phân tích kênh bán (Marketing Weekly Tracker) cũng cần biết khách hàng đang ở segment nào (Customer Operational Dashboard). Hai loại insight này bổ sung cho nhau — tách ra buộc người dùng phải nhảy qua lại.

### Operations giữ sub-collections

**Lý do:** Operations có 6 dashboards — nhiều nhất. Nhưng người dùng có 2 workflow hoàn toàn khác:
- **Daily Monitoring**: Mở nhiều lần/ngày, cần nhanh → 4 dashboards
- **Periodic Reviews**: Mở 1 lần/tuần hoặc 1 lần/tháng → 2 dashboards

Gộp chung 6 dashboard vào 1 level sẽ khiến người ops phải scan qua các report tuần/tháng mỗi lần muốn mở dashboard hôm nay. Sub-collection giải quyết đúng vấn đề này.

---

## 5. Quy tắc cho Dashboard mới

### Bước 1: Xác định người dùng chính

Hỏi: "Ai sẽ mở dashboard này hàng ngày/tuần?"

### Bước 2: Dùng Decision Tree

```text
Dashboard mới cần tạo
       │
       ├── Dành cho CEO / Founders / Directors (tổng quan all business)?
       │       → Executive [All] — Layer 1
       │
       ├── Dành cho Marketing / Phân tích khách lẻ?
       │       → Marketing & Customers [Retail] — Layer 2
       │
       ├── Dành cho theo dõi khách sỉ / đối tác (B2B)?
       │       → Operations > B2B Operations [B2B] — Layer 2
       │
       ├── Dành cho US CrossBorder / export arrangement?
       │       → Operations > US CrossBorder [US] — Layer 2
       │
       ├── Dành cho vận hành retail hàng ngày? (xem nhiều lần/ngày)
       │       → Operations > Daily Monitoring [Retail] — Layer 2
       │
       ├── Dành cho review tuần/tháng (retail ops)?
       │       → Operations > Periodic Reviews [Retail] — Layer 2
       │
       ├── Dành cho so sánh cross-segment / research?
       │       → Analytics [Cross] — Layer 3
       │
       └── Không khớp?
               → Xem Report Segmentation Guide để chọn scope
               → CẬP NHẬT collection_registry.yml trước
               → KHÔNG tự tạo collection mới
```

**Quan trọng:** Luôn xác định scope (scope_sales, scope_retail, scope_b2b) TRƯỚC khi chọn collection. Xem [Report Segmentation Guide](./report_segmentation.md).

### Bước 3: Kiểm tra giới hạn

- Nếu collection đích đã có **> 8 dashboards** → cân nhắc tạo sub-collection
- Nếu collection đích chỉ có **1 dashboard** → cân nhắc gộp vào collection gần nhất

---

## 6. Khi nào cần thay đổi cấu trúc?

Cấu trúc hiện tại (6 top-level + sub-collections) phù hợp với team nhỏ-vừa (~10-20 người dùng Metabase). Cần điều chỉnh khi:

| Tín hiệu | Hành động |
|:---|:---|
| **Team Customer Success tách biệt khỏi Marketing** (> 15 người, có KPI riêng) | Tách `Marketing & Customers` → `Marketing` + `Customer Analytics` |
| **Sales Director ≠ CEO**, cần permission riêng | Tách `Executive` → `Executive` + `Sales Analytics` |
| **Operations > Daily Monitoring > 6 dashboards** | Tạo sub-collection theo chức năng (ví dụ: `Fulfillment Monitoring`) |
| **B2B team có KPI riêng biệt với Retail** | Đã tách: `Operations > B2B Operations` |
| **Xuất hiện domain mới** (Finance, Logistics) có audience riêng | Tạo top-level collection mới |
| **Cần phân tích cross-segment thường xuyên** | Đã có: `Analytics` collection cho Layer 3 |
| **Finance domain explode (P&L marts mới)** | **Đã tách 2026-05-27: `Finance` top-level — driven by `fact_order_economics`, `fact_order_costs`, `fact_order_returns`** |
| **Audience mismatch trong sub-collection** (vd Data team lẫn Store Manager) | **Đã fix 2026-05-27: tách `Operations > Logistics` và `Operations > Data Platform` khỏi Daily Monitoring** |

**Nguyên tắc:**
- **Gộp** khi cùng người dùng
- **Tách** khi khác người dùng
- **Phân lớp** khi cùng người dùng nhưng khác scope (Retail vs B2B)

---

## 7. Liên kết kỹ thuật

| Tài liệu | Mục đích |
|:---|:---|
| [`collection_registry.yml`](../collection_registry.yml) | Machine-readable registry — deploy script đọc file này |
| [`AGENTS.md`](../AGENTS.md) → Section "Collection Governance" | Quy trình cho AI agents — lookup table + syntax `>` |
| [`dashboard_design_patterns.md`](./dashboard_design_patterns.md) | Quy chuẩn layout dashboard (Executive Pulse, Operational Cockpit, etc.) |
| [`report_segmentation.md`](./report_segmentation.md) | **Quan trọng:** Phân lớp báo cáo (L1/L2/L3), scope definitions, naming conventions |
| [`../../context/customer-segmentation.md`](../../context/customer-segmentation.md) | 8 chiều phân loại khách hàng, đặc biệt `customer_type` |
| [`../../context/sales-segmentation-guide.md`](../../context/sales-segmentation-guide.md) | Gom nhóm kênh/sản phẩm/team |
