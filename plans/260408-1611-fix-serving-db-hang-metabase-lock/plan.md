---
type: fix-plan
date: 2026-04-08
status: proposal
scope: orchestration/assets/serving.py, scripts/provisioning/generate_serving_db.py, docker-compose
related:
  - plans/reports/design-260408-1531-dagster-stability-flexibility.md
  - orchestration/assets/serving.py
  - scripts/provisioning/generate_serving_db.py
trigger: Job 2c6d50cf stuck 16h tại sapo_serving_db
---

# Fix Plan — Serving DB Hang + Metabase Lock Contention

## TL;DR

> **POST-MORTEM UPDATE (2026-04-08, after Day 4):** Original hypothesis about
> Metabase JDBC lock was **WRONG**. Verification showed DuckDB read_only mode
> does NOT acquire file locks, and RW connections succeed in 15ms while Metabase
> is running. The ONLY root cause of the 16h hang is subprocess pipe deadlock
> (Phase 1.2). Pattern C (Phase 2) was kept for design cleanliness and
> schema-drift detection, not lock avoidance. See "Post-mortem" section below.

Job stuck **thực tế chỉ có 1 nguyên nhân**:

1. **Subprocess pipe deadlock** (root cause hang) — `capture_output=True` + không timeout + script in nhiều log → OS pipe đầy → child block → parent block forever.

Các vấn đề khác phát hiện trong quá trình điều tra:
2. ~~Metabase JDBC giữ exclusive lock~~ — **sai**, đã verify không có lock contention.
3. **Warning detector quá lỏng** — flag `[!] Empty folder` (bình thường) thành warning, đồng thời `if "error" in stdout_lower` match cả "0 errors". Noise + false negative.

Fix theo 3 phase, mỗi phase độc lập deploy được. **Phase 1 = stop the bleeding** (ĐÚNG root cause). Phase 2-3 = design cleanup + observability (giá trị độc lập, không liên quan lock).

---

## Hiện trạng (đã verify)

| Quan sát | Vị trí | Kết luận |
|---|---|---|
| `subprocess.run(..., capture_output=True, check=True)` không timeout | `orchestration/assets/serving.py:36-42` | Pipe buffer deadlock khi log dài |
| `duckdb.connect(SERVING_DB_PATH)` mở read-write mặc định | `scripts/provisioning/generate_serving_db.py:78` | Đụng exclusive lock với Metabase |
| Print verbose `[GC] Deleted...` mỗi file × mỗi table | `generate_serving_db.py:42-54` | Tăng pipe pressure |
| Marker `[!]` dùng cho cả info + warning + error | `generate_serving_db.py` toàn bộ | Detector không phân biệt được severity |
| Metabase chạy cùng `docker-compose` | docker-compose.yml | Pool persistent cả ngày, lock cả ngày |

---

## Phase 1 — Stop the Bleeding (P0, 30 phút)

**Mục tiêu:** Job không bao giờ hang nữa. Chấp nhận fail nhanh thay vì hang lâu.

### 1.1 Kill stuck run hiện tại

```bash
# Trong Dagster UI: Runs → 2c6d50cf → Terminate
# Hoặc CLI:
docker compose exec dagster dagster run terminate 2c6d50cf

# Verify python con đã chết
docker compose exec dagster ps aux | grep generate_serving_db
# Nếu còn → kill PID
```

Dọn DuckDB lock file thừa nếu còn:
```bash
# Trong volume data lake
ls -la /data/serving/olap.duckdb*
# Nếu có .wal mồ côi và Metabase cũng đang giữ → restart Metabase trước, rồi xóa .wal
```

### 1.2 Fix subprocess pattern

Sửa `orchestration/assets/serving.py:34-46` → streaming read thay vì buffer:

```python
import subprocess

try:
    proc = subprocess.Popen(
        [PYTHON_EXE, SCRIPT_PATH],
        cwd=PROJECT_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,    # gộp 1 pipe → đỡ deadlock 2 pipe
        text=True,
        bufsize=1,                    # line buffered
    )
    output_lines = []
    for line in proc.stdout:
        line = line.rstrip()
        output_lines.append(line)
        context.log.info(line)        # streaming vào Dagster log
    proc.wait(timeout=1800)           # 30 phút trần
    if proc.returncode != 0:
        raise Exception(f"Serving script exit {proc.returncode}")
except subprocess.TimeoutExpired:
    proc.kill()
    proc.wait()
    raise Exception("Serving script timeout sau 1800s")

result_stdout = "\n".join(output_lines)
```

**Tại sao đây là fix tối thiểu:** Streaming đọc loại bỏ pipe buffer; `timeout` là cứu cánh; gộp `stderr` vào `stdout` tránh phải đọc 2 pipe (cũng nguồn deadlock kinh điển).

### 1.3 Sửa warning detector — bớt noise

Thay block `serving.py:48-61` bằng:

```python
# Severity-based detection — match marker prefix, không match từ rời rạc
import re
WARN_RE = re.compile(r"\[!\]\s+(Failed|WARNING|ERROR)", re.IGNORECASE)
warnings = [line for line in output_lines if WARN_RE.search(line)]

if warnings:
    for w in warnings:
        context.log.warning(f"⚠️ {w}")
    # Không raise — script đã exit 0 thì là warning, không phải error
```

Bỏ hẳn check `"error" in stdout_lower` (fragile, match "0 errors", "no errors", "ErrorBoundary"...).

### Kết quả Phase 1

| Metric | Before | After |
|---|---|---|
| Hang vô hạn có thể xảy ra | ✅ | ❌ (timeout 30 phút) |
| Log streaming vào Dagster | ❌ | ✅ |
| False positive warning | ✅ | ❌ |
| Metabase lock vẫn block view update | ✅ | ✅ (sẽ fix ở Phase 2) |

---

## Phase 2 — Root Cause: Eliminate Lock Contention (P1, 2-3 giờ)

**Mục tiêu:** Pipeline không bao giờ phải connect vào `olap.duckdb` ở runtime → Metabase muốn giữ lock bao lâu cũng được.

### 2.1 Áp dụng "Pattern C — Bootstrap views once"

Tách `generate_serving_db.py` thành 2 tác vụ:

**A. `bootstrap_serving_views.py`** (chạy thủ công khi schema thay đổi):
- Connect vào DB (chấp nhận cần dừng Metabase tạm thời, hoặc Metabase chưa kết nối)
- Scan tất cả subdirs → `CREATE OR REPLACE VIEW` cho từng table
- Rolling Self-Refresh View đã có sẵn logic `WHERE filename = max_fn` → tự pick parquet mới nhất
- Đóng connection, exit

**B. `refresh_rolling.py`** (chạy mỗi pipeline run, asset hiện tại):
- **Không** import `duckdb`
- **Không** mở DB
- Chỉ làm: scan rolling dir → garbage collect file cũ
- Exit

→ Asset `sapo_serving_db` chuyển sang gọi `refresh_rolling.py`. Metabase lock không còn liên quan.

### 2.2 Vấn đề "table mới do partition/rolling"

User confirm: **không có table mới thường xuyên**, NHƯNG partition/rolling có thể tạo subdir mới (vd: tháng mới → folder mới).

**Giải pháp:** Thêm step "schema drift detection" vào `refresh_rolling.py`:
- Sau khi GC, list current subdirs
- So với danh sách subdirs lần trước (lưu trong file marker `.serving_views.json`)
- Nếu có subdir mới → log warning + (optional) trigger Phase 3 sensor để rebuild view

Hoặc cách KISS hơn: rolling self-refresh view dùng glob pattern `rolling/<table>/*.parquet`. Nếu table folder đã tồn tại từ đầu, không cần update view khi có file mới (view auto-pick max). Chỉ cần rebuild view khi có **table folder** mới — chuyện hiếm.

→ Viable: `refresh_rolling.py` ghi list subdirs hiện tại ra file marker. Nếu khác lần trước → emit log line `[!] SCHEMA_DRIFT: new table 'X'` → run_failure_sensor (Phase 2 của Dagster plan) sẽ alert qua Lark → người vận hành chạy `bootstrap_serving_views.py` thủ công 1 lần.

### 2.3 Mở Metabase ở read-only mode (semantic correctness — must-have)

**Bối cảnh:** Metabase trong hệ thống này chỉ dùng để **view dashboard**, không write back vào DuckDB. Read-only là config đúng về mặt ngữ nghĩa — rw mặc định là lỗi config từ đầu.

Trong Metabase Admin → Database → DuckDB connection → JDBC URL hoặc Additional JDBC Params:
```
jdbc:duckdb:/data/serving/olap.duckdb?duckdb.read_only=true
```

**Lợi ích khi confirmed view-only:**
- Metabase chỉ giữ **shared lock** → `bootstrap_serving_views.py` có thể acquire exclusive lock khi cần (vẫn phải đợi Metabase release shared lock tạm thời, nhưng không block vĩnh viễn)
- Không có rủi ro Metabase vô tình write (vd: saved questions với side effect SQL)
- Semantic đúng — bất kỳ ai đọc config cũng hiểu Metabase = reader

**Test cách áp dụng:**
1. Metabase Admin → Databases → DuckDB entry → Edit
2. Field "Additional JDBC connection string options" → thêm `duckdb.read_only=true`
3. Save → Metabase sync lại schema → nếu success thì OK
4. Nếu driver version cũ không support param → báo lỗi → revert và upgrade driver trước

**Tương tác với Pattern C:** Cộng hưởng, không trùng lặp:
- Pattern C: pipeline không cần mở DB ở runtime → không đụng lock
- Read-only mode: ngay cả khi tương lai cần mở DB (vd: chạy lại bootstrap sau schema drift), Metabase không chặn vĩnh viễn
- → Hai layer phối hợp đúng nghĩa defense-in-depth, không redundant

### 2.4 Bỏ verbose GC log

Trong `refresh_rolling.py`, gộp GC log:
```python
deleted_count = 0
skipped_count = 0
# ... loop
print(f"  [GC] {table_name}: deleted {deleted_count}, skipped {skipped_count}")
```

Giảm 90% log volume → giảm pipe pressure → giảm I/O → tốc độ pipeline tăng nhẹ.

### Kết quả Phase 2

| Metric | Before | After |
|---|---|---|
| Pipeline cần lock DuckDB lúc runtime | ✅ | ❌ |
| Rolling Self-Refresh View stale khi Metabase chạy | ✅ | ❌ |
| Restart Metabase để sync schema | Không cần (vì view không update) | Chỉ cần khi schema drift (hiếm) |
| GC log volume | ~N×M dòng | ~N dòng (1/table) |

---

## Phase 3 — Synergy với Dagster Stability Plan (P2, observability)

Đây là phần research user yêu cầu: **kết hợp với plan `design-260408-1531-dagster-stability-flexibility.md` xem giải quyết được vấn đề nào triệt để hơn**.

### Map giữa 2 plan

| Vấn đề serving hang | Phase nào của Dagster Plan giải quyết | Mức triệt để |
|---|---|---|
| Subprocess pipe deadlock | Không. Phải fix trong Phase 1 plan này. | N/A |
| Job stuck mà không ai biết suốt 16h | **Dagster Phase 2 (Lark failure_sensor)** | ⚠️ Một phần — chỉ fire khi job FAIL, không fire khi STUCK |
| Metabase lock contention | Không. Phải fix trong Phase 2 plan này (Pattern C) | N/A |
| Manual mutex giữa các writer (dbt + serving + sync) | **Dagster Phase 1 (`duckdb_writer:1` tag)** | ✅ Triệt để ở mức Dagster |
| Schema drift cần manual rebuild view | **Dagster Phase 2 (failure_sensor) + log marker** | ✅ Triệt để khi gắn marker `[!] SCHEMA_DRIFT` |
| Trigger bootstrap view tự động khi drift | **Dagster Phase 3 (run_status_sensor)** — có thể triển khai như "stuck-state sensor" | ⚠️ Cần custom |

### Synergy 1 — `duckdb_writer:1` tag (Dagster Phase 1) cộng hưởng với Phase 2 plan này

Sau khi Phase 2 plan này áp dụng (pipeline không lock DB nữa), tag `duckdb_writer` còn ý nghĩa gì? **Vẫn còn** — vì:
- dbt vẫn ghi vào DuckDB nội bộ (`sapo.duckdb` data lake)
- nightly reconciliation có thể write
- Tag bảo vệ những writer này khỏi đụng nhau

→ **Hai plan độc lập, không xung đột.** Plan này fix runtime path của serving; Dagster plan fix coordination giữa các job.

### Synergy 2 — failure_sensor (Dagster Phase 2) làm visibility cho plan này

**Critical:** Hiện tại job stuck 16h mà không ai biết. Sau khi:
- Phase 1 plan này thêm `timeout=1800` → stuck → raise → run FAILED
- Dagster Phase 2 (Lark sensor) → fire alert trong < 1 phút

→ MTTD giảm từ "khi user complain" xuống **< 31 phút** trong worst case (30 phút timeout + 1 phút sensor tick).

**Đây là tổ hợp cần thiết, không phải nice-to-have.** Fix timeout mà không có alerting = vẫn mù, chỉ là job fail nhanh hơn.

### Synergy 3 — Schema drift alert qua Lark

Khi `refresh_rolling.py` phát hiện table folder mới, in `[!] SCHEMA_DRIFT: new table X`. Asset code có thể detect marker này và:
- **Option A (đơn giản):** raise Exception → job FAILED → failure_sensor → Lark alert
- **Option B (nhẹ nhàng hơn):** không raise, nhưng emit `AssetCheckSeverity.WARN` → cần thêm asset check setup, phức tạp hơn

→ Khuyến nghị Option A trong giai đoạn đầu. Operator nhận alert → chạy `bootstrap_serving_views.py` thủ công → next run pass.

### Synergy 4 — "Stuck-run sensor" (mở rộng Dagster Phase 3)

Phát hiện ra: `run_failure_sensor` **không fire** khi run đang STARTED nhưng treo. Cần custom sensor:

```python
# orchestration/sensors/stuck_run_alerter.py
from datetime import datetime, timedelta
from dagster import sensor, RunStatus, SkipReason
from orchestration.notifications.lark_client import send_lark_card

STUCK_THRESHOLD = timedelta(minutes=45)  # > 30 phút timeout của serving

@sensor(minimum_interval_seconds=300)  # tick mỗi 5 phút
def stuck_run_sensor(context):
    instance = context.instance
    started_runs = instance.get_runs(filters=RunsFilter(statuses=[RunStatus.STARTED]))
    now = datetime.utcnow()
    for run in started_runs:
        age = now - run.start_time
        if age > STUCK_THRESHOLD:
            send_lark_card(
                title="⏱️ Dagster Run STUCK",
                color="orange",
                fields={
                    "Job": run.job_name,
                    "Run ID": run.run_id,
                    "Started": str(run.start_time),
                    "Age": str(age),
                },
            )
    return SkipReason("Stuck check completed")
```

**Đây là vấn đề mà Dagster Plan ban đầu chưa cover.** Nên thêm vào Dagster Plan như "Phase 2.5 — Stuck Run Detection". Cost: ~30 dòng, value: ngăn tái diễn vụ 16h.

### Tổng kết synergy

**Triển khai bộ đôi `Plan này (Phase 1+2) + Dagster Plan (Phase 1+2 + 2.5)` sẽ giải quyết triệt để:**

| Vấn đề | Plan nào fix |
|---|---|
| Pipe deadlock | Plan này P1 |
| Hang vô hạn | Plan này P1 (timeout) + Dagster P2.5 (sensor) |
| Metabase lock | Plan này P2 (Pattern C) |
| Cross-job collision | Dagster P1 (queue + tag) |
| Job fail không ai biết | Dagster P2 (failure_sensor) |
| Job stuck không ai biết | Dagster P2.5 (stuck_run_sensor — MỚI) |
| Schema drift im lặng | Plan này P2 emit marker + Dagster P2 alert |

**Không có lỗ hổng nào còn lại** trong scope của 2 plan này.

---

## Đề xuất thứ tự thực thi (kết hợp 2 plan)

```
Day 0 (ngay):
  ├─ [Plan này 1.1] Kill stuck run 2c6d50cf
  └─ [Plan này 1.2] Fix subprocess Popen + timeout (CỨU CÁNH)

Day 1:
  ├─ [Plan này 1.3] Sửa warning detector
  ├─ [Dagster Plan 1] Tạo dagster.yaml + tags + xóa manual mutex
  └─ Smoke test trên staging

Day 2:
  ├─ [Dagster Plan 2.1-2.4] Lark failure_sensor + helper
  ├─ [Plan này 2.5 — MỚI] Stuck run sensor
  └─ Smoke test alert path

Day 3:
  ├─ [Plan này 2.1-2.2] Tách bootstrap_views.py + refresh_rolling.py
  ├─ [Plan này 2.4] Bỏ verbose GC log
  └─ Migrate asset code

Day 4:
  ├─ [Plan này 2.3] Mở Metabase read-only mode (semantic correctness)
  └─ Verify Pattern C end-to-end với Metabase đang chạy
```

Rollback: Mỗi step là 1 commit độc lập, revert dễ dàng.

---

## Risk Assessment

| Risk | Mitigation |
|---|---|
| Tách bootstrap → schema drift bị bỏ lỡ | Marker `[!] SCHEMA_DRIFT` + failure_sensor |
| Timeout 30 phút có thể quá ngắn cho lần đầu sau outage dài | Cho config qua env `SERVING_TIMEOUT_SEC` |
| Stuck sensor fire false positive cho job dài thật | Threshold per-job tag (vd `expected_max_runtime`) |
| Pattern C cần bootstrap thủ công khi schema mới — operator quên | Script bootstrap idempotent + alert là trigger rõ ràng |
| Read-only Metabase không hoạt động với DuckDB driver version cũ | Test JDBC param trước; fallback giữ rw nếu cần |

---

## Files to modify

**Phase 1:**
- `orchestration/assets/serving.py` — fix subprocess pattern + warning detector

**Phase 2:**
- `scripts/provisioning/generate_serving_db.py` — split thành 2 file:
  - `scripts/provisioning/bootstrap_serving_views.py` (mới)
  - `scripts/provisioning/refresh_rolling.py` (mới, thay thế)
- `orchestration/assets/serving.py` — gọi `refresh_rolling.py`
- `docker-compose.yml` — Metabase JDBC URL với `read_only=true` (optional)

**Phase 3 (synergy):**
- `orchestration/sensors/stuck_run_alerter.py` (mới)
- `orchestration/definitions.py` — đăng ký sensor

---

## Success Criteria

1. ✅ Job `sapo_serving_db` không bao giờ chạy quá 30 phút mà không log gì
2. ✅ Metabase mở web cả ngày, pipeline vẫn chạy bình thường, view không stale
3. ✅ Khi job fail hoặc stuck → Lark alert trong < 5 phút
4. ✅ Schema drift (table folder mới) → operator nhận alert + biết action cần làm
5. ✅ Log Dagster cho serving asset hiển thị streaming, không phải dump cuối
6. ✅ `definitions.py` đã clean theo Dagster Plan Phase 1

---

## Decisions (user-confirmed 2026-04-08)

1. **Serving timeout**: `SERVING_TIMEOUT_SEC = 1800` (30 phút). Config qua env, override được nếu cần.
2. **Stuck sensor tick interval**: **10 phút** (`minimum_interval_seconds=600`). Threshold phát hiện stuck: > 45 phút. Worst case detect ~55 phút sau khi stuck (giảm 20 phút so với tick 30 phút). Cost negligible (~144 query/ngày).
3. **Dedupe alert**: Dùng state cursor — mỗi `run_id` chỉ alert **1 lần**, không re-alert cùng run. Nhưng nếu run tiếp tục stuck qua nhiều tick → vẫn không spam vì đã có trong cursor.
4. **Auto-recovery policy**: **KHÔNG auto-kill**. Chỉ alert để operator biết run đang stuck và có thể điều tra. Nếu sau này thêm auto-kill → **bắt buộc** phải alert trước và sau khi kill (2 alert riêng biệt: "STUCK detected" + "AUTO-KILLED").

### Stuck sensor pseudocode với cursor

```python
# orchestration/sensors/stuck_run_alerter.py
import json
from datetime import datetime, timedelta, timezone
from dagster import sensor, SensorEvaluationContext, SkipReason, RunsFilter, DagsterRunStatus
from orchestration.notifications.lark_client import send_lark_card

STUCK_THRESHOLD = timedelta(minutes=45)

@sensor(minimum_interval_seconds=600)  # tick mỗi 10 phút — cursor dedup đủ chống spam
def stuck_run_sensor(context: SensorEvaluationContext):
    # Load already-alerted run_ids from cursor
    alerted = set(json.loads(context.cursor) if context.cursor else [])
    instance = context.instance
    started = instance.get_runs(
        filters=RunsFilter(statuses=[DagsterRunStatus.STARTED])
    )
    now = datetime.now(timezone.utc)
    new_alerts = []

    for run in started:
        if run.run_id in alerted:
            continue
        if not run.start_time:
            continue
        age = now - datetime.fromtimestamp(run.start_time, tz=timezone.utc)
        if age > STUCK_THRESHOLD:
            send_lark_card(
                title="⏱️ Dagster Run STUCK (no auto-kill)",
                color="orange",
                fields={
                    "Job": run.job_name,
                    "Run ID": run.run_id,
                    "Age": str(age).split(".")[0],
                    "Action": "Operator kiểm tra thủ công",
                },
            )
            new_alerts.append(run.run_id)

    if new_alerts:
        alerted.update(new_alerts)
        # Giữ cursor nhỏ: chỉ lưu tối đa 100 run_id gần nhất
        context.update_cursor(json.dumps(list(alerted)[-100:]))
        return SkipReason(f"Alerted {len(new_alerts)} stuck run(s)")
    return SkipReason("No stuck runs detected")
```

**Ghi chú:**
- Cursor dedup theo `run_id` → 1 run chỉ alert 1 lần, dù tick bao nhiêu lần.
- Tick 10 phút + threshold 45 phút → worst case phát hiện sau ~55 phút. Spam được chống bằng cursor nên tick nhanh không gây noise.
- Cursor giới hạn 100 run_id để không phình vô hạn. Run cũ sẽ rơi ra; không alert lại vì cũng không còn ở STARTED.

## Post-mortem: Lock hypothesis was wrong

Sau khi triển khai xong toàn bộ plan, user đặt câu hỏi: "Metabase dùng lớp
serving_db, làm sao bị lock?". Verify thực tế phát hiện giả định ban đầu sai.

**Test** (Metabase + data_platform cùng up, cùng dùng `/app/data_lake/serving/olap.duckdb`):
```
RW connect SUCCESS in 15.2ms
RO connect SUCCESS (parallel)
```

**Kết luận kỹ thuật:**
- DuckDB `read_only=true` mode **KHÔNG acquire file lock** — chỉ mmap file để
  đọc. Khác với SQLite (dùng shared lock cho reader).
- Metabase driver MotherDuck v1.4.4 với `read_only=true` cũng không giữ lock.
- Writer mới có thể connect bất cứ lúc nào, kể cả khi Metabase đang query.

**Hệ quả cho hypothesis cũ:**
- Giả định "Metabase JDBC exclusive lock chặn pipeline" → SAI
- Giả định "views không update được khi Metabase chạy" → SAI (không test được
  từ đầu, chỉ suy luận sai từ catch block trong code cũ)
- `[!] WARNING: Could not connect to DuckDB` catch trong `generate_serving_db.py`
  có thể chưa bao giờ fire trong production hiện tại, chỉ là defensive code.

**Tại sao Phase 2 (Pattern C) vẫn được giữ:**
1. Runtime asset không cần import `duckdb` — smaller dependency surface
2. Separation of concerns: bootstrap = schema lifecycle, refresh = data GC
3. Schema drift detection via `.known_tables.json` — feature mới, không cũ
4. Bootstrap explicit command rõ ràng trong runbook hơn "silent skip" cũ
5. Code đã deploy và verified, revert sẽ churn thêm

**Lessons learned:**
- Hypothesis về locking cần verify bằng test thực tế trước khi build plan lớn
- "Catch + warning" trong code cũ không tự động chứng minh bug tồn tại —
  defensive code có thể không fire bao giờ
- Root cause analysis cần phân biệt: "bug thực sự gây vụ việc" vs "bug tiềm năng"

## Additional Decisions (user-confirmed 2026-04-08, round 2)

5. **Metabase JDBC read-only mode**: **Must-have**, vì Metabase trong hệ thống này confirmed view-only. Read-only là semantic correctness, không phải optional. Thêm `duckdb.read_only=true` vào Metabase Admin → Databases → DuckDB → Additional JDBC Params. Xếp Day 4 vì cần Pattern C ổn định trước để test end-to-end.

6. **File `olap.duckdb` cũ**: **KHÔNG xóa, reuse file hiện tại**. File chỉ chứa views, data nằm trong parquet → xóa không mất data nhưng tốn công. `CREATE OR REPLACE VIEW` trong bootstrap script idempotent, overwrite view cũ OK. Chỉ xóa reactive khi file corrupt hoặc storage format upgrade breaking.

7. **Bootstrap lần đầu — opportunistic manual command**:
   - **Không dùng Dagster job** (phức tạp, cần detect lock busy + retry, YAGNI)
   - **Không dùng init container** (miss case schema drift runtime)
   - **Dùng manual command** với runbook rõ ràng trong `docs/operations/`:
     ```bash
     # Stop Metabase tạm thời để giải phóng lock
     docker compose stop metabase
     # Run bootstrap
     docker compose run --rm dagster python scripts/provisioning/bootstrap_serving_views.py
     # Restart Metabase
     docker compose start metabase
     ```
   - **Trigger workflow**: khi `refresh_rolling.py` detect schema drift → emit `[!] SCHEMA_DRIFT: new table X` → `run_failure_sensor` → Lark alert với hint "Run bootstrap script when convenient" → operator pick thời điểm low traffic chạy manual.
   - **Upgrade path**: Nếu drift xảy ra > 1 lần/tuần → mới cân nhắc auto-trigger qua `run_status_sensor`. YAGNI cho đến khi có số liệu.

## Unresolved Questions (còn lại)

Không còn câu hỏi chưa quyết. Tất cả đã có direction. Các rủi ro còn lại xử lý reactive khi gặp.
