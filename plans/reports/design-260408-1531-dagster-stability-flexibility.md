---
type: design-suggestion
date: 2026-04-08
status: proposal
scope: orchestration/
related:
  - orchestration/definitions.py
  - orchestration/docs/SCHEDULES.md
  - orchestration/docs/JOBS.md
---

# Design Suggestion — Ổn định & Flexibility cho Dagster Orchestration

## TL;DR

Vấn đề hiện tại **không phải** thiếu sensor. Là thiếu **run coordinator + concurrency primitives**, cộng thêm thiếu **failure alerting** và **event chaining**.

Đề xuất 3 phase, ROI giảm dần. **Phase 1 bắt buộc** — fix root cause. Phase 2-3 tùy chọn theo nhu cầu.

---

## Hiện trạng (đã scan)

- 3 jobs: `realtime` (~3 min), `incremental` (10 min), `nightly` (4 AM), `sheets` (manual)
- 3 schedules: tự implement mutex bằng `instance.get_runs() → SkipReason`
- Cron offset trick: realtime chạy phút 1,4,7,11... để tránh race với incremental `*/10`
- **KHÔNG** có `dagster.yaml` → đang dùng default `DefaultRunCoordinator` (no queue, no global concurrency)
- **KHÔNG** có sensors
- **KHÔNG** có failure notification
- Asset-level lock cho duckdb (đã có, comment trong code)

### Pain points (suy luận từ code)

| # | Triệu chứng | Root cause |
|---|---|---|
| 1 | Phải dùng cron offset trick + manual mutex | Không có run coordinator queue |
| 2 | Mỗi schedule duplicate ~30 dòng `get_runs()` logic | Không có concurrency primitive |
| 3 | Nếu job fail → không ai biết | Không có alerting |
| 4 | Nightly xong nhưng serving phải chờ tick tiếp theo | Không có event chain |
| 5 | Webhook ingest nhưng phải đợi cron drain queue | Webhook là push, scheduler là pull → mismatch |

---

## Phase 1 — Stability Fix (BẮT BUỘC, High ROI)

**Mục tiêu:** Xóa toàn bộ manual mutex logic, fix race ở mức instance.

### 1.1 Tạo `dagster.yaml`

Đặt tại `$DAGSTER_HOME/dagster.yaml` (hoặc `orchestration/dagster.yaml` + set env).

```yaml
run_coordinator:
  module: dagster.core.run_coordinator
  class: QueuedRunCoordinator
  config:
    max_concurrent_runs: 4
    tag_concurrency_limits:
      # Toàn bộ sapo sync jobs share 1 slot → mutual exclusion tự nhiên
      - key: "sapo_sync_group"
        limit: 1
      # DBT writes vào duckdb → 1 slot
      - key: "duckdb_writer"
        limit: 1

run_launcher:
  module: dagster.core.launcher
  class: DefaultRunLauncher
```

### 1.2 Tag jobs trong `definitions.py`

```python
sapo_realtime_sync_job = define_asset_job(
    name="sapo_realtime_sync_job",
    selection=...,
    tags={
        "sapo_sync_group": "true",
        "duckdb_writer": "true",
    },
)
# Tương tự cho incremental, nightly, sheets
```

### 1.3 Xóa logic mutex thủ công

Sau khi có queue + concurrency tag, **xóa toàn bộ** `get_runs() → SkipReason` trong 3 schedules. Schedule trở về dạng tối giản:

```python
@schedule(
    job=sapo_realtime_sync_job,
    cron_schedule="*/3 * * * *",  # back to clean cron
    execution_timezone="Asia/Ho_Chi_Minh",
)
def realtime_schedule(_context):
    return RunRequest()
```

Lý do: Coordinator tự QUEUE runs khi slot busy. Race condition không còn vì state check ở mức instance, không phải mức tick.

### 1.4 Cleanup

- Xóa cron offset trick (1,4,7,11...) → đổi về `*/3`
- Xóa `priority_jobs` lists trong từng schedule
- `definitions.py` rút gọn ~150 → ~60 dòng

### Kết quả Phase 1

| Metric | Before | After |
|---|---|---|
| `definitions.py` LOC | ~306 | ~120 |
| Manual mutex code paths | 3 | 0 |
| Race condition window | Có (start-time) | Không (queue level) |
| Cron logic | Lệch phút khó hiểu | Standard |

---

## Phase 2 — Failure Alerting via Larksuite (High ROI, Low Cost)

**Mục tiêu:** Biết ngay khi có job fail, đẩy alert vào **Larksuite (Lark/Feishu) chat group** qua Custom Bot webhook. Đây là use case sensor **đáng dùng nhất**.

### 2.1 Setup Larksuite Bot

1. Mở Lark group muốn nhận alert → **Settings → Group Bots → Add Bot → Custom Bot**
2. Đặt tên (vd: `Dagster Alerts`) → copy **Webhook URL** dạng:
   `https://open.larksuite.com/open-apis/bot/v2/hook/<UUID>`
3. (Khuyến nghị) Bật **Signature Verification** → copy `secret` để ký request (chống abuse)
4. Lưu vào env:
   ```bash
   LARK_ALERT_WEBHOOK=https://open.larksuite.com/open-apis/bot/v2/hook/...
   LARK_ALERT_SECRET=<optional signing secret>
   ```

### 2.2 Tạo helper `orchestration/notifications/lark_client.py`

Tách helper riêng để tái sử dụng cho các loại alert khác sau này (DRY).

```python
"""Larksuite Custom Bot client - sends rich card messages to Lark chat groups."""
import os
import time
import hmac
import hashlib
import base64
import requests
from typing import Optional


def _sign(secret: str, timestamp: int) -> str:
    """Lark signature: base64(HMAC-SHA256(timestamp + '\n' + secret, ''))."""
    string_to_sign = f"{timestamp}\n{secret}"
    digest = hmac.new(
        string_to_sign.encode("utf-8"), b"", digestmod=hashlib.sha256
    ).digest()
    return base64.b64encode(digest).decode("utf-8")


def send_lark_card(
    title: str,
    fields: dict,
    color: str = "red",
    webhook: Optional[str] = None,
    secret: Optional[str] = None,
) -> bool:
    """Send an interactive card to Lark group via Custom Bot webhook.

    Args:
        title: Card header title.
        fields: Key-value pairs rendered as card body.
        color: Header theme color (red|orange|yellow|green|blue|grey).
        webhook: Override env LARK_ALERT_WEBHOOK.
        secret: Override env LARK_ALERT_SECRET (signature verification).

    Returns:
        True if sent successfully, False otherwise.
    """
    webhook = webhook or os.getenv("LARK_ALERT_WEBHOOK")
    if not webhook:
        return False
    secret = secret or os.getenv("LARK_ALERT_SECRET")

    # Build interactive card payload
    body_elements = [
        {
            "tag": "div",
            "fields": [
                {
                    "is_short": False,
                    "text": {"tag": "lark_md", "content": f"**{k}:** {v}"},
                }
                for k, v in fields.items()
            ],
        }
    ]
    payload = {
        "msg_type": "interactive",
        "card": {
            "header": {
                "title": {"tag": "plain_text", "content": title},
                "template": color,
            },
            "elements": body_elements,
        },
    }

    # Optional signature
    if secret:
        ts = int(time.time())
        payload["timestamp"] = str(ts)
        payload["sign"] = _sign(secret, ts)

    try:
        resp = requests.post(webhook, json=payload, timeout=5)
        return resp.status_code == 200 and resp.json().get("code", 0) == 0
    except Exception:
        return False
```

### 2.3 Tạo sensor `orchestration/sensors/failure_alerting.py`

```python
"""Run failure sensor - pushes Dagster job failures to Larksuite chat."""
from dagster import run_failure_sensor, RunFailureSensorContext
from orchestration.notifications.lark_client import send_lark_card
from orchestration.definitions import (
    sapo_realtime_sync_job,
    sapo_incremental_sync_job,
    sapo_nightly_reconciliation_job,
    sheets_sync_job,
)


@run_failure_sensor(
    monitored_jobs=[
        sapo_realtime_sync_job,
        sapo_incremental_sync_job,
        sapo_nightly_reconciliation_job,
        sheets_sync_job,
    ],
    minimum_interval_seconds=60,
)
def lark_failure_sensor(context: RunFailureSensorContext):
    """Send failure alert to Lark group on any monitored job failure."""
    run = context.dagster_run
    error_msg = (context.failure_event.message or "")[:500]

    send_lark_card(
        title="🚨 Dagster Job FAILED",
        color="red",
        fields={
            "Job": run.job_name,
            "Run ID": run.run_id,
            "Status": str(run.status),
            "Error": f"```{error_msg}```",
        },
    )
```

### 2.4 Đăng ký vào `Definitions`

```python
from orchestration.sensors.failure_alerting import lark_failure_sensor

defs = Definitions(
    assets=all_assets,
    schedules=[realtime_schedule, incremental_schedule, nightly_schedule],
    sensors=[lark_failure_sensor],
    resources={...},
)
```

### 2.5 Smoke test

```python
# tests/test_lark_alert.py - run manually before deploy
from orchestration.notifications.lark_client import send_lark_card

assert send_lark_card(
    title="Test - Dagster Alert Channel",
    color="blue",
    fields={"Message": "Lark webhook hoạt động OK", "Env": "staging"},
)
```

### Cost / Value

- Code: ~120 dòng (helper + sensor)
- Cấu hình: 1-2 env var (`LARK_ALERT_WEBHOOK`, optional `LARK_ALERT_SECRET`)
- Value: Visibility tức thì cho mọi failure → giảm MTTD từ "khi user complain" xuống "<1 phút"
- Helper `lark_client.py` reusable cho: success summary, SLA breach, data quality alerts...

### Lưu ý vận hành

1. **Rate limit Lark**: ~100 msg/min/bot. Failure storm có thể bị throttle → cân nhắc dedupe trong sensor (vd: skip nếu cùng job fail trong 5 phút trước).
2. **Signature verification**: Bật nếu webhook URL có thể bị leak. Không bật cũng OK trong môi trường nội bộ.
3. **Card vs text**: Dùng `interactive card` thay vì plain text vì render đẹp + structured. Lark chấp nhận cả 2.
4. **Khu vực**: `open.larksuite.com` cho Lark global; nếu dùng Feishu (Trung Quốc) đổi sang `open.feishu.cn`.

---

## Phase 3 — Event Chaining (Medium ROI, tùy nhu cầu)

**Mục tiêu:** Trigger downstream **ngay khi** upstream success, không chờ tick.

### Use case cụ thể của bạn

Hiện tại nightly xong → serving_db chỉ refresh khi nightly kết thúc trong cùng asset job. Nhưng nếu muốn:
- "Khi nightly success → trigger riêng `dbt test job`"
- "Khi sheets sync xong → trigger lại nightly để recompute marketing spend"

→ Đây là chỗ `run_status_sensor` thắng.

### 3.1 Tạo `orchestration/sensors/job_chain.py`

```python
from dagster import run_status_sensor, DagsterRunStatus, RunRequest, SkipReason

@run_status_sensor(
    run_status=DagsterRunStatus.SUCCESS,
    monitored_jobs=[sheets_sync_job],
    request_job=sapo_nightly_reconciliation_job,
)
def sheets_to_nightly_chain(context):
    """Trigger reconciliation sau khi sheets cập nhật xong (vd: marketing spend update)."""
    return RunRequest(
        run_key=f"sheets_chain_{context.dagster_run.run_id}",
        tags={"trigger_source": "sheets_sync_chain"},
    )
```

### Khi KHÔNG nên làm Phase 3

- Nếu downstream đã ở cùng asset job → asset materialization tự handle, không cần sensor
- Nếu downstream chỉ cần "sometime soon" thay vì "immediately" → cron đơn giản hơn

---

## Phase 4 — Tùy chọn nâng cao (Skip nếu không có nhu cầu rõ)

| Idea | Khi nào dùng |
|---|---|
| `asset_sensor` cross-code-location | Khi tách thành nhiều Dagster deployments |
| Custom sensor đọc Sapo API watermark | Khi muốn skip incremental run nếu không có data mới (tiết kiệm compute) |
| `freshness_policy` + auto-materialize | Khi muốn declarative scheduling thay vì imperative |
| Backfill sensor với cursor | Khi cần catch-up logic phức tạp |

**Cảnh báo:** Đây là YAGNI territory. Chỉ thêm khi có pain cụ thể.

---

## Quyết định khuyến nghị

| Phase | Khuyến nghị | Lý do |
|---|---|---|
| **Phase 1** | **DO NOW** | Fix root cause stability, code sạch hơn 60% |
| **Phase 2** | **DO NEXT** | High value, ~30 dòng, không có alerting hiện tại = mù |
| **Phase 3** | Conditional | Chỉ nếu thực sự có cross-job chain. Hiện tại assets cùng job đã tự chain |
| **Phase 4** | Skip | YAGNI |

---

## Migration Plan (nếu approve Phase 1+2)

```
Day 1 — Phase 1 setup
  ├─ Tạo dagster.yaml với QueuedRunCoordinator
  ├─ Set DAGSTER_HOME nếu chưa có
  ├─ Add tags vào jobs
  └─ Test local: chạy 2 jobs đồng thời, verify queue behavior

Day 2 — Phase 1 cleanup
  ├─ Xóa manual mutex logic trong 3 schedules
  ├─ Refactor cron về standard
  ├─ Update orchestration/docs/SCHEDULES.md
  └─ Smoke test: deploy staging, observe 1 ngày

Day 3 — Phase 2 (Lark Alerting)
  ├─ Tạo Lark Custom Bot trong group, copy webhook URL
  ├─ Set env LARK_ALERT_WEBHOOK (+ optional LARK_ALERT_SECRET)
  ├─ Thêm notifications/lark_client.py (helper, reusable)
  ├─ Thêm sensors/failure_alerting.py (run_failure_sensor)
  ├─ Đăng ký sensor vào Definitions
  ├─ Smoke test: gọi send_lark_card() từ REPL → verify card xuất hiện
  └─ Integration test: trigger fake job failure → verify alert
```

Rollback: Phase 1 reversible bằng cách restore old `definitions.py` và xóa `dagster.yaml`.

---

## Trade-offs cần biết

1. **QueuedRunCoordinator delay**: Run khi enqueue có thể chờ vài giây trước khi launch (vs DefaultRunCoordinator launch ngay). Với job chạy phút, không đáng kể.
2. **Tag concurrency là instance-wide**: Nếu sau này tách multiple deployments, phải re-think.
3. **Sensor cost**: Mỗi sensor tick = 1 query DB. `failure_sensor` 60s interval = 1440 query/day → negligible.
4. **Lark rate limit**: ~100 msg/min/bot. Nếu storm fail có thể bị throttle → cân nhắc dedupe trong sensor (state cursor).

---

## Unresolved Questions

1. `DAGSTER_HOME` hiện tại đang trỏ đâu? (Cần biết để đặt `dagster.yaml` đúng chỗ)
2. Lark group nào sẽ nhận alert? (cần create Custom Bot trong group đó để lấy webhook URL). Ai là owner để add bot?
3. Sheets sync hiện đang manual — có muốn schedule định kỳ kèm chain → nightly không, hay giữ manual?
4. Có yêu cầu SLA cụ thể nào (vd: realtime < 5 phút lag) đang miss vì cron offset trick không?
5. Có job nào tương lai chạy ở code location khác (vd: ML pipeline, GA ingestion) sẽ cần cross-location coordination?
