# Tổng quan Data Model — Phân loại & Attribution

> **Dành cho:** Data Team, Business Analysts
> **Cập nhật:** 2026-04-18
> **Bảo trì:** Data Team

## Mục đích

Tài liệu này cung cấp cái nhìn tổng quan về data model cho các chiều phân loại và attribution. Mỗi chiều được mô tả chi tiết trong tài liệu riêng.

---

## 1. Entity Relationships

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              STAR SCHEMA                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│                           ┌─────────────────┐                               │
│                           │   dim_channels  │                               │
│                           │─────────────────│                               │
│                           │ channel_category│                               │
│                           │ channel_format  │                               │
│                           │ platform        │                               │
│                           │ channel_name    │                               │
│                           │ source_type     │                               │
│                           └────────┬────────┘                               │
│                                    │                                        │
│  ┌─────────────────┐    ┌─────────┴─────────┐    ┌─────────────────┐       │
│  │   dim_teams     │    │                   │    │  dim_customers  │       │
│  │─────────────────│    │    fact_orders    │    │─────────────────│       │
│  │ team_code       │◄───│                   │───►│ customer_type   │       │
│  │ revenue_type    │    │    fact_sales     │    │ value_group     │       │
│  │ revenue_filter  │    │                   │    │ lifecycle_stage │       │
│  └─────────────────┘    └─────────┬─────────┘    │ ...8 dimensions │       │
│                                   │              └─────────────────┘       │
│                           ┌───────┴───────┐                                │
│                           │ dim_products  │                                │
│                           │───────────────│                                │
│                           │ brand_name    │                                │
│                           │ product_type  │                                │
│                           └───────────────┘                                │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Các Dimension Chính

| Dimension | Entity | Mô tả | Tài liệu chi tiết |
|-----------|--------|-------|-------------------|
| **Channel** | dim_channels | Bán ở đâu? 4-tier taxonomy | [sales-segmentation-guide.md](./sales-segmentation-guide.md) |
| **Team** | dim_teams | Ai sở hữu doanh số? | [team-management.md](./team-management.md) |
| **Customer** | dim_customers | Khách hàng là ai? 8 chiều phân loại | [customer-segmentation.md](./customer-segmentation.md) |
| **Product** | dim_products | Sản phẩm gì? Thương hiệu nào? | [sales-segmentation-guide.md](./sales-segmentation-guide.md#32-thương-hiệu-sản-phẩm-vs-thương-hiệu-kênh) |
| **Branch** | dim_branch_locations | Ai xử lý đơn? | [sales-segmentation-guide.md](./sales-segmentation-guide.md#33-chi-nhánh--ai-xử-lý) |

---

## 3. Nguyên tắc Thiết kế

| Nguyên tắc | Mô tả |
|------------|-------|
| **Single Responsibility** | Mỗi entity chỉ chứa thông tin thuộc về nó |
| **No Fallbacks** | Không dùng default values khi thiếu data — để NULL |
| **Explicit Classification** | `source_type` explicit trong seed, không derive từ tên |
| **SCD2 for Time-variant** | Team membership, customer attributes track lịch sử |
| **Config in Owner** | Team định nghĩa revenue_type, không phải Channel |
| **Derive over Capture** | Customer type join khi cần, không capture trên order |
| **Actual over Policy** | Giá thực tế trên order phản ánh pricing |

---

## 4. Source Type — Phân loại nguồn đơn hàng

Sapo `source` field chứa nhiều concepts khác nhau. Dùng `source_type` để phân loại:

| source_type | Mô tả | Ví dụ sources |
|-------------|-------|---------------|
| `channel` | Kênh bán hàng thực sự | Shopee, Zalo, POS, Web |
| `customer_type` | Loại khách hàng | Đại Lý, Chợ sỉ |
| `team` | Team/function xử lý | CS, Telesale |
| `purpose` | Mục đích đơn hàng | Test SP, Quà Tặng, Ưu đãi NV |
| `arrangement` | Thỏa thuận đặc biệt | US (CrossBorder Fulfillment) |

Chi tiết: [sales-segmentation-guide.md - Section 7](./sales-segmentation-guide.md#7-known-limitations--source-field-overloading)

---

## 5. Team Attribution

Team doanh số được xác định theo `revenue_type`:

| revenue_type | Logic | Ví dụ |
|--------------|-------|-------|
| `platform` | Doanh số từ platform (tier 3) | Team Marketplace owns Shopee, Lazada |
| `channel_name` | Doanh số từ channel_name (tier 4) | Team Retail owns POS - Trương Định |
| `member` | Tổng doanh số nhân viên trong team | Team Social, Team B2B |

Chi tiết: [team-management.md](./team-management.md)

---

## 6. Customer Segmentation

8 chiều phân loại độc lập:

| Nhóm | Chiều | Loại | Mô tả |
|------|-------|------|-------|
| **Commercial** | `customer_type` | Manual | RETAIL, WHOLESALE, PARTNER, STAFF, KOL |
| | `payment_behavior` | Auto | Hành vi thanh toán |
| **Behavioral** | `value_group` | Auto | VALUE_VIP, VALUE_GOLD, ... (RFM) |
| | `lifecycle_stage` | Auto | NEW, ACTIVE, AT_RISK, CHURNED |
| | `channel_preference` | Auto | Kênh mua ưa thích |
| | `product_affinity` | Auto | Brand ưa thích |
| **Demographic** | `geo_region` | Auto | Vị trí địa lý |
| | `acquisition_source` | Manual | Nguồn khách hàng |

Chi tiết: [customer-segmentation.md](./customer-segmentation.md)

---

## 7. Quy tắc Quan trọng

### 7.1. customer_type vs value_group

```
customer_type = Bản chất quan hệ       value_group = Giá trị đóng góp
       │                                      │
       ▼                                      ▼
  RETAIL, WHOLESALE,                   VALUE_VIP, VALUE_GOLD,
  PARTNER, STAFF, KOL                  VALUE_SILVER, VALUE_BRONZE

→ Khách lẻ chi 50M+ = customer_type=RETAIL + value_group=VALUE_VIP
→ Đại lý mới = customer_type=WHOLESALE + value_group=VALUE_BRONZE
```

### 7.2. Team không "own" Channel

```
SAI:  dim_channels.default_team = 'Marketplace'
ĐÚNG: dim_teams.revenue_type = 'platform', revenue_filter = 'Shopee,Lazada'

→ Team định nghĩa revenue logic, không phải Channel
```

### 7.3. Không capture customer_type trên Order

```
SAI:  fact_orders.customer_type = 'WHOLESALE'
ĐÚNG: fact_orders.customer_key → dim_customers.customer_type

→ Join khi query, không duplicate data
→ Giá thực tế trên order phản ánh pricing policy
```

---

## 8. Tài liệu liên quan

| Tài liệu | Nội dung |
|----------|----------|
| [sales-segmentation-guide.md](./sales-segmentation-guide.md) | 4-tier channel taxonomy, source_type |
| [team-management.md](./team-management.md) | Team revenue_type, attribution logic |
| [customer-segmentation.md](./customer-segmentation.md) | 8 dimensions, customer_type values |
| [sapo-platform.md](./sapo-platform.md) | Sapo API, data sources |
| [channel-grouping-analysis.md](./channel-grouping-analysis.md) | Analysis của channel grouping |

---

## Changelog

| Date | Change |
|------|--------|
| 2026-04-18 | Initial version — consolidate insights from source normalization discussion |
