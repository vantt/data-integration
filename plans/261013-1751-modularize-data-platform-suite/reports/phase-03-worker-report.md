status: complete

# Báo cáo p03a01 — Phase 3: CDM đóng các chỗ core đọc thẳng connector

## Kết quả
- 10 view `std_*` mới trong `transformation/models/cdm/staging/` (pass-through, cột/kiểu/thứ tự như nguồn, `source_system` ở cuối, không `source_version`): `std_customer_{addresses,contacts,notes,tags}`, `std_order_events` (từ `int_order_snapshots_ranked`), `std_order_tags` (từ `src_sapo_v2_orders`: order_id, tags), `std_teams`, `std_team_members`, `std_targets`, `std_marketing_spend`. Kiểu cột lấy từ `information_schema` của lake-A.
- 11 model core đổi `ref`: `dim_customer_{addresses,contacts,notes,tags}`, `dim_teams`, `fact_targets`, `fact_marketing_spend`, `fact_order_transitions` (đọc `std_order_events` + `std_orders` cho `order_code`), `fact_orders`, `fact_sales`, `int_order_tags`. Các model này đều có danh sách cột tường minh nên `source_system` không lọt ra bảng public.
- Test schema: generic test mới `transformation/tests/generic/std_column_contract.sql` (so tên/thứ tự/kiểu cột với `information_schema`), gắn ở `_cdm__models.yml` cho 10 std với `config: {severity: warn}`. Không bật contract enforced. Cả 10 test pass trong build.
- `dim_gl_account`: đã ở `packs/finance`, không cần dời.

## Changed files
- Mới: 10 `transformation/models/cdm/staging/std_*.sql`, `transformation/tests/generic/std_column_contract.sql`, `scripts/tests/test_dbt_inventory.py`
- Sửa: `_cdm__models.yml`, 11 model core (trên), `scripts/checks/model_buckets.yaml` (cdm 14→24), `scripts/checks/boundary_allowlist.yaml`, `scripts/checks/dbt_inventory.py`, `scripts/checks/README.md`, docs (dưới)

## Allowlist
Đã xoá 15 mục core→connector (sapo_v2 ×9: customer_* ×4, fact_order_transitions ×2 [`int_order_snapshots_ranked`, `stg_sapo_v2_orders`], `int_order_tags`; gsheet ×6: dim_teams ×2, fact_orders ×2, fact_sales ×2, fact_marketing_spend, fact_targets — tổng 15 theo thống kê script). Còn 46 = 37 dbt-path + 9 dbt-ref (4 tenant hook, 2 MISA, 3 Shopee). `check_boundaries`: 0 vi phạm mới, 0 mục stale.

## Sửa harness (đã được coordinator duyệt, q-p03-a01-01)
`dbt_inventory.py diff`: với `--allow-code-change`, đổi `depends_on` được chấp nhận khi mọi dependency bị bỏ vẫn là tổ tiên của node trong đồ thị nhánh (INFO ghi "stg -> via std"); mọi trường hợp khác vẫn DIFF. Lý do: lần chạy đầu gate có 11 DIFF depends_on do chính việc repoint. 3 unit test mới (chấp nhận repoint, từ chối khi dep không còn là tổ tiên, từ chối khi thiếu cờ) pass.

## Checks
`scripts/shadow/gate.sh S --allow-new --allow-code-change` (lần chạy cuối, sau khi sửa harness):
```
ok: dbt build (branch)          (PASS=649 WARN=1 ERROR=0; WARN=1 cũng có ở baseline lake-A)
compare: 83 vs 83 tables, 0 difference(s)  / ok: golden
dbt inventory: 176 vs 186 nodes, 0 difference(s), 32 info / ok: dbt inventory
ok: compiled SQL
boundaries: 46 known ({'dbt-path': 37, 'dbt-ref': 9}), 0 new violation(s), 0 stale / ok: module boundaries
dagster inventory: 0 difference(s), 25 info / ok: dagster inventory
ok: dagster dbt subset run
ok: pytest   (một lần flaky test_concurrent_writes_no_lock_error ở lần chạy 1, rerun pass)
ok: golden on empty-rolling lake (83 vs 83, 0 difference)
ok: golden after full refresh (83 vs 83, 0 difference)
GATE S: PASS
```
INFO của dagster: thêm 10 asset `staging/std_*` + 10 asset check `std_column_contract_*`; selection lớn thêm chỉ gồm các view std mới ở các job `ingest_sheets_sync_job` (std_marketing_spend, std_targets), `pipeline_batch_fullrefresh_job`, `pipeline_batch_nightly_job`, `pipeline_sapo_v2_incremental_job`, `pipeline_sapo_v2_realtime_job` (cả 10 view). Không có selection nào mất phần tử. Log: scratchpad gate.log (lần 1 FAIL do inventory), gate2.log (lần cuối PASS).

## Docs đã cập nhật
- `docs/architecture/modules.md`: trạng thái (61→46 vi phạm), §3 (cdm 24 model, vi phạm 24→9, mô tả các cạnh đã đóng), §6 (bảng 10 std mới, nguồn, `source_system`, test warn).
- `docs/architecture/std-layer-conventions.md`: R9 (ma trận phụ thuộc, danh sách std mới, bucket, danh sách cột tường minh), R10 (test warn), checklist.
- `docs/operations/refactor-safety-harness.md` §6.2 và `scripts/checks/README.md`: luật repoint mới.

## Rollback
Revert commit. Các view `std_*` sẽ còn lại trong `main_staging` (vô hại): std_customer_addresses, std_customer_contacts, std_customer_notes, std_customer_tags, std_order_events, std_order_tags, std_teams, std_team_members, std_targets, std_marketing_spend. Xoá nếu cần: `DROP VIEW main_staging.<tên>;`.

## Blockers
Không. Chưa commit (coordinator commit). Lưu ý: không đụng `/home/vantt/app/fg-dataware-house`; lake shadow nhánh đã được gate tự xoá.

## Gợi ý không chặn
- `std_order_tags` chỉ có 2 cột (order_id, tags) thay vì pass-through toàn bộ `src_sapo_v2_orders`, vì consumer chỉ cần tags; nếu muốn faithful hoàn toàn thì mở rộng sau.
- `std_order_events` đọc `int_order_snapshots_ranked` (connector intermediate) — nếu sau này tách history-log thành connector staging, đổi nguồn một chỗ.
