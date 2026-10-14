# Pack `hug` (orchestration)

**HUG là module nối lại khách từ sàn thương mại điện tử về mua trực tiếp với shop** (tại quầy, website). Phần dbt và mô tả đầy đủ: [transformation/models/packs/hug/README.md](../../../transformation/models/packs/hug/README.md).

Pack này **không có code Dagster riêng** (`ASSETS`, `NIGHTLY_ASSETS`, `JOBS`, `SCHEDULES`, `SENSORS` đều rỗng):

- Ingestion sự kiện quét/đăng ký là connector `hug` ([orchestration/connectors/hug/](../../connectors/hug/)): asset `ingest_hug_webhook_consumer_asset`, job `pipeline_hug_realtime_job` (*/3), ghi `data_lake/hug_raw/`. Connector lấy dữ liệu, pack dùng dữ liệu.
- Các model dbt của pack chạy trong asset dbt của kernel.
- Voucher HUG được app CRM phát (`crm/src/hug/`) và xuất về warehouse bởi pack `crm` (`crm_hug_voucher_export`).

Package có mặt để `packs:` trong `config/modules.yaml` khớp với phía dbt. Cấu hình riêng Fine Japan của luồng HUG (URL webhook worker) nằm ở `ingestion/.dlt/config.toml`, xem [orchestration/tenants/fine_japan/README.md](../../tenants/fine_japan/README.md).
