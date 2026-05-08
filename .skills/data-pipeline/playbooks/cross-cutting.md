# Cross-Cutting Concerns — Canonical Reference

Tám concerns này xuất hiện trong nhiều nhóm. File này là **canonical home** — các playbook
khác chỉ link tới đây, không duplicate nội dung.

---

## DuckDB Locking

**Anchor:** `#duckdb-locking`

DuckDB là **single-writer** storage. Vi phạm rule này gây `IO Error: Could not set lock on
file` hoặc silent data corruption.

### Rules

- Mọi asset write DuckDB PHẢI có: `op_tags={"dagster/concurrency_key": "duckdb_lock"}`
  với pool limit=1 (L11)
- **read_only mode KHÔNG acquire lock** — safe để Metabase query song song với writer (L18)
- **Asset-level concurrency** (`op_tags`), KHÔNG job-level (`concurrency_group`) — job-level
  không đủ granular khi assets từ nhiều job cùng chạy
- **Slot leak khi cancel runs (L20):** Cancel không tự giải phóng slot → janitor (L39)
  chạy mỗi 5 phút để reclaim leaked slots

### Windows / Bind-Mount Risks

- **Windows NTFS bind-mount (L62, L70, L73):** `dllhost.exe` (COM Surrogate / Windows
  Defender) có thể lock DuckDB file trên bind-mount → `IO Error` dù Dagster slot available
- **Defender exclusion (L72):** Thêm toàn bộ `data_lake/` directory vào Defender exclusion
  list — không chỉ `.duckdb` file. Defender scan parquet cũng gây lock contention
- **Fix dứt khoát (L73):** Dùng named Docker volume thay bind-mount cho DuckDB files
  (`sapo_warehouse.duckdb`, `olap.duckdb`) — named volume không expose Windows filesystem locks

### Purge VACUUM Warning

- **VACUUM exclusive lock (L74):** SQLite VACUUM (health DB purge) acquire exclusive lock
  5+ phút — block mọi Dagster reads trong thời gian đó. Schedule VACUUM trong maintenance
  window, không giữa production schedule.

### Referenced from

OPS (`op_tags` setup), MODEL (dbt là writer chính), SERVE (read_only semantics),
INGEST (nếu asset write warehouse trực tiếp)

---

## Env Vars / Config Resolution

**Anchor:** `#env-vars-config-resolution`

### Layered Config (ưu tiên từ cao xuống thấp)

```
Process env (docker-compose environment:) ← highest priority
  ↑
.env.docker / .env.local (loaded by python-dotenv)
  ↑
ingestion/.dlt/secrets.toml (dlt-specific secrets)
  ↑
ingestion/.dlt/config.toml (dlt non-secret config)
  ↑
ingestion/.dlt/secrets.toml.sample (defaults / template) ← lowest priority
```

### DLT Double-Underscore Mapping

DLT map env var → config key theo pattern `__` (double underscore):

```
SOURCES__SAPO__DOMAIN        → sources.sapo.domain
SOURCES__SAPO__API_TOKEN     → sources.sapo.api_token
DESTINATION__FILESYSTEM__BUCKET_URL → destination.filesystem.bucket_url
```

Dùng env vars này trong `.env.docker` / CI — không hardcode credentials trong config.toml.

### `extra_placeholders` cho Custom Partition Fields

```toml
# ingestion/.dlt/config.toml
[destination.filesystem]
bucket_url = "file:///app/var/data_lake"

[destination.filesystem.layout_params]
extra_placeholders = ["ingest_method"]
```

Partition path `{table_name}/ingest_method={ingest_method}/year={year}/month={month}/`
yêu cầu `extra_placeholders` declare explicit.

### Single .env Organization

Dùng **một `.env` file duy nhất** với sections (comments), KHÔNG split per-service.
Xem memory `feedback_config_organization`. Đặt `.env.local` ở **project root**
(không phải `ingestion/`) — `load_dlt_configuration()` tìm ở project root (L9, L10, L35).

### Referenced from

INGEST (primary user), OPS (deployment env), MODEL (DBT_DATA_LAKE_PATH, DBT_EXPORT_PATH)

---

## Docker Mount Paths

**Anchor:** `#docker-mount-paths`

### Convention

- Code tại `/app/` trong container
- Data tại `/app/var/` trong container

```
Host (app_data/)              Container (/app/var/)
├── data_lake/           →    /app/var/data_lake
├── dagster_home/        →    /app/var/dagster_home
├── logs/                →    /app/var/logs
└── backups/             →    /app/var/backups
```

### Path Resolution Pattern

```python
data_lake_path = os.environ.get("DBT_DATA_LAKE_PATH", "/app/var/data_lake")
```

Dùng env var + Docker default — không hardcode path.

### Runbook A — Serving Views Absolute Paths (sau mount change)

<!-- VERBATIM từ SKILL.md "Critical Rules > Serving Views & Absolute Paths" -->

**⚠️ CRITICAL AFTER DOCKER MOUNT CHANGES:**

Serving views (`olap.duckdb`) bake absolute paths into their SQL. If you change Docker
volume mount paths or directory structure:

1. **Stop Metabase first** (releases DuckDB lock):
   ```bash
   docker compose down
   ```

2. **Regenerate serving views** on the data_platform container:
   ```bash
   docker compose up -d data_platform
   docker compose exec data_platform python scripts/provisioning/bootstrap_serving_views.py
   ```

3. **Restart Metabase** (will connect to updated views):
   ```bash
   docker compose up -d metabase
   ```

**Why?** Views contain embedded paths like:
```sql
CREATE VIEW dim_customers AS SELECT * FROM '/app/var/data_lake/export/marts/rolling/dim_customers/*.parquet'
```

If `/app/var/data_lake` changes to `/app/data_lake`, view paths break and Metabase queries fail.

### Runbook B — dbt Target Cache (sau mount change)

<!-- VERBATIM từ SKILL.md "Critical Rules > dbt Target Cache & Rolling Parquet Paths" -->

**⚠️ CRITICAL AFTER DOCKER MOUNT CHANGES:**

dbt's `target/` directory caches compiled SQL and model state including **absolute parquet
output paths** from `get_rolling_location()`. When Docker mount paths change
(e.g. `/app/data_lake` → `/app/var/data_lake`):

- Cached state still references old paths → dbt tries to read/write to non-existent old paths
- Error: `IO Error: Cannot open file "/app/data_lake/export/marts/rolling/...": No such file or directory`

**Fix:** Clean dbt target cache and regenerate manifest before Dagster uses it:
```bash
docker exec data_platform bash -c "rm -rf /app/transformation/target"
docker exec data_platform bash -c "cd /app/transformation && dbt deps && dbt parse"
docker compose restart data_platform
```

**⚠️ Order matters:** `dbt parse` MUST run before Dagster restarts — Dagster imports
`manifest.json` at startup. If you `rm -rf target/` and restart without `dbt parse`,
Dagster crashes with `DagsterDbtManifestNotFoundError`.

Or selectively rebuild only failing models (no target nuke needed):
```bash
docker exec data_platform bash -c "cd /app/transformation && dbt build --select model_name_1 model_name_2"
```

### Referenced from

MODEL (rolling output paths), SERVE (view absolute paths), OPS (volumes in maintenance)

---

## Telemetry / Zombie Threads

**Anchor:** `#telemetry-zombie-threads`

### Problem

DLT và dbt spawn background telemetry threads. Các threads này **không tự dừng** khi
pipeline hoàn thành — giữ Python process alive → Dagster job không exit → executor timeout.

### Fix (set ở process level)

```bash
# Trong .env.docker hoặc docker-compose environment:
DLT_TELEMETRY_DISABLED=true
DBT_SEND_ANONYMOUS_USAGE_STATS=false
```

Phải set ở **process level** (env var), không phải trong code — dbt đọc env var trước
khi init Python runtime.

### Reference

Lesson 4 trong `references/dagster-patterns.md` — "Zombie Background Threads" — chi tiết
về detection và fix. Cả INGEST và MODEL process bị ảnh hưởng.

### Referenced from

OPS (canonical), INGEST (dlt process), MODEL (dbt subprocess)

---

## File Locking Windows vs Linux

**Anchor:** `#file-locking-windows-vs-linux`

### Behavior Difference

| Platform | Advisory lock | Implication |
|----------|--------------|-------------|
| Windows | Lock là mandatory (OS-enforced) | `PermissionError` khi process khác đang hold |
| Linux container | Lock là advisory (cooperative) | Không có error — race condition silent |

### Windows-Specific Issues

- **`dllhost.exe` (COM Surrogate / Defender):** Lock DuckDB file trên NTFS bind-mount
  ngay cả khi không có Dagster process (L62, L70)
- **Workaround:** Named Docker volume (không expose NTFS filesystem) hoặc Defender exclusion
- **L12:** Cross-platform file locking primitive — dùng `fcntl` (Linux) hoặc `msvcrt` (Windows)
  với proper fallback

### Linux Container Handling

- File lock không automatic → phải implement explicit: retry loop, swap pattern,
  hoặc graceful skip
- DuckDB WAL files (`.wal`, `.shm`) biến mất mid-copy → `cp -a` return non-zero (L68)
  — handle exit code explicitly

### SQLite on Windows

- SQLite WAL mode hoạt động khác trên Windows vs Linux — xem `#sqlite-wal-safety`

### Referenced from

OPS (dllhost detection), INGEST (file-drop sensor), cross-cutting DuckDB locking

---

## SQLite WAL Safety

**Anchor:** `#sqlite-wal-safety`

SQLite được dùng cho health DB (`ingestion_health.db`) và Dagster metadata store.

### Known Issues

| ID | Issue | Fix |
|----|-------|-----|
| L56 | SQLite WAL safety trong purge/cleanup — WAL file phải flush trước khi copy/delete | `PRAGMA wal_checkpoint(TRUNCATE)` trước backup |
| L68 | `cp -a` return non-zero khi WAL/SHM biến mất mid-copy | Handle exit code; kiểm tra file integrity sau copy |
| L74 | SQLite VACUUM acquires exclusive lock 5+ phút — block tất cả readers | Schedule VACUUM trong maintenance window (01:00-02:00 ICT), KHÔNG trong production schedule |

### Ghost Lock Detection (L62)

Health DB watchdog chạy mỗi 10 phút:
- Detect ghost lock: process hold lock đã exit nhưng lock file còn
- Detect stale lock: lock held > 2h (ký hiệu hung process)
- Action: alert + optional force-unlock

### Dagster SQLite Store

Dagster dùng SQLite cho run history, event log. Purge job (`prune_dagster_history`) phải
acquire `duckdb_lock` slot (L47) để tránh concurrent write conflict với backup.

### Referenced from

OPS (purge VACUUM, Dagster store), TRUST (health DB)

---

## CWD and `load_dlt_configuration`

**Anchor:** `#cwd-and-load_dlt_configuration`

### Problem

DLT resolve config paths (`config.toml`, `secrets.toml`) **từ CWD tại thời điểm chạy**,
không phải từ script location. Dagster assets chạy với CWD = project root, nhưng dlt config
nằm trong `ingestion/.dlt/`.

### Fix Pattern (L8, L9, L10)

```python
import os
from orchestration.assets.utils import DLT_DIR, load_dlt_configuration

@asset(...)
def my_ingestion_asset(context):
    os.chdir(DLT_DIR)           # L9: phải gọi TRƯỚC load_dlt_configuration
    load_dlt_configuration()     # L10: phải gọi đầu mỗi asset
    run_my_pipeline(argv=[])     # L8: argv=[] tránh pick up Dagster sys.argv
```

### `.env.local` Location

File `.env.local` đặt ở **project root** (cùng cấp với `ingestion/`, `transformation/`),
KHÔNG phải trong `ingestion/`. `load_dlt_configuration()` tìm `.env.local` ở project root.

### Referenced from

INGEST (primary user), OPS (asset wiring pattern)

---

## Composite PK Update Trap (ingestion_runs)

**Anchor:** `#composite-pk-update-trap`

### Problem

`ingestion_runs` table dùng composite PK `(asset_key, run_id)`. Trong một Dagster job,
**nhiều assets share cùng `run_id`**. Nếu UPDATE/DELETE chỉ filter `run_id` (không filter
`asset_key`), operation sẽ affect tất cả assets trong job — gây data corruption.

### Rule (L44)

```sql
-- WRONG — affect tất cả assets trong job
UPDATE ingestion_runs SET rows_written = 42 WHERE run_id = 'abc123';

-- CORRECT — chỉ affect đúng asset
UPDATE ingestion_runs SET rows_written = 42
WHERE asset_key = 'sapo/orders_batch' AND run_id = 'abc123';
```

**Mọi** UPDATE, DELETE, SELECT WHERE trên `ingestion_runs` PHẢI filter cả hai:
`asset_key AND run_id`.

### Code Review Rule

Đây là mandatory code review check — reviewer phải grep mọi `UPDATE ingestion_runs`
và `DELETE FROM ingestion_runs` để verify composite filter. Xem memory
`feedback_ingestion_runs_composite_pk`.

### Referenced from

TRUST (health recorder), INGEST (record_run call sites)
