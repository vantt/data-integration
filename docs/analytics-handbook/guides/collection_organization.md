# Hướng dẫn Tổ chức Collection trong Metabase

> **Dành cho:** Tất cả người dùng Metabase, AI Agents tạo dashboard
> **Cập nhật:** 2026-03-31
> **Bảo trì:** Data Team
> **Tham chiếu kỹ thuật:** [`collection_registry.yml`](../collection_registry.yml)

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

```text
                         ┌─────────────────────────────────┐
                         │         Metabase Root            │
                         └───────┬──────────┬───────────────┘
                                 │          │               │
                    ┌────────────┤     ┌────┴─────┐   ┌─────┴──────────┐
                    │            │     │          │   │                │
              ┌─────┴─────┐  ┌──┴──┐  │Marketing │   │   Operations   │
              │ Executive │  │     │  │    &     │   │                │
              │           │  │     │  │Customers │   ├──Daily         │
              │ 3 boards  │  │     │  │          │   │  Monitoring    │
              └───────────┘  │     │  │ 3 boards │   │  (4 boards)   │
                             │     │  └──────────┘   │                │
                             │     │                 ├──Periodic      │
                             │     │                 │  Reviews       │
                             │     │                 │  (2 boards)    │
                             │     │                 └────────────────┘
```

| Collection | Câu hỏi chính | Ai mở? | Dashboards |
|:---|:---|:---|:---|
| **Executive** | "Công ty đang thế nào?" | CEO, Founders, Sales Director | CEO Weekly Pulse, CEO Monthly Scorecard, Sales Executive Dashboard |
| **Marketing & Customers** | "Kênh/Khách thế nào?" | Marketing Manager, Brand Manager, Customer Success | Marketing Weekly Tracker, Marketing Monthly Analysis, Customer Operational Dashboard |
| **Operations** | "Hôm nay cần làm gì?" | Store Managers, Sales Ops, CS Lead | _Xem sub-collections bên dưới_ |
| ↳ Daily Monitoring | "Ngay bây giờ ra sao?" | Store Managers, Sales Team | Daily Sales, Yesterday's Sales, Today's Orders, Yesterday's Orders |
| ↳ Periodic Reviews | "Tuần/Tháng này thế nào?" | Sales Ops Lead, CS Lead | Sales Ops Weekly Review, Sales Ops Monthly Summary |

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
       ├── Dành cho CEO / Founders / Ban giám đốc?
       │       → Executive
       │
       ├── Dành cho Marketing / Phân tích khách hàng?
       │       → Marketing & Customers
       │
       ├── Dành cho vận hành hàng ngày? (xem nhiều lần/ngày)
       │       → Operations > Daily Monitoring
       │
       ├── Dành cho review tuần/tháng? (xem 1 lần/tuần hoặc /tháng)
       │       → Operations > Periodic Reviews
       │
       └── Không khớp?
               → CẬP NHẬT collection_registry.yml trước
               → KHÔNG tự tạo collection mới
```

### Bước 3: Kiểm tra giới hạn

- Nếu collection đích đã có **> 8 dashboards** → cân nhắc tạo sub-collection
- Nếu collection đích chỉ có **1 dashboard** → cân nhắc gộp vào collection gần nhất

---

## 6. Khi nào cần thay đổi cấu trúc?

Cấu trúc 3-collection phù hợp với team nhỏ (~5-10 người dùng Metabase). Cần tách khi:

| Tín hiệu | Hành động |
|:---|:---|
| **Team Customer Success tách biệt khỏi Marketing** (> 15 người, có KPI riêng) | Tách `Marketing & Customers` → `Marketing` + `Customer Analytics` |
| **Sales Director ≠ CEO**, cần permission riêng | Tách `Executive` → `Executive` + `Sales Analytics` |
| **Operations > Daily Monitoring > 6 dashboards** | Tạo sub-collection theo chức năng (ví dụ: `Fulfillment Monitoring`) |
| **Xuất hiện domain mới** (Finance, Logistics) có audience riêng | Tạo top-level collection mới |

Nguyên tắc: **gộp khi cùng người dùng, tách khi khác người dùng.**

---

## 7. Liên kết kỹ thuật

| Tài liệu | Mục đích |
|:---|:---|
| [`collection_registry.yml`](../collection_registry.yml) | Machine-readable registry — deploy script đọc file này |
| [`AGENTS.md`](../AGENTS.md) → Section "Collection Governance" | Quy trình cho AI agents — lookup table + syntax `>` |
| [`dashboard_design_patterns.md`](./dashboard_design_patterns.md) | Quy chuẩn layout dashboard (Executive Pulse, Operational Cockpit, etc.) |
