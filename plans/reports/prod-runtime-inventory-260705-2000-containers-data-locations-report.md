# Prod Runtime Inventory — Containers + Data Locations (máy hiện tại = PROD)

**Date:** 2026-07-05 | **Host:** Windows 11 + Docker Desktop (WSL2) | **Feeds:** plan `260705-1704-modular-monorepo-boundary-hardening`

## 1. Containers thuộc data-integration (8 running)

| Container | Image (local build) | Port host | Caddy hostname | Ghi chú |
|---|---|---|---|---|
| `data_platform` | data-integration-data_platform (3.37GB) | 3000→3001 | etl.lan.fwg.vn | Dagster |
| `metabase` | data-integration-metabase (3.18GB) | 3001→3000 | bi.lan.fwg.vn | |
| `rill` | data-integration-rill (1.87GB) | 3002→9009 | rill.lan.fwg.vn | |
| `data_fileserver` | caddy:alpine | 3004→8080 | (files) | serve standalone exports |
| `detail_view` | data-integration-detail_view (347MB) | 3005→8000 | — | **RETIRED nhưng vẫn chạy** |
| `evidence` | data-integration-evidence (1.98GB) | 3006→3000 | evidence.lan.fwg.vn | |
| `crm` | data-integration-crm (602MB) | 3007→8090 | — (direct port) | |
| `crm_drill_runner` | data-integration-crm_drill_runner (306MB) | 9000 (internal) | — | mount docker.sock, spawn sibling container theo TÊN |

Tất cả 8 services đều hardcode `container_name:` trong compose (chặn dual-stack — xem §5).

## 2. Hệ thống KHÁC chạy chung máy (không đụng)

- `nu-*` (nu-data-pipeline — hệ Docker riêng, ports 13000-13004), `goclaw-*` (3010, 5432, 6379, 9222, 4317-4318, 16686, 18790), `vnstock-*` (8100), `repo-*`/`fgos-*` (2222-2223, 5173, 8765-8766), `hermes` (8642, 9119), `neural-memory` (8000), `caddy-global` (**80/443** — reverse proxy chung, network `caddy_net` external, route theo compose labels `caddy: <hostname>`).
- Port đã chiếm trên host: 80, 443, 2222-2223, 3000-3010, 4317-4318, 5173, 5432, 6379, 8000, 8100, 8642, 8765-8766, 9119, 9222, 13000-13004, 16686, 18790. **Dải trống đề xuất cho dev stack: 4000-4010.**

## 3. Data map — data-integration

### Bind mounts (host `D:\Vantt\app\data-integration\app_data\`)

| Path | Size | Ai ghi | Ai đọc (`:ro`) |
|---|---|---|---|
| `app_data/data_lake/` | 1.1GB | data_platform | metabase, rill, evidence, crm, detail_view |
| ├ `*_raw` zones (sapo_v2_raw, misa_raw, hug_raw, gsheet_raw, shopee_raw…) | — | dlt ingestion | dbt |
| ├ `sapo_warehouse.duckdb` (+.wal) | — | dbt | — |
| ├ `serving/olap.duckdb` | — | bootstrap_serving_views | Metabase, CRM |
| ├ `serving/standalone/` | — | export jobs | data_fileserver (port 3004) |
| └ `crm_export/`, `export/` | — | crm / pipeline | transformation |
| `app_data/dagster_home/` | 6.4GB | data_platform | — (run history lớn — có skill /purge-dagster-runs) |
| `app_data/backups/` | **12GB** | data_platform (backup jobs) | — |
| `app_data/metabase_data/` | 680MB | metabase (H2 app-db) | — |
| `app_data/input_source/` | 49MB | user file-drop | data_platform |
| `app_data/rill/` | ~0 | rill (.rill state) | — |
| `app_data/analysis`, `logs`, `crm_verify_tmp` | ~1MB | misc | — |
| `app_data/metabase_data.backup.20260423-145815/` | 140MB | — | — (backup thủ công cũ — candidate dọn) |

Config mounts đặc biệt vào `data_platform` (`:ro`, phục vụ `scripts/backup/backup.sh` copy config): `./docker-compose.yml`, `./Dockerfile.dataplatform`, `./Dockerfile.metabase`.

### Named volumes (trong WSL2 VM, KHÔNG nằm trong repo dir)

| Volume | Size | Links | Mounted vào |
|---|---|---|---|
| `data-integration_crm_data` | 42.8MB | 2 | crm `/data` (RW — **SQLite CRM sống ở đây**); data_platform `/app/var/crm_data` (`:ro` — pipeline export crm_app_user/crm_task đọc trực tiếp) |
| `data-integration_crm_backups` | 275MB | 2 | crm `/backups` (RW); crm_drill_runner (`:ro`) |
| `data-integration_monitoring_db` | 51.9MB | 2 | data_platform + metabase, cùng mount `/app/var/data_lake/monitoring` (SQLite WAL monitoring) |
| `data-integration_crm_verify_data` | 0B | 1 | crm_drill_runner `/verify_data` (drill scratch) |
| `crm_data` (không prefix) | 426kB | 0 | **ORPHAN** — volume thời chưa có project prefix; ứng viên xóa (cần approve) |
| `45f9546ddd…` (anonymous) | ? | 0 | orphan, ứng viên xóa (cần approve) |

### Env files (root repo)

- `.env.docker` — data_platform + metabase: Sapo credentials, dlt destination, Lark webhook/secret, Metabase API key, MB_* (secrets — không commit).
- `.env` — CRM: HUG_ADMIN_SECRET, CRM tokens, DRILL_TOKEN, CF Access (secrets).
- `.env.local`, `.env.example`, `.env.docker.example` — đã tồn tại (examples cập nhật 2026-07-05).

## 4. Data contract phát hiện thêm (bổ sung Phase 6)

`data_platform` đọc **trực tiếp volume SQLite của CRM** (`data-integration_crm_data` → `/app/var/crm_data:ro`) — đây là data contract cứng giữa 2 components, phải vào boundary doc. Đổi schema crm.db = MAJOR đối với data-platform export.

## 5. Blockers cho dual-stack (dev+prod cùng máy) — phải sửa trong Phase 5

1. **`container_name:` hardcode cả 8 services** → 2 stacks không thể cùng chạy. Gỡ hoặc parameterize `${STACK_PREFIX}`. Lưu ý ripple: `crm_drill_runner` spawn sibling container **theo tên** (kiểm `crm/ops/restore_verify_crm.py`), backup/restore script + docs tham chiếu `docker compose restart crm`.
2. **Host ports hardcode** (3000-3007) → parameterize `${PORT_*}`; dev dùng 4000-4010.
3. **Caddy hostnames hardcode** (etl/bi/rill/evidence.lan.fwg.vn) → parameterize; dev: `*.dev.lan.fwg.vn` (cần thêm DNS record/wildcard cho caddy-global — kiểm tra caddy-global config DNS01).
4. **Named volumes prefix theo compose project name** → dev clone ở dir khác (vd `D:\Vantt\app\data-integration-dev`) tự có prefix riêng — OK miễn gỡ container_name.
5. **Nguồn ingestion là MỘT (Sapo/MISA/webhook prod)** → dev data_platform KHÔNG được chạy sensors/schedules mặc định (double-ingest, ghi đè cursor dlt state, kill loop webhook consumer). Dev cần: sensors OFF + data_lake snapshot copy, hoặc chỉ chạy dbt trên copy.
6. **crm_drill_runner mount docker.sock + spawn container** — dev stack nên disable service này (profiles: prod-only) trừ khi cần test drill.
7. detail_view RETIRED vẫn chạy — đề xuất: không mang sang dev stack, cân nhắc stop ở prod (cần user quyết).

## Unresolved Questions

1. Orphan volumes (`crm_data` không prefix, anonymous `45f95…`) + `metabase_data.backup.20260423/` (140MB) — xóa không?
2. detail_view: stop hẳn trên prod?
3. Dev stack cần data gì: snapshot `data_lake` copy-on-setup (1.1GB, rẻ) có đủ? (dagster_home/backups KHÔNG copy — 18GB vô nghĩa cho dev)
4. DNS `*.dev.lan.fwg.vn` — caddy-global đang dùng DNS01 wildcard hay per-host record?
