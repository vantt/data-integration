# Hướng dẫn Phân loại Kênh bán hàng & Gom nhóm Báo cáo

> **Dành cho:** Tất ca nhân sự xem/tạo báo cáo doanh thu
> **Cập nhật:** 2026-03-30
> **Bảo trì:** Data Team

## 1. Vấn đề

Mỗi người trong công ty có cách gom nhóm doanh thu khác nhau. Marketing gom theo "Shopee, Lazada, Facebook". Brand Manager gom theo "Fine Japan, JPC". Sếp hỏi "Ecommerce bán bao nhiêu?". Kết quả: các báo cáo mâu thuẫn nhau, không ai biết con số nào đúng.

**Nguyên nhân gốc:** mọi người đang trộn lẫn nhiều khái niệm khác nhau vào chung một từ "kênh bán hàng".

Tài liệu này thiết lập cách phân loại chuẩn cho toàn công ty.

---

## 2. Nguyên tắc cốt lõi

**Mỗi đơn hàng có thể được nhìn từ nhiều góc độ khác nhau. Mỗi góc độ trả lời MỘT câu hỏi. Các góc độ này độc lập nhau — có thể kết hợp tự do.**

```text
                    "Bán ở đâu?"                "Bán sản phẩm gì?"
                    Kênh bán hàng                Thương hiệu sản phẩm
                         |                              |
                         v                              v
                    +-----------+                +--------------+
                    | dim       |                | dim          |
                    | channels  |----> fact <----| products     |
                    +-----------+    sales       +--------------+
                                    line
                    +-----------+   items        +--------------+
                    | dim       |                | Thị trường   |
                    | branches  |----> fact <----| & Phân khúc  |
                    +-----------+    sales       +--------------+
                         ^                              ^
                         |                              |
                    "Ai xử lý?"                 "Bán cho ai?"
                    Chi nhánh                    Nội địa/Xuất khẩu
                                                B2C/B2B
```

Khi muốn xem doanh thu theo góc nào, chỉ cần gom nhóm (GROUP BY) theo cột tương ứng. Không cần tạo báo cáo riêng — cùng một bộ dữ liệu, nhìn từ nhiều phía.

---

## 3. Bảng tham chiếu nhanh

Khi cần báo cáo, tra bảng bên dưới để biết cần gom nhóm theo cột nào.

| Tôi muốn xem doanh thu theo...              | Gom nhóm theo                           | Ví dụ kết quả                               |
| --------------------------------------------- | ---------------------------------------- | ----------------------------------------------- |
| Ecommerce vs Offline                          | Phân loại kênh                        | Ecommerce: 70%, Offline: 30%                    |
| Loại kênh (Sàn, MXH, Web, Cửa hàng)      | Loại kênh                              | Marketplace: 50%, Social: 15%, Retail: 25%      |
| Từng nền tảng                              | Nền tảng                               | Shopee: 35%, Lazada: 10%, TikTok: 5%            |
| Từng nguồn cụ thể                         | Nguồn đơn hàng                       | Shopee JPC OFFICIAL: 12%, Shopee Fine Japan: 8% |
| Từng thương hiệu sản phẩm               | Thương hiệu SP                        | Fine Japan: 40%, FG Care: 25%, Fine Care: 15%   |
| Từng thương hiệu kênh                    | Thương hiệu kênh                     | JPC: 35%, Fine Japan: 30%, The Healthy Us: 20%  |
| Từng chi nhánh                              | Chi nhánh                               | Trương Dinh: 50%, Hau Giang: 30%              |
| Nội địa vs Xuất khẩu                     | Thị trường                            | Domestic: 95%, Export: 5%                       |
| Bán lẻ vs Bán sỉ                          | Phân khúc KH                           | B2C: 85%, B2B: 15%                              |
| SP Fine Japan bán nhiều nhất ở sàn nào? | Thương hiệu SP + Nền tảng           | *(kết hợp 2 chiều)*                        |
| JPC bán bao nhiêu SP Fine Japan?            | Thương hiệu kênh + Thương hiệu SP | *(kết hợp 2 chiều)*                        |

---

## 4. Chi tiết từng chiều phân loại

### 4.1. Kênh bán hàng — "Bán ở đâu?"

Kênh bán hàng có 3 tầng, từ tổng quát đến chi tiết:

```text
Tầng 1 — Phân loại kênh (Ecommerce / Offline / Internal)
  └── Tầng 2 — Loại kênh (Marketplace / Social Commerce / Website / Retail / B2B)
        └── Tầng 3 — Nền tảng (Shopee / Lazada / Facebook / POS / ...)
              └── (Nguồn đơn hàng cụ thể)
```

Bảng phân loại đầy đủ:

| Tầng 1: Phân loại kênh   | Tầng 2: Loại kênh    | Tầng 3: Nền tảng | Nguồn cụ thể (ví dụ)                          |
| ---------------------------- | ----------------------- | ------------------- | -------------------------------------------------- |
| **Ecommerce (Online)** | Marketplace (Sàn TMDT) | Shopee              | Shopee - JPC OFFICIAL, Shopee - Fine Japan Vietnam |
|                              |                         | Lazada              | Lazada - JPC SHOP, Lazada - Fine Japan Vietnam     |
|                              |                         | TikTok              | TiktokShop                                         |
|                              |                         | Tiki                | Tiki - FINE WORLD GROUP                            |
|                              |                         | Sendo               | Sendo                                              |
|                              |                         | Grab                | GrabMart                                           |
|                              | Social Commerce (MXH)   | Facebook            | Facebook, FaceBookJPC, FaceBookFJPTViet            |
|                              |                         | Instagram           | Instagram                                          |
|                              |                         | Zalo                | Zalo                                               |
|                              | Website (DTC)           | Website             | Web, WebOrder                                      |
| **Offline**            | Retail (Cửa hàng)     | POS                 | POS - Trương Dinh, POS - Hau Giang               |
|                              | B2B (Bán sỉ)          | Wholesale           | Đại Lý, Chợ sỉ                                |
| **Internal**           | System (Nội bộ)       | System              | Telesale, CS, Test Sản Phẩm, Quà Tặng          |

**Lưu ý:**

- **Ecommerce** bao gồm tất cả kênh bán hàng trực tuyến: sàn TMDT, mạng xã hội, và website. Đây là nghĩa rộng của "thương mại điện tử".
- Nguồn **Internal** (Telesale, CS, Test, Quà Tặng...) **không tính vào doanh thu bán hàng** trong các báo cáo sales. Chúng phục vụ mục đích nội bộ.
- Mỗi nền tảng có thể có nhiều nguồn cụ thể (nhiều shop trên Shopee, nhiều page Facebook...).

---

### 4.2. Thương hiệu sản phẩm vs. Thương hiệu kênh — Khái niệm quan trọng nhất

Đây là khái niệm **dễ nhầm lẫn nhất** trong toàn bộ hệ thống phân loại. Công ty có hai loại thương hiệu hoàn toàn khác nhau:

#### Thương hiệu sản phẩm (Product Brand)

**Định nghĩa:** Thương hiệu gắn liền với sản phẩm — ai sản xuất, ai sở hữu sản phẩm đó.

Ví dụ: Fine Japan Vietnam, FG Care, Fine Care.

Mỗi sản phẩm (SKU) thuộc về **đúng một** thương hiệu sản phẩm. Thông tin này nằm trên dữ liệu sản phẩm (trường "vendor" trên Sapo).

#### Thương hiệu kênh (Channel Brand)

**Định nghĩa:** Thương hiệu mà công ty **tạo ra để xây kênh bán hàng**. Đây là "danh nghĩa" mà khách hàng nhìn thấy khi mua hàng.

Ví dụ:

- **JPC (Japanese Premium Collection)**: thương hiệu kênh do công ty tạo ra, chuyên bán nhiều sản phẩm Nhật từ nhiều nhà sản xuất khác nhau. JPC có shop Shopee, Lazada, Website, Facebook riêng.
- **Fine Japan Vietnam**: vừa là thương hiệu sản phẩm, vừa là thương hiệu kênh (có shop riêng bán chính sản phẩm Fine Japan).
- **The Healthy Us**: thương hiệu kênh, bán sản phẩm từ nhiều thương hiệu sản phẩm khác nhau.

#### Tại sao phải phân biệt?

Vì một shop (kênh) có thể bán sản phẩm của nhiều thương hiệu:

```text
Shop "JPC OFFICIAL" trên Shopee            (Thương hiệu kênh: JPC)
  |
  |--- Bán sản phẩm Fine Japan             (Thương hiệu SP: Fine Japan)
  |--- Bán sản phẩm FG Care                (Thương hiệu SP: FG Care)
  |--- Bán sản phẩm nhập từ Nhật khác      (Thương hiệu SP: khác)
```

Nếu trộn lẫn hai khái niệm này, khi hỏi "doanh thu Fine Japan bao nhiêu?" sẽ không biết đang hỏi:

- **(A)** Tổng doanh thu **sản phẩm** Fine Japan, bất kể bán ở shop nào? (kể cả bán trên shop JPC)
- **(B)** Tổng doanh thu **các kênh** mang tên Fine Japan? (chỉ shop Fine Japan Vietnam, không tính shop JPC)

Hai con số này **khác nhau**. Hệ thống phân loại cho phép trả lời cả hai:

| Câu hỏi                                     | Cách lọc                                                        |
| --------------------------------------------- | ----------------------------------------------------------------- |
| (A) Doanh thu SP Fine Japan ở mọi kênh     | Thương hiệu sản phẩm = "Fine Japan Vietnam"                  |
| (B) Doanh thu các kênh Fine Japan           | Thương hiệu kênh = "Fine Japan Vietnam"                       |
| JPC bán bao nhiêu SP Fine Japan?            | Thương hiệu kênh = "JPC" AND Thương hiệu SP = "Fine Japan" |
| SP Fine Japan bán mạnh nhất ở kênh nào? | Thương hiệu SP = "Fine Japan" + gom theo Thương hiệu kênh  |

#### Bảng tham chiếu thương hiệu

| Tên               | Là TH sản phẩm? | Là TH kênh? | Ghi chú                                         |
| ------------------ | ------------------ | ------------- | ------------------------------------------------ |
| Fine Japan Vietnam | Co                 | Co            | Vừa sản xuất, vừa có kênh riêng           |
| FG Care            | Co                 | Co            | Vừa sản xuất, vừa có kênh riêng           |
| Fine Care          | Co                 | Co            | Vừa sản xuất, vừa có kênh riêng           |
| JPC                | Khong              | Co            | Chỉ là thương hiệu kênh, không sản xuất |
| The Healthy Us     | Khong              | Co            | Chỉ là thương hiệu kênh, không sản xuất |
| Fine World Group   | Khong              | Co            | Thương hiệu công ty mẹ                      |

---

### 4.3. Chi nhánh — "Ai xử lý?"

Chi nhánh là đơn vị vật lý chịu trách nhiệm thực hiện đơn hàng (lưu kho, đóng gói, giao hàng, hoặc bán tại quầy).

| Chi nhánh        | Ma  | Ghi chú              |
| ----------------- | --- | --------------------- |
| 16 Trương Dinh  | VVT | Trụ sở / kho chính |
| Hậu Giang        | HG  |                       |
| MM Market An Phú | MMA |                       |
| TheHealthyUs      | HUS |                       |
| ShowroomVVT       | ST  |                       |

**Lưu ý:** Chi nhánh liên quan đến **vận hành**, không liên quan đến kênh bán. Một đơn hàng từ Shopee có thể được xử lý bởi bất kỳ chi nhánh nào.

---

### 4.4. Thị trường & Phân khúc khách hàng

Hai phân loại bổ sung, dùng khi cần tách riêng doanh thu theo đối tượng:

| Chiều phân loại       | Giá trị             | Áp dụng cho                              |
| ------------------------ | --------------------- | ------------------------------------------ |
| **Thị trường**  | Domestic (Nội địa) | Hầu hết các kênh                       |
|                          | Export (Xuất khẩu)  | US, và các kênh xuất khẩu tương lai |
| **Phân khúc KH** | B2C (Bán lẻ)        | Shopee, Lazada, Website, POS...            |
|                          | B2B (Bán sỉ)        | Đại Lý, Chợ Sỉ                        |

---

## 5. Ví dụ kết hợp thực tế

Sức mạnh của hệ thống phân loại này nằm ở khả năng **kết hợp nhiều chiều** trong cùng một báo cáo.

### Ví dụ 1: "Shopee đang bán thương hiệu nào tốt nhất?"

> Gom nhóm: **Nền tảng** = Shopee + gom theo **Thương hiệu kênh**

| Thương hiệu kênh | Doanh thu Shopee |
| -------------------- | ---------------- |
| JPC                  | 120,000,000      |
| Fine Japan Vietnam   | 85,000,000       |
| The Healthy Us       | 45,000,000       |
| FG Care              | 30,000,000       |

### Ví dụ 2: "SP Fine Japan bán trên kênh nào nhiều nhất?"

> Lọc: **Thương hiệu SP** = Fine Japan + gom theo **Nền tảng**

| Nền tảng | Doanh thu SP Fine Japan |
| ---------- | ----------------------- |
| Shopee     | 95,000,000              |
| Lazada     | 40,000,000              |
| POS        | 35,000,000              |
| Website    | 15,000,000              |

### Ví dụ 3: "So sánh hiệu quả kênh JPC vs kênh Fine Japan trên Marketplace"

> Lọc: **Loại kênh** = Marketplace + gom theo **Thương hiệu kênh** + **Nền tảng**

| TH kênh   | Shopee | Lazada | TikTok | Tiki |
| ---------- | ------ | ------ | ------ | ---- |
| JPC        | 120M   | 45M    | 30M    | 10M  |
| Fine Japan | 85M    | 35M    | —     | 8M   |

### Ví dụ 4: "Báo cáo tổng quát cho CEO"

> Gom nhóm: **Phân loại kênh** (tầng 1)

| Kênh     | Doanh thu   | Tỷ trọng |
| --------- | ----------- | ---------- |
| Ecommerce | 450,000,000 | 72%        |
| Offline   | 175,000,000 | 28%        |

---

## 6. Tài liệu kỹ thuật (dành cho Data Team)

### 6.1. Tổng quan kiến trúc

Hệ thống phân loại kênh bán hàng được xây dựng trên mô hình Star Schema. Dữ liệu bán hàng (fact) được phân tích qua nhiều chiều (dimension) độc lập, cho phép báo cáo linh hoạt mà không cần thay đổi cấu trúc.

```text
                              ┌─────────────────────┐
                              │   dim_channels       │
                              │─────────────────────│
                              │ channel_key (SK)     │
                              │ channel_name         │
                              │ channel_code         │
                              │ channel_category     │  ← derived
                              │ platform_group       │
                              │ platform             │
                              │ channel_brand        │  ← from seed
                              │ market               │  ← from seed
                              │ customer_segment     │  ← from seed
                              │ is_sales_channel     │  ← derived
                              │ source_id            │
                              │ location_id          │
                              │ is_active            │
                              └────────┬────────────┘
                                       │
┌─────────────────────┐       ┌────────┴────────────┐       ┌─────────────────────┐
│   dim_products       │       │   fact_sales         │       │ dim_branch_locations │
│─────────────────────│       │─────────────────────│       │─────────────────────│
│ product_key (SK)     │──────│ product_key (FK)     │       │ branch_location_key  │
│ product_id           │       │ channel_key (FK)     │──────│ branch_location_id   │
│ variant_id           │       │ branch_key (FK)      │       │ branch_location_name │
│ sku                  │       │ order_date           │       │ branch_location_code │
│ barcode              │       │ quantity             │       └─────────────────────┘
│ product_name         │       │ revenue              │
│ variant_name         │       │ discount             │
│ product_type         │       │ ...                  │
│ brand_name           │  ←    └─────────────────────┘
│ brand_code           │  ←
│ unit                 │
│ weight_grams         │
│ last_sold_price      │
│ last_seen_at         │
└─────────────────────┘
```

### 6.2. Seed Files — Dữ liệu tham chiếu

Seed files là các file CSV chứa dữ liệu phân loại, được maintain thủ công bởi Data Team.

#### 6.2.1. ref_order_sources — Danh sách nguồn đơn hàng

> **File:** `transformation/seeds/ref_order_sources.csv`

Mỗi dòng đại diện cho một nguồn đơn hàng cụ thể trong Sapo (một shop trên sàn, một page Facebook, POS, hoặc nguồn nội bộ).

**Schema đầy đủ:**

| Cột                  | Kiểu   | Bắt buộc | Mô tả                                                                                                    | Ví dụ                         |
| --------------------- | ------- | ---------- | ---------------------------------------------------------------------------------------------------------- | ------------------------------- |
| `id`                | string  | Co         | ID nguồn trên Sapo. Dạng gốc (ví dụ `3988158`) hoặc composite cho sub-source (`3988158_1`)      | `3988158_1`                   |
| `name`              | string  | Co         | Tên hiển thị đầy đủ                                                                                 | `Shopee - Fine Japan Vietnam` |
| `status`            | boolean | Co         | Nguồn còn hoạt động không                                                                            | `true`                        |
| `platform_group`    | string  | Co         | Loại kênh (Tầng 2). Giá trị:`Ecom`, `Social`, `Web`, `Retail`, `B2B`, `System`, `Other` | `Ecom`                        |
| `is_generic_source` | boolean | Co         | `true` nếu nguồn cần expand theo chi nhánh (hiện chỉ POS)                                          | `false`                       |
| `platform`          | string  | Co         | Nền tảng cụ thể (Tầng 3)                                                                              | `Shopee`                      |
| `mapping_tag`       | string  | Khong      | Tag dùng để map đơn hàng từ Sapo vào nguồn cụ thể                                               | `Shopee_Fine Japan Vietnam`   |
| `channel_brand`     | string  | Khong      | Thương hiệu kênh sở hữu nguồn này                                                                  | `Fine Japan Vietnam`          |
| `market`            | string  | Co         | Thị trường. Giá trị:`Domestic`, `Export`                                                          | `Domestic`                    |
| `customer_segment`  | string  | Co         | Phân khúc khách hàng. Giá trị:`B2C`, `B2B`                                                       | `B2C`                         |

**Quy tắc platform_group:**

| Giá trị platform_group | Ý nghĩa                                   | Thuộc channel_category |
| ------------------------ | ------------------------------------------- | ----------------------- |
| `Ecom`                 | Sàn thương mại điện tử (Marketplace) | Ecommerce               |
| `Social`               | Mạng xã hội (Social Commerce)            | Ecommerce               |
| `Web`                  | Website công ty (DTC)                      | Ecommerce               |
| `Retail`               | Cửa hàng vật lý                         | Offline                 |
| `B2B`                  | Bán sỉ, đại lý                         | Offline                 |
| `System`               | Nội bộ (Telesale, CS, Test...)            | Internal                |
| `Other`                | Khác                                       | Other                   |

**Quy tắc is_generic_source:**

- `false` (mặc định): Nguồn map 1-1 thành 1 channel trong `dim_channels`.
- `true`: Nguồn được expand bằng cách cross-join với `ref_branch_locations`, tạo 1 channel cho mỗi chi nhánh. Hiện chỉ áp dụng cho POS (cửa hàng vật lý).

**Ví dụ dữ liệu đầy đủ:**

```csv
id,name,status,platform_group,is_generic_source,platform,mapping_tag,channel_brand,market,customer_segment
3988158_1,Shopee - Fine Japan Vietnam,true,Ecom,false,Shopee,"Shopee_Fine Japan Vietnam",Fine Japan Vietnam,Domestic,B2C
3988158_4,Shopee - JPC OFFICIAL,true,Ecom,false,Shopee,Shopee_JPC OFFICIAL,JPC,Domestic,B2C
3988158_8,Shopee - FINE WORLD GROUP,true,Ecom,false,Shopee,Shopee_FINE WORLD GROUP,Fine World Group,Domestic,B2C
3988155_2,Lazada - JPC SHOP,true,Ecom,false,Lazada,Lazada_JPC SHOP,JPC,Domestic,B2C
3988153,Facebook,true,Social,false,Facebook,,,Domestic,B2C
3988152,Web,true,Web,false,Website,,,Domestic,B2C
3988157,Pos,true,Retail,true,Retail,,,Domestic,B2C
4164989,Đại Lý,false,B2B,false,Wholesale,,,Domestic,B2B
4110169,US,false,Other,false,Other,,,Export,B2B
4517138,Telesale,false,System,false,System,,,Domestic,B2C
```

#### 6.2.2. ref_brands — Chuẩn hóa tên thương hiệu sản phẩm

> **File:** `transformation/seeds/ref_brands.csv` *(seed mới)*

Bảng mapping để chuẩn hóa giá trị `vendor` trên Sapo thành tên thương hiệu sản phẩm thống nhất. Cần thiết vì vendor trên Sapo có thể ghi không nhất quán (viết hoa/thường, viết tắt, thiếu hậu tố...).

**Schema:**

| Cột           | Kiểu  | Mô tả                                              | Ví dụ                |
| -------------- | ------ | ---------------------------------------------------- | ---------------------- |
| `vendor_raw` | string | Giá trị vendor gốc trên Sapo (khớp chính xác) | `Fine Japan`         |
| `brand_name` | string | Tên thương hiệu sản phẩm chuẩn                | `Fine Japan Vietnam` |
| `brand_code` | string | Mã viết tắt                                       | `FJV`                |

**Ví dụ dữ liệu:**

```csv
vendor_raw,brand_name,brand_code
Fine Japan,Fine Japan Vietnam,FJV
Fine Japan Vietnam,Fine Japan Vietnam,FJV
FINE JAPAN,Fine Japan Vietnam,FJV
JPC,JPC,JPC
FG Care,FG Care,FGC
FG CARE,FG Care,FGC
The Healthy Us,The Healthy Us,THU
Fine Care,Fine Care,FC
```

**Lưu ý:** Nếu một vendor trên Sapo không có trong bảng này, `dim_products` sẽ giữ nguyên giá trị vendor gốc làm `brand_name` và đặt `brand_code = NULL`. Khi phát hiện vendor mới, Data Team cần bổ sung vào bảng này.

#### 6.2.3. ref_branch_locations — Danh sách chi nhánh

> **File:** `transformation/seeds/ref_branch_locations.csv` *(không thay đổi)*

**Schema:**

| Cột     | Kiểu   | Mô tả                  | Ví dụ                |
| -------- | ------- | ------------------------ | ---------------------- |
| `id`   | integer | ID chi nhánh trên Sapo | `68578`              |
| `code` | string  | Mã viết tắt           | `VVT`                |
| `name` | string  | Tên chi nhánh          | `16 Trương Định` |

---

### 6.3. Dimension Models — Logic xây dựng

#### 6.3.1. dim_channels — Chiều kênh bán hàng

> **File:** `transformation/models/marts/core/dim_channels.sql`

**Nguồn dữ liệu:** `ref_order_sources`, `ref_branch_locations`

**Logic xây dựng:**

```text
Bước 1: Lấy specific sources (is_generic_source = false)
        → Mỗi source = 1 channel, location_id = NULL

Bước 2: Lấy generic sources (is_generic_source = true)
        → Cross-join với ref_branch_locations
        → Mỗi source x location = 1 channel

Bước 3: UNION ALL kết quả bước 1 và 2

Bước 4: Derive các cột tính toán:
        → channel_category = CASE platform_group
              WHEN 'Ecom'   THEN 'Ecommerce'
              WHEN 'Social' THEN 'Ecommerce'
              WHEN 'Web'    THEN 'Ecommerce'
              WHEN 'Retail' THEN 'Offline'
              WHEN 'B2B'    THEN 'Offline'
              WHEN 'System' THEN 'Internal'
              ELSE 'Other'
          END
        → is_sales_channel = (platform_group != 'System')

Bước 5: Generate surrogate key từ source_id + COALESCE(location_id, 'Unknown')

Bước 6: Thêm Unknown Member (cho đơn hàng không xác định được kênh)
```

**Output schema đầy đủ:**

| Cột                 | Kiểu   | Null  | Mô tả                        | Nguồn                                                   |
| -------------------- | ------- | ----- | ------------------------------ | -------------------------------------------------------- |
| `channel_key`      | string  | Khong | Surrogate key (MD5)            | Generated                                                |
| `channel_name`     | string  | Khong | Tên hiển thị                | Seed:`name` (specific) hoặc `branch.name` (generic) |
| `channel_code`     | string  | Khong | Mã viết tắt                 | Seed:`name` (specific) hoặc `branch.code` (generic) |
| `channel_category` | string  | Khong | Ecommerce / Offline / Internal | Derived từ `platform_group`                           |
| `platform_group`   | string  | Khong | Loại kênh (Tầng 2)          | Seed:`platform_group`                                  |
| `platform`         | string  | Khong | Nền tảng (Tầng 3)           | Seed:`platform`                                        |
| `channel_brand`    | string  | Co    | Thương hiệu kênh           | Seed:`channel_brand`                                   |
| `market`           | string  | Khong | Domestic / Export              | Seed:`market`                                          |
| `customer_segment` | string  | Khong | B2C / B2B                      | Seed:`customer_segment`                                |
| `is_sales_channel` | boolean | Khong | true = kênh bán hàng thật  | Derived:`platform_group != 'System'`                   |
| `source_id`        | string  | Co    | FK về Sapo source             | Seed:`id`                                              |
| `location_id`      | string  | Co    | FK về chi nhánh (chỉ POS)   | Branch:`id`                                            |
| `is_active`        | boolean | Khong | Nguồn còn hoạt động       | Seed:`status`                                          |

#### 6.3.2. dim_products — Chiều sản phẩm

> **File:** `transformation/models/marts/core/dim_products.sql`

**Nguồn dữ liệu:** `std_order_items`, `ref_brands`

**Logic xây dựng:**

```text
Bước 1: Lấy tất cả order items có product_id NOT NULL

Bước 2: ROW_NUMBER() PARTITION BY product_id, variant_id ORDER BY extracted_at DESC
        → Giữ bản ghi mới nhất cho mỗi sản phẩm ("Last Record Wins")

Bước 3: LEFT JOIN ref_brands ON UPPER(vendor) = UPPER(vendor_raw)
        → Map vendor gốc sang brand_name và brand_code chuẩn hóa
        → Fallback: nếu không match, giữ vendor gốc làm brand_name

Bước 4: Generate surrogate key từ product_id + variant_id

Bước 5: Thêm Unknown Member
```

**Output schema đầy đủ:**

| Cột                | Kiểu     | Null  | Mô tả                            | Nguồn                       |
| ------------------- | --------- | ----- | ---------------------------------- | ---------------------------- |
| `product_key`     | string    | Khong | Surrogate key (MD5)                | Generated                    |
| `product_id`      | string    | Khong | ID sản phẩm trên Sapo           | Order items                  |
| `variant_id`      | string    | Co    | ID biến thể                      | Order items                  |
| `sku`             | string    | Co    | Mã SKU                            | Order items                  |
| `barcode`         | string    | Co    | Mã barcode                        | Order items                  |
| `product_name`    | string    | Khong | Tên sản phẩm                    | Order items                  |
| `variant_name`    | string    | Co    | Tên biến thể                    | Order items                  |
| `product_type`    | string    | Co    | Loại sản phẩm                   | Order items                  |
| `brand_name`      | string    | Co    | Thương hiệu SP chuẩn hóa      | ref_brands hoặc vendor gốc |
| `brand_code`      | string    | Co    | Mã TH viết tắt                  | ref_brands                   |
| `unit`            | string    | Co    | Đơn vị                          | Order items                  |
| `weight_grams`    | numeric   | Co    | Trọng lượng (gram)              | Order items                  |
| `last_sold_price` | numeric   | Co    | Giá bán gần nhất               | Order items                  |
| `last_seen_at`    | timestamp | Co    | Lần cuối xuất hiện trong đơn | Order items                  |

#### 6.3.3. dim_branch_locations — Chiều chi nhánh

> **File:** `transformation/models/marts/core/dim_branch_location.sql` *(không thay đổi)*

**Output schema:**

| Cột                     | Kiểu  | Mô tả             |
| ------------------------ | ------ | ------------------- |
| `branch_location_key`  | string | Surrogate key (MD5) |
| `branch_location_id`   | string | ID trên Sapo       |
| `branch_location_name` | string | Tên chi nhánh     |
| `branch_location_code` | string | Mã viết tắt      |

---

### 6.4. Fact Tables — Không thay đổi

Các bảng fact không cần sửa đổi. Chúng đã có sẵn các foreign key cần thiết:

| Fact Table               | channel_key | product_key | branch_key | Ghi chú                              |
| ------------------------ | ----------- | ----------- | ---------- | ------------------------------------- |
| `fact_orders`          | Co          | Khong       | Co         | Grain: 1 đơn hàng                  |
| `fact_sales`           | Co          | Co          | Co         | Grain: 1 dòng sản phẩm trong đơn |
| `fact_marketing_spend` | Co          | Khong       | Khong      | Grain: chi phí theo kênh/ngày      |
| `fact_targets`         | Co          | Khong       | Khong      | Grain: chỉ tiêu theo kênh/kỳ      |

**Lưu ý:** Báo cáo theo **thương hiệu sản phẩm** chỉ khả dụng trên `fact_sales` (có `product_key`), không khả dụng trên `fact_orders` (không có product detail).

---

### 6.5. Mapping thuật ngữ kinh doanh — Tên cột kỹ thuật

Bảng tra cứu nhanh cho người tạo báo cáo trên Metabase hoặc SQL:

| Thuật ngữ trong báo cáo | Bảng                | Tên cột                | Giá trị mẫu                          |
| --------------------------- | -------------------- | ------------------------ | --------------------------------------- |
| Phân loại kênh (Tầng 1) | dim_channels         | `channel_category`     | Ecommerce, Offline, Internal            |
| Loại kênh (Tầng 2)       | dim_channels         | `platform_group`       | Ecom, Social, Web, Retail, B2B, System  |
| Nền tảng (Tầng 3)        | dim_channels         | `platform`             | Shopee, Lazada, Facebook, Website, POS  |
| Thương hiệu kênh        | dim_channels         | `channel_brand`        | JPC, Fine Japan Vietnam, The Healthy Us |
| Nguồn đơn hàng          | dim_channels         | `channel_name`         | Shopee - JPC OFFICIAL                   |
| Thị trường               | dim_channels         | `market`               | Domestic, Export                        |
| Phân khúc KH              | dim_channels         | `customer_segment`     | B2C, B2B                                |
| Chỉ kênh bán hàng thật | dim_channels         | `is_sales_channel`     | true / false                            |
| Thương hiệu sản phẩm   | dim_products         | `brand_name`           | Fine Japan Vietnam, FG Care             |
| Mã TH sản phẩm           | dim_products         | `brand_code`           | FJV, FGC, FC                            |
| Chi nhánh                  | dim_branch_locations | `branch_location_name` | 16 Trương Định, Hậu Giang          |

---

### 6.6. Quy trình vận hành

#### Khi thêm nguồn đơn hàng mới (shop mới, page mới...)

1. Tạo nguồn đơn hàng trên Sapo
2. Thêm 1 dòng vào `ref_order_sources.csv`:
   | Cột                  | Hành động                                                      |
   | --------------------- | ----------------------------------------------------------------- |
   | `id`                | Lấy ID từ Sapo, hoặc tạo composite ID (ví dụ:`3988158_9`) |
   | `name`              | Đặt tên dạng "Platform - Shop Name"                           |
   | `status`            | `true`                                                          |
   | `platform_group`    | Chọn: Ecom / Social / Web / Retail / B2B / System / Other        |
   | `is_generic_source` | `false` (trừ khi là loại cần expand theo chi nhánh)        |
   | `platform`          | Tên nền tảng cụ thể                                          |
   | `mapping_tag`       | Tag khớp với dữ liệu Sapo (nếu có)                          |
   | `channel_brand`     | Thương hiệu kênh sở hữu                                     |
   | `market`            | Domestic hoặc Export                                             |
   | `customer_segment`  | B2C hoặc B2B                                                     |
3. Chạy `dbt build --select ref_order_sources+ ` để cập nhật seed và các model phụ thuộc
4. Kiểm tra nguồn mới xuất hiện đúng trong `dim_channels`

#### Khi phát hiện vendor mới trên Sapo

1. Query `dim_products` để tìm sản phẩm có `brand_code = NULL`
2. Thêm mapping vào `ref_brands.csv`
3. Chạy `dbt build --select ref_brands dim_products`

#### Khi thay đổi cơ cấu tổ chức (thêm chi nhánh, đổi team...)

- **Thêm chi nhánh:** Thêm dòng vào `ref_branch_locations.csv`. POS channels tự động expand.
- **Đổi team/phân công:** Không ảnh hưởng data model. Team hiện derive từ `platform_group`. Nếu cần báo cáo theo team khác cơ cấu hiện tại, thêm cột `team` vào `ref_order_sources`.

---

### 6.7. Lưu ý về chất lượng dữ liệu

| Rủi ro                                  | Ảnh hưởng                                                                    | Cách phát hiện                                         | Cách xử lý                                                  |
| ---------------------------------------- | ------------------------------------------------------------------------------- | --------------------------------------------------------- | -------------------------------------------------------------- |
| `vendor` trống trên Sapo             | brand_name = NULL, không gom nhóm được                                     | Query:`WHERE brand_name IS NULL` trên dim_products     | Bổ sung vendor trên Sapo hoặc thêm mapping vào ref_brands |
| `vendor` ghi không nhất quán        | Cùng brand nhưng tách thành nhiều dòng                                    | Query:`GROUP BY brand_name` tìm tên gần giống       | Thêm tất cả biến thể vào ref_brands                      |
| Đơn hàng không có source trên Sapo | channel = Unknown                                                               | Query:`WHERE channel_name = 'Unknown'` trên fact_sales | Kiểm tra quy trình tạo đơn trên Sapo                     |
| Shop mới chưa thêm vào seed          | Đơn hàng rơi vào source cha (ví dụ: "Shopee" thay vì "Shopee - Shop X") | So sánh source IDs trong raw data vs ref_order_sources   | Thêm dòng mới vào ref_order_sources                        |
