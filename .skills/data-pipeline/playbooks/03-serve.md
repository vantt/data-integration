# SERVE Playbook — Rolling Views & Dual DuckDB

## Trách nhiệm

SERVE group expose analytics data từ rolling Parquet snapshots thành queryable views trong
`olap.duckdb` — database mà Metabase queries.

**Đầu vào:** Rolling Parquet snapshots tại `data_lake/export/marts/rolling/{model}/`
  (produced by MODEL layer dbt run)
**Đầu ra:** DuckDB views trong `data_lake/serving/olap.duckdb` — read-only cho Metabase

**Dual DuckDB architecture:**
- `sapo_warehouse.duckdb` — dbt write target (MODEL layer, read-write)
- `olap.duckdb` — serving database (SERVE layer, read-only for Metabase)

Views trong `olap.duckdb` bake absolute paths vào SQL → mount path change = broken views.

---

## Pre-flight Checklist (đọc TRƯỚC khi implement)

- [ ] Mart models có `location="{{ get_rolling_location() }}"` — KIỂM TRA trước khi setup serve.
      Thiếu → dbt overwrite single file thay vì rolling snapshot → view scan thấy cũ hoặc trống
- [ ] Serving asset khai báo `deps=[dbt_assets]` — Critical Rule 7 SKILL.md.
      Thiếu → Dagster có thể trigger serve trước dbt completes → stale view
- [ ] Verify dual DuckDB files: warehouse (`sapo_warehouse.duckdb`) KHÁC serving (`olap.duckdb`).
      Không share file giữa dbt write và Metabase read
- [ ] Serving views phải regen sau Docker mount path change —
      views bake absolute paths, mount change = broken paths (xem Runbook A trong cross-cutting.md)
- [ ] `bootstrap_serving_views.py` chạy với Metabase đã stop (docker compose down metabase).
      Metabase giữ read lock trên `olap.duckdb` → script write fails nếu Metabase đang chạy
- [ ] dbt target cache cleared sau mount change:
      `rm -rf transformation/target/` + `dbt parse` TRƯỚC khi Dagster restart (cross-cutting Runbook B)
- [ ] Empty folder trong rolling/ → serve script DROP view đó — expected behavior (serving-layer.md §5).
      Nếu model bị xóa, folder empty = clean removal of view
- [ ] Pre-create rolling dirs cho mỗi mart model TRƯỚC lần run đầu tiên.
      `scripts/ensure_dbt_directories.py` hoặc inline trong `@dbt_assets` (serving-layer.md §6)

---

## Mental Model & Patterns

### Rolling Self-Refresh Views (serving-layer.md §2)

```
rolling/dim_customers/
  dim_customers_20260407120000.parquet   ← older
  dim_customers_20260407130000.parquet   ← latest

VIEW dim_customers AS
  SELECT * FROM read_parquet('rolling/dim_customers/dim_customers_*.parquet')
  WHERE filename = max(filename)  -- self-refresh: picks latest without CREATE OR REPLACE
```

Cơ chế: filename timestamp suffix → lexical sort = chronological sort → `max(filename)` = latest.
**View KHÔNG cần rebuild** sau mỗi dbt run — chỉ cần GC old parquets.

Deep-dive: `../references/serving-layer.md` — "2. Rolling Self-Refresh View Pattern"

### Garbage Collection (serving-layer.md §3)

`generate_serving_db.py` scan rolling/ và delete files cũ hơn N versions.
GC chạy atomically sau view creation — cũ files vẫn valid trong flight queries.

### DuckDB Lock Behavior — Read-Only Mode (L18)

`olap.duckdb` opened bởi Metabase với `read_only=True` → KHÔNG acquire exclusive lock.
Multiple readers OK. Write lock chỉ cần khi `bootstrap_serving_views.py` / `generate_serving_db.py`
chạy → phải stop Metabase trước write ops.

**Implication:** Serving layer KHÔNG contend với dbt write trên `sapo_warehouse.duckdb`.
Dual file architecture eliminates the lock conflict.

### Zero-Downtime Swap

Rolling pattern inherently zero-downtime: cũ parquet vẫn readable trong flight queries khi
mới parquet được thêm vào folder. Metabase reads cũ version của view cho đến khi view regen.

---

## Templates

| Template | Khi nào dùng |
|----------|-------------|
| `../templates/serve/dagster-serving-asset-template.py` | Dagster asset wrap `generate_serving_db.py`. Must declare `deps=[dbt_assets]`. |

---

## Supporting Scripts

Scripts relevant to SERVE group — từ `../references/supporting-scripts.md`:

| Script | Khi nào dùng |
|--------|-------------|
| `scripts/provisioning/generate_serving_db.py` | Normal flow: rolling Parquet → Rolling Self-Refresh Views + GC |
| `scripts/provisioning/bootstrap_serving_views.py` | Safer alternative khi mount path đổi — explicit view rebuild (dùng với Metabase down) |
| `scripts/provisioning/metabase_provisioner.py` | Metabase admin provisioning (questions, dashboards) |
| `scripts/provisioning/refresh_rolling.py` | Roll forward Parquet exports thủ công |
| `scripts/debug_duckdb.py` | Query debug on serving DB — inspect views, schema, row counts |

**Decision logic:** Xem `../references/supporting-scripts.md` section "Khi Nào Gọi Script Nào"
để biết tình huống nào gọi script nào.

**Normal dbt run flow:** `generate_serving_db.py` (automatic trong Dagster serving asset)
**After mount path change:** `bootstrap_serving_views.py` (manual, with Metabase stopped)

---

## Mart-Add Checklist (Cross-ref)

Khi thêm mart model mới, PHẢI satisfy cả 3 sources:

1. **MODEL playbook** pre-flight checklist (`../playbooks/02-model.md`)
2. **serving-layer.md checklist** — `../references/serving-layer.md` "Checklist khi thêm mart model mới":
   - [ ] `location="{{ get_rolling_location() }}"` in dbt config
   - [ ] `ensure_dbt_directories.py` → tạo rolling dir
   - [ ] `dbt run --select {model}` → verify parquet written
   - [ ] `generate_serving_db.py` → verify view created
   - [ ] Test view via `duckdb olap.duckdb -c "SELECT * FROM {model} LIMIT 5"`
   - [ ] Re-run dbt → verify GC, view still returns fresh data
3. **checklist.md Phase 3.5** (`../checklist.md`)

---

## Debug Recipes

### serving-layer.md "Debug Commands" section

```bash
# Liệt kê tất cả views trong serving DB
duckdb data_lake/serving/olap.duckdb -c "SELECT name FROM sqlite_master WHERE type='view'"

# Xem view definition
python transformation/check_view.py

# Count rows
duckdb data_lake/serving/olap.duckdb -c "SELECT COUNT(*) FROM dim_customers"

# Kiểm tra latest file trong rolling folder
ls -lt data_lake/export/marts/rolling/dim_customers/ | head -5

# Force rerun serving script
python scripts/provisioning/generate_serving_db.py
```

### troubleshooting.md — Serving Layer section

Xem `../references/troubleshooting.md` "Serving Layer" section:
- View không có data → check rolling dir có file không
- View definition sai path → mount change → chạy `bootstrap_serving_views.py`
- Metabase không thấy table → view chưa regen hoặc Metabase cache

### troubleshooting.md — Metabase section

Xem `../references/troubleshooting.md` "Metabase — Dashboard Deploy" section:
- Metabase field ID mismatch sau view regen
- Blueprint deploy fails

---

## Lessons Cross-Reference

| ID | Title | File |
|----|-------|------|
| L18 | DuckDB read_only mode KHÔNG acquire file lock | `../references/lessons-learned.md#L18` |
| dbt-Lesson-5 | Rolling Location cho Marts (CRITICAL) | `../references/dbt-patterns.md` |

**Full SERVE knowledge base:** `../references/serving-layer.md` (all sections)
- §1 Rolling Snapshots từ dbt
- §2 Rolling Self-Refresh View Pattern
- §3 Garbage Collection
- §4 DuckDB Lock Behavior
- §5 Empty Folder → Drop View
- §6 Pre-Create Rolling Directories
- §7 Dagster Integration
- Checklist khi thêm mart model mới
- Debug Commands

---

## When This Group Interacts with Others

| Upstream/Downstream | Interaction |
|---------------------|-------------|
| MODEL → SERVE | Rolling Parquet từ `dim_/fact_` là input. SERVE chỉ READ Parquet, không modify. |
| SERVE → (Metabase) | `olap.duckdb` views là interface duy nhất. Metabase queries views. |
| SERVE + OPS | Dagster serving asset orchestrated by OPS schedules. `deps=[dbt_assets]` enforced. |
| SERVE + MODEL | `get_rolling_location()` macro shared — Lesson 5 dbt-patterns canonical pattern. |

---

## Related Cross-cutting Concerns

| Concern | Canonical file |
|---------|---------------|
| DuckDB read vs write semantics | `../playbooks/cross-cutting.md#duckdb-locking` |
| Docker mount paths → view paths bake absolute | `../playbooks/cross-cutting.md#docker-mount-paths` |
| dbt target cache after mount change | `../playbooks/cross-cutting.md#dbt-target-cache-after-mount-change` |

**Key rule from cross-cutting:** Serving views SQL embeds absolute paths like:
```sql
CREATE VIEW dim_customers AS
  SELECT * FROM '/app/var/data_lake/export/marts/rolling/dim_customers/*.parquet'
  WHERE filename = (SELECT max(filename) FROM ...)
```
If `/app/var/data_lake` changes → ALL views broken → run Runbook A.
