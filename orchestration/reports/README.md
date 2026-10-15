# orchestration/reports — report site build and summary messages

Kernel module (loaded by `definitions.py` through `orchestration.reports.definitions(nightly_job)`).
It never builds pages itself: the builder is the `evidence` container
(`evidence/scripts/build-areas.sh`); this module asks for builds, watches them and announces them.

```
pipeline_batch_nightly_job SUCCESS
  └─ report_site_build_after_nightly_sensor ─► report_site_build_job
        writes <REPORT_BUILD_DIR>/request.json {request_id, requested_at, trigger}
evidence container (builder) builds every area, writes <REPORT_BUILD_DIR>/status.json
report_site_build_status_sensor (every 5 min)
  ├─ an area failed            ─► Lark card on the alert channel (send_lark_card, LARK_ALERT_WEBHOOK)
  ├─ no result 2 h after request ─► Lark card (alert channel)
  └─ build ok, data fresh, message due ─► report_summary_message_job (run_key summary-<report>@<as_of>)
        KPI tiles of the report compiled by the `analytics` package, run read-only on a copy of
        the serving catalog, sent to every channel of the report
```

| File | Content |
|---|---|
| `build_request.py` | `report_site_build_job` (also the manual "build now"), `make_after_nightly_sensor` |
| `build_status.py` | `report_site_build_status_sensor`; decision logic `evaluate()` is pure and tested |
| `summary_message.py` | `report_summary_message_job`, `send_summary()`, `due_reports()` |
| `__tests__/` | request file, failure/delay alerts, due and stale rules, dry run, no fallback to the alert webhook, cost tiles |

## Configuration

| Where | What |
|---|---|
| `tenants/<t>/analytics/profile.yml` → `message.channels[]` | `id`, `title` (chat group name), `env_webhook`, `env_secret` (names of the environment variables), `can_view_cost` |
| `tenants/<t>/analytics/profile.yml` → `message.reports[]` | `report` (catalog id, engine evidence), `channels`, `weekdays`, `not_before` (local time) |
| `tenants/<t>/analytics/profile.yml` → `access.site_url` | base of the link in the message |
| `.env.docker` (data_platform) | the webhook and secret of each channel, e.g. `LARK_REPORT_LEADERSHIP_WEBHOOK`, `LARK_REPORT_LEADERSHIP_SECRET`; `REPORT_MESSAGE_DRY_RUN=0` to really send (default `1`: only logged) |
| `REPORT_BUILD_DIR` (optional) | default `/app/var/data_lake/report_build` (host `app_data/data_lake/report_build/`, also mounted in the `evidence` container) |

Rules: a channel whose webhook variable is unset is skipped, never sent to the alert channel; tiles
of cost-sensitive metrics go only to channels with `can_view_cost: true`; a message is sent only for a
build whose data ends yesterday (a failed nightly sends nothing, the failure is alerted instead); a
failure to build or send a message is logged and never fails the run. The `data_platform` container
mounts `analytics/` and `tenants/` read-only for this module.

Fine Japan: Weekly Pulse goes to the leadership Lark group (with profit and margin) on Mondays from
07:00; the exact group is still to be confirmed, so the channel has no `title` and stays dry-run until
its webhook is set.
