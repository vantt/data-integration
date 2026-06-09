# Phase 03 — Rolling KEEP=3 (Configurable Retention)

## Context Links

- Plan: [plan.md](plan.md)
- Existing: `scripts/provisioning/refresh_rolling.py:46-71` (current GC keeps latest only)
- Audit: `docs/architecture/locking-and-concurrency.md` §"Defensive Dead Code" (verifies GC works empirically)

## Overview

- **Priority:** P3 (independent improvement, can ship with or without Phase 1-2)
- **Status:** Pending
- **Description:** Promote `garbage_collect()` từ keep-1 sang keep-N với env var `ROLLING_KEEP_VERSIONS` (default 3). Trade-off: +2x storage trên rolling/ folder để có rollback + audit trail.

## Key Insights

- Current GC strategy aggressive (keep 1) — không có safety net cho rollback hoặc filesystem hiccup.
- Increasing KEEP **không** giải quyết mid-COPY crash (cần `.tmp+rename` riêng — out of scope).
- Lợi ích thật: rollback nhanh (delete file mới → view tự đọc file cũ thông qua `max(filename)`), audit trail (so sánh snapshots).
- View definition trong `bootstrap_serving_views.py:64-76` đã chọn `max(filename)` → tự nhiên dùng file mới nhất, file cũ chỉ là fallback khi delete file mới.
- Storage: hiện ~vài trăm MB/snapshot × 3 = ~vài GB. Không vấn đề với data volume hiện tại.

## Requirements

### Functional
- Env `ROLLING_KEEP_VERSIONS` (default `3`) điều khiển số version giữ lại.
- Backward compatible: nếu env = `1`, behavior y hệt hiện tại.
- GC chỉ xóa khi có > N file `.parquet` (sort lexically, keep last N).

### Non-functional
- Không thêm dependency.
- Không thay đổi schema drift detection logic.
- Per-table summary log giữ format hiện tại.

## Architecture

```
Trước:
  rolling/<table>/
    └── <table>_<oldTS>.parquet     ← keep
    + tất cả file cũ                 ← deleted

Sau (KEEP=3):
  rolling/<table>/
    ├── <table>_<TS-2>.parquet       ← keep (audit / rollback)
    ├── <table>_<TS-1>.parquet       ← keep
    └── <table>_<TS-0>.parquet       ← keep (latest, view picks this via max(filename))
    + file cũ hơn                    ← deleted
```

View không thay đổi — vẫn `max(filename)` chọn file mới nhất.

## Related Code Files

**MODIFY:**
- `scripts/provisioning/refresh_rolling.py` — refactor `garbage_collect()` accept `keep_n`, read env var
- `.env.docker.example` (nếu có) — document `ROLLING_KEEP_VERSIONS=3`

**READ for context:**
- `scripts/provisioning/bootstrap_serving_views.py:64-76` — verify view picks max(filename) (no change needed)

## Implementation Steps

1. **Refactor `garbage_collect()` signature:**
   ```python
   def garbage_collect(folder_path: str, keep_n: int) -> tuple[int, int]:
       files = sorted(glob.glob(os.path.join(folder_path, "*.parquet")))
       if len(files) <= keep_n:
           return 0, 0
       to_delete = files[:-keep_n]  # keep last N (lexically max = newest timestamps)
       deleted = 0
       skipped = 0
       for f in to_delete:
           try:
               os.remove(f)
               deleted += 1
           except PermissionError:
               skipped += 1
           except OSError:
               time.sleep(0.5)
               try:
                   os.remove(f); deleted += 1
               except Exception:
                   skipped += 1
           except Exception as e:
               print(f"  [!] ERROR deleting {os.path.basename(f)}: {e}")
               skipped += 1
       return deleted, skipped
   ```

2. **Read env var at module top:**
   ```python
   ROLLING_KEEP_VERSIONS = max(1, int(os.environ.get("ROLLING_KEEP_VERSIONS", "3")))
   ```
   `max(1, ...)` guards against accidental `0` setting that would wipe everything.

3. **Update call site `refresh_rolling()`:**
   - Replace `garbage_collect(table_dir, latest)` với `garbage_collect(table_dir, ROLLING_KEEP_VERSIONS)`.
   - Update per-table log line: `print(f"  {table_name}: kept={min(N, count)} gc(deleted={deleted}, skipped={skipped})")`.

4. **Remove `latest` arg dependency:**
   - Top-level loop no longer needs `get_latest_file()` for GC purposes; nhưng `get_latest_file()` vẫn dùng để log (nếu có) — giữ hoặc xóa tùy clean.

5. **Default in `.env.docker`:**
   ```
   ROLLING_KEEP_VERSIONS=3
   ```

6. **Compile + run inside container:**
   ```bash
   docker compose exec data_platform python scripts/provisioning/refresh_rolling.py
   ```
   - Verify log shows `kept=3` per table after pipeline đã chạy ≥ 3 lần.

7. **Storage check:**
   ```bash
   docker compose exec data_platform du -sh /app/var/data_lake/export/marts/rolling/
   ```
   So sánh trước/sau. Expect ~3x.

## Todo List

- [ ] Refactor `garbage_collect()` signature
- [ ] Add `ROLLING_KEEP_VERSIONS` env handling with min=1 guard
- [ ] Update call site
- [ ] Update log format
- [ ] Add to `.env.docker` (or env example doc)
- [ ] Manual run, verify behavior
- [ ] Storage delta acceptable

## Success Criteria

- Sau 3+ pipeline runs, `ls rolling/<table>/` thấy đúng 3 files.
- Log line: `<table>: kept=3 gc(deleted=N skipped=0)`.
- Setting `ROLLING_KEEP_VERSIONS=1` → behavior y hệt trước (regression check).
- Metabase view query vẫn dùng file mới nhất (max(filename)), không lỗi.
- Storage `rolling/` folder ≤ 3x baseline.

## Risk Assessment

| Risk | Mitigation |
|---|---|
| KEEP=0 wipe all | `max(1, int(...))` guard ở module load |
| View accidentally đọc file cũ | View dùng `max(filename)` → luôn file mới nhất |
| Storage runaway nếu KEEP set quá cao | Document `3` là default; ops phải chỉnh env tay |
| Breaking change cho test downstream | Tests đọc `*.parquet` filtered by max → unaffected |

## Security Considerations

- File parquet có sensitive business data — không thay đổi exposure surface (vẫn trong container `data_lake/export/`).
- Không thêm endpoint mới.

## Next Steps

- Phase 4: Document KEEP=3 reasoning trong `data-flow.md` + `.skills/data-pipeline/playbooks/03-serve.md`.
- Future (out of scope): consider `.tmp+rename` atomic write nếu xảy ra mid-COPY crash incident.
