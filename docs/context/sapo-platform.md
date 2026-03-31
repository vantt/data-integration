# Mô Tả Bối Cảnh Dữ Liệu

## 🏢 Nguồn Dữ Liệu: Hệ Thống Sapo

**Sapo** là hệ thống bán hàng e-commerce quản lý toàn bộ nghiệp vụ kinh doanh.

### Dữ Liệu Được Quản Lý

#### 📦 Quản lý đơn hàng (Orders)

- Thông tin đơn hàng, trạng thái
- Line items (sản phẩm trong đơn)
- Fulfillments (xử lý đơn)
- Shipments (vận chuyển)
- Payments/Returns (thanh toán/trả hàng)

#### 👥 Quản lý khách hàng (Customers)

- Thông tin cá nhân
- Địa chỉ
- Lịch sử mua hàng
- Customer groups
- Chương trình loyalty

#### 📦 Quản lý sản phẩm (Products)

- Thông tin sản phẩm
- Variants (biến thể)
- Giá, khuyến mãi
- Tồn kho

#### 🏪 Quản lý kho & chi nhánh (Warehouses/Locations)

- Locations (kho, cửa hàng)
- Tồn kho theo kho
- Staff assignments

#### 🚚 Quản lý vận chuyển (Shipping)

- Shipment tracking
- Delivery status
- Shipping providers

#### 💰 Quản lý tài chính

- Payments
- Prepayments
- Discounts/Promotions

#### 👤 Quản lý nội bộ

- Accounts (nhân viên)
- Sales channels
- Price lists

---

## ⚠️ Hạn Chế Quan Trọng: Webhook Không Đầy Đủ

### Entities Có Webhook ✅

- Orders (đơn hàng)
- Customers (khách hàng)

### Entities KHÔNG Có Webhook ❌

- Shipments (vận chuyển)
- Payments (thanh toán)
- Products
- Returns
- Inventory (tồn kho)
- Locations (kho/chi nhánh)
- Accounts (nhân viên)
- Customer Groups (nhóm khách hàng)
- Price Lists (bảng giá)
- Promotions (khuyến mãi)
- Loyalty Programs (chương trình tích điểm)
- Sales Channels (kênh bán hàng)

### Ý Nghĩa Của Hạn Chế Này

**Điều này có nghĩa:**

- Chỉ nhận được real-time events cho một số entities
- Các entities khác cần phương pháp khác để lấy dữ liệu (API polling, manual sync, etc.)
- Dữ liệu webhook có thể thiếu thông tin liên quan (missing references)
- Cần chiến lược để handle missing data và maintain referential integrity

---

## 🔌 Phương Thức Lấy Dữ Liệu & Giới Hạn API

### 1. JSON API (Orders & Customers)

#### Phương Thức Truy Cập

- **Authentication:** Giả lập cookie (cookie-based authentication)
- **Data format:** JSON API
- **Method:** GET requests

#### Giới Hạn Chức Năng

**Sorting:**

- ✅ Chỉ có thể sort theo `created_on`
- ❌ Không thể sort theo các trường khác (modified_on, status, total, etc.)

**Filtering:**

- ✅ Có thể filter theo **trạng thái đơn hàng**
- ❌ **KHÔNG thể filter theo created_on** (hoặc bất kỳ trường thời gian nào)
- ❌ Không có filter nâng cao khác

**Pagination:**

- ✅ Có thể di chuyển theo page (page 1, 2, 3...)
- Phải duyệt tuần tự từ page đầu

**Ví dụ:**

```
GET /admin/orders?page=1&sort=created_on&order=desc       # Page 1, sorted by created_on
GET /admin/orders?status=confirmed&page=2                 # Page 2, filtered by status
GET /admin/customers?page=1                               # Cannot filter by date
```

#### ⚠️ Giới Hạn Quan Trọng: Không Có Lịch Sử Thay Đổi

**Vấn đề lớn nhất:**

- Order/Customer luôn trả về **trạng thái mới nhất**
- **KHÔNG** có thông tin lịch sử thay đổi
- **KHÔNG** có audit trail của các thay đổi trước đó

**Ví dụ:**

```json
// Gọi API lấy order #123
{
  "id": 123,
  "status": "completed", // ← Chỉ có trạng thái hiện tại
  "modified_on": "2024-01-20T10:00:00Z"
  // ❌ Không biết order này đã qua các trạng thái gì
  // ❌ Không biết khi nào chuyển từ pending → confirmed → completed
}
```

### 2. Chiến Lược Lấy Dữ Liệu

Do giới hạn trên, chỉ có thể lấy data theo 2 cách:

#### Cách 1: Lấy Tất Cả Theo Thứ Tự Thời Gian

```
GET /admin/orders?sort=created_on&page=1
GET /admin/orders?sort=created_on&page=2
...
```

- ❌ **KHÔNG thể filter theo ngày tạo**
- Phải lấy TẤT CẢ orders, sorted by created_on
- Duyệt từng page một (page 1, 2, 3...)
- **Ưu điểm:** Lấy được đầy đủ
- **Nhược điểm:**
  - Phải duyệt toàn bộ nếu muốn orders mới
  - Không thể chỉ lấy "hôm nay" hoặc "tuần này"
  - Tốn bandwidth và time

#### Cách 2: Lấy Theo Trạng Thái

```
GET /admin/orders?status=completed&page=1
GET /admin/orders?status=cancelled&page=1
GET /admin/orders?status=draft&page=1
```

- Lấy orders theo trạng thái cụ thể
- Vẫn phải duyệt từng page
- **Ưu điểm:**
  - Có thể focus vào trạng thái quan tâm
  - Capture 2 trạng thái kết thúc (completed/cancelled)
- **Nhược điểm:**
  - Vẫn không filter theo thời gian
  - Thiếu toàn bộ quá trình ở giữa
  - Không biết thời điểm chuyển trạng thái
  - Không biết ai thực hiện thay đổi

#### ⚠️ Hệ Quả Nghiêm Trọng

```
Kịch bản: Muốn lấy orders của hôm nay (20/01/2024)

Không thể làm:
❌ GET /admin/orders?created_on=2024-01-20
❌ GET /admin/orders?created_on_min=2024-01-20

Phải làm:
1. GET /admin/orders?sort=created_on&page=1
2. Lấy hết tất cả orders từ page 1, 2, 3...
3. Duyệt đến khi gặp order created_on=2024-01-20
4. Tiếp tục duyệt đến khi hết orders của ngày 20/01
5. Stop khi gặp order created_on=2024-01-21

→ Phải load nhiều data không cần thiết
→ Không efficient cho incremental sync
```

```
Timeline của Order #123:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
10:00  draft      ← CÓ (nếu query lúc này)
10:15  pending    ← THIẾU
10:30  confirmed  ← THIẾU
11:00  processing ← THIẾU
14:00  shipped    ← THIẾU
15:30  completed  ← CÓ (nếu query lúc này)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

→ Chỉ lấy được snapshots tại thời điểm query
→ Mất toàn bộ lịch sử ở giữa
→ KHÔNG thể lấy "chỉ orders hôm nay"
```

### 3. Webhook (Real-time Events)

#### Entities Hỗ Trợ

- ✅ **Orders:** Đẩy webhook khi có thay đổi
- ✅ **Customers:** Đẩy webhook khi có thay đổi

#### Payload

```json
{
  "entity_type": "order",
  "entity_id": "123",
  "action": "order.status_changed",
  "action_group": "status",
  "payload": {
    // Data đơn hàng tại thời điểm event
    "id": 123,
    "status": "confirmed",
    "modified_on": "2024-01-20T10:30:00Z"
  }
}
```

#### Ưu & Nhược Điểm

**Ưu điểm:**

- ✅ Real-time, nhận ngay khi có thay đổi
- ✅ Có action classification (created, updated, status_changed)
- ✅ Capture được data tại từng thời điểm thay đổi

**Nhược điểm:**

- ❌ Có thể miss events (network issues, downtime)
- ❌ Không có re-delivery mechanism tốt
- ❌ Out-of-order events
- ❌ Duplicate events

### 4. Entity Update History Log API

#### Tổng Quan

Sapo cung cấp **JSON API lấy entity update history log** cho **TẤT CẢ entities**.

```
GET /admin/audit_logs?entity_type=order&from_date=2024-01-20
```

#### Cấu Trúc Log Item

```json
{
  "id": 789,
  "entity_type": "order",
  "entity_id": 123,
  "action": "status_changed",
  "changed_at": "2024-01-20T10:30:00Z",
  "changed_by": "user_456",
  "entity_uri": "/admin/orders/123.json" // ← URI để lấy data
}
```

#### ⚠️ Giới Hạn Quan Trọng

**URI trả về data MỚI NHẤT, không phải data lúc log:**

```json
// Log ghi nhận lúc 10:30
{
  "changed_at": "2024-01-20T10:30:00Z",
  "entity_uri": "/admin/orders/123.json"
}

// Gọi URI lúc 15:00 (5 giờ sau)
GET /admin/orders/123.json
→ Trả về: { "status": "completed" }  // ← Trạng thái hiện tại
                                      // ❌ KHÔNG phải "confirmed" lúc 10:30
```

#### Cách Lấy Data Đúng Thời Điểm

**Chỉ có 1 cách:**

```
1. Liên tục poll history log API
2. Khi thấy log item mới
3. GỌI NGAY entity_uri (trong vòng vài giây/phút)
4. Lưu data vào database với timestamp của log

→ Nếu trễ, data đã thay đổi, mất thông tin lịch sử
```

**Ví dụ flow:**

```
10:30:00 - Log: order #123 changed
10:30:05 - Detect log item
10:30:10 - Call /admin/orders/123.json
10:30:15 - Get { status: "confirmed" } ✅ Đúng
10:30:20 - Save to DB with timestamp 10:30:00

vs.

10:30:00 - Log: order #123 changed
15:00:00 - Detect log item (delay 4.5h)
15:00:05 - Call /admin/orders/123.json
15:00:10 - Get { status: "completed" } ❌ Sai, đã thay đổi
```

### 5. Tổng Hợp Phương Thức & Giới Hạn

| Phương Thức         | Coverage                               | Real-time | History | Filtering   | Giới Hạn                                                                                            |
| ------------------- | -------------------------------------- | --------- | ------- | ----------- | --------------------------------------------------------------------------------------------------- |
| **JSON API**        | Orders, Customers                      | ❌        | ❌      | Status only | Chỉ sort theo created_on; Không filter theo date; Chỉ có trạng thái mới nhất; Phải paginate tuần tự |
| **Webhook**         | Orders, Customers, Payments, Shipments | ✅        | Partial | N/A         | Có thể miss events; Out-of-order; Duplicate                                                         |
| **History Log API** | ALL entities                           | ❌        | ✅      | Date range  | URI trả data mới nhất; Cần gọi ngay lúc log; Phải poll thường xuyên                                 |

### 6. Hệ Quả & Chiến Lược

#### Vấn Đề

```
❌ Không có single source of truth cho historical data
❌ Phải kết hợp 3 phương thức để có data đầy đủ
❌ Vẫn có gaps trong lịch sử
❌ Phụ thuộc vào timing (gọi API đúng lúc)
❌ JSON API không thể filter theo date → phải load toàn bộ data
❌ Không efficient cho incremental sync
```

#### Chiến Lược Cần Thiết

```
1. Webhook làm primary source (real-time)
   → Capture mọi thay đổi ngay khi xảy ra

2. History Log API làm backup (poll 5-10 phút)
   → Detect changes webhook missed
   → Gọi entity URI ngay lập tức

3. JSON API để initial load & reconcile
   → Chỉ dùng cho full sync ban đầu
   → Hoặc reconcile hàng tuần (không phù hợp cho daily incremental)
   → Accept phải load toàn bộ data

4. Store toàn bộ raw data để reconstruct history

5. Accept rằng sẽ có data gaps
```

#### Data Collection Strategy

```
┌─────────────────────────────────────────┐
│  PRIMARY: Webhooks (Real-time)          │
│  → Store immediately to CouchDB         │
│  → Capture mọi thay đổi                 │
└─────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────┐
│  BACKUP: History Log API (Poll 5-10min) │
│  → Detect changes webhook missed        │
│  → Call entity URI immediately          │
│  → Store to CouchDB                     │
└─────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────┐
│  RECONCILIATION: JSON API               │
│  → Initial load only (load all)         │
│  → Weekly full sync (not daily)         │
│  → Accept phải paginate toàn bộ         │
│  → Fill gaps in history                 │
└─────────────────────────────────────────┘
```

#### ⚠️ Incremental Sync Challenge

```
Problem: Không thể làm daily incremental sync bằng JSON API

Lý do:
- Không filter được theo created_on/modified_on
- Phải load toàn bộ orders từ đầu
- 1,000 orders/day × 30 days = 30,000 orders phải load mỗi lần

Solutions:
1. Rely heavily on Webhooks (must be reliable)
2. History Log API for backup (poll frequently)
3. JSON API chỉ dùng cho:
   - Initial setup (one-time full load)
   - Weekly/monthly reconciliation
   - Emergency recovery
```

---

## 🎯 Yêu Cầu Xử Lý

Cần lấy dữ liệu từ Sapo về và transform thành **2 dạng** phục vụ 2 mục đích khác nhau:

### 1️⃣ OLAP (Online Analytical Processing)

**Mục đích:** Báo cáo, phân tích kinh doanh

**Đặc điểm:**

- Dữ liệu được tổ chức để phân tích
- Tập trung vào đọc, truy vấn phức tạp
- Có thể trễ (batch processing hàng ngày)
- Dữ liệu lịch sử, aggregated
- Schema: Dimensional model (star/snowflake)

**Ví dụ Use Cases:**

- Báo cáo doanh số theo ngày/tuần/tháng/năm
- Phân tích khách hàng: RFM analysis, cohort analysis, retention rate
- Hiệu suất bán hàng theo kênh, chi nhánh, nhân viên
- Phân tích sản phẩm: best-sellers, slow-movers, inventory turnover
- Dashboard tổng hợp cho quản lý cấp cao
- Trend analysis và forecasting
- Customer lifetime value analysis
- Product category performance

### 2️⃣ OLTP (Online Transaction Processing)

**Mục đích:** Các chương trình quản lý nội bộ, ứng dụng vận hành

**Đặc điểm:**

- Dữ liệu cho ứng dụng thực tế
- Tập trung vào ghi/cập nhật
- Cần real-time hoặc near real-time
- Transactional integrity
- Schema: Normalized tables

**Ví dụ Use Cases:**

- Hệ thống thông báo: alert khi có đơn hàng mới, hàng sắp hết
- Dashboard real-time cho staff (số đơn đang xử lý, pending tasks)
- Tool tra cứu đơn hàng cho Customer Service team
- Ứng dụng quản lý inventory real-time
- Workflow automation: auto-assign orders, trigger fulfillment
- Task management cho nhân viên kho/giao hàng
- Notification system cho khách hàng (order updates, shipping status)
- Internal tools cho operations team

---

## 📊 Đặc Điểm Dữ Liệu

### Volume (Khối Lượng)

- **Hiện tại:** ~1,000 đơn hàng/ngày
- **Tương lai:** Có thể scale đến 10,000 đơn hàng/ngày
- **Ước tính storage:**
  - Mỗi order webhook: ~5-10KB
  - 1,000 orders/day = ~5-10MB/day
  - ~300MB/month (chưa bao gồm related entities)

### Complexity (Độ Phức Tạp)

#### Entity Relationships

Dữ liệu có mối quan hệ phức tạp giữa các entities:

```
Order
├── Customer (1:1)
│   ├── CustomerGroup (1:1)
│   └── Addresses (1:N)
├── OrderLineItems (1:N)
│   ├── Product (N:1)
│   │   └── Variant (1:1)
│   ├── Discounts (1:N)
│   └── LotDates (1:N)
├── Fulfillments (1:N)
│   ├── FulfillmentLineItems (1:N)
│   └── Shipment (1:1)
│       └── Address (1:1)
├── Payments (1:N)
├── Prepayments (1:N)
├── Discounts (1:N)
├── PromotionRedemptions (1:N)
├── Returns (1:N)
├── BillingAddress (1:1)
├── ShippingAddress (1:1)
├── Location (N:1)
├── Account (N:1) - Sales person
├── SalesChannel (N:1)
└── PriceList (N:1)
```

#### Data Structure

- **Nested data:** Order chứa nhiều line items, mỗi line item có discounts, lots, serials...
- **Reference data:** Order references đến nhiều entities khác (customer, product, location, staff...)
- **Embedded data:** Customer data, addresses thường được embed trực tiếp trong order
- **Temporal data:** Nhiều timestamps tracking lifecycle của đơn hàng

#### Data Types

- Structured: JSON objects với schema rõ ràng
- Semi-structured: Custom fields, tags
- Temporal: Timestamps, dates
- Financial: Amounts, currencies, tax calculations
- Textual: Notes, descriptions
- References: IDs linking entities

### Freshness Requirements (Yêu Cầu Độ Mới)

#### OLAP (Analytics)

- **Latency cho phép:** 24 giờ
- **Processing:** Batch ETL hàng ngày (có thể chạy vào ban đêm)
- **Priority:** Tính chính xác > Tốc độ
- **Update frequency:** Daily, weekly reports
- **Historical data:** Cần giữ lâu dài (years)

#### OLTP (Operations)

- **Latency yêu cầu:** Real-time hoặc near real-time (trong vòng vài phút)
- **Processing:** Event-driven, streaming
- **Priority:** Tốc độ & Availability > Tính toàn vẹn tuyệt đối
- **Update frequency:** Continuous
- **Historical data:** Có thể archive sau 3-6 tháng

### Data Quality Concerns

**Challenges:**

- **Webhook issues:**
  - Có thể miss events (network issues, rate limits)
  - Out-of-order events (event B đến trước event A)
  - Duplicate events (retry mechanisms)
- **API limitations:**
  - JSON API không có historical data (chỉ current state)
  - History Log API timing-dependent (phải gọi ngay)
  - Không thể reconstruct đầy đủ entity lifecycle
  - Sort và filter capabilities hạn chế
- **Data completeness:**
  - Incomplete data (missing references)
  - Gaps trong lịch sử thay đổi
  - Data inconsistency giữa entities
- **Schema evolution:**
  - Sapo có thể thay đổi data structure
  - Không có versioning rõ ràng

**Requirements:**

- Idempotency handling
- Event ordering
- Data validation
- Missing data handling
- Reconciliation mechanisms
- **Multi-source data collection strategy:**
  - Primary: Webhooks
  - Backup: History Log API (poll frequently)
  - Reconciliation: JSON API (daily)
- **Accept data gaps và implement gap detection**

---

## 🔍 Tóm Tắt Bối Cảnh

### Nguồn Dữ Liệu

- **System:** Sapo E-commerce Platform
- **Data coverage:** Toàn bộ nghiệp vụ bán hàng (orders, customers, products, inventory, shipping, payments, returns)
- **Integration methods:**
  - **Webhooks:** Real-time events (orders, customers, payments, shipments) - Primary source
  - **History Log API:** Entity update logs (all entities) - Backup & gap filling
  - **JSON API:** Batch sync (orders, customers) - Reconciliation
- **Volume:** ~1,000 orders/day, có thể scale đến 10,000 orders/day
- **Critical limitation:** Không có historical data đầy đủ, chỉ có snapshots tại các thời điểm

### Thách Thức Chính

1. **Webhook không cover hết entities** - Chỉ có một số entities, thiếu master data
2. **API limitations nghiêm trọng:**
   - JSON API không có lịch sử thay đổi (chỉ có trạng thái mới nhất)
   - **KHÔNG thể filter theo created_on** - phải load toàn bộ data mỗi lần
   - Không thể làm daily incremental sync bằng JSON API
   - Chỉ sort theo created_on, phải paginate tuần tự
   - History Log API trả data hiện tại, không phải data lúc log
   - Phải gọi API đúng timing để capture historical data
3. **Missing historical data** - Không có audit trail đầy đủ, chỉ capture được snapshots
4. **Entity relationships phức tạp** - Nhiều references cần maintain integrity
5. **Dual processing paths** - Phải maintain 2 pipelines khác nhau (OLAP vs OLTP)
6. **Scale requirements** - Từ 1K → 10K orders/day
7. **Data freshness tradeoffs** - Real-time cho OLTP vs batch cho OLAP
8. **Data quality & completeness:**
   - Webhook có thể miss events
   - Out-of-order events
   - Duplicate events
   - Gaps trong historical data
   - Phụ thuộc vào timing của API calls
9. **Sync efficiency** - JSON API không efficient cho incremental sync, phải rely on webhooks/history log

### Mục Tiêu

1. Build data pipeline từ Sapo về hệ thống nội bộ
2. Transform data sang 2 formats:
   - **OLAP:** Dimensional model cho analytics/reporting
   - **OLTP:** Normalized tables cho operational applications
3. Support cả batch processing (OLAP) và event-driven (OLTP)
4. Ensure data quality và consistency
5. Handle scale từ 1K đến 10K orders/day

### Constraints (Ràng Buộc)

- **Budget:** Sử dụng free tier cloud services (Vercel, Cloudant, Neon)
- **Infrastructure:** Local processing cho heavy workload
- **Development:** Minimize custom code, leverage existing tools (dbt, CouchDB sync)
- **Reliability:** Phải handle offline scenarios, network issues
- **Maintenance:** Simple monitoring và maintenance procedures
- **API Limitations:**
  - JSON API không thể filter theo date → không dùng cho daily incremental sync
  - Phải rely heavily on Webhooks cho real-time data
  - History Log API phải poll frequently (5-10 phút)
- **Data Completeness:** Accept 10% data gaps do API constraints

### Success Metrics

- **Data availability:** >99% webhook events captured
- **Historical data completeness:** >90% (accept gaps due to API limitations)
- **Latency:** OLTP <5 minutes, OLAP <24 hours
- **Data quality:** >99% accuracy for captured data
- **Referential integrity:** >95% complete references
- **Scale:** Support 10,000 orders/day without infrastructure changes
- **Cost:** Maintain within free tier limits
- **API polling efficiency:** History Log API polled every 5-10 minutes

---

## 📡 Chi Tiết Endpoints Theo Entity

> Nội dung dưới đây mô tả chi tiết cách lấy dữ liệu (channels) từ Sapo cho từng entity, bao gồm endpoints, phương thức query và bản chất sắp xếp dữ liệu.
> Xem thêm: [ingestion/docs/SOURCES.md](../ingestion/docs/SOURCES.md) cho API-level reference.

### 1. Orders (Đơn Hàng)

#### A. JSON API (Batch Sync)

Dùng để đồng bộ hàng loạt hoặc initial load.

- **URL/Host**: `GET /admin/orders.json`
- **Query Parameters**:
  - `page`: Số trang (1, 2, 3...)
  - `limit`: Số lượng item mỗi trang (thường là 50 hoặc 100)
  - `sort_by`: `modified_on desc` (Sắp xếp theo thời gian sửa đổi giảm dần)
- **Bản chất Query/Sort**:
  - API hỗ trợ filter cơ bản (status, order dates...).
  - **Lưu ý**: Sapo API có giới hạn về sort theo thời gian sửa đổi. Code hiện tại đang cố gắng dùng `sort_by=modified_on desc` để hỗ trợ incremental sync.
  - **Payload**: Trả về toàn bộ thông tin đơn hàng (nested JSON) bao gồm line items, fulfillments, billing address, v.v.

#### B. Webhook (Real-time)

Dùng để nhận sự kiện thay đổi tức thời.

- **URL/Host**: Endpoint nội bộ của bạn (e.g., `https://<your-domain>/webhook/sapo/orders`)
- **Events**: `order/create`, `order/update`, `order/cancelled`, `order/delete`.
- **Payload**: JSON chứa thông tin đơn hàng tại thời điểm sự kiện.

#### C. History Log API (Gap Filling)

Dùng để phát hiện các thay đổi bị miss bởi webhook.

- **URL/Host**: `GET /admin/settings/get_logs`
- **Logic**:
  1.  Lấy log hoạt động (`rootType=Order`).
  2.  Lấy `rootId` (Entity ID).
  3.  Gọi lại API chi tiết đơn hàng: `GET /admin/orders/{id}.json`.

### 2. Customers (Khách Hàng)

#### A. JSON API (Batch Sync - Search Endpoint)

Sử dụng endpoint tìm kiếm để có khả năng filter tốt hơn.

- **URL/Host**: `GET /admin/customers/doSearch.json`
- **Query Parameters**:
  - `page`: Số trang.
  - `limit`: Số lượng item.
  - `sort`: `created_on,desc` (Sắp xếp theo thời gian sửa đổi mới nhất).
  - `condition_type`: `must`.
- **Bản chất Query/Sort**:
  - Endpoint này cho phép sort theo `created_on` tốt hơn endpoint list chuẩn `/admin/customers.json`.
  - Hỗ trợ incremental loading dựa trên `created_on`.
  - Lưu ý: không hỗ trợ sort theo modified_on (điều này là quan trọng và có thể gây ra nhược điểm cho incremental sync)

#### B. History Log API (Gap Filling)

Dùng để phát hiện các thay đổi bị miss bởi webhook.

- **URL/Host**: `GET /admin/settings/get_logs`
- **Logic**:
  1.  Lấy log hoạt động (`rootType=Customer`).
  2.  Lấy `rootId` (Entity ID).
  3.  Gọi lại API chi tiết khách hàng: `GET /admin/customers/{id}.json`.

#### C. Webhook (Real-time)

- **Events**: `customers/create`, `customers/update`. (Note: Sapo thường gộp customer events hoặc cấu hình riêng).
- **Payload**: JSON chứa thông tin khách hàng tại thời điểm sự kiện.

### 3. Accounts (Nhân Viên / User)

#### A. JSON API (Batch Sync)

Dùng để lấy danh sách nhân viên.

- **URL/Host**: `GET /admin/accounts.json`
- **Query Parameters**:
  - `page`: Số trang.
  - `limit`: Số lượng item.
- **Bản chất Query/Sort**:
  - **Sort**: Mặc định thường là theo ID hoặc tên, API này **không hỗ trợ mạnh về sort theo modified_on** như Orders hay Customers.
  - **Incremental**: Code hiện tại vẫn check trường `modified_on` của từng item trả về để filter, nhưng việc fetch data phải duyệt qua danh sách (hoặc toàn bộ nếu số lượng ít) do không đảm bảo API trả về đúng thứ tự sửa đổi.
  - **Volume**: Thường số lượng accounts ít (< vài trăm), nên có thể load toàn bộ mỗi lần chạy hoặc chấp nhận scan hết.

#### B. History Log API (Gap Filling)

Dùng để phát hiện các thay đổi bị miss bởi webhook.

- **URL/Host**: `GET /admin/settings/get_logs`
- **Logic**:
  1.  Lấy log hoạt động (`rootType=Account`).
  2.  Lấy `rootId` (Entity ID).
  3.  Gọi lại API chi tiết nhân viên: `GET /admin/accounts/{id}.json`.

#### C. Webhook (Real-time)

- **Events**: `accounts/create`, `accounts/update`. (Note: Sapo thường gộp account events hoặc cấu hình riêng).
- **Payload**: JSON chứa thông tin nhân viên tại thời điểm sự kiện.

### 4. Tổng Hợp Ma Trận Channels

| Entity        | Channel Chính | Endpoint                         | Sort Nature        | Lưu ý                                                                         |
| :------------ | :------------ | :------------------------------- | :----------------- | :---------------------------------------------------------------------------- |
| **Orders**    | JSON API      | `/admin/orders.json`             | `modified_by desc` | Dùng để sync lịch sử và daily batch.                                          |
|               | Webhook       | Listener                         | N/A                | Dùng cho real-time updates.                                                   |
| **Customers** | JSON API      | `/admin/customers/doSearch.json` | `modified_on,desc` | Dùng endpoint `doSearch` thay vì list chuẩn.                                  |
|               | Webhook       | Listener                         | N/A                | Real-time updates.                                                            |
| **Accounts**  | JSON API      | `/admin/accounts.json`           | Default (ID/Alpha) | Số lượng ít, thường crawl toàn bộ hoặc scan page. Không sort chuẩn theo time. |

### 5. History Log API (Dùng chung cho tất cả)

Đây là kênh dự phòng quan trọng để đảm bảo tính toàn vẹn dữ liệu.

- **URL Base**: `/admin/settings/get_logs`
- **Sort**: API trả về log mới nhất trước (DESC theo thời gian log).
- **Cách hoạt động**:
  - Crawler duyệt ngược thời gian (Page 1 -> Page N).
  - Dựa vào `occurAt` để xác định điểm dừng (incremental checkpoint).
  - **Gap Filling**: Khi phát hiện log change, hệ thống tự động suy diễn endpoint chi tiết (ví dụ: `/admin/orders/123.json`) để lấy dữ liệu mới nhất.

---

## 📋 Next Steps

Với bối cảnh này, các bước tiếp theo cần thực hiện:

1. **Design schemas** cho OLAP và OLTP databases
2. **Define transformation logic** trong dbt
3. **Strategy cho missing entities** (không có webhook)
4. **Multi-source data collection strategy:**
   - Implement webhook handler
   - Implement History Log API poller
   - Implement JSON API reconciliation
5. **Implement data quality checks** và validation rules
6. **Gap detection và handling mechanisms**
7. **Setup monitoring và alerting**
8. **Plan for scale** và performance optimization
