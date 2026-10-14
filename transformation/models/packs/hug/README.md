# Pack `hug` (dbt)

**HUG là module nối lại khách từ sàn thương mại điện tử về mua trực tiếp với shop** (tại quầy, website): khách mua trên sàn quét mã trong gói hàng, đăng ký nhận ưu đãi, nhận voucher qua CRM và mua lại ở kênh trực tiếp. Pack đo phễu đăng ký và đơn quy đổi voucher. Pack là sản phẩm dùng lại được; Fine Japan là doanh nghiệp đầu tiên bật dùng. Kiến trúc: [docs/architecture/modules.md](../../../../docs/architecture/modules.md) mục 8.

**Cho ai:** marketing/CSKH theo dõi khách sàn chuyển về kênh trực tiếp; app CRM (định danh khách đăng ký, phát voucher).

## Đầu vào

| Nguồn | Ghi bởi | Ghi chú |
|---|---|---|
| `src_hug_scan`, `src_hug_optin_event` (connector `hug`, `models/connectors/hug/`) | Connector `orchestration/connectors/hug/` (poll Cloudflare D1, ghi `data_lake/hug_raw/`) | Pack đọc connector của chính nó: `pack_connectors` có `hug: [hug]` |
| dbt source `crm_export.crm_hug_voucher` | Pack `crm` (`crm_writeback_assets`) | Voucher CRM đã phát và đã dùng |
| `core`: `dim_customers`, `fact_orders` | dbt | |
| `finance`: `fact_order_economics` | dbt | Biên lợi nhuận của đơn quy đổi (pack → pack, khai báo trong allowlist) |

## Đầu ra

| Model | Layer | Dùng ở |
|---|---|---|
| `stg_hug_scan`, `stg_hug_optin_event`, `stg_crm__hug_voucher` | staging (view) | Trong pack |
| `mart_hug_optin` | marts (rolling, serving) | App CRM (`crm/src/hug/`: định danh khách, phát voucher) |
| `mart_hug_attribution` | marts (rolling, serving) | Báo cáo quy đổi voucher HUG theo đơn |

## Cấu hình

Không có biến dbt riêng. Ingestion và endpoint webhook là của connector `hug` (`ingestion/.dlt/config.toml`, phần worker là cấu hình Fine Japan, xem [orchestration/tenants/fine_japan/README.md](../../../../orchestration/tenants/fine_japan/README.md)).

## Phần còn là dữ liệu Fine Japan

- Sự kiện quét/đăng ký và voucher là của khách Fine Japan; landing page và chiến dịch là của Fine Japan.

## Phụ thuộc chéo (ghi trong `scripts/checks/boundary_allowlist.yaml`)

- `mart_hug_attribution` → `fact_order_economics` (pack `finance`).
- `stg_crm__hug_voucher` đọc source `crm_export`.

Hướng sản phẩm (roadmap, không làm trong Đợt 1): agent friendly, data model chuẩn, phân quyền, API/CLI/MCP; giao diện admin và landing page dựng trên đó.
