# Research: Áp dụng nu-data-pipeline serving-layer-design vào data-integration

**Date:** 2026-05-08 23:05+07
**Source design:** `D:\Vantt\app\nu-data-pipeline\docs\serving-layer-design.md`
**Target system:** `D:\Vantt\app\data-integration` (Sapo data lakehouse)
**Verdict:** Phần lớn cơ chế **đã tồn tại** (và xịn hơn). Chỉ **1 cơ chế mới** (Standalone Export DuckDB) là thực sự đáng áp dụng.

---

## 1. So sánh từng cơ chế

| Cơ chế | nu-pipeline (đề xuất) | data-integration (hiện tại) | Trạng thái |
|---|---|---|---|
| Dual DuckDB (warehouse vs serving) | Có | `sapo_warehouse.duckdb` (write) + `serving/olap.duckdb` (view-only) | ✅ Đã có |
| Rolling Self-Refresh parquet | Đề xuất full | `transformation/macros/get_rolling_location.sql` + `refresh_rolling.py` | ✅ Đã có |
| `serving.duckdb` chỉ chứa VIEW | Mục tiêu refactor | `olap.duckdb` đã 100% là view (24/24 marts dùng `get_rolling_location()`) | ✅ Đã có (xịn hơn) |
| Atomic write parquet | `.tmp` → rename | dbt-duckdb COPY trực tiếp; an toàn vì giữ N-1 version + GC sau | ⚠️ Khác cách làm, vẫn ổn |
| GC giữ N versions | Giữ **3** | Giữ **1** (latest only) | ⚠️ Aggressive hơn |
| Hybrid base-table + view (legacy) | Đang phải refactor xóa | Không có hybrid — đã thuần view | ✅ Vượt mức đề xuất |
| Schema drift handling | Không nêu | `.known_tables.json` marker + Dagster fail → Lark alert | ✅ Vượt mức đề xuất |
| Metabase coexistence | Không phân tích lock | Đã verify empirically: `read_only=true` không hold lock; `bootstrap_serving_views.py` chạy được khi Metabase up (13.3 ms RW connect) | ✅ Vượt mức đề xuất |
| **Standalone export `.duckdb`** | **Đề xuất** | **Chưa có** | ❌ Áp dụng được |
| HTTP serve standalone file | Caddy + basic auth | Chưa có | ❓ Tùy nhu cầu |

### Kết luận so sánh
**Design của nu-pipeline mô tả end-state mà ta đã đạt từ 2026-04 (xem `plans/archive/260408-1611-fix-serving-db-hang-metabase-lock/`).** Việc "refactor" họ đang plan, ta đã làm xong. Ngoài Standalone Export, không có gì thực sự mới để áp dụng từ document này.

---

## 2. Cơ chế DUY NHẤT đáng áp dụng — Standalone Export DuckDB

### Vấn đề
- `olap.duckdb` chỉ là **catalog view** → query views cần đọc parquet files tại `data_lake/export/marts/rolling/<table>/*.parquet`.
- Path này chỉ tồn tại trong container hoặc trên máy có đầy đủ data lake.
- **Người dùng ngoài** (analyst chạy DBeaver/Python notebook trên laptop, chia sẻ snapshot, backup) **không dùng được** `olap.duckdb` standalone.

### Use cases cụ thể (cần xác nhận với user — xem unresolved)
1. **Offline analysis**: Phân tích viên cầm 1 file `.duckdb` về máy, không cần VPN/path mount.
2. **Snapshot/backup**: Lưu trữ định kỳ state của serving layer.
3. **External integration**: Tool ngoài (Claude Code, MotherDuck, Evidence.dev) attach vào.
4. **Air-gapped distribution**: Gửi qua email/cloud share không cần pipeline access.

### Thiết kế đề xuất

```
Inputs (read-only, no lock):
  - serving/olap.duckdb              (view definitions)
  - export/marts/rolling/*/*.parquet (data)

Output:
  - serving/standalone/sapo_export_<YYYYMMDDHHMMSS>.duckdb
  - serving/standalone/sapo_export_latest.duckdb (symlink/copy)
```

### Cơ chế

```python
# scripts/provisioning/build_standalone_export.py
import duckdb, os, glob

src_view_db   = "/app/var/data_lake/serving/olap.duckdb"
out_dir       = "/app/var/data_lake/serving/standalone"
ts            = datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")).strftime("%Y%m%d%H%M%S")
out_tmp       = f"{out_dir}/sapo_export_{ts}.duckdb.tmp"
out_final     = f"{out_dir}/sapo_export_{ts}.duckdb"

con = duckdb.connect(out_tmp)
con.sql("SET TimeZone='Asia/Ho_Chi_Minh'")
con.sql(f"ATTACH '{src_view_db}' AS src (READ_ONLY)")

# List all views in source
views = con.sql(
    "SELECT table_name FROM src.information_schema.tables "
    "WHERE table_schema='main' AND table_type='VIEW'"
).fetchall()

for (vname,) in views:
    con.sql(f"CREATE TABLE {vname} AS SELECT * FROM src.{vname}")

con.sql("DETACH src")
con.close()
os.replace(out_tmp, out_final)

# GC: keep last N standalone files
gc_old_exports(out_dir, keep=3)

# Optional: refresh "latest" alias
shutil.copy2(out_final, f"{out_dir}/sapo_export_latest.duckdb.tmp")
os.replace(f"{out_dir}/sapo_export_latest.duckdb.tmp",
           f"{out_dir}/sapo_export_latest.duckdb")
```

### Lock analysis (tại sao an toàn)
- **Đọc parquet**: không lock (DuckDB chỉ mmap khi query).
- **Đọc `olap.duckdb`** với `(READ_ONLY)`: không hold lock (đã verify L18 trong audit 2026-04-08).
- **Ghi `sapo_export_*.duckdb.tmp`**: file mới, độc quyền của script.
- **`os.replace`**: atomic trên cả Linux và Windows.
- **Không bao giờ cần `unlink()` file đang được đọc** → không lock conflict với consumer.

### Tích hợp Dagster
Thêm asset `sapo_standalone_export` downstream của `sapo_serving_db`:

```python
# orchestration/assets/serving.py (thêm sau sapo_serving_db)
@asset(
    deps=[sapo_serving_db],
    group_name="serving_layer",
    description="Materialize all serving views into a portable standalone DuckDB file."
)
def sapo_standalone_export(context):
    # Popen + stream + timeout pattern (theo L17, không phải capture_output=True)
    ...
```

**Schedule cân nhắc:**
- Sau mỗi nightly: snapshot daily.
- Hoặc on-demand asset: Dagster UI launch khi cần.
- KHÔNG nên chạy mỗi run realtime/incremental — full materialize tốn CPU/IO.

### Trade-offs

| | Nhận xét |
|---|---|
| ✅ Self-contained file | Mang đi đâu cũng query được, không cần parquet path |
| ✅ Lock-safe | Mọi input đều read-only, output là file mới |
| ✅ Idempotent | Mỗi lần chạy tạo file timestamped mới |
| ✅ Tận dụng cơ chế hiện có | Đọc thẳng từ views, không cần thêm SQL logic |
| ⚠️ Storage cost | Mỗi snapshot ~ tổng size mart (hiện ~ vài trăm MB → vài GB). Cần GC hợp lý. |
| ⚠️ Time to build | O(rows) — full SELECT + INSERT cho mỗi view. Với fact_orders/fact_sales lớn có thể 1-5 phút. |
| ⚠️ Snapshot vs live | Không refresh tự động — user phải biết file timestamp. Khác hẳn `olap.duckdb` view (luôn live). |

---

## 3. Đề xuất phụ — Tăng GC retention rolling parquet (P3, optional)

### Hiện trạng
`refresh_rolling.py` giữ **1 version** (latest) và xóa hết phần còn lại. Audit 2026-04-09 confirm `tables=24 deleted=17 skipped=0` — không có vấn đề thực tế.

### Lý do cân nhắc nâng lên 2-3
1. **Resilience**: nếu `dbt build` crash giữa lúc COPY parquet, file đang ghi có thể không hoàn chỉnh. Hiện tại dbt-duckdb COPY trực tiếp vào path đích (không qua `.tmp`). Crash giữa chừng = file dở dang. Nếu chỉ giữ 1 → query view sẽ thấy file dở dang.
2. **Safety net cho schema migration**: đôi khi muốn rollback tức thì → chỉ cần xóa file mới, view tự lấy file cũ.

### Đánh giá thực tế
- Storage tăng 2-3x trên rolling/. Hiện tổng rolling/ size khá nhỏ (~vài trăm MB), nâng lên 3x vẫn dưới 2 GB → **chấp nhận được**.
- Empirical: 10 runs gần nhất không thấy dbt crash giữa COPY → vấn đề lý thuyết, không thực tế.
- **Ưu tiên thấp**, chỉ làm nếu thực sự cần safety net.

### Implementation
Thêm `ROLLING_KEEP_VERSIONS` env var (default `1` để backward compat, set `3` để follow nu-pipeline):

```python
# refresh_rolling.py
KEEP = int(os.environ.get("ROLLING_KEEP_VERSIONS", "1"))

def garbage_collect(folder_path: str, keep_n: int) -> tuple[int,int]:
    files = sorted(glob.glob(...))
    to_keep = set(files[-keep_n:])
    # delete files not in to_keep
```

---

## 4. KHÔNG nên áp dụng

### `.tmp` + rename pattern cho rolling export
nu-pipeline đề xuất dbt write to `.parquet.tmp` rồi rename. Lý do **không cần**:
- dbt-duckdb không support natively (cần macro override hoặc post-hook).
- Hiện tại GC chỉ giữ 1 version, không có file cũ làm fallback nếu đang ghi file mới — nhưng nếu nâng KEEP_VERSIONS=2-3 (đề xuất §3) thì vấn đề tự giải quyết: file mới chưa xong sẽ là "lexically max" và view vẫn đọc nó (có thể fail), HOẶC ta đổi view definition lấy max(filename) **trừ** filename đang được hold.
- Phức tạp hóa codebase với rủi ro thấp.

### `Caddy + basic auth` HTTP serve
nu-pipeline expose file qua HTTP. data-integration **chưa có nhu cầu** này (nội bộ team, dùng Metabase). **Bỏ qua** trừ khi user có yêu cầu cụ thể.

### Refactor `bootstrap_serving_views.py` / `refresh_rolling.py`
Hai script đã clean, well-documented, có schema drift detection. **Không sửa.**

---

## 5. Kế hoạch áp dụng đề xuất (nếu approve)

### Phase 1 — Standalone export (P1, ~2 giờ)
- [ ] Tạo `scripts/provisioning/build_standalone_export.py`
- [ ] Tạo Dagster asset `sapo_standalone_export` (downstream của `sapo_serving_db`)
- [ ] GC keep last 3 exports trong `serving/standalone/`
- [ ] Cập nhật `docker-compose.yml` mount nếu cần expose ra host
- [ ] Test: query bằng DuckDB CLI ngoài container, verify schema khớp

### Phase 2 — GC retention bump (P3, ~30 phút, optional)
- [ ] Refactor `garbage_collect()` lấy param `keep_n`
- [ ] Add env var `ROLLING_KEEP_VERSIONS` (default 1)
- [ ] Cân nhắc bật default = 2 cho an toàn

### Phase 3 — Docs (P2)
- [ ] Update `docs/architecture/data-flow.md` mô tả standalone export branch
- [ ] Lesson learned trong `.skills/data-pipeline/playbooks/03-serve.md`

---

## 6. Unresolved questions (cần user xác nhận)

1. **Use case Standalone Export là gì cụ thể?** Phân tích offline trên laptop? Backup? External tool? Distribution? — Quyết định schedule (nightly vs on-demand) và scope (toàn bộ marts vs allowlist tables).
2. **Có cần expose qua HTTP không?** Nếu có → cần Caddy/nginx + auth, ngược lại chỉ cần file path mount.
3. **Filename convention?** `sapo_export_<timestamp>.duckdb` + `_latest.duckdb` symlink/copy, OR fixed name `sapo_serving.duckdb` overwrite mỗi lần (nhưng overwrite không atomic-safe nếu có ai đang đọc)?
4. **Có muốn nâng `ROLLING_KEEP_VERSIONS=2-3` không?** Storage cost thấp, safety net cao hơn — nhưng hiện tại không có incident nào cần.
5. **Standalone có nên include marts intermediate (`int_*`) không?** Hay chỉ public `dim_*`/`fact_*`/`mart_*`?
