# Báo cáo thực thi phase 7 (tài liệu, ADR, cưỡng chế): worker

- Ngày: 14/10/2026 (Asia/Saigon)
- Worktree: `/home/vantt/app/fg-dw-phase7` (nhánh `refactor/phase-7`, HEAD `64103e50`). **Chưa commit, chưa stash, chưa push.** Các file mới chưa `git add` (xem mục 1).
- Không làm task 3 (dọn shadow, xoá worktree) và không sửa `plans/260705-1704-.../plan.md` (văn bản đề xuất ở mục 7).
- Không đụng checkout prod (ngoài file này), `fg-dw-modular`, `fg-dw-baseline`, container, `app_data/`. Không tạo/xoá gì trong `/home/vantt/app/fg-dw-shadow`: mọi lần chạy container dùng `SHADOW_ROOT` tạm trong scratchpad của session, `deps` là symlink tới `fg-dw-shadow/deps` (chỉ đọc; `PYTHONDONTWRITEBYTECODE=1`, `-p no:cacheprovider`), lake là thư mục rỗng tạm.
- Không sửa SQL, tên relation, asset key, job, selection, tên sensor hay khoá cursor của sensor.

## 1. File thay đổi

| File | Thay đổi |
|---|---|
| `docs/decisions/015-module-boundaries.md` (mới) | ADR ranh giới module: bucket, ma trận, cdm là cửa duy nhất, hook qua allowlist sinh từ manifest, kernel giữ vị trí, connector package, tenant overlay, cưỡng chế + `run-all.sh` |
| `docs/decisions/016-taxonomy-module.md` (mới) | ADR taxonomy Đợt 1: đặc tả + dời seed + check cảnh báo, không tách macro; bộ máy là plan sau Đợt 1; mốc dự phòng 6 tuần |
| `docs/decisions/017-packs-and-tenants.md` (mới) | ADR pack/tenant: các quyết định 14/10, nguyên tắc "số liệu nguồn cung cấp thuộc lõi; chọn/đối chiếu/tính chi phí thuộc finance", chỉ US shipment riêng FJ, bảng hook + lối ra `pack_ref`, tách `mart_sku_economics_monthly`, `crm_cache_refresh` connector → pack có allowlist, URL Sheet chỉ ở env |
| `docs/decisions/README.md`, `docs/README.md` | Mục lục ADR 014 (còn thiếu từ trước) đến 017; `docs/README.md` thêm `taxonomy-engine.md` |
| `scripts/checks/check_boundaries.py` | Luật mới `dbt-seed` |
| `scripts/checks/boundary_allowlist.yaml` | +3 mục `dbt-seed` (33 → 36), chỉ thêm, không đổi mục cũ |
| `scripts/tests/test_check_boundaries.py` | +3 test (lõi/cdm/connector đọc seed tenant bị bắt; pack, monitoring, chính tenant được phép, tenant khác bị bắt; vi phạm cài sẵn làm `main()` trả 1) |
| `scripts/checks/run-all.sh` (mới, +x) | dbt parse → check_boundaries → dagster definitions validate → pytest |
| `scripts/checks/README.md` | Mục `run-all.sh`, luật `dbt-seed`, số mục allowlist 36 |
| `ingestion/src/gsheet_auth.py` | `spreadsheet_url(name)`, `SPREADSHEET_NAMES`, `SpreadsheetUrlNotConfigured` |
| `ingestion/src/gsheet_{targets,marketing_spend,us_shipment_prices,team_config,overhead_classification}.py` | Bỏ URL mặc định và `SHEET_URL` cấp module; URL lấy lúc đọc sheet |
| `ingestion/src/gsheet_budget_sync/{fetch,__init__,sheet_writeback}.py` | `SHEET_URL` → hàm `sheet_url()`; writeback gọi client trước, URL sau (giữ thứ tự lỗi credential cũ) |
| `ingestion/tests/test_gsheet_sheet_urls.py` (mới), `ingestion/tests/test_gsheet_budget_sync.py` | Test thiếu/rỗng → lỗi nêu tên biến, không gọi API; có → dùng đúng URL; không reader nào chứa `docs.google.com`; budget: fixture autouse đặt URL giả (test cũ dựa vào mặc định), +4 test |
| `orchestration/sensors/sheets_modified_sensor.py` | Đọc `SOURCES__SPREADSHEET_URL__{TARGETS,MARKETING_SPEND,US_SHIPMENT_PRICES}` qua `spreadsheet_url`, đổi link sheet thành link CSV export (`csv_export_url`) |
| `orchestration/sensors/__tests__/test_sheets_modified_sensor.py` (mới) | URL từ env, dạng export, URL không phải sheet bị từ chối, thiếu từng biến → tick lỗi nêu tên biến, tick dùng đúng URL |
| `orchestration/tenants/fine_japan/config.py`, `orchestration/tenants/__tests__/test_tenant_setting.py` | Bỏ 3 `SHEETS_SENSOR_*_URL`; test tenant chuyển sang key CRM, thêm test "tenant config không chứa URL sheet" |
| `orchestration/tenants/fine_japan/README.md` | Bảng 6 biến là cấu hình Fine Japan, nơi đọc, hành vi khi thiếu |
| `.env.docker.example` | Thêm `SOURCES__SPREADSHEET_URL__US_SHIPMENT_PRICES` (đủ 6 tên, giá trị placeholder), chú thích bắt buộc/không mặc định |
| `.env.example` | Thay 2 ID sheet thật bằng placeholder; bỏ 3 dòng comment `SHEETS_SENSOR_*` |
| `ingestion/.dlt/config.toml` | Chỉ comment: bỏ câu "hardcoded fallback default" |
| `AGENTS.md` | Mục "Module architecture", "Pre-commit checks (MANDATORY)", Architecture Map, Documentation Map, số ADR |
| `transformation/AGENTS.md`, `orchestration/README.md` | Luật seed tenant, `run-all.sh`, link ADR |
| `docs/architecture/overview.md` | Mục mới "Modules in the 7 hops" (bảng + mermaid), đường dẫn dbt theo module, sửa `sapo_raw` → `<source>_raw`, sửa 4 link component hỏng có từ trước |
| `docs/architecture/std-layer-conventions.md` | Rà: R7 trỏ `_sources.yml` của connector, R9 thêm seed tenant + `pack_connectors` + run-all, sửa checklist mâu thuẫn R2 (`source_version`), ghi hiện trạng tên `src_sapo_v2_*` khác quy ước hậu tố R3 |
| `docs/architecture/modules.md` | Rà lần cuối với code (mục 4 dưới) |

## 2. Luật mới `dbt-seed` và allowlist

Luật: model có bucket `core`, `cdm`, `connector:*` (hoặc `tenant:<khác>`) phụ thuộc seed nằm dưới `seeds/tenants/<t>/` thì là vi phạm. Pack, `monitoring` và chính `tenant:<t>` được đọc (pack là logic, tenant là dữ liệu; 5 cạnh pack → seed tenant hiện có là đúng thiết kế). Seed taxonomy không bị ảnh hưởng.

Manifest parse từ nhánh cho **đúng 3 cạnh**, khớp danh sách được giao:

| Subject | Target |
|---|---|
| `dim_channel_targets` | `seed_channel_targets [core -> tenant:fine_japan]` |
| `dim_sku_alias` | `seed_sku_alias_manual [core -> tenant:fine_japan]` |
| `int_customer_sku_supply_tracking` | `seed_sku_regimen_config [core -> tenant:fine_japan]` |

Mỗi mục có lý do (model dùng seed vào việc gì) và lối ra: "after Đợt 1 core ships an empty seed with the same columns and the tenant overrides it (with pack_ref)". `--write-allowlist` chạy lại cho kết quả ổn định (giữ lý do). Bỏ một mục khỏi allowlist trên manifest thật → `VIOLATION [dbt-seed] dim_sku_alias -> ...`, exit 1 (đã thử với bản sao allowlist).

## 3. URL Google Sheet (chỉ tên, không giá trị)

| Biến | Trước | Sau |
|---|---|---|
| `SOURCES__SPREADSHEET_URL__TARGETS` | env, mặc định viết cứng trong reader; sensor dùng `SHEETS_SENSOR_TARGETS_URL` (env) hoặc tenant config | Chỉ env; reader và sensor (tab đầu) cùng đọc |
| `SOURCES__SPREADSHEET_URL__MARKETING_SPEND` | như trên (`SHEETS_SENSOR_MARKETING_URL`) | Chỉ env; reader và sensor (tab đầu) |
| `SOURCES__SPREADSHEET_URL__US_SHIPMENT_PRICES` | như trên (`SHEETS_SENSOR_US_SHIPMENT_PRICES_URL`) | Chỉ env; reader và sensor (`gid=304875363`) |
| `SOURCES__SPREADSHEET_URL__TEAM_CONFIG` | env + mặc định | Chỉ env |
| `SOURCES__SPREADSHEET_URL__OVERHEAD_CLASSIFICATION` | env + mặc định | Chỉ env |
| `SOURCES__SPREADSHEET_URL__BUDGET` | env + mặc định (đọc + ghi gợi ý) | Chỉ env |

- Thiếu hoặc rỗng → `SpreadsheetUrlNotConfigured: SOURCES__SPREADSHEET_URL__<NAME> is not set: ...` tại lúc đọc sheet (asset run hoặc tick sensor). Import reader và load Definitions không cần biến: `dagster definitions validate` pass trong container **không có** biến `SOURCES__*` nào.
- Sensor: `csv_export_url(url, gid)` lấy scheme, host, `/spreadsheets/d/<id>` từ link trong env, ghép `/export?format=csv` (+ `&gid=` cho tab US). Với link của cùng sheet, kết quả **trùng ký tự** với URL cũ trong tenant config (test với ID giả). Khoá cursor giữ nguyên (`targets`, `marketing_spend`, `us_shipment_prices`), nên không có cold start.
- Ingestion không import `orchestration` (luật `py-import`, sạch).

**Cần coordinator kiểm trên prod trước deploy (không in giá trị):** hành vi chỉ giống hệt nếu (a) prod `.env.docker` không đặt `SHEETS_SENSOR_*_URL` và (b) ID sheet trong 3 biến `SOURCES__` trùng ID sensor đang dùng. Lệnh đọc, chỉ in match/MISMATCH, chạy với code đang chạy trên prod (main):

```bash
grep -c '^SHEETS_SENSOR_' /home/vantt/app/fg-dataware-house/.env.docker   # mong đợi 0
docker exec data_platform python -c '
import os,re
from orchestration.sensors.sheets_modified_sensor import SHEET_URLS
for k,(n,g) in {"targets":("TARGETS",None),"marketing_spend":("MARKETING_SPEND",None),"us_shipment_prices":("US_SHIPMENT_PRICES","304875363")}.items():
    m=re.search(r"^(https?://[^/]+/spreadsheets/d/[A-Za-z0-9_-]+)",os.environ.get("SOURCES__SPREADSHEET_URL__"+n,""))
    new=m.group(1)+"/export?format=csv"+("&gid="+g if g else "") if m else None
    print(k,"match" if new==SHEET_URLS[k] else "MISMATCH")'
```

Nếu MISMATCH: sau deploy sensor theo dõi đúng sheet mà reader đang ingest (đúng hơn trước), hash cursor đổi một lần và bắn một run `ingest_sheets_sync_job` (vô hại), nhưng đó là đổi hành vi nên cần user biết.

## 4. Rà `docs/architecture/modules.md` với code

Đã đối chiếu: 182 model (172 bật, 10 tắt) và số model từng bucket với `model_buckets.yaml`; 14 seed (8 taxonomy, 6 tenant); 5 connector, 4 pack orchestration, 1 tenant với thư mục thật; 7 asset của connector `sheets`; khối module trong `dbt_project.yml`; 36 mục allowlist. Sửa: trạng thái (36 vi phạm, dòng run-all, dòng ADR, tenant overlay), mục 1/10 (sơ đồ: env Sheet URL, tenant config chỉ còn endpoint CRM, cạnh seed tenant → core thành ⚠), mục 2 (quyền đọc seed tenant), mục 3 (sơ đồ, cột seeds của ma trận, bảng vi phạm +1 nhóm), mục 4 (giao diện `spreadsheet_url`, `setting` không còn dùng cho sensor, đoạn sensor), mục 5, 7, 12. Sửa mục lục: 6 anchor hỏng có từ trước (heading có ✅ nên slug thêm `-`), thêm 2b.

## 5. Kiểm tra đã chạy

Tất cả trong container shadow (`scripts/shadow/run-shadow.sh`, image prod, `--network none`) với `SHADOW_ROOT` tạm trong scratchpad (lake rỗng, `deps` symlink), trừ `check_boundaries.py` và link check (python host). Không có venv host có dagster.

```text
pytest (file mới/liên quan: ingestion URL, budget, sensors, tenants)   87 passed
pytest scripts/tests/test_check_boundaries.py                         30 passed
dbt parse --profiles-dir . (worktree phase7)                          OK
check_boundaries.py --manifest <manifest worktree>                    36 known (dbt-ref 16, dbt-seed 3, dbt-source 12, orch-import 5), 0 new, 0 stale
  (trước khi thêm allowlist: đúng 3 VIOLATION dbt-seed)
dagster definitions validate (không có biến SOURCES__*)               Validation successful
scripts/checks/run-all.sh (2 lần, SHADOW_ROOT tạm)                    RUN-ALL: PASS; pytest 271 passed
  lần 2: test_concurrent_writes_no_lock_error lỗi lần đầu, chạy lại pass → in FLAKY (đúng cơ chế)
check_taxonomy_inventory.py                                           79 blocks, 46 domains, 0 warning(s)
link check 13 file doc tạo/sửa                                        204 link tương đối, 0 hỏng (kể cả anchor)
```

Không chạy `gate.sh`, `build-lake.sh`, `clone-lake.sh`, `cleanup.sh`, `pytest-shadow.sh` trên `fg-dw-shadow`. Không chạy golden: không đổi SQL, nhưng coordinator vẫn chạy gate M theo kế hoạch.

## 6. Lệch so với brief

- `.env.example` (không nằm trong danh sách): thay 2 ID sheet thật bằng placeholder và bỏ comment `SHEETS_SENSOR_*` đã lỗi thời. `ingestion/.dlt/config.toml`: chỉ sửa comment nói về fallback.
- `docs/decisions/README.md` và `docs/README.md` thiếu ADR-014 từ trước; đã thêm cùng 015–017.
- `overview.md`: sửa 4 link hỏng có từ trước (`../ingestion/docs/README.md` → `../../...`) và một dòng khung ASCII lệch.
- `run-all.sh` không gồm `check_taxonomy_inventory.py` (brief chỉ nêu 4 bước; gate vẫn chạy nó ở bước 3c).
- Luật `dbt-seed` chặn cả `cdm`, connector và tenant khác (không chỉ `core`); kết quả trên manifest vẫn đúng 3 mục.
- ADR-016: bản nháp đầu nêu lý do sai ("macro đổi số"); đã sửa theo hồ sơ phase 4 và synthesis (tách macro nguyên văn không đổi số nhưng là làm hai lần; 4/4 phản biện đồng ý; mốc dự phòng 6 tuần).

## 7. Văn bản đề xuất cho `plans/260705-1704-modular-monorepo-boundary-hardening/plan.md`

Đặt ở đầu file (sau front matter), và đổi trạng thái các phase tương ứng:

> **Cập nhật 14/10/2026.** Plan `261013-1751-modularize-data-platform-suite` (Đợt 1) đã thay ba phase của plan này: phase 2 (cắt import crm → orchestration: luật `py-import` của `scripts/checks/check_boundaries.py`), phase 3 (kiểm tra import: `check_boundaries.py` với các luật `py-import`, `orch-import`, `dbt-ref`, `dbt-seed`, ... chạy trong `scripts/checks/run-all.sh` trước mỗi commit) và phase 6 (tài liệu ranh giới: `docs/architecture/modules.md`, ADR-015/016/017). Các phase này **không làm nữa**. Phase 0, 1, 4, 5 (đóng gói image, GHCR, tách dev/prod) là **Đợt 2** trong roadmap của plan 261013 và là bước tiếp theo; khi làm, dựa trên bố cục module hiện có (`orchestration/config/modules.yaml`, `orchestration/{connectors,packs,tenants}/`, `transformation/models/<module>/`) và các ADR trên.

Bảng phase: phase 2, 3, 6 → `superseded by 261013-1751`; phase 0, 1, 4, 5 → giữ `pending` (Đợt 2).

## 8. Câu hỏi chưa giải quyết

1. **`run-all.sh` phụ thuộc `$SHADOW_ROOT/deps`** (dbt_packages, DuckDB extensions, pytest ghim). Task 3 (`cleanup.sh --all` khi đóng plan) xoá luôn `deps`, sau đó `run-all.sh` báo "missing deps" cho tới khi chạy lại `prepare-shadow.sh` (script này còn cần hai backup để dựng `lake-base`). Hai điều kiện Verification của phase ("run-all pass trên main" và "fg-dw-shadow không còn") vì vậy xung đột. Đề xuất: trước khi đóng plan, tách phần dựng `deps` của `prepare-shadow.sh` thành lệnh riêng (không cần backup, không có PII) hoặc chuyển `deps` ra khỏi thư mục bị xoá; quyết định thuộc planning session.
2. `run-all.sh` (qua guard của `run-shadow.sh`) từ chối checkout prod: commit phải làm từ worktree. Đúng với quy trình hiện tại của plan, nhưng sau khi đóng plan cần ghi rõ quy trình commit (AGENTS.md đã ghi "run from the worktree you commit from").
3. Kiểm prod trước deploy theo mục 3 (`SHEETS_SENSOR_*` trong `.env.docker`, ID sheet trùng).
4. `std-layer-conventions.md` R3 và `naming-conventions.md` §7 quy định hậu tố `_v<N>` (`src_sapo_orders_v2`), còn code dùng `src_sapo_v2_<entity>`. Tôi chỉ ghi hiện trạng, không đổi quy ước: cần chốt quy ước tên trước khi thêm Sapo v3.
5. `docs/analytics-handbook/guides/finance-budget-user-guide.md` (hướng dẫn cho người dùng tài chính) vẫn ghi link sheet ngân sách. Không phải code, để nguyên; nếu muốn "mỗi URL một nơi" tuyệt đối thì cần quyết định có bỏ khỏi hướng dẫn hay không.

Status: DONE_WITH_CONCERNS
Summary: Đã viết ADR 015/016/017 từ code thật, thêm luật `dbt-seed` (đúng 3 mục allowlist theo manifest, có test), bỏ URL Sheet mặc định ở 6 reader và cho sensor đọc chung biến `SOURCES__SPREADSHEET_URL__*` (fail closed lúc dùng), thêm `scripts/checks/run-all.sh` (PASS) và cập nhật toàn bộ tài liệu được giao (204 link, 0 hỏng).
Concerns/Blockers: `run-all.sh` sẽ không chạy được sau khi xoá shadow (cần dựng `deps` riêng); coordinator cần kiểm `SHEETS_SENSOR_*` và ID sheet trên prod (lệnh ở mục 3) trước deploy; gate M chưa chạy.
