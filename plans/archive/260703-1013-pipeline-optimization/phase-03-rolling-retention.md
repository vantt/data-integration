# Phase 3: Rolling Parquet Retention
**Effort:** 1-2 ngày | **Risk:** Trung bình (xóa file — cần test kỹ trước khi enable)

## Context

Mỗi dbt run tạo file mới theo pattern `{model}_{YYYYMMDDHHMMSS}.parquet` trong `rolling/`. Không có cơ chế cleanup → file tích lũy vô hạn. DuckDB đọc `rolling/{model}/*.parquet` (glob) → scan tất cả files kể cả cũ.

Dagster asset `build_serving_db` (hoặc `refresh_rolling`) là điểm phù hợp để thêm cleanup.

---

## 3.1 Tìm Script Hiện Tại

Trước khi implement, xác định entry point:

```bash
grep -r "rolling" orchestration/assets/ --include="*.py" -l
grep -r "refresh_rolling\|build_serving" orchestration/ --include="*.py" -l
```

---

## 3.2 Retention Logic

Giữ **N file gần nhất** (theo mtime) cho mỗi model. Mặc định N=7 — đủ để rollback 7 dbt runs nếu có lỗi.

```python
# ingestion hoặc orchestration — thêm vào sau dbt run thành công
import os
import glob
from pathlib import Path

ROLLING_RETENTION_COUNT = int(os.getenv("ROLLING_RETENTION_COUNT", "7"))

def cleanup_rolling_files(rolling_dir: str, retention_count: int = ROLLING_RETENTION_COUNT) -> None:
    """Keep only the N most-recent parquet files per model directory."""
    rolling_path = Path(rolling_dir)
    if not rolling_path.exists():
        return

    for model_dir in rolling_path.iterdir():
        if not model_dir.is_dir():
            continue

        # Chỉ xét flat parquet files (chưa partitioned); skip hive subdirs
        parquets = sorted(
            [f for f in model_dir.glob("*.parquet") if f.is_file()],
            key=lambda f: f.stat().st_mtime,
            reverse=True  # newest first
        )

        to_delete = parquets[retention_count:]
        for old_file in to_delete:
            old_file.unlink()
            print(f"[retention] Deleted old rolling file: {old_file.name}")
```

**Quan trọng:** Gọi `cleanup_rolling_files()` **sau** khi verify dbt run thành công — không cleanup nếu run failed.

---

## 3.3 Điểm Tích Hợp

Tìm Dagster asset `build_serving_db` hoặc tương đương:

```python
# orchestration/assets/serving_assets.py (tên file có thể khác)
@asset(...)
def build_serving_db(context, dbt_run_result):
    # ... existing logic ...
    
    # Thêm sau khi dbt run thành công:
    if dbt_run_result.success:
        cleanup_rolling_files(
            rolling_dir=os.getenv("ROLLING_DIR", "data_lake/rolling"),
            retention_count=int(os.getenv("ROLLING_RETENTION_COUNT", "7"))
        )
```

Nếu cleanup logic đủ lớn (>30 lines), tách ra `orchestration/utils/rolling_cleanup.py`.

---

## 3.4 Môi Trường và Env Vars

Thêm vào `.env`:
```bash
# Rolling parquet retention: số file giữ lại mỗi model (default 7)
ROLLING_RETENTION_COUNT=7
```

---

## 3.5 Rollback Safety

- Retention cleanup chỉ xóa file cũ hơn N-th newest — version mới nhất luôn an toàn
- Nếu cần khôi phục: dbt run lại sẽ regenerate file (data vẫn có trong raw/intermediate)
- Không thêm cleanup vào `--full-refresh` runs để tránh xóa backup trong khi rebuild

---

## Validation

```bash
# 1. Chạy cleanup dry-run (in ra files sẽ bị xóa, không xóa thật)
# Thêm dry_run=True param vào function, chỉ print không unlink

# 2. Sau cleanup, verify DuckDB vẫn đọc được
docker compose exec data_platform duckdb data_lake/serving/olap.duckdb -c "
SELECT COUNT(*) FROM read_parquet('rolling/fact_orders/*.parquet');
"

# 3. Đếm files trong rolling dir trước và sau
find data_lake/rolling -name "*.parquet" | wc -l
```
