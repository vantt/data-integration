# Pack `facebook_messenger` (orchestration)

Hội thoại Facebook Messenger: `dim_fb_conversations`, `fact_fb_messages` ở [transformation/models/packs/facebook_messenger/](../../../transformation/models/packs/facebook_messenger/).

Pack này **không có code Dagster riêng** (`ASSETS`, `NIGHTLY_ASSETS`, `JOBS`, `SCHEDULES`, `SENSORS` đều rỗng), và **các model dbt của nó đang tắt** bằng `config(enabled=false)` trong từng model: script ingestion (`ingestion/run_facebook_messenger_batch.py`) có nhưng connector `facebook_messenger` chưa có asset Dagster. Có tên trong `enabled_packs` không bật lại các model đó (config trong model thắng config theo thư mục).

Package có mặt để `packs:` trong `config/modules.yaml` khớp với phía dbt (biến `enabled_packs`).
