# Pack `facebook_ads` (orchestration)

Quảng cáo Facebook: `dim_fb_ads`, `fact_fb_ads_insights_daily` ở [transformation/models/packs/facebook_ads/](../../../transformation/models/packs/facebook_ads/).

Pack này **không có code Dagster riêng** (`ASSETS`, `NIGHTLY_ASSETS`, `JOBS`, `SCHEDULES`, `SENSORS` đều rỗng), và **các model dbt của nó đang tắt** bằng `config(enabled=false)` trong từng model: script ingestion (`ingestion/run_facebook_ads_batch.py`) có nhưng connector `facebook_ads` chưa có asset Dagster. Có tên trong `enabled_packs` không bật lại các model đó (config trong model thắng config theo thư mục).

Package có mặt để `packs:` trong `config/modules.yaml` khớp với phía dbt (biến `enabled_packs`).
