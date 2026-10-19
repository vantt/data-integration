# Phase 5: hợp đồng cache chuẩn từ kho (v1)

**Effort:** 5d (nửa kho 2.5d, nửa CRM 2.5d) · **Phụ thuộc:** phase 0 (nửa kho); phase 4 (nửa CRM) · **Đụng prod:** có (data_platform và CRM) · **Cần user duyệt giờ:** có (hai deploy) · **Migration:** không ở `crm.db` (cache dựng lại được)

## Bối cảnh

- Cache hiện có 11 bảng `wh_*` theo nhu cầu Fine Japan (`crm/sync/cache_schema.sql`), sync đọc thẳng `main_marts.*` (`crm/sync/duckdb_reader.py`) và chép vào `cache.db` (`reverse_etl_warehouse_to_crm.py:176-232`). Chạy khi CRM khởi động và mỗi lần `/admin/refresh` (sau mỗi lần build serving của 6 job connector).
- Người đọc cache (ngoài `crm/sync`): `cache_repository.py`, `action_state_repository.py`, `action_catalog_repository.py`, `segment_service.py`, `campaign_service.py`, `campaign_repository.py`, `task_service.py`, `reason_rail.py`, `worklist_ranking.py`, `party_seed_service.py`, `party_service.py`, `tag_acl_sync_service.py`, `sync_party_tags.py`, `hug/targeting_engine.py`, `hug/customer_push.py`, `hug/sapo_order_proxy.py`, `hug/identity_resolver_io.py`, `adapters/inbound/http/admin_handler.py`, `adapters/inbound/http/task_handler.py`, entity `cache_insight.py`, `party.py`, `task.py`; và **ngoài `crm/`**: `orchestration/packs/sales_playbook/approach_script_generation.py` (đọc `wh_sku_action_queue`).
- Thiết kế hợp đồng: design §4. Bảng không ai đọc (`wh_product`, `wh_product_insight`, `wh_order_cogs_summary`) bị bỏ khỏi hợp đồng.

## Yêu cầu

### Nửa kho (làm song song được sau phase 0)

1. **Model hợp đồng** trong `transformation/models/packs/crm/contract/`: `crm_contract__party_source`, `crm_contract__party_source_contact`, `crm_contract__customer_summary`, `crm_contract__transaction`, `crm_contract__signal`, `crm_contract__signal_type`, `crm_contract__retail_deadstock_target`. Chỉ chọn và đổi tên cột từ mart hiện có, **không tính lại số**. Có `_crm_contract__models.yml` với mô tả cột, test `unique`/`not_null` theo khoá ở design §4.2, và `meta.contract_version: 1`.
2. Materialization theo kết luận phase 0: view dbt nếu serving phơi được view của pack mà không tốn build; nếu không, thay bằng file SQL có phiên bản `crm/sync/contract/v1/*.sql` (cùng tên và cột) và bỏ phần dbt (ghi lý do trong README pack).
3. Đăng ký model mới trong `scripts/checks/public_models.yaml` (là hợp đồng công khai) và ghi danh sách 6 view serving mà CRM đọc trực tiếp (design H10) với ghi chú "CRM đọc".
4. `margin_level` lấy theo kết quả phase 0 (bậc CM thật của `lifetime_contribution_margin`); `lifetime_margin_vnd` NULL khi pack finance tắt (dùng `pack_ref` như lõi đang làm).

### Nửa CRM

5. **Bộ sync** (`crm/sync/`): thêm DDL bảng hợp đồng vào `cache_schema.sql`; đọc model hợp đồng và chép 1:1 vào `wh_party_source`, `wh_party_source_contact`, `wh_customer_summary`, `wh_transaction` (giữ HWM theo `date_key`), `wh_signal`, `wh_signal_type`, `wh_retail_deadstock_target`, `wh_contract_meta`. **Vẫn ghi bảng cũ** như hiện tại trong cùng lần chạy. Nếu đọc hợp đồng lỗi (chưa deploy nửa kho) thì bỏ qua bảng mới, ghi `wh_sync_run` lỗi, không làm hỏng bảng cũ (giống cách `wh_action_scenario_registry` đang được bọc, `reverse_etl_warehouse_to_crm.py:159-174`).
6. **Parity cache** `crm/sync/contract_parity.py`: với mỗi cặp bảng cũ/mới, so theo khoá các cột được ánh xạ; in số dòng khác. Chạy ở cuối mỗi lần sync (chỉ log, giới hạn thời gian), và chạy tay trên bản sao.
7. **Chuyển người đọc** sang bảng hợp đồng sau cờ `CRM_CACHE_CONTRACT=v0|v1` (mặc định `v0` khi deploy): `CacheRepository` và các repository/service ở mục bối cảnh đọc qua một lớp `ContractReader` (tên bảng và ánh xạ cột ở một chỗ). Entity domain (`cache_insight.py`) giữ nguyên trường, để màn hình không đổi.
8. **Pack sales_playbook**: `approach_script_generation.py` đọc `wh_signal` khi có (lọc `source_mart='mart_customer_sku_action_queue'`), nếu không thì `wh_sku_action_queue`. Thay đổi đi theo runbook data_platform.
9. Bỏ khỏi sync `wh_product`, `wh_product_insight` (không ai đọc) sau khi phase 0 xác nhận; `wh_order_cogs_summary` bỏ khỏi DDL.
10. Đổi cờ sang `v1` khi parity 0 khác biệt 3 lần sync liên tiếp trên prod (đọc log), và parity snapshot trên bản sao không khác.

## File

- Kho: tạo `transformation/models/packs/crm/contract/*.sql` + yml (hoặc `crm/sync/contract/v1/*.sql`); sửa `scripts/checks/public_models.yaml`, `transformation/models/packs/crm/README.md`, `orchestration/packs/sales_playbook/approach_script_generation.py`.
- CRM: sửa `crm/sync/cache_schema.sql`, `duckdb_reader.py`, `sqlite_upsert.py`, `reverse_etl_warehouse_to_crm.py`; tạo `crm/sync/contract_parity.py`, `crm/src/adapters/outbound/sqlite/contract_reader.py`; sửa `cache_repository.py`, `domain/ports/cache_repository.py` và các người đọc ở bối cảnh; test `crm/sync/tests/test_contract_sync.py`, `crm/src/tests/test_cache_contract_switch.py`.
- Tài liệu: `orchestration/packs/crm/README.md` mục "App CRM đọc gì từ warehouse", `crm/AGENTS.md` (quy tắc: CRM chỉ đọc cache qua `ContractReader`).

## Các bước

1. Worktree `feat/crm-cache-contract`.
2. Model hợp đồng + test dbt; gate `scripts/shadow/gate.sh S --allow-new` (golden 0 khác trên bảng public cũ).
3. Deploy nửa kho theo runbook data_platform (D1), giờ user duyệt. Theo dõi nightly.
4. Sync ghi song song + parity cache + test (fixture DuckDB giả).
5. `ContractReader` + chuyển người đọc sau cờ; test chạy cả hai giá trị cờ cho mọi test hiện có liên quan cache (parametrize).
6. Deploy nửa CRM (D2) với cờ `v0`; theo dõi log parity 3 lần sync.
7. Đổi cờ `v1` (biến môi trường, `docker compose up -d crm` sau khi lưu log), giờ user duyệt; theo dõi 7 ngày.

## Test

| Mức | Nội dung |
|---|---|
| dbt | `unique`/`not_null` theo khoá; số dòng mỗi model hợp đồng bằng số dòng mart nguồn tương ứng |
| Unit (sync) | Bảng mới được nạp đúng 1:1; lỗi đọc hợp đồng không làm hỏng bảng cũ; HWM của `wh_transaction` giống `wh_order_hdr` |
| Unit (CRM) | Toàn bộ test liên quan cache chạy với `v0` và `v1` cho cùng kết quả |
| Tích hợp | `contract_parity.py` trên bản sao: 0 khác biệt |

## Kiểm "CRM như cũ"

- Với cờ `v0`: hành vi đúng như trước (chỉ thêm bảng trong `cache.db`); `parity_snapshot diff` chỉ khác số dòng bảng cache mới.
- Với cờ `v1`: `parity_snapshot diff` giữa `v0` và `v1` trên cùng bản sao phải **rỗng** (worklist, 360, segment, campaign, tìm kiếm cho cùng hash).
- Sau deploy: `GET /admin/refresh/status` `ok`; `wh_sync_run` không có dòng `failed` mới; approach script đêm kế tiếp sinh đủ số file như đêm trước (±5%).

## Đụng prod và duyệt

Có: D1 data_platform (model mới), D2 CRM (sync, đọc), D3 đổi cờ. Cả ba cần user duyệt giờ (D2 và D3 có thể gộp nếu parity đã sạch trên bản sao).

## Rủi ro

| Rủi ro | K × T | Giảm thiểu |
|---|---|---|
| Model hợp đồng lệch mart vì lọc khác | Thấp × Trung bình | Chỉ chọn cột; so số dòng trong test dbt; parity theo khoá |
| Sync chậm hơn vì chép hai lần | Thấp × Thấp | Dữ liệu nhỏ; đo thời gian sync trước/sau, báo nếu > 2 lần |
| Quên một người đọc cache | Trung bình × Trung bình | Danh sách bối cảnh từ `grep`; test parametrize cờ; `grep` lại `wh_` trước khi đổi cờ |

## Rollback

- Cờ: đặt `CRM_CACHE_CONTRACT=v0`, `docker compose up -d crm`.
- Code CRM: `git revert`, `docker restart crm`; bảng mới trong `cache.db` vô hại (hoặc xoá `cache.db` để sync dựng lại).
- Kho: `git revert` theo runbook data_platform; view/model mới mất, không ai khác đọc.
