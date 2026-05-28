# Audit: Metabase Collection Tree — Tài liệu vs Thực tế vs UX

> **Ngày:** 2026-05-27
> **Scope:** Tài liệu mô tả Collection tree + cross-check với 30 blueprints + **live Metabase query** + đánh giá UX cho end-user
> **Người chạy:** Claude Code (đã query live Metabase tại `127.0.0.1:3001`)

---

## 1. Tài liệu tìm thấy (5 nguồn)

| File | Vai trò | Status |
|:---|:---|:---|
| `docs/analytics-handbook/collection_registry.yml` | Single source of truth máy đọc | Deploy script đọc file này |
| `docs/analytics-handbook/guides/collection_organization.md` | Vietnamese guide cho user/agent | Cập nhật 2026-04-19 |
| `docs/analytics-handbook/guides/report_segmentation.md` | 3-layer architecture (L1/L2/L3) | Cập nhật 2026-04-19 |
| `docs/analytics-handbook/AGENTS.md` → "Collection Governance" | Hướng dẫn cho AI agent | Mới hơn ADR-009 |
| `docs/decisions/009-collection-by-audience.md` | ADR — quyết định kiến trúc | 2026-03-31 |

---

## 2. Triết lý hiện tại (đúng nguyên tắc)

- **Tổ chức theo AUDIENCE** ("Ai mở dashboard này?") thay vì theo chủ đề (Sales/Finance) hay tần suất (Daily/Weekly).
- 3 câu hỏi mặc định mỗi collection trả lời:
  - Executive → "Công ty đang thế nào?"
  - Marketing & Customers → "Kênh/Khách thế nào?"
  - Operations → "Hôm nay cần làm gì?"
- Cadence (daily/weekly/monthly) nằm trong **tên dashboard**, không trong tên collection.
- Max 2 levels deep; color-coding (purple/yellow/green).
- Có decision tree + lookup table cho cả AI agent lẫn human.

**Đánh giá:** Triết lý đúng. Pattern này khớp best practice của Metabase/Tableau community. Vấn đề nằm ở **thực thi**, không phải triết lý.

---

## 3. Bất nhất giữa các tài liệu (CRITICAL)

| Item | `collection_registry.yml` | `collection_organization.md` | `report_segmentation.md` | `AGENTS.md` | `ADR-009` |
|:---|:---|:---|:---|:---|:---|
| Số top-level collections | **3** | **4** (có Analytics) | **4** (có Analytics) | **3** | **3** |
| Sub-collections Operations | Daily Monitoring, Periodic Reviews | + Retail Ops, B2B Ops | + Retail Ops, B2B Ops, Ingestion Health | Daily Monitoring, Periodic Reviews | Daily Monitoring, Periodic Reviews |
| Dashboards trong Executive | 4 (CEO×2, Sales Exec, Channel Profitability) | 5 (+ Order Profit, Finance P&L, Logistics) | 5 (same as above) | 3 (CEO×2, Sales Exec) | 3 |
| Marketing & Customers count | 5 | 4 | 4 | 4 | 3 |
| Collection Analytics tồn tại? | **KHÔNG** | **CÓ** | **CÓ** | KHÔNG | KHÔNG |

**Tác động:** AI agent đọc `collection_registry.yml` (deploy đọc file này → ưu tiên) nhưng human user/dev đọc guide thấy 4 collection → mâu thuẫn → khi tạo dashboard mới sẽ confused.

---

## 4. Bất nhất giữa spec và blueprint thực tế

Quét 30 blueprints, phát hiện **6 collection paths được dùng nhưng KHÔNG đăng ký** trong `collection_registry.yml`:

| Blueprint | Collection thực dùng | Tồn tại trong registry? |
|:---|:---|:---|
| `sales_promotion_analysis` | `Operations > Retail Operations` | ❌ |
| `b2b_sales_daily`, `b2b_orders_tracking` | `Operations > B2B Operations` | ❌ |
| `us_crossborder_operations` | `Operations > CrossBorder Operations` | ❌ (cũng không có trong guide) |
| `order_detail` | `Operations > Order Management` | ❌ (không có ở bất kỳ đâu) |
| `customer_support_social_commerce` | `Operations > Daily Monitoring` | Registry quy định: `Operations` (top-level) |
| `ingestion_health` | `Operations > Daily Monitoring` | `report_segmentation.md` quy định: `Operations > Ingestion Health` |
| `product_performance` | `Operations > Periodic Reviews` | Registry list không có dashboard này |

Đồng nghĩa: **chính file source of truth đang lạc hậu so với blueprints**. Deploy script sẽ tự tạo collection mới bất kỳ lúc nào blueprint dùng tên lạ → silent drift.

---

## 5. LIVE Metabase tree (query trực tiếp 127.0.0.1:3001)

**Tổng: 36 dashboards / 9 collections (loại Personal & Sample)**

```text
Metabase Root
├── [46] Executive (10 dashboards — VƯỢT threshold; có duplicate)
│   ├── CEO Monthly Scorecard            ┐ DUPLICATE PAIR
│   ├── CEO Monthly Scorecard [All]      ┘
│   ├── CEO Weekly Pulse                 ┐ DUPLICATE PAIR
│   ├── CEO Weekly Pulse [All]           ┘
│   ├── Order Profitability              ┐ DUPLICATE PAIR
│   ├── Order Profitability [All]        ┘
│   ├── Channel Profitability Monthly
│   ├── Finance P&L Dashboard
│   ├── Product Profitability
│   └── Sales Monthly Business Review
│
├── [52] Marketing & Customers (9 dashboards — VƯỢT threshold; có duplicate)
│   ├── Customer Operational Dashboard   ┐ DUPLICATE PAIR
│   ├── Customer Operational [Retail]    ┘
│   ├── Marketing Weekly Tracker         ┐ DUPLICATE PAIR
│   ├── Marketing Weekly Tracker [Retail]┘
│   ├── Customer Intelligence Monthly   ← theo `report_segmentation.md` phải ở Analytics
│   ├── Customer Retention & Lifecycle
│   ├── Marketing Monthly Analysis
│   ├── Marketing ROI
│   └── Promotion & Discount Analysis    ← TRÙNG LOGIC với Promotion Analysis [Retail] ở Operations
│
├── [47] Operations (0 dashboards ở root — chỉ chứa sub-folders)
│   ├── [48] Daily Monitoring (8 dashboards; có duplicate, sai audience)
│   │   ├── Daily Sales Dashboard        ┐ DUPLICATE PAIR
│   │   ├── Daily Sales [Retail]         ┘
│   │   ├── Yesterday's Sales Dashboard  ┐ DUPLICATE PAIR
│   │   ├── Yesterday's Sales [Retail]   ┘
│   │   ├── Order Listing
│   │   ├── Social Commerce Operations
│   │   ├── Ingestion Health Monitor    ← AUDIENCE SAI: Data Team
│   │   └── Logistics Operations Center ← AUDIENCE SAI: Logistics Manager
│   ├── [49] Periodic Reviews (4 dashboards) — OK
│   │   ├── Product Performance         ← analytics chứ không "ops review"
│   │   ├── Sales Ops Monthly Summary
│   │   ├── Sales Ops Weekly Review
│   │   └── Shopee Channel Economics
│   ├── [60] B2B Operations (2 dashboards) — OK
│   │   ├── B2B Daily Sales [B2B]
│   │   └── B2B Orders Tracking [B2B]
│   ├── [59] Retail Operations (1 dashboard)  ← VI PHẠM "1-board → gộp"
│   │   └── Promotion Analysis [Retail]
│   ├── [61] CrossBorder Operations (1 dashboard) ← VI PHẠM
│   │   └── US CrossBorder Daily [US]
│   └── [57] Order Management (1 dashboard)   ← VI PHẠM
│       └── Order Detail
│
└── [58] Tests                                ← dev artifact, không nên expose cho user
```

### 5.1 PHÁT HIỆN MỚI: 7 cặp duplicate — KHÔNG đồng loại

So sánh SQL từng cặp → **3 loại khác nhau**, không phải "migration dở dang đơn thuần":

#### Loại A: True duplicate (SQL identical → archive bản cũ)

| Pair | Old views | New views | Hành động |
|:---|:---|:---|:---|
| CEO Weekly Pulse (11) vs `[All]` (43) | ? | ? | Archive bản cũ |

#### Loại B: Refactor — cùng purpose, SQL khác (decide canonical, archive bản kia)

| Pair | Old SQL | New SQL | Old views | New views |
|:---|:---|:---|:---|:---|
| CEO Monthly Scorecard (12) vs `[All]` (44) | `channel_name != 'US'` (hardcoded exclude) | `is_sales_channel` (flag-based) | 69 | 16 |
| Order Profitability (45) vs `[All]` (35) | Hardcoded `is_sales_channel` filter | Parametric channel filter | 24 | **38** |

→ Số liệu có thể **khác nhau** vì filter khác (vd CEO Monthly: old chỉ loại US, new loại tất cả non-sales channels như Internal/STAFF/KOL → revenue thấp hơn). Cần Product Owner verify số nào "đúng".

#### Loại C: Semantic duplicate — KHÁC PURPOSE, KHÔNG nên archive

| Pair | Bản cũ (purpose) | Bản mới `[Retail]` (purpose) | Old views | New views |
|:---|:---|:---|:---|:---|
| Daily Sales Dashboard (2) vs `[Retail]` (41) | **Mixed scope** (gồm cả B2B) | Retail thuần | **190** | 17 |
| Yesterday's Sales Dashboard (5) vs `[Retail]` (42) | Mixed scope | Retail thuần | **286** | 13 |
| Marketing Weekly Tracker (10) vs `[Retail]` (47) | Mixed scope (no customer_type filter) | `customer_type='RETAIL'` | 44 | 15 |
| Customer Operational Dashboard (4) vs `[Retail]` (48) | Mixed scope | Retail thuần | 63 | 14 |

→ **Bản cũ và bản mới CÓ MỤC ĐÍCH KHÁC NHAU** theo Layer 1 (All) vs Layer 2 (Retail) trong `report_segmentation.md`. Vấn đề: **tên bản cũ thiếu suffix `[All]`** nên user không biết nó là "mixed scope". → Đây chính là quan sát của user: "filter có purpose nhưng tên không phản ánh".

#### Tín hiệu quan trọng từ view_count

User vẫn dùng **bản cũ áp đảo** (190/17, 286/13) → 2 khả năng:
1. User chưa biết bản `[Retail]` tồn tại (discoverability problem)
2. User cần view "tổng cả retail+B2B" thay vì retail thuần → bản `[Retail]` mới thực sự ít giá trị

Theo `report_segmentation.md` thì **promotion/marketing/customer phải dùng scope_retail**, do đó nếu user đang ra quyết định marketing dựa trên bản cũ (mixed) thì **số liệu đang sai về mặt business logic** (mixed scope cho promotion = vô nghĩa per `report_segmentation.md` §1).

### 5.2 Cross-collection duplicate

- `Promotion & Discount Analysis` (Marketing & Customers) **trùng mục đích** với `Promotion Analysis [Retail]` (Operations > Retail Operations). Cùng audience Marketing/Sales Ops nhưng đặt ở 2 chỗ → confused.

---

## 6. Đánh giá UX cho End-User (12 vấn đề)

### 6.1 Cognitive overload ở top-level

- **Executive 8 dashboards** đè ngược tinh thần "CEO mở thấy đúng 3 thứ cần".
- **Marketing & Customers 6 dashboards** sắp chạm threshold 8. Customer ≠ Marketing — CS team scale thì sẽ phải tách.
- Thiếu **grouping visual trong Profitability** (Order/Product/Channel Profitability đều ở Executive).

### 6.2 Audience trộn lẫn

- `Ingestion Health` (Data Engineering / Data Team) bị đặt cùng `Daily Sales` (Store Manager) trong **Daily Monitoring** → vi phạm trực tiếp ADR-009.
- `Customer Intelligence Monthly` (analyst-grade, Layer 3 per spec) nằm cùng `Marketing Weekly Tracker` (operational) → user nhỏ team không phân biệt được tầng.

### 6.3 Sub-collection có 1 dashboard duy nhất

`Retail Operations`, `CrossBorder Operations`, `Order Management` — vi phạm chính guideline file đề xuất ("nếu collection chỉ có 1 dashboard → gộp"). Tạo folder để chứa 1 file = thêm 1 click vô nghĩa.

### 6.4 Tên dashboard dễ nhầm

- `Order Profitability` vs `Order Profitability All` — không có suffix segment `[All]` / `[Retail]` để user phân biệt.
- `Customer Operational Dashboard` vs `Customer Intelligence Monthly` — operational vs analytical nhưng tên không gợi mở.

### 6.5 Segment indicator (`[All]`/`[Retail]`/`[B2B]`/`[Cross]`) KHÔNG được áp dụng

`report_segmentation.md` quy định mọi dashboard phải có suffix. Quét tên thực tế trong blueprints → **không thấy suffix nào**. Người dùng không biết dashboard đang ở scope nào nếu không mở từng cái.

### 6.6 Thiếu collection cho audience phụ

| Audience | Có collection riêng? | Hiện đang ở đâu |
|:---|:---|:---|
| Finance / CFO | ❌ | Finance P&L lẫn vào Executive |
| Logistics Manager | ❌ | Logistics Operations lẫn vào Daily Monitoring |
| Data / Engineering Team | ❌ | Ingestion Health sai chỗ |
| B2B Account Manager | ✅ (B2B Operations) | OK |

### 6.7 Naming inconsistency trong chính blueprints

- Header style: `## Collection:` (2 file) vs `## 📂 Collection:` (28 file).
- Path syntax: `Operations` > `Daily Monitoring` (backticks tách rời) vs `Operations > Daily Monitoring` (liền) — gây bug parser khi deploy.
- Một số blueprint có `> **Target Collection:**` ở header, đa số không có → thiếu standard.

### 6.8 Không có landing/orientation collection

User mới mở Metabase → thấy 3 folder lạ, không biết bắt đầu từ đâu. Không có "📍 Start Here" hay README dashboard giải thích cấu trúc.

### 6.9 Không có Personal/Sandbox workspace

User muốn tự thử nghiệm query → đặt ở đâu? Không có guideline → sẽ rơi vào tình trạng đặt vào Operations rồi quên xóa.

### 6.10 Operations top-level gần như rỗng

Theo registry chỉ có `Social Commerce Operations` ở Ops root, nhưng blueprint đẩy nó vào `Daily Monitoring`. Kết quả: top-level Operations trống → user mở thấy chỉ có sub-folders → không có "fast path" cho dashboard chính.

### 6.11 Không có cơ chế Archive

Dashboards bị deprecated (ví dụ `order_profitability` vs `order_profitability_all`) không có chỗ archive → tích tụ noise cho end-user.

### 6.12 Color-coding chỉ định trong registry nhưng chưa rõ enforce

Registry quy định màu (purple/yellow/green) nhưng deploy script có set không? Không verify được trong session này. Nếu chưa set, mất lợi thế visual scan.

---

## 7. Đề xuất ưu tiên

### P0 — Sửa drift ngay (URGENT — ảnh hưởng end-user)
1. **Dọn 7 cặp dashboard duplicate** (CEO Monthly/Weekly, Order Profitability, Customer Op, Marketing Weekly, Daily Sales, Yesterday's Sales) — archive bản legacy, giữ bản `[suffix]` mới.
2. **Hợp nhất 2 Promotion dashboards** trùng logic (Marketing vs Retail Ops) — chọn 1 chỗ.
3. Cập nhật `collection_registry.yml` để chứa **Retail Operations, B2B Operations, CrossBorder Operations, Order Management** (đang có trong Metabase live nhưng chưa đăng ký).
4. Quyết định dứt khoát: **Có hay không Analytics collection?** 3 doc nói có, 2 doc nói không, Metabase live **chưa có**. Chọn 1, update tất cả.
5. Di chuyển `Ingestion Health Monitor` & `Logistics Operations Center` ra khỏi `Daily Monitoring` (audience sai) → tạo sub-collection riêng HOẶC top-level `Data Platform`.
6. Ẩn/move collection `Tests` (id 58) khỏi tầm nhìn user thông thường.

### P1 — Giảm cognitive load
4. Tách Executive: gom 3 profitability dashboards (`Order/Product/Channel Profitability`) vào sub-collection `Executive > Profitability`.
5. Gộp/xóa sub-collection 1-board: nâng `Sales Promotion Analysis`, `US CrossBorder`, `Order Detail` lên parent.
6. Áp dụng suffix `[All]/[Retail]/[B2B]/[Cross]` cho **tên dashboard thực tế** (không chỉ trong doc).

### P2 — Enhancement
7. Đổi `Customer Intelligence Monthly` → Analytics collection (theo Layer 3 spec).
8. Move `Product Performance` & `Shopee Channel Economics` khỏi `Periodic Reviews` → `Analytics` (đây là analysis, không phải ops review).
9. Tạo `📍 Start Here` collection với 1 dashboard "How to use this Metabase".
10. Thêm validator script (CI) so sánh `collection_registry.yml` với grep `## Collection:` trong blueprints → fail nếu drift.
11. Standardize blueprint header: 1 format duy nhất cho `## 📂 Collection: A > B`.

---

## 8. Câu hỏi chưa giải quyết

1. **Analytics collection** — quyết định cuối là CÓ hay KHÔNG? 3 doc nói có, registry và Metabase live đều **chưa có**.
2. **7 cặp duplicate dashboard** — bản nào là canonical? Bản legacy hay bản `[suffix]` mới? Migration đang ở trạng thái nào?
3. Sự khác nhau giữa `Order Profitability` và `Order Profitability [All]` là gì? Có phải bản `[All]` là refactor mới (dùng scope_sales đúng) còn bản cũ vẫn dùng filter sai? Cần verify SQL bên trong.
4. Color-coding trong registry có được deploy script enforce vào Metabase API không? (Metabase API có field `color` ở collection nhưng output JSON không thấy custom color set.)
5. Team size hiện tại bao nhiêu user? (Thấy 5 personal collection trong API → ~5 user active.)
6. Có user nào đã complain về việc không tìm thấy dashboard? Có dashboard view count log không?
7. Sub-collection `B2B Operations` (2 board), `Retail Operations` (1 board), `CrossBorder Operations` (1 board), `Order Management` (1 board) — có roadmap mở rộng không? Nếu không, có nên gộp?
8. `Customer Intelligence Monthly` ở Marketing & Customers — analyst có thực sự dùng không, hay đây là dashboard "tạo cho có"?
