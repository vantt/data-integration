# Phase 02 — Read-back notes/activities từ crm.db (WS-A1)

## Yêu cầu
`build_approach_prompts.py` (và generator phase 03) fill `{{recent_notes}}` bằng dữ liệu thật thay hardcode `[]`. `{{recent_convos}}` giữ `[]` (FB messages = ngoài scope).

## Thiết kế
- Module `scripts/crm_history_reader.py`:
  - Lấy crm.db: mặc định `docker cp crm:/data/crm.db {scratch}/crm_history_snapshot.db` (volume named, không mount host); flag `--crm-db <path>` bỏ qua docker. Copy = tránh lock DB sống.
  - Map: `crm_party_identity` WHERE `identity_type='sapo_customer'` AND `identity_value IN (customer_ids)` → party_id.
  - Notes: `crm_note` WHERE party_id, `deleted_at IS NULL`, ORDER BY created_at DESC LIMIT 5 → `{date, body, kind:"note"}`.
  - Activities: `crm_activity_log` WHERE party_id, ORDER BY occurred_at DESC LIMIT 5 → `{date, body, kind:"activity", channel, outcome(contact_outcome||outcome)}`.
  - Gộp 2 nguồn, sort desc theo date, cắt 5 (contract template: "tối đa 5 ghi chú CRM gần nhất").
  - API: `fetch_recent_notes(customer_ids: list[int], crm_db: Path|None) -> dict[int, list[dict]]` — batch 1 query, không per-customer.
- Degrade mềm: docker fail / db thiếu / không có identity → `{}` + warning, prompt vẫn sinh với `[]` (giữ hành vi cũ, không chặn batch).
- `build_approach_prompts.py`: thêm flag `--no-history`; mặc định đọc history.

## Files
- Tạo: `scripts/crm_history_reader.py`
- Sửa: `scripts/build_approach_prompts.py` (fill nhận `recent_notes`)

## Validate
- Chạy builder với `--ids` của khách có note thật (party 26e92c46… / 0c5bcb75…) → prompt chứa body note.
- Khách không có note → `recent_notes: []`.
- Tắt docker path (`--crm-db` sai) → warning + vẫn sinh prompt.
