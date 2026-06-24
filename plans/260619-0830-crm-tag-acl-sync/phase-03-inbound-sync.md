# Phase 03 — Inbound Sync: Warehouse → CRM Party Tags

**Context:** [plan.md](plan.md) · Requires: Phase 01 + 02 done

## Overview
- **Priority:** P1
- **Status:** ⬜ TODO
- Extend reverse-ETL pipeline với module `tag_sync.py`: đọc `customer_group` từ `wh_customer_base` (cache.db), lookup ACL mapping trong `crm_ext_tag_map`, upsert `crm_party_tag` với `source='sapo_v2_sync'`.

## Key Insights
- **Không đọc warehouse trực tiếp** — `customer_group` đã có trong `wh_customer_base` (cache.db) từ reverse-ETL step hiện tại. Tag sync chỉ đọc cache.db + ghi crm.db.
- **1-writer rule** phải giữ: Python sync writes `crm_party_tag` (crm.db) — đây là ngoại lệ so với rule "Go app writes crm.db". Cần xác nhận không có concurrent write conflict (reverse-ETL chạy scheduled, không concurrent với Go app).
- Lookup ACL: `crm_ext_tag_map` nằm trong `crm.db` → tag_sync cần ATTACH cả 2 file.
- Conflict rule: `ON CONFLICT(party_id, tag_id) DO NOTHING` — không override `source='crm_user'`.

## Architecture

```
cache.db (read-only)          crm.db (write)
  wh_customer_base              crm_party
    customer_id                   party_id
    customer_group          ←→    crm_party_external_id (lookup party_id)
                                  crm_ext_tag            (ACL registry)
                                  crm_ext_tag_map        (mapping)
                                  crm_party_tag          (target — upsert)

Flow:
  1. Fetch wh_customer_base WHERE customer_group IS NOT NULL
  2. For each row:
     a. Lookup crm_party_external_id(source_system='sapo_v2', external_key=customer_id) → party_id
     b. Lookup crm_ext_tag(source_system='sapo_v2', ext_key=customer_group) → ext_tag_id
     c. Lookup crm_ext_tag_map(ext_tag_id, is_active=1, direction IN ('inbound','both')) → [crm_tag_id, ...]
     d. For each crm_tag_id:
          INSERT INTO crm_party_tag(party_id, tag_id, source, ext_ref, tagged_at)
          VALUES (?, ?, 'sapo_v2_sync', customer_group, now())
          ON CONFLICT(party_id, tag_id) DO NOTHING   ← CRM user tags protected
  3. Log sync stats (count tagged, count skipped no-party, count skipped no-mapping)
```

## Related Code Files
- **Tạo:** `crm/sync/tag_sync.py` — module độc lập, callable từ reverse_etl
- **Sửa:** `crm/sync/reverse_etl_warehouse_to_crm.py` — gọi `tag_sync.run(cache_conn, crm_db_path)` sau khi upsert wh_customer_base
- **Đọc:** `crm/sync/sqlite_upsert.py` — pattern open_cache_db, insert_sync_run để follow
- **Đọc:** `crm/sync/duckdb_reader.py` — fetch_customer_base (nguồn customer_group)

## Implementation Steps

1. **Tạo `crm/sync/tag_sync.py`:**
   - `def run(cache_conn, crm_db_path: str) -> dict` — trả stats dict
   - Open crm.db connection (sqlite3, WAL mode, foreign_keys=ON)
   - Load `wh_customer_base` từ cache_conn (customer_id, customer_group)
   - Load toàn bộ active mapping từ crm.db vào dict: `{(source_system, ext_key): [crm_tag_id, ...]}`
   - Load `crm_party_external_id` lookup: `{(source_system, external_key): party_id}`
   - Iterate rows, resolve party_id + crm_tag_ids, batch INSERT với executemany
   - Log stats (tagged/skipped-no-party/skipped-no-mapping/error)

2. **Sửa `reverse_etl_warehouse_to_crm.py`:**
   - Import `from crm.sync import tag_sync`
   - Sau step upsert_customer_base, gọi `tag_sync.run(cache_conn, crm_db_path())`
   - Wrap trong try/except — tag sync failure không chặn toàn bộ ETL

3. **Viết tests** `crm/sync/tests/test_tag_sync.py`:
   - in-memory SQLite fixture với vài rows wh_customer_base + crm_ext_tag_map + crm_party_external_id
   - Assert crm_party_tag được tạo đúng với source='sapo_v2_sync'
   - Assert CRM user tag (source='crm_user') không bị override

## Todo
- [ ] `crm/sync/tag_sync.py`
- [ ] Update `reverse_etl_warehouse_to_crm.py`
- [ ] `crm/sync/tests/test_tag_sync.py`
- [ ] Chạy reverse-ETL end-to-end, verify crm_party_tag có rows source='sapo_v2_sync'

## Success Criteria
- Sau khi chạy reverse-ETL: party có `customer_group=TYPE_WHOLESALE` → có `crm_party_tag` với tag "KH Sỉ" và `source='sapo_v2_sync'`
- Party đã có tag "KH Sỉ" do CRM user gán → `source='crm_user'` vẫn giữ nguyên sau sync
- `skipped-no-party` count đo được (party chưa seed vào CRM)
- `skipped-no-mapping` count đo được (customer_group chưa có trong crm_ext_tag)

## Risk
- **1-writer rule breach:** Python ghi crm.db trong khi Go app đang dùng → dùng `busy_timeout=5000` và batch nhỏ; chạy scheduled ngoài giờ cao điểm
- **Party chưa tồn tại trong crm.db** (Go seed consumer chưa chạy) → skip + log, không crash
- **customer_group thay đổi trong Sapo** → tag cũ vẫn còn trong crm_party_tag (không auto-remove); cần quyết định: giữ (conservative) hay clean (risk data loss). **v1: giữ — không auto-remove sync tags**
