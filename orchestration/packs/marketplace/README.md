# Pack `marketplace` (orchestration)

Logic dùng chung cho đơn hàng trên sàn thương mại điện tử: hiện là 3 model Shopee `int_shopee_order_items`, `int_shopee_order_fees`, `int_shopee_order_adjustments` ở [transformation/models/packs/marketplace/](../../../transformation/models/packs/marketplace/). Pack `finance` đọc `int_shopee_order_fees` (phụ thuộc pack → pack đã khai báo, [docs/architecture/modules.md §8](../../../docs/architecture/modules.md)).

Pack này **không có code Dagster riêng** (`ASSETS`, `NIGHTLY_ASSETS`, `JOBS`, `SCHEDULES`, `SENSORS` đều rỗng):

- Các model dbt của pack chạy trong asset dbt của kernel.
- Dữ liệu Shopee đến từ connector `shopee` ([orchestration/connectors/shopee/](../../connectors/shopee/)), connector duy nhất pack được đọc thẳng (`pack_connectors` trong `scripts/checks/model_buckets.yaml`).

Package có mặt để `packs:` trong `config/modules.yaml` khớp với phía dbt (biến `enabled_packs`).
