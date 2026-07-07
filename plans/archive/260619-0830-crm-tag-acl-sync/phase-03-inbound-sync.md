# Phase 03 — App-side Consumer: Mirror Sync Warehouse → CRM Party Tags

**Context:** [plan.md](plan.md) · Requires: Phase 00 + 01 + 02 done

## Overview
- **Priority:** P1
- **Status:** ✅ DONE — see [phase-03 report](reports/phase-03-implementation-report.md)
- CLI mới `crm/src/sync_party_tags.py` (theo đúng tiền lệ `sync_parties.py`): đọc `wh_customer_base.customer_group_id` từ cache.db (read-only), resolve qua ACL tables trong crm.db, **mirror-reconcile** `crm_party_tag` cho rows sync-owned. Kèm app change: `attach_tag` upgrade `source` khi user gán đè tag sync.

## Key Insights
- **Giữ invariant 1-writer:** `reverse_etl_warehouse_to_crm.py` docstring ghi rõ "app writes crm.db. Never cross-write." Bản plan cũ cho Python pipeline ghi thẳng crm.db là vi phạm — bản này chạy consumer trong `crm/src/` (app codebase, writer hợp lệ), reverse-ETL **không sửa gì**.
- **Không cần bảng desired-state riêng:** desired state = projection của `wh_customer_base` (customer_id, customer_group_id) đã có sẵn trong cache.db. Consumer tự resolve — KISS.
- **Mirror-reconcile, không append-only:** rows `source='sapo_v2_sync'` là hình chiếu trạng thái Sapo hiện tại. Khách đổi group → tag cũ bị xóa cứng, tag mới insert. Rows `source='crm_user'` không bao giờ bị đụng. (Bản cũ "không auto-remove" bị loại: append-only làm CRM trôi khỏi sự thật vĩnh viễn — ngược mục tiêu hệ trung tâm.)
- Tiền lệ code: `sync_parties.py` (CLI entry), `application/party_seed_service.py` (service), `adapters/outbound/sqlite/tag_note_repository.py` (tag repo hiện có `attach_tag`/`detach_tag`).

## Architecture

```
cache.db (read-only)              crm.db (app là writer duy nhất)
  wh_customer_base                  crm_party_external_id  (resolve party_id)
    customer_id                     crm_ext_tag + crm_ext_tag_map (ACL)
    customer_group_id         →     crm_party_tag          (mirror target)

sync_party_tags.py (chạy sau reverse-ETL + sync_parties.py):
  1. Load desired: wh_customer_base WHERE customer_group_id IS NOT NULL
     → resolve party_id (crm_party_external_id, source_system='sapo_v2', external_key=customer_id)
     → resolve crm_tag_ids (crm_ext_tag ext_key=customer_group_id → map is_active=1, direction IN ('inbound','both'))
     → desired set: {(party_id, tag_id)}
  2. Load current: SELECT party_id, tag_id FROM crm_party_tag WHERE source='sapo_v2_sync'
  3. Reconcile trong 1 transaction:
     - INSERT (desired − current): source='sapo_v2_sync', ext_ref=customer_group_id,
       ON CONFLICT(party_id, tag_id) DO NOTHING     ← row crm_user trùng cặp → giữ nguyên
     - DELETE (current − desired): WHERE source='sapo_v2_sync'  ← chỉ rows sync-owned
  4. Log stats: inserted / deleted / skipped-no-party / skipped-no-mapping
```

## App change: source upgrade khi user gán tag

`attach_tag` (tag_note_repository) hiện INSERT thuần. Sửa thành upsert:

```sql
INSERT INTO crm_party_tag (party_id, tag_id, tagged_by, tagged_at, source)
VALUES (?, ?, ?, ?, 'crm_user')
ON CONFLICT(party_id, tag_id)
DO UPDATE SET source='crm_user', tagged_by=excluded.tagged_by
```

User gán đè tag đang là sync → tag trở thành user-owned, reconcile sau đó không xóa nữa (conflict rule dòng 3 trong plan.md — bản cũ khai báo rule nhưng không phase nào implement).

## Related Code Files
- **Tạo:** `crm/src/sync_party_tags.py` — CLI entry (mirror `sync_parties.py`)
- **Tạo:** `crm/src/application/tag_acl_sync_service.py` — reconcile logic (testable, tách khỏi CLI)
- **Sửa:** `crm/src/adapters/outbound/sqlite/tag_note_repository.py` — `attach_tag` upsert + repo methods cho reconcile (list sync-owned, batch insert/delete)
- **Sửa:** nơi schedule `sync_parties.py` (orchestration) — thêm `sync_party_tags.py` vào cùng chuỗi, NGAY SAU sync_parties
- **Đọc:** `crm/src/application/party_seed_service.py`, `crm/src/adapters/outbound/sqlite/cache_repository.py` (pattern đọc cache.db)

## Implementation Steps

1. Repo methods (tag_note_repository hoặc repo mới nếu boundary rõ hơn): `list_party_tags_by_source(source)`, `bulk_attach_synced(rows)`, `bulk_detach_synced(pairs, source)` — DELETE có điều kiện `source=?` trong SQL, không chỉ trong Python.
2. `tag_acl_sync_service.py`: load desired + current, diff, apply trong 1 transaction; trả stats dict.
3. `sync_party_tags.py` CLI: arg `--data` như sync_parties, wire CRMDatabase + cache read-only.
4. Schedule: thêm vào chuỗi orchestration sau `sync_parties.py` (party phải seed trước để resolve external_id).
5. Tests `crm/src/tests/test_tag_acl_sync.py`:
   - insert mới với source='sapo_v2_sync' + ext_ref đúng
   - khách đổi group → row sync cũ bị xóa, row mới insert
   - row `crm_user` cùng cặp (party, tag) → không insert đè, không xóa
   - `attach_tag` lên tag đang sync → source upgrade thành 'crm_user', reconcile sau đó không xóa
   - party chưa seed / group không có mapping → skip + đếm stats

## Todo
- [x] Repo methods + `tag_acl_sync_service.py`
- [x] `sync_party_tags.py` CLI + schedule vào chuỗi orchestration
- [x] `attach_tag` source-upgrade
- [x] `test_tag_acl_sync.py` (5 case trên + idempotency + guard, 7/7 pass)
- [x] Chạy end-to-end: reverse-ETL → sync_parties → sync_party_tags, verify rows `source='sapo_v2_sync'` (939 rows, matches seeded mapping exactly)

**Deviation found + fixed (verified, not a design change):** phase doc's party
resolution via `crm_party_external_id` is a dead table (zero writers in the
actual codebase) — `sync_parties.py` writes `crm_party_identity` instead.
Switched resolution accordingly; confirmed correct via live run
(`skipped_no_party` dropped from 7592 to 0). See implementation report for detail.

## Success Criteria
- Khách group WHOLESALE → có tag "KH Sỉ" `source='sapo_v2_sync'`, `ext_ref='1812239'`
- Đổi group trong wh_customer_base rồi re-run → tag cũ biến mất, tag mới xuất hiện; tag crm_user giữ nguyên
- Chạy 2 lần liên tiếp không đổi input → 0 insert, 0 delete (idempotent)
- Stats skipped-no-party / skipped-no-mapping đo được

## Risk
- **Concurrent write app vs consumer:** cùng codebase + SQLite WAL + busy_timeout sẵn có của CRMDatabase; consumer chạy scheduled batch ngắn — chấp nhận được. Transaction ngắn, batch executemany.
- **Party chưa tồn tại** (sync_parties chưa chạy/khách mới) → skip + log; lần chạy sau tự vá (mirror tự hội tụ).
- **Xóa nhầm khi warehouse feed rỗng bất thường:** guard — nếu desired set rỗng toàn phần trong khi current > N (threshold), abort + log error thay vì xóa sạch (bảo hiểm feed hỏng).
- CRM code baked trong image → sau khi thêm file: `docker compose up -d --build crm` (consumer chạy trong container crm).
