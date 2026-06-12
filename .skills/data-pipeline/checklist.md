# Checklist: Thêm Data Source Mới (Pattern A, End-to-End)

> Mỗi phase mapped vào 1 functional group. Đọc playbook tương ứng (`playbooks/0X-{group}.md`) song song với checklist này.

Thay thế trước khi dùng:  
`{source}`, `{entity}`, `{cursor_field}`, `{biz_key}`, `{response_key}`, `{entity_upper}`

---

## Phase 1 — dlt Config  [INGEST]

- [ ] Thêm section `[sources.{source}]` vào `ingestion/.dlt/config.toml`:
  ```toml
  [sources.{source}]
  domain = "api.example.com"
  request_delay = 1.0
  base_url = "https://api.example.com/v1"
  ```

- [ ] Thêm credentials template vào `ingestion/.dlt/secrets.toml.sample`:
  ```toml
  [sources.{source}]
  api_token = "your_token_here"
  ```

- [ ] Thêm env vars vào `.env.example` (format `SOURCES__{SOURCE}__{KEY}`):
  ```bash
  SOURCES__{SOURCE}__API_TOKEN=your_token
  ```

- [ ] Copy `secrets.toml.sample` → `secrets.toml` (gitignored), điền credentials thật

---

## Phase 2 — dlt Source Code  [INGEST]

- [ ] Tạo `ingestion/src/{source}/__init__.py` (rỗng)
- [ ] Tạo `ingestion/src/{source}/{entity}.py` từ `templates/source-template.py`
- [ ] Implement auth (session hoặc token)
- [ ] Tạo `ingestion/run_{entity}_batch.py` từ `templates/run-entry-point-template.py`
- [ ] Test thủ công:
  ```bash
  cd ingestion
  python run_{entity}_batch.py --limit 1
  ls data_lake/{entity}/ingest_method=batch_sync/year=*/month=*/
  ```

---

## Phase 3 — dbt Transformation  [MODEL]

### 3.1 Source Registration

- [ ] Thêm table vào `transformation/models/sources.yml`:
  ```yaml
  - name: {source}_raw
    schema: main
    meta:
      external_location: "read_parquet(
        '{{ env_var('DBT_DATA_LAKE_PATH') }}/{source}_raw/{name}/ingest_method=*/**/*.parquet',
        hive_partitioning=1,
        union_by_name=true
      )"
    tables:
      - name: {entity}
  ```

### 3.2 src_ Model (Incremental + Dedup)

- [ ] Tạo `transformation/models/staging/src_{source}_{entity}.sql` từ `templates/src-model-template.sql`
- [ ] Extract tất cả scalar JSON fields cần thiết
- [ ] Giữ nested arrays as `{field}_json` text nếu downstream cần unnest
- [ ] Test:
  ```bash
  cd transformation
  dbt run --select src_{source}_{entity}
  ```

### 3.3 stg_ Model (Enrichment, View) — Optional

Tạo nếu cần enrichment joins (ref tables, cross-entity):
- [ ] Tạo `transformation/models/staging/stg_{source}_{entity}.sql` (view)
- [ ] Chỉ đọc từ `src_{source}_{entity}` (không đọc lại source)
- [ ] LEFT JOIN ref seeds nếu cần

### 3.4 std_ Model (Golden Layer) — Optional

Tạo nếu consolidate multiple sources:
- [ ] Tạo `transformation/models/staging/standard/std_{entity}.sql`
- [ ] Normalize field names, status values, cast types

### 3.5 Mart Models (dim_/fact_)

- [ ] Tạo `transformation/models/marts/{domain}/dim_{entity}.sql` từ `templates/dim-model-template.sql`
- [ ] **CRITICAL:** Phải có `location="{{ get_rolling_location() }}"` trong config
- [ ] Thêm Unknown row UNION ALL
- [ ] Dùng `dbt_utils.generate_surrogate_key` cho PK
- [ ] Tạo `transformation/models/marts/{domain}/fact_{process}.sql` từ `templates/fact-model-template.sql` nếu cần
- [ ] Pre-create rolling dirs:
  ```bash
  python scripts/ensure_dbt_directories.py
  ```

### 3.6 Tests

- [ ] Thêm tests vào `transformation/models/staging/schema.yml` và `marts/schema.yml` từ `templates/schema-yml-template.yml`:
  - `unique` + `not_null` trên primary key
  - `relationships` cho foreign keys trong facts
  - `accepted_values` cho status fields
- [ ] Chạy tests:
  ```bash
  dbt test --select {model_name}
  ```

---

## Phase 4 — Serving Layer  [SERVE]

- [ ] Chạy `dbt run --select +dim_{entity}` → verify parquet ở `rolling/dim_{entity}/`
- [ ] Chạy `python scripts/provisioning/generate_serving_db.py`
- [ ] Verify view được tạo:
  ```bash
  duckdb data_lake/serving/olap.duckdb -c \
    "SELECT COUNT(*) FROM dim_{entity}"
  ```
- [ ] **Nếu script báo "Empty folder"** → mart model thiếu `location=get_rolling_location()`

---

## Phase 5 — Dagster Orchestration  [OPS + INGEST asset wiring]

- [ ] Tạo/update `orchestration/assets/{source}_assets.py` từ `templates/dagster-asset-template.py`
- [ ] Import `run_{entity}_batch` ở đầu file
- [ ] Đăng ký asset trong `orchestration/definitions.py`:
  - Thêm vào `load_assets_from_modules([..., {source}_assets])`
  - Chọn job phù hợp:
    - `pipeline_batch_nightly_job` → batch sync (chạy 04:00 AM)
    - `ingest_sapo_incremental_job` → history log, event polling (mỗi 10 phút)
    - `ingest_sapo_realtime_job` → webhook consumer (mỗi 3 phút)
- [ ] Nếu asset write DuckDB: thêm `op_tags={"dagster/concurrency_key": "duckdb_lock"}`
- [ ] Verify asset DAG: `{source}_ingestion_asset → dbt_assets → serving_db_asset`

---

## Phase 6 — Verify End-to-End  [TRUST]

- [ ] Chạy ingestion asset:
  ```bash
  dagster asset materialize --select {source}/{entity}_batch_asset
  ```
- [ ] Chạy dbt assets (nếu không tự trigger):
  ```bash
  dagster asset materialize --select sapo_dbt_assets
  ```
- [ ] Chạy serving asset:
  ```bash
  dagster asset materialize --select build_serving_db
  ```
- [ ] Query Metabase (hoặc direct DuckDB):
  ```sql
  SELECT * FROM dim_{entity} LIMIT 10;
  ```
- [ ] Chạy lại asset ingestion lần 2 → verify incremental chỉ load data mới
- [ ] Chạy lại dbt → verify rolling/ chỉ giữ parquet mới nhất (GC hoạt động)

---

## Rollback Plan

Nếu pipeline fail và cần rollback:

1. **dlt state corrupt:**
   ```bash
   python scripts/clean_dlt_state.py
   # hoặc
   python run_{entity}_batch.py --full-refresh
   ```

2. **dbt incremental bị stuck:**
   ```bash
   dbt run --full-refresh --select src_{source}_{entity}
   ```

3. **Serving view bị drop:**
   - Fix mart model `location` config
   - Chạy `dbt run --select dim_{entity}`
   - Chạy `python scripts/provisioning/generate_serving_db.py`

4. **Xóa source hoàn toàn:**
   - Xóa `ingestion/src/{source}/`, `run_{entity}_batch.py`
   - Xóa dbt models `src_{source}_*`, `stg_{source}_*`
   - Xóa Dagster asset từ `{source}_assets.py` và `definitions.py`
   - Xóa section trong `config.toml`, `secrets.toml.sample`
   - Xóa parquet: `rm -rf data_lake/{source}_raw/`
