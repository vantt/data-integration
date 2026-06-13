# Phase 01 — Nền tảng, Stack & Local Environment

**Context:** [plan.md](plan.md) · Report: `../reports/schema-scan-260613-1133-raw-serving-semantic-integration-report.md`

## Overview
- **Priority:** P0 (chặn mọi phase khác)
- **Status:** ⬜ Not started
- Dựng nền: Postgres 16, repo Go app (**hexagonal**), migration SQL-first, docker-compose local. **Auth hoãn** (tin-cậy-LAN như `detailView`); chỉ tạo `app_user` để gán owner/assignee. Quy mô **~10 user** → pool nhỏ.

## Key Insights
- Stack chốt: Go (single binary, deploy dễ) + Python pipeline (đồng bộ ingestion) + **SQLite WAL** nhúng (`modernc.org/sqlite`, no CGO).
- Convention bắt buộc: **TIMESTAMPTZ mọi nơi** (memory: naive TIMESTAMP gây sai date_key). `created_at`/`updated_at` mặc định `now()` (UTC), hiển thị ICT ở app.
- Tách **2 file**: `crm.db` (Go ghi, bảng `crm_*`) vs `cache.db` (Python ghi, `wh_*`; Go ATTACH RO). Fuzzy dedup dùng FTS5 (Phase 02) — SQLite không có pg_trgm.

## Requirements
- **FR:** crm.db (WAL) + cache.db (ATTACH RO) khởi tạo được; migrate up/down; Go app `/healthz`; `crm_app_user` map về `dim_staff`.
- **NFR:** Reproducible (`make build` → 1 binary chạy ngay, không cần container DB); SQL-first migration versioned; 10 user → đơn giản.

## Architecture
- Layout đề xuất — **hexagonal** (domain thuần ⟂ ports ⟂ adapters; giống `detailView`):
```
crm/
  app/
    cmd/server/           # entrypoint
    internal/
      domain/             # entity + business rule THUẦN (no pg/http import)
      ports/              # interface: PartyRepo, InsightReader, SapoWriter...
      adapters/
        inbound/http/      # chi handler + templ/HTMX
        outbound/sqlite/   # sqlc + modernc.org/sqlite (crm.db, ATTACH cache.db RO)
        outbound/duckdb/   # KHÔNG cần — Python sync ghi cache.db (Phase 04)
        outbound/sapo/     # write-back adapter (Phase 07, làm sau)
    sqlc.yaml              # engine: sqlite
  migrations/             # NNNN_*.up.sql / *.down.sql (golang-migrate, dialect sqlite3)
  sync/                   # Python: reverse-ETL ghi cache.db + ingest chat (Phase 04/05/06)
  data/                   # crm.db + cache.db (gitignore)
  AGENTS.md               # KHÔNG có docker DB — chạy binary + python
```
- **Architecture test** (như detailView): domain/ports KHÔNG import sqlite/http/sapo — enforce bằng test.
- **2 file SQLite:** Go mở `crm.db` (read-write, WAL) + `ATTACH 'cache.db' AS cache` **read-only** (`?mode=ro`). Python sync chỉ mở `cache.db`.
- PRAGMA bắt buộc mỗi connection (Go & Python): `journal_mode=WAL`, `foreign_keys=ON`, `busy_timeout=5000`, `synchronous=NORMAL`.
- Không có extension — fuzzy dedup dùng FTS5 (built-in SQLite) + chuẩn hoá app-side (Phase 02).

### Core DDL (Phase 01) — SQLite dialect
```sql
-- crm.db (Go ghi). SQLite không có schema → prefix crm_*. UUID sinh ở app (TEXT).
CREATE TABLE crm_app_user (
  user_id    TEXT PRIMARY KEY,            -- UUID do app sinh
  staff_id   INTEGER,                     -- ↔ dim_staff.staff_id (Sapo account)
  email      TEXT UNIQUE NOT NULL,
  full_name  TEXT NOT NULL,
  role       TEXT NOT NULL DEFAULT 'sales',   -- sales|care|manager|admin (chưa enforce, auth hoãn)
  is_active  INTEGER NOT NULL DEFAULT 1,       -- bool = 0/1
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),  -- UTC ISO-8601
  updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

-- audit: trigger updated_at (lặp lại pattern này cho mọi bảng có updated_at)
CREATE TRIGGER trg_app_user_touch AFTER UPDATE ON crm_app_user
BEGIN
  UPDATE crm_app_user SET updated_at = strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE rowid = NEW.rowid;
END;
```

## Related Code Files
- **Tạo:** `crm/migrations/0001_app_user_pragmas.up.sql` (+`.down.sql`), `crm/app/cmd/server/main.go`, `crm/app/internal/adapters/outbound/sqlite/db.go` (mở crm.db WAL + ATTACH cache.db RO + PRAGMA), `crm/app/sqlc.yaml`, `crm/AGENTS.md`, `crm/.env.example`, `crm/Makefile` (migrate-up/down/build).
- **Đọc tham chiếu:** `detailView/` (mẫu hexagonal + LAN-trust no-auth — học cấu trúc).

## Implementation Steps
1. Tạo sub-project `crm/` + `AGENTS.md` (ranh giới: Go app & migration chỉ trong `crm/`).
2. `sqlite/db.go`: mở `crm.db` (`_pragma=journal_mode(WAL)&busy_timeout=5000&foreign_keys(1)`) + `ATTACH 'cache.db' AS cache` read-only (tạo file rỗng nếu chưa có).
3. Migration `0001`: `crm_app_user` + trigger touch + seed 1 admin (UUID app-gen).
4. Go skeleton: chi router, `/healthz` (ping `SELECT 1` cả crm.db & cache).
5. `sqlc.yaml` engine `sqlite` + generate query layer rỗng.
6. golang-migrate (dialect sqlite3) + `Makefile` migrate-up/down, build single binary.

## Todo
- [ ] Sub-project `crm/` + AGENTS.md
- [ ] `sqlite/db.go` mở crm.db WAL + ATTACH cache.db RO + PRAGMA
- [ ] Migration 0001 (app_user + trigger) up/down sạch
- [ ] Go `/healthz` xanh (cả 2 file)
- [ ] sqlc (engine sqlite) generate OK
- [ ] Makefile build → 1 binary chạy được, README

## Success Criteria
- `make build` → 1 binary; chạy → `/healthz` 200, `crm.db` (WAL: có `-wal`/`-shm`) + `cache.db` ATTACH read-only OK, `crm_app_user` có admin, `migrate down` rollback sạch. **Không cần container DB.**

## Risk Assessment
- **modernc.org/sqlite (pure-Go)**: chậm hơn CGO chút nhưng đủ cho 10 user; đổi lại cross-compile dễ, no CGO.
- **Cross-process write** (Go crm.db / Python cache.db): tách 2 file → mỗi file 1 writer, hết tranh chấp. WAL + busy_timeout cho an toàn.
- **Windows path** (memory): forward-slash; SQLite file lock trên Windows OK (local disk, KHÔNG để file trên network share).

## Security
- Secrets qua env/`.env` (gitignore). File `crm.db`/`cache.db` để local disk (KHÔNG network share). **Auth hoãn** (LAN-trust như detailView); `crm_app_user.role` để sẵn cho phân quyền sau, chưa enforce login ở v1.

## Next Steps
→ Phase 02 (party/identity) cần crm.db + migrate + PRAGMA WAL/FK sẵn sàng.
