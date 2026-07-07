# Phase 05 — Trigger theo worklist-refresh + auto-load (bỏ review)

## Vì sao (bối cảnh quyết định)
Câu hỏi gốc: sinh cả cohort trước tốn kém & sinh lúc mở cockpit thì user phải đợi (codex/API + review). Điểm cân bằng: hook vào **worklist-refresh** — thời điểm `wh_sku_action_queue` được refresh (asset `crm_sync.crm_cache_refresh`, chạy trong `pipeline_batch_nightly_job` 03:00 ICT, và nhiều job khác mỗi ~3-10 phút — xem `orchestration/definitions.py:83,97,124,145,195,210,235`). Neo vào bản nightly (đảm bảo full refresh 1 lần/ngày, đủ đệm thời gian trước ca gọi) thay vì mọi job realtime (tránh gọi LLM dồn dập).

User chốt thêm (2026-07-06): **bỏ hẳn bước người duyệt** cho luồng tự động này — chỉ còn linter máy (phase 01) làm gate. Xem cảnh báo ở § Rủi ro.

**[Cập nhật 2026-07-07, resolve unresolved Q1 của bản gốc]** Lúc code phase này phát hiện hạ tầng đã đổi khác so với khi viết plan (2026-07-06):
- `data_platform` **đã có** `crm_data:/app/var/crm_data:ro` (thêm từ commit `37f75eb9` 2026-06-23, cho mục đích backup — tác giả phase 05 không thấy dòng này khi viết plan). Nghĩa là `crm.db` đã đọc được thẳng tại `/app/var/crm_data/crm.db` từ trong `data_platform`, không cần `docker cp`.
- `main_marts.mart_customer_sku_action_queue` (nguồn của `cache.wh_sku_action_queue`) đã có **rolling parquet export** tại `app_data/data_lake/export/marts/rolling/mart_customer_sku_action_queue/*.parquet` — cùng cơ chế `dim_customers` mà `build_approach_prompts.py` đã đọc. Parquet này có sẵn cột `customer_id` (INTEGER), không cần join qua `customer_key`.
- → **Không cần** GET endpoint mới trên CRM để hỏi cohort. Cohort actionable = query DuckDB trực tiếp trên 2 parquet có sẵn (dim_customers GATE ∩ customer_id trong mart_customer_sku_action_queue), y hệt cách `fetch_cohort()` đã làm — chỉ thêm 1 mệnh đề `AND customer_id IN (...)`.
- Endpoint mới **vẫn cần** cho chiều ghi (auto-load, xem dưới) — hướng warehouse→CRM không đổi, `crm` vẫn không share volume ghi được với `data_platform`.
- **Provider cho luồng tự động (user chốt 2026-07-07)**: dùng `codex` CLI (đã login OAuth sẵn trong container, phase 04) **tạm thời**, KHÔNG phải `anthropic` — vì `.env.docker` chưa có `ANTHROPIC_API_KEY` thật. Chấp nhận rủi ro quota/OAuth cá nhân bị dùng chung cho batch đêm (đã nêu ở phase 04) cho tới khi có key thật; đổi provider chỉ cần set env `APPROACH_SCRIPT_AUTOGEN_PROVIDER=anthropic`, không sửa code.
- **regen-after-days (user chốt 2026-07-07)**: gắn theo tín hiệu thay vì hằng số — `next_purchase_signal IN ('DUE_SOON','OVERDUE')` → 14 ngày (tình huống đổi nhanh), còn lại (VIP/GOLD ổn định) → 30 ngày. KHÔNG dùng `lifecycle_stage` (memory: `lifecycle_stage=NEW` không đáng tin, xem `project_lifecycle_stage_new_unreliable`). `--regen-after-days N` override CLI vẫn còn, ép flat N cho mọi khách (dùng khi test).

## Ràng buộc hạ tầng (đã xác minh)
- `data_platform` (chạy Dagster + `scripts/`) và `crm` (đọc `{scripts_dir}/{customer_id}.json`) là **2 container khác nhau, không share volume ghi** — `crm_data` là named volume của `crm`, mount **read-only** vào `data_platform` (đủ để đọc, không đủ để ghi script mới vào thư mục CRM đọc).
- → Theo đúng pattern đã có (`crm_cache_refresh` gọi `POST /admin/refresh` để CRM tự làm việc trong container của nó), asset mới POST kết quả đã lint-pass sang một endpoint admin mới trên CRM; CRM tự ghi file vào `CRM_APPROACH_SCRIPT_DIR`.
- `crm` container không mount `scripts/` (`Dockerfile.crm` chỉ `COPY crm/ ./crm/`) → không tái dùng `approach_script_lint.py` bên phía CRM được; endpoint mới **tin tưởng payload đã lint-pass từ phía gọi**, chỉ validate JSON well-formed + có `customer_id` trước khi ghi (không lint lại nghiệp vụ).
- `generate_approach_scripts.py` gốc viết cho HOST (`PARQUET_GLOB` relative tới repo root); chạy trong `data_platform` cần resolve theo `DBT_DATA_LAKE_PATH` (env đã set `/app/var/data_lake` trong `.env.docker`, quy ước đã dùng ở `scripts/ensure_*_placeholder.py`) — sửa `build_approach_prompts.py` để tự nhận biết 2 môi trường (env set → container path, unset → host default `ROOT/app_data/data_lake`).

## Flow
1. **Cohort actionable**: `build_approach_prompts.py::fetch_cohort()` (đã sửa) — khi `--cohort-from-queue`, thêm mệnh đề SQL `AND customer_id IN (SELECT DISTINCT customer_id FROM read_parquet(mart_customer_sku_action_queue mới nhất))` vào cạnh `GATE` hiện có. Không cần hàm/module riêng, không cần đọc `cache.db`.
2. **Regen-guard (tiết kiệm, đúng tinh thần "chỉ sinh khi cần")**: module mới `scripts/approach_script_regen_state.py` — file state `scripts/approach_out/.generated_state.json` (`{customer_id: last_loaded_at}`), bind-mount sẵn có (`./scripts:/app/scripts`) nên persist qua các lần chạy container (đã gitignore sẵn, cả thư mục `approach_out/`). Bỏ qua customer nếu `last_loaded_at` mới hơn ngưỡng tiered (14/30 ngày, xem trên). Chỉ áp dụng khi cohort đến từ GATE (không áp dụng khi dùng `--ids` tường minh — giữ đúng ngữ nghĩa "tôi muốn khách này" bypass mọi guard trừ lint). `--force-regen` bỏ qua guard này khi cần.
3. **Generate**: với mỗi customer còn lại — `fill()` prompt (đã có, phase 02, dùng `--crm-db /app/var/crm_data/crm.db` để đọc notes thật không qua `docker cp`) → `provider.complete()` (hexagon, phase 04; provider = `codex`, xem quyết định trên) → `extract_json_block` → `lint_script` (phase 01). Fail → ghi `_failed/{cid}.stdout.txt` như cũ (không chặn asset, không chặn các customer khác).
4. **Auto-load (không qua người duyệt)**: khi `--auto-load-url` được set, các script pass lint KHÔNG ghi vào `approach_out/{cid}.json` nữa — gom thành 1 batch JSON `[{"customer_id": cid, "script": {...}}]`, POST tới CRM: `POST /admin/approach-scripts/load` (endpoint mới, xem dưới). Không set `--auto-load-url` (luồng thủ công) → hành vi cũ không đổi (ghi `approach_out/`, chờ tay người + `load_approach_scripts.py`).
5. Cập nhật `.generated_state.json` cho các customer vừa load thành công (dựa trên `written`/`skipped` trong response CRM) — chỉ cập nhật khi auto-load thành công, script đang chờ duyệt tay (luồng thủ công) không tính là "đã sinh" cho mục đích regen-guard.
6. Luồng thủ công cũ (`generate_approach_scripts.py` không cờ tự động + `load_approach_scripts.py` + review tay) **giữ nguyên, không xoá** — vẫn dùng được khi ai đó muốn regen tay/soi tay một khách cụ thể.

## CRM: endpoint mới
- File mới `crm/src/adapters/inbound/http/admin_approach_scripts_handler.py` (tách khỏi `admin_handler.py` — đã 343 dòng, đủ ngưỡng modularize):
  - `POST /admin/approach-scripts/load` — body: `list[dict]` (mỗi item là JSON script đã có `meta.customer` hoặc field `customer_id` ở top-level để định danh file đích). Auth: header `X-Refresh-Token` giống `/admin/refresh` (tái dùng `CRM_REFRESH_TOKEN`, không thêm secret mới).
  - Validate tối thiểu: mỗi item parse được `customer_id` (int), còn lại tin tưởng caller đã lint. Ghi atomic (`tmp` + `os.replace`) vào `{CRM_APPROACH_SCRIPT_DIR}/{customer_id}.json`.
  - Trả `{written: N, skipped: [...]}`.
- Đăng ký router mới trong `crm/src/composition.py`/app factory (theo đúng chỗ `admin_handler` được include hiện tại).

## Dagster
- Tạo `orchestration/assets/approach_script_generation.py::approach_script_autogen`, `@asset(deps=[crm_sync.crm_cache_refresh], group_name="approach_script_autogen", ...)` — group riêng, KHÔNG tái dùng group `crm_writeback` có sẵn (group đó là chiều CRM→warehouse export, ngược hướng với asset này). Subprocess (Popen+stream, không `capture_output=True` — tránh lặp lại lesson pipe-buffer-hang ở `serving.py`) gọi `python scripts/generate_approach_scripts.py --cohort-from-queue --provider codex --auto-load-url http://crm:8090/admin/approach-scripts/load --crm-db /app/var/crm_data/crm.db --limit <APPROACH_SCRIPT_AUTOGEN_LIMIT, mặc định 10>` trong chính `data_platform` container (đã có `scripts/` mount + `crm_data:ro` + codex CLI + network `caddy_net` để gọi `crm:8090`).
- Wire vào `pipeline_batch_nightly_job`: thêm `| AssetSelection.assets(approach_script_generation.approach_script_autogen)` sau dòng `crm_sync.crm_cache_refresh` trong `_nightly_batch_selection`.
- Fire-and-forget về mặt pipeline: lỗi generate/load KHÔNG red cả nightly job (giống triết lý `crm_cache_refresh`) — log warning, để `_failed/` cho người soi sau, không chặn dbt/serving chạy tiếp.
- `--limit` mặc định nhỏ (10) cho vài đêm đầu để đo cost/chất lượng thật trước khi mở hết cohort — chỉnh qua env `APPROACH_SCRIPT_AUTOGEN_LIMIT`.

## Files
- Tạo: `crm/src/adapters/inbound/http/admin_approach_scripts_handler.py`
- Tạo: `orchestration/assets/approach_script_generation.py`
- Tạo: `scripts/approach_script_regen_state.py`
- Tạo: `scripts/approach_script_autoload.py` (`post_batch()` — tách khỏi generator để giữ dưới ~200 dòng)
- Sửa: `scripts/build_approach_prompts.py` (env-aware data-lake root, `--cohort-from-queue`), `scripts/crm_history_reader.py` (auto-detect `/app/var/crm_data/crm.db` trước khi `docker cp`), `scripts/generate_approach_scripts.py` (cờ `--auto-load-url/--regen-after-days/--force-regen/--state-file`, batch POST), `orchestration/definitions.py` (import + wire asset), `crm/src/composition.py` (đăng ký router mới), `crm/src/adapters/outbound/file/approach_script_file_repository.py` (expose `scripts_dir` property cho router dùng lại, tránh đọc env 2 nơi)
- Sửa: `docker-compose.yml` — thêm `./plans:/app/plans:ro` vào `data_platform` (phát hiện khi smoke-test thật: `build_approach_prompts.py::load_template()` đọc `plans/260624-.../customer-insight-prompt-template.md` lúc runtime, nhưng `data_platform` trước đó không mount `plans/` — chỉ có `transformation/ingestion/orchestration/scripts`). Cần `docker compose up -d data_platform` (recreate, không phải restart) để áp dụng mount mới.

## Cập nhật 2026-07-07 (sau khi phase 05 "done") — chi phí codex
Phát hiện khi user hỏi thêm `--model` để tránh chạy model đắt: **model KHÔNG
chọn được** với ChatGPT-subscription login này — mọi `-m` khác default đều bị
400 `"not supported when using Codex with a ChatGPT account"` (thử `gpt-5`,
`gpt-5-codex`, `gpt-5.1`, `gpt-5.1-codex`, `gpt-5.5-codex`, `gpt-5-mini`, `o3`,
`o4-mini` — tất cả fail). Không truyền `-m` → luôn chạy `gpt-5.5`. Đòn bẩy chi
phí duy nhất còn lại: reasoning effort (`-c model_reasoning_effort=<level>`).

Đã thêm `--reasoning-effort {minimal,low,medium,high}` (default `low`, env
`APPROACH_SCRIPT_REASONING_EFFORT`) vào `generate_approach_scripts.py`, plumb
qua `CodexCliCompletionProvider` (`scripts/approach_script_completion/codex_cli_provider.py`).
`minimal` bị lỗi (400 — 2 tool mặc định `image_gen`/`web_search` không tương
thích với effort này), degrade sạch vào `_failed/`, không chặn batch — verify
thật. `low` chạy OK thật (customer 86375978), `meta.model` giờ ghi
`"codex(reasoning=low)"` để audit sau này. Asset nightly (`approach_script_generation.py`)
đã truyền `--reasoning-effort low` qua env `APPROACH_SCRIPT_AUTOGEN_REASONING_EFFORT`.

## Verify thật đã chạy (2026-07-07, không phải chỉ đọc code)
- `docker compose exec data_platform codex login status` → đã login (ChatGPT subscription).
- Smoke-test cohort-from-queue + codex + auto-load thật (limit=1, khách 86375978): codex sinh script hợp lệ (lint pass, `recommended=true`), POST `/admin/approach-scripts/load` → `{"written": 1, "skipped": []}`, file xuất hiện đúng `/data/approach_scripts/86375978.json` trong container `crm`, state file ghi đúng `{"86375978": "2026-07-07"}`. Đã dọn file test này khỏi CRM sau khi verify (không phải script thật đã duyệt).
- Full Dagster `Definitions` load trong `data_platform` (238 asset keys, `approach_script_autogen` có trong `pipeline_batch_nightly_job` asset selection) — không lỗi import.
- Lưu ý: `orchestration/assets/approach_script_generation.py` KHÔNG dùng `from __future__ import annotations` — dagster (bản đang cài) fail validate `context: AssetExecutionContext` khi annotation bị deferred thành string (khớp pattern các asset khác trong repo như `crm_sync.py`/`serving.py`, cũng không dùng future-annotations).

## Validate
- Materialize `approach_script_autogen` trong Dagster dev UI với cohort nhỏ (`--limit`/test override) → xác nhận file xuất hiện đúng `{CRM_APPROACH_SCRIPT_DIR}` (không cần `docker compose restart crm` vì `FileApproachScriptRepository.list_customer_ids()` tự re-scan mỗi phút, `crm/src/adapters/outbound/file/approach_script_file_repository.py:20,66-91`).
- Test CRM: request giả tới `/admin/approach-scripts/load` với payload hợp lệ/không hợp lệ (thiếu `customer_id`) → verify ghi đúng/skip đúng, auth token check.
- Test cohort regen-guard: chạy 2 lần liên tiếp trong ngày → lần 2 skip toàn bộ (state file chặn), không gọi provider thừa.

## Rủi ro
- **Bỏ review hoàn toàn** (kể cả `recommended=false`) — script sai/nhạy cảm có thể lọt thẳng ra cockpit không ai soi trước khi gọi khách. Đây là quyết định user đã chốt 2026-07-06; ghi nhận rủi ro, không tự ý thêm review-gate ngược lại.
- **Provider = codex tạm thời (user chốt 2026-07-07)**: batch đêm dùng chung quota/OAuth subscription cá nhân đã login trong container (rủi ro đã nêu ở phase 04 — đúng lý do phase 04 tách hexagon). Khi có `ANTHROPIC_API_KEY` thật, đổi qua bằng cách set env `APPROACH_SCRIPT_AUTOGEN_PROVIDER=anthropic`, không cần sửa code.
- Chi phí/quota mỗi đêm cho cả cohort actionable — chưa có ước lượng số lượng khách/đêm; `--limit` mặc định 10 (env `APPROACH_SCRIPT_AUTOGEN_LIMIT`) cho vài đêm đầu để đo thật trước khi mở hết cohort.
- `recommended=false` không còn ai duyệt — cân nhắc (không bắt buộc, hỏi user riêng) một guard máy nhẹ: nếu `recommended=false`, cockpit hiện banner "chưa qua người duyệt" thay vì im lặng phục vụ như script bình thường — nhưng đây là scope UI mới, để ngoài phase này trừ khi user muốn thêm.

## Unresolved questions
(none — Q1 tự resolve khi phát hiện hạ tầng đã đổi, xem § Vì sao; Q2/Q3 user đã chốt 2026-07-07, xem trên)
