# Hướng dẫn Tổ chức Collection trong Metabase

> **Dành cho:** Tất cả người dùng Metabase, AI Agents tạo dashboard
> **Cập nhật:** 2026-04-19
> **Bảo trì:** Data Team
> **Tham chiếu kỹ thuật:** [`collection_registry.yml`](../collection_registry.yml)
> **Xem thêm:** [Report Segmentation Guide](./report_segmentation.md) — Phân lớp báo cáo theo scope

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

> **Thay đổi 2026-04-19:** Thêm B2B Operations và Analytics collection. Xem [Report Segmentation Guide](./report_segmentation.md) để hiểu 3-layer architecture.

```text
                              ┌─────────────────────────────────┐
                              │         Metabase Root            │
                              └──┬─────────┬─────────┬──────────┬┘
                                 │         │         │          │
              ┌──────────────────┤    ┌────┴────┐   ┌┴────────┐ │
              │                  │    │         │   │         │ │
        ┌─────┴─────┐      ┌─────┴────┴──┐  ┌───┴───┴──┐  ┌───┴─┴────┐
        │ Executive │      │  Operations │  │Marketing │  │Analytics │
        │   [L1]    │      │    [L2]     │  │& Customer│  │   [L3]   │
        │           │      │             │  │ [L2-Ret] │  │          │
        │ 5 boards  │      │             │  │ 4 boards │  │ 4 boards │
        └───────────┘      │             │  └──────────┘  └──────────┘
                           │             │
              ┌────────────┼─────────────┼────────────┐
              │            │             │            │
        ┌─────┴─────┐ ┌────┴────┐ ┌─────┴────┐ ┌─────┴─────┐
        │  Retail   │ │   B2B   │ │  Daily   │ │ Periodic  │
        │Operations │ │Operations│ │Monitoring│ │ Reviews   │
        │ [Retail]  │ │  [B2B]  │ │ [Retail] │ │ [Retail]  │
        │ 1 board   │ │ 4 boards│ │ 4 boards │ │ 2 boards  │
        └───────────┘ └─────────┘ └──────────┘ └───────────┘
```

| Collection | Layer | Câu hỏi chính | Ai mở? | Scope | Dashboards |
|:---|:---|:---|:---|:---|:---|
| **Executive** | L1 | "Công ty đang thế nào?" | CEO, Founders, Directors | scope_sales [All] | CEO Weekly Pulse, CEO Monthly Scorecard, Order Profitability, Finance P&L, Logistics |
| **Operations** | L2 | "Hôm nay cần làm gì?" | Ops team | (xem sub-collections) | — |
| ↳ Retail Operations | L2 | "Bán lẻ ra sao?" | Sales Ops (Retail) | scope_retail [Retail] | Promotion Analysis |
| ↳ B2B Operations | L2 | "Khách sỉ thế nào?" | B2B Sales | scope_b2b [B2B] | B2B Daily Sales, B2B Orders Tracking, Partner Performance, B2B Margin |
| ↳ Daily Monitoring | L2 | "Ngay bây giờ ra sao?" | Store Managers | scope_retail [Retail] | Daily Sales, Yesterday's Sales, Today's Orders, Yesterday's Orders |
| ↳ Periodic Reviews | L2 | "Tuần/Tháng này?" | Sales Ops Lead | scope_retail [Retail] | Sales Ops Weekly, Sales Ops Monthly |
| **Marketing & Customers** | L2-Retail | "Kênh/Khách retail?" | Marketing Manager, CS | scope_retail [Retail] | Marketing Weekly, Marketing Monthly, Customer Ops, Customer Retention |
| **Analytics** | L3 | "So sánh segment?" | Analysts, Leadership | scope_sales + breakdown [Cross] | Customer Intelligence, Channel Profitability, Product Profitability, Acquisition Analysis |

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
       ├── Dành cho vận hành retail hàng ngày? (xem nhiều lần/ngày)
       │       → Operations > Daily Monitoring [Retail] — Layer 2
       │
       ├── Dành cho review tuần/tháng (retail ops)?
       │       → Operations > Periodic Reviews [Retail] — Layer 2
       │
       ├── Dành cho phân tích promotion/discount?
       │       → Operations > Retail Operations [Retail] — BẮT BUỘC scope_retail
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

Cấu trúc hiện tại (4 top-level + sub-collections) phù hợp với team nhỏ-vừa (~10-20 người dùng Metabase). Cần điều chỉnh khi:

| Tín hiệu | Hành động |
|:---|:---|
| **Team Customer Success tách biệt khỏi Marketing** (> 15 người, có KPI riêng) | Tách `Marketing & Customers` → `Marketing` + `Customer Analytics` |
| **Sales Director ≠ CEO**, cần permission riêng | Tách `Executive` → `Executive` + `Sales Analytics` |
| **Operations > Daily Monitoring > 6 dashboards** | Tạo sub-collection theo chức năng (ví dụ: `Fulfillment Monitoring`) |
| **B2B team có KPI riêng biệt với Retail** | Đã tách: `Operations > B2B Operations` |
| **Xuất hiện domain mới** (Finance, Logistics) có audience riêng | Tạo top-level collection mới |
| **Cần phân tích cross-segment thường xuyên** | Đã có: `Analytics` collection cho Layer 3 |

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
