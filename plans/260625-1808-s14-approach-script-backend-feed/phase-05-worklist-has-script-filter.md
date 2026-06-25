# Phase 05 — Worklist "Có kịch bản" filter (auto-handle scripts mới)

**Priority:** P1 · **Status:** ✅ (commit 62ff52c) · Depends: Phase 01–04 (repo + loaded scripts).

## Overview
S01 Worklist lọc / gắn badge **action item** của khách **có approach script**. Bấm "Gọi" trên row có script → mở S14 cockpit. **Tự động** nhận file script mới: không restart, không re-index.

## Key insight — match TRỰC TIẾP bằng customer_id
- Script keyed theo `customer_id` (file `{cid}.json`).
- `wh_action_queue` chỉ có `customer_key` (surrogate), KHÔNG có customer_id. `wh_customer_base` có cả hai.
- → **Expose `customer_id` trên ActionQueueItem** (JOIN `wh_action_queue.customer_key → wh_customer_base.customer_id`). Rồi khớp **trực tiếp**: `action.customer_id ∈ script_cids`.
- Lợi: **0 SQL resolve mỗi load** (chỉ 1 listdir lấy `script_cids`); không phụ thuộc `party_id` (match được cả action chưa sync party); `customer_id` ổn định → không stale do merge.
- **Auto-handle (cốt lõi):** `list_customer_ids()` = `os.scandir` MỖI lần gọi → file mới (loader/Dagster drop vào dir) tự xuất hiện ở worklist load kế tiếp. KHÔNG cache stale, KHÔNG restart.
- **Scope v1:** filter áp cho **action items** (script lái call-queue). Task thủ công (chỉ party_id) tạm KHÔNG áp; cần sau thì resolve party→customer riêng.

## Requirements
- Filter `has_script` (chip bật/tắt) — giữ action có `customer_id ∈ script_cids`.
- Badge "Có kịch bản" + nút "Gọi" trên action có script → S14 (`action_queue.call_mode_requested`).
- **Dynamic:** thêm `{cid}.json` → load worklist sau tự phản ánh (no restart).
- "Có script" v1 = **file tồn tại** (cockpit tự lo STOP khi recommended=false). Phân biệt recommended=false bằng badge để sau.
- YAGNI: chưa cache — listdir vài trăm/nghìn file/load là rẻ.

## Caching / key decision
- Match trên **`customer_id`** (warehouse natural key, ổn định) — KHÔNG dùng `customer_key` (surrogate) cũng KHÔNG dùng `party_id`.
- KHÔNG persist party_id/customer_id ra ngoài file (script chỉ keyed customer_id; party_id để identity table làm chủ → tránh stale do merge/re-link, giữ value-link no-FK R3).
- `script_cids` tính 1 lần/load, mọi action test membership O(1).

## Related code files
- **Modify** `crm/src/domain/entities/cache_insight.py` — thêm `customer_id: int` (hoặc `Optional[int]`) vào `ActionQueueItem`
- **Modify** `crm/src/adapters/outbound/sqlite/cache_repository.py` — `_fetch_actions`: LEFT JOIN `wh_customer_base bc ON bc.customer_key = a.customer_key`, select `bc.customer_id`
- **Modify** `crm/src/domain/ports/approach_script_repository.py` — add `list_customer_ids() -> set[int]`
- **Modify** `crm/src/adapters/outbound/file/approach_script_file_repository.py` — implement (`os.scandir`, regex `^(\d+)\.json$` → int; bỏ file lỗi)
- **Modify** `crm/src/application/worklist_filters.py` — `parse_filters` đọc `has_script`; `apply_filters` nhận `script_cids: set[int]`, narrow action theo `customer_id`
- **Modify** `crm/src/adapters/inbound/web/screen_worklist.py` — lấy `approach_repo` (app.state) → `script_cids = list_customer_ids()`; truyền vào filters + template (gắn badge per action)
- **Modify** worklist template — chip "Có kịch bản" + badge action + nút "Gọi"→S14
- **Modify** `crm/docs/ui-spec/screens/S01-worklist-dashboard.md` (+ C05 filter-bar) — filter interaction + badge (spec)
- **Tests:** `repo.list_customer_ids` (tmp dir; "drop file mới → xuất hiện"); `worklist_filters` has_script (action in/out theo set); cache_repository action có customer_id

## Implementation steps
1. Entity: thêm `customer_id` vào `ActionQueueItem` (Optional[int], None khi base thiếu).
2. Reader: `_fetch_actions` LEFT JOIN `wh_customer_base` theo `customer_key`, select `customer_id`; map vào entity.
3. Repo: `list_customer_ids()` — scandir, parse `{cid}.json` → set[int]. Gọi mỗi lần (no cache) ⇒ auto-handle.
4. Filter: `parse_filters` thêm `has_script`; `apply_filters(actions, tasks, filters, script_cids)`: nếu bật → `[a for a in actions if a.customer_id in script_cids]` (tasks giữ nguyên — không áp v1). Pure: set truyền vào.
5. `screen_worklist._load_worklist_data`: `script_cids = approach_repo.list_customer_ids()` → vào `apply_filters` + vào template để badge action có `customer_id in script_cids`.
6. Template: chip toggle `?has_script=1`; badge + nút "Gọi" trên action có script → emit `action_queue.call_mode_requested` (→ S14).
7. Spec: filter interaction + badge vào S01 (+ C05); `npm run check` xanh.

## Todo
- [ ] ActionQueueItem.customer_id + reader JOIN + test
- [ ] repo `list_customer_ids()` + test ("file mới tự xuất hiện")
- [ ] filter has_script (parse+apply) + test
- [ ] screen_worklist wiring
- [ ] template chip + badge + Gọi→S14
- [ ] spec S01/C05 + check
- [ ] e2e: bật chip → chỉ action có script; thêm file mới → badge ở load sau (no restart)

## Success criteria
- Bật "Có kịch bản" → worklist chỉ còn action của khách có file script.
- **Drop `{cid}.json` mới → action khách đó có badge + lọt filter ở load kế tiếp, KHÔNG restart.**
- Action match cả khi `party_id` chưa sync (match theo customer_id).
- Tests xanh.

## Risks
- `customer_key` không có trong `wh_customer_base` → `customer_id=None` → action đó không match (chấp nhận; LEFT JOIN).
- Dùng `customer_id` (natural) để match, KHÔNG `customer_key`.
- Perf: listdir/load — ổn; option TTL-cache nếu dir phình + QPS cao.
