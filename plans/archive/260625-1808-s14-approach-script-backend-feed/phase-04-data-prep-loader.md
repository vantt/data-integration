# Phase 04 — Data Prep Loader + E2E Verify

**Priority:** P0 · **Status:** ⬜ · Depends: Phase 02, 03.

## Overview
Đưa 31 JSON pilot vào `{data_dir}/approach_scripts/{customer_id}.json` để màn chạy data thật. Loader idempotent, dùng lại được cho mỗi đợt test mới.

## Key insight
`data_dir = dirname(crm_db_path())` — cùng chỗ cache.db, đã nằm trong volume `crm_data`. ⇒ **KHÔNG cần sửa docker-compose.** Loader chỉ copy file vào đó.

## Requirements
- Đổi tên `script-{NN}-{customer_id}.json` → `{customer_id}.json`.
- Idempotent: chạy lại ghi đè, không nhân bản.
- Chạy được cả host (Windows) lẫn trong container.

## Related code files
- **Create** `crm/scripts/load_approach_scripts.py` (hoặc `scripts/`) — copy + rename
- **Modify** (nếu cần) `.env` / compose: thêm `CRM_APPROACH_SCRIPT_DIR` (optional; default đã ổn)

## Implementation steps
1. Loader:
   - args: `--src` (default `plans/260624-1917-customer-insight-prompt-template/pilot-run-1/scripts/`), `--dest` (default `{data_dir}/approach_scripts`)
   - mỗi file: rút `customer_id` từ tên (`script-NN-{cid}.json`) **hoặc** từ JSON (`customer_json.customer_id`) — ưu tiên JSON để chắc; ghi `{dest}/{cid}.json`
   - `os.makedirs(dest, exist_ok=True)`; log số file ghi
2. Chạy loader (host hoặc `docker compose exec crm python ...`).
3. **E2E verify:**
   - `curl /api/parties/{id}/approach-script` cho 1 party map tới customer_id pilot → trả script
   - thử 1 ca `recommended=false` (nếu có trong cohort — thực ra cohort đã loại; dùng riêng ca Leflair để test gate nếu cần)

## Todo
- [ ] loader `load_approach_scripts.py`
- [ ] chạy loader → 31 file `{cid}.json` ở data_dir/approach_scripts
- [ ] e2e: curl endpoint trả đúng cho ≥2 khách
- [ ] cập nhật `plan.md` trạng thái phases

## Success criteria
- 31 file ở đúng thư mục; endpoint trả script thật cho khách pilot. Backend SẴN SÀNG cho `ui-port`.

## Risks
- party↔customer_id: không phải mọi party test có `sapo_customer` identity khớp cohort. Chọn party có map để verify; ghi rõ 1-2 party_id dùng test.
- Trong docker, loader ghi vào volume `crm_data` (rw từ container CRM) — chạy loader TRONG container CRM để chắc đúng volume.

## Handoff → ui-port (ngoài scope phase này)
Backend xong = contract sẵn: `GET /api/parties/{id}/approach-script` + entity. Bạn chạy `ui-port` dựng `screen_call_cockpit.py` + template theo spec S14, gọi `approach_repo.get_by_customer_id` (server-rendered) hoặc fetch endpoint.
