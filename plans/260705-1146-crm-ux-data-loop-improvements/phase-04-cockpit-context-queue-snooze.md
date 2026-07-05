# Phase 04 — Cockpit Context, Queue Counter & Task Snooze (A1 + A2 + A4)

**Status:** DONE | **Priority:** P1 | **Depends on:** — (độc lập) | **Blocked by phase 05:** cùng đụng S14 templates

## Context links

- Design: `crm/docs/ui-spec/notes/ux-action-queue-task-cockpit-data-loop-design.md` §4 A1/A2/A4
- Master plan: `plans/260705-1146-crm-ux-data-loop-improvements/plan.md`
- Spec: `crm/docs/ui-spec/screens/S01-worklist-dashboard.md`, `S14-call-mode-cockpit.md`, `S15-task-detail.md`, `crm/docs/ui-spec/overlays/O03-postpone-task-overlay.md`
- Impl notes: `crm/docs/ui-spec/notes/S14-implementation-notes.md`

## Requirements

### A1 — Denormalize value_at_stake_vnd + top_affinity_product vào task khi claim

- **Giá trị (value_at_stake_vnd):** SUM tất cả `value_at_stake_vnd` của các actions được claim. Justification: claim một khách = nhận toàn bộ cơ hội; max(single action) đánh giá thấp; SUM phản ánh đúng tổng tiềm năng.
- **Sản phẩm (top_affinity_product):** lấy từ action có `value_at_stake_vnd` cao nhất trong batch.
- **Tại sao không JOIN render-time:** `list_all_action_queue()` filter `NOT EXISTS (crm_task source='action_queue_claim' AND party_id)` — actions của khách đã claim bị ẩn hoàn toàn khỏi worklist query. Worklist task row lấy data từ `crm_task` table (via `list_tasks()`) không có action_queue fields. Join ngược lại cần either: couple `TaskRepository` với cache DB, hoặc N+1 lookup, cả hai tăng độ phức tạp. Persist at claim time là đơn giản và nhất quán trên mọi surface.
- Display: `_wl_row.html` task row claim hiện `💰 {fmt_vnd(value)}` + `🛍 {top_affinity_product}` khi có; `task_detail.html` provenance block hiện cả hai.

### A2 — Queue counter #n/N + nút "Khách kế →"

- Worklist "Vào chế độ gọi" → `/customers/{id}/call?queue_ids={comma-party_ids}&queue_pos={0-indexed}`
- Danh sách queue_ids = ordered party_ids từ ranked worklist, capped 50, chỉ lấy rows có `party_id`.
- Cockpit handler: parse params → render `#(pos+1)/{total}` + href "Khách kế" = `queue_ids[pos+1]` với `queue_pos=pos+1`.
- Khi `queue_ids` rỗng (enter từ S15 hoặc direct URL): counter ẩn, nút "Khách kế" không render (như hiện tại).
- KISS: không có session state table, không server-side re-query — queue context sống trong URL.

### A4 — Snooze task claim

- Thêm snooze dropdown (1/3/7 ngày) vào task row `source='action_queue_claim'` trong worklist.
- Mechanic: `PATCH /tasks/{task_id}/snooze?days=N` → shift `due_at` = today_ict + N days (ICT→UTC), reset `status='open'` nếu đang `doing`.
- **Tại sao dùng due_at (không thêm cột mới):** task đang ở B0/B1 vì `due_at` ≤ hôm nay. Shift `due_at` = ngày wake → task chuyển sang B2 (đúng hạn) hoặc B1 khi đến ngày. Underlying actions đã ẩn qua `NOT EXISTS` filter (task vẫn `open` / `doing`). Không cần cột riêng — `due_at` đã encode đúng semantic.
- S15 "Hoãn" button (A-S15-003 → O03) đã xử lý full-overlay postpone; không đụng.

## Files to modify / create

| File | Thay đổi |
|---|---|
| `crm/migrations/0036_task_claim_context_fields.up.sql` | **NEW** — `ALTER TABLE crm_task ADD COLUMN value_at_stake_vnd INTEGER;` + `ADD COLUMN top_affinity_product TEXT;` (0035 đã dành cho phase-03 `activity_outcome_reason`; dùng số kế tiếp còn trống lúc triển khai) |
| `crm/migrations/0036_task_claim_context_fields.down.sql` | **NEW** — SQLite không DROP COLUMN: noop + comment |
| `crm/src/domain/entities/task.py` | Thêm 2 optional fields: `value_at_stake_vnd: Optional[int] = None`, `top_affinity_product: Optional[str] = None` |
| `crm/src/adapters/outbound/sqlite/task_repository.py` | `_INSERT` (+2 cols), `_UPDATE` (+2 SET), `_task_from_row` (+2 fields) |
| `crm/src/application/task_service.py` | `claim_customer_actions()`: compute sum/best và set 2 fields mới trên Task trước khi insert |
| `crm/src/adapters/inbound/web/screen_worklist.py` | (1) PATCH `/tasks/{task_id}/snooze` — mới; (2) build `queue_party_ids` list từ ranked worklist + truyền vào template |
| `crm/src/adapters/inbound/web/templates/fragments/_wl_row.html` | (1) Claim task row: hiện 💰 value + 🛍 product; (2) Snooze `<details>` cho `source='action_queue_claim'` rows |
| `crm/src/adapters/inbound/web/templates/fragments/task_detail.html` | Provenance block: thêm dòng value + product khi có |
| `crm/src/adapters/inbound/web/screens/customer360/screen_call_cockpit.py` | Accept `queue_ids: str = ""`, `queue_pos: int = 0`; parse → `queue_next_party_id`, `queue_total` vào context |
| `crm/src/adapters/inbound/web/templates/call_cockpit.html` | Render `#n/N` counter khi `queue_ids` có; wire "Khách kế" href = next party call URL |
| `crm/docs/ui-spec/screens/S01-worklist-dashboard.md` | Task row spec: ghi nhận 💰/🛍 trên claim rows + snooze button |
| `crm/docs/ui-spec/screens/S14-call-mode-cockpit.md` | Topbar spec: queue counter wired (A2); `samples.topbar` đã có `#9/31` |
| `crm/docs/ui-spec/screens/S15-task-detail.md` | Provenance block: ghi nhận value + product fields |

## Implementation steps

### Step 1 — Migration + entity + repo (A1 foundation)

1. Tạo `0036_task_claim_context_fields.up.sql`:
   ```sql
   ALTER TABLE crm_task ADD COLUMN value_at_stake_vnd INTEGER;
   ALTER TABLE crm_task ADD COLUMN top_affinity_product TEXT;
   ```
2. `task.py`: thêm 2 optional fields sau `channel`.
3. `task_repository.py`: `_INSERT` thêm 2 placeholder `?,?` (tổng 18 cols); `_UPDATE` thêm 2 SET; `_task_from_row` đọc với `.get()` fallback (tương thích row cũ).

### Step 2 — Service: capture tại claim time (A1)

Trong `claim_customer_actions()` trước khi tạo `Task`:
```python
value_at_stake_vnd = sum(getattr(a, "value_at_stake_vnd", 0) or 0 for a in actions)
best = max(actions, key=lambda a: getattr(a, "value_at_stake_vnd", 0) or 0, default=None)
top_affinity_product = getattr(best, "top_affinity_product", "") or "" if best else ""
```
Set cả hai field trên `Task(...)`.

### Step 3 — Worklist snooze endpoint (A4)

Trong `screen_worklist.py`, sau handle_cancel_task:
```python
@router.patch("/tasks/{task_id}/snooze")
async def handle_snooze_task(request, task_id, days: int = 1):
    # shift due_at = today_ict + days, reset status to open if doing
    # return task row fragment via _wl_row macro or 200 empty for delete swap
```
Pattern tương tự `handle_cancel_task`.

### Step 4 — Template cập nhật (A1 display + A4 snooze button)

`_wl_row.html` — task row section:
- Thêm sau `wl-row__top`: nếu `t.source == 'action_queue_claim'` và có value/product → render inline.
- Thêm snooze `<details>` cùng pattern action row cho `source='action_queue_claim'` rows.

`task_detail.html` — provenance block: hiện `value_at_stake_vnd | fmt_vnd` + `top_affinity_product`.

### Step 5 — Queue counter (A2)

`screen_worklist.py` `_load_worklist_data()`:
```python
queue_party_ids = [
    str(r.payload.party_id)
    for r in ranked_rows
    if r.payload.party_id
][:50]
```
Truyền `queue_party_ids` vào template context.

Worklist template: "Vào chế độ gọi" button đổi thành:
```html
/customers/{{ a.party_id }}/call?queue_ids={{ queue_party_ids | join(',') }}&queue_pos={{ loop.index0 }}
```

`screen_call_cockpit.py` handler: thêm params `queue_ids: str = ""`, `queue_pos: int = 0`. Parse queue, tính `queue_next_party_id = queue[queue_pos+1]` nếu trong range.

`call_cockpit.html` topbar:
```html
{% if queue_total > 0 %}<span class="s14-queue-count">#{{ queue_pos+1 }}/{{ queue_total }}</span>{% endif %}
{% if queue_next_party_id %}
<a href="/customers/{{ queue_next_party_id }}/call?queue_ids=...&queue_pos={{ queue_pos+1 }}">Khách kế →</a>
{% endif %}
```

### Step 6 — Spec updates

Cập nhật S01, S14, S15 per bảng files. Không thay đổi interaction IDs hiện có.
Ghi chú rebuild generated registry sau khi cập nhật spec.

## Tests & validation

| Test | Cách kiểm tra |
|---|---|
| Claim persists value + product | Unit: `claim_customer_actions()` với 3 actions có value [100, 500, 200] → task.value_at_stake_vnd=800, top_affinity_product = product của action 500 |
| Zero value edge case | Tất cả actions có value=0 → task.value_at_stake_vnd=0, top_affinity_product từ action đầu tiên |
| Queue next navigation | `screen_call_cockpit.py`: `queue_ids="a,b,c"&queue_pos=1` → `queue_next_party_id="c"`, counter `#2/3` |
| Queue end | `queue_pos=2` trong list 3 → `queue_next_party_id=None`, nút "Khách kế" không render |
| Snooze shifts due_at | PATCH `/tasks/{id}/snooze?days=3` → task.due_at = today+3, status reset to open |
| Snoozed task leaves B0 | Sau snooze: task không còn trong band 0 (overdue) ở worklist |
| Backward compat | Task rows cũ (columns absent) load không lỗi (`_task_from_row` fallback None) |

## Risks & rollback

- **Migration (ALTER TABLE):** SQLite ALTER TABLE ADD COLUMN an toàn (nullable, no default). Không cần restart app — migration chạy at startup. Rollback: không cần down migration (nullable columns không break existing queries).
- **URL length (A2):** 50 party_ids × 36 chars = ~1800 chars, an toàn dưới 8KB URL limit. Nếu dưới 1000 khách thì queue cũng ≤ 50.
- **Template regression:** `_wl_row.html` là shared macro — test với action row + task row + claim task row. Snooze button chỉ render khi `source='action_queue_claim'`.

## Unresolved questions

1. `task_detail.html` provenance block structure (fragment vs full-page): cần verify path `crm/src/adapters/inbound/web/templates/fragments/task_detail.html` có đúng là block hiển thị source/rationale không, hay là ở `task_detail.html` (full page).
2. Worklist template: confirm `worklist_fragment.html` hay `worklist.html` là nơi render action rows có "Vào chế độ gọi" button (cần truyền `queue_party_ids` từ context).
3. `queue_pos` cho claim task rows (không phải action rows): task rows không có button "Vào chế độ gọi" trong spec hiện tại — confirm A2 chỉ áp dụng cho action rows (📋 Gọi path), không cho task rows.
