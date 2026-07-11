# M05 No-Party Route & Redirect Handling — Research Summary

## 1. Confirmed 404 Bug in Worklist

**Status**: CONFIRMED, current state verified.

- **File**: `crm/src/adapters/inbound/web/templates/worklist.html:26`
  ```html
  <button class="btn btn--primary"
          hx-get="/modals/m05?return_to=stay"
          hx-target="#modal-root"
          hx-swap="innerHTML">
    {% include "icons/plus.svg" %} Tạo task
  </button>
  ```
  Button sends `?return_to=stay` but **NO `party_id` param**.

- **File**: `crm/src/adapters/inbound/web/templates/fragments/modal_m05_create_task.html:43`
  ```html
  <form hx-post="/customers/{{ party_id }}/tasks" ...>
  ```
  Create-mode form posts to `/customers/{{ party_id }}/tasks`. With empty `party_id` → posts to `/customers//tasks` → 404 (no matching route).

**Fix path**: Either pass `party_id` from worklist context OR route create-mode to `/tasks` (no path param) when party_id is absent.

---

## 2. Alternative Route Analysis: `/tasks` Handler

**File**: `crm/src/adapters/inbound/web/screen_tasks_board.py:131–163`

### Handler Signature
```python
@router.post("/tasks", response_class=HTMLResponse)
async def handle_create_task(
    request: Request,
    title: str = Form(...),
    description: str = Form(default=""),
    due_at: str = Form(default=""),
    party_id: str = Form(default=""),
    assignee_user_id: str = Form(default=""),
) -> Response:
```

### Form Parameters Accepted by `/tasks`
- `title` (required)
- `description` (optional, defaults "")
- `due_at` (optional, defaults "")
- `party_id` (optional, defaults "")
- `assignee_user_id` (optional, defaults "")

### Form Parameters Sent by M05 Create-Mode (modal_m05_create_task.html)
Reading all `name=` attributes:
- **Line 57**: `<input type="text" name="title" ...>` ✓ accepted
- **Line 67**: `<select name="task_party_display" disabled ...>` ✗ **NOT accepted by /tasks**
- **Line 88**: `<select name="task_kind">` ✗ **NOT accepted by /tasks**
- **Line 113**: `<input type="hidden" name="due_at" ...>` ✓ accepted
- **Line 137**: `<select name="priority">` ✗ **NOT accepted by /tasks**
- **Line 154**: `<select name="assignee_user_id">` ✓ accepted
- **Line 217**: `<textarea name="description" ...>` ✓ accepted
- **Line 44** (create mode): `<input type="hidden" name="party_id" ...>` ✓ accepted
- **Line 45** (create mode): `<input type="hidden" name="return_to" ...>` ✗ **NOT accepted by /tasks**
- **Line 47** (optional): `<input type="hidden" name="source" ...>` ✗ **NOT accepted by /tasks**
- **Line 48** (optional): `<input type="hidden" name="source_ref" ...>` ✗ **NOT accepted by /tasks**

### Field Name Mismatches
1. **task_party_display** (M05 sends, hardcoded form field) — `/tasks` ignores it entirely
2. **priority** (M05 line 137) — `/tasks` ignores; handler hardcodes `priority: 0` (line 149)
3. **task_kind** (M05 line 88 or 103) — `/tasks` ignores; handler hardcodes `source: "manual"` (line 148) and does NOT derive task_kind
4. **source** + **source_ref** (M05 optional lines 47–48) — `/tasks` ignores
5. **return_to** (M05 line 45) — `/tasks` ignores completely

### Verdict
`/tasks` endpoint accepts **subset** of M05's fields. **Cannot be drop-in replacement** without template changes and/or handler updates.

---

## 3. `/tasks` Handler Response & Redirect Behavior

**File**: `crm/src/adapters/inbound/web/screen_tasks_board.py:160–163`

```python
try:
    task_creator.create_task(task_data)
except Exception as exc:
    log.error("create task: %s", exc)
    return HTMLResponse("failed to create task", status_code=500)
return Response(
    status_code=200,
    headers={"HX-Trigger": '{"closeModal":true}', "HX-Redirect": "/tasks"},
)
```

### Response Behavior
- **On success**: Returns 200 with headers:
  - `HX-Trigger: {"closeModal":true}` — closes modal
  - `HX-Redirect: /tasks` — **hard redirect to /tasks board**
- **On failure**: 500 with error message
- **`return_to` handling**: **NONE**. Always redirects to `/tasks` (hardcoded).

### Comparison to POST /customers/{party_id}/tasks

**File**: `crm/src/adapters/inbound/web/screens/modals/screen_modal_task.py:190–192`

```python
if return_to == "stay":
    return HTMLResponse("", status_code=200, headers={"HX-Trigger": '{"worklistRefresh": true}'})
redirect = f"/customers/{party_id}?tab=tasks" if party_id else "/tasks"
return Response(status_code=200, headers={"HX-Redirect": redirect})
```

The `/customers/{party_id}/tasks` handler:
- **Respects `return_to="stay"`**: Refreshes worklist without redirect (line 141–142)
- **Supports `return_to="redirect"`** (default): Redirects to customer profile or `/tasks` (line 143–144)

### Regression Risk
Routing no-party case to `/tasks` would **LOSE `return_to=stay` support** already shipped for the party case. Worklist "stay in place" fix (from prior session) would not apply to no-party creates.

---

## 4. Existing Test File Location & Pattern

**Test file found**: `crm/src/tests/test_quick_outcome_cockpit_post.py`

### Test Coverage Status
- **`post_task` / `patch_task_edit`**: **NO existing tests** in the codebase.
- The test file covers activity disposition, not task creation/editing.

### Closest Existing Test Pattern

**File**: `crm/src/tests/test_quick_outcome_cockpit_post.py:28–49` (handler recovery)

```python
def _get_log_activity_handler(activity_log_mock, task_svc=None, profile=None):
    """Register the routes on a mock router and recover handle_log_activity."""
    import crm.src.adapters.inbound.web.screens.customer360.screen_customer_360_activity as mod

    router_mock = MagicMock()
    templates_mock = MagicMock()

    mod.register_activity_routes(
        router_mock,
        templates_mock,
        profile=profile or MagicMock(),
        identities=MagicMock(),
        notes=MagicMock(),
        activity_log=activity_log_mock,
        task_svc=task_svc,
        app_users=None,
        action_state=None,
    )

    post_decorator_calls = router_mock.post.return_value.call_args_list
    assert len(post_decorator_calls) >= 1, "Expected at least one POST handler"
    return post_decorator_calls[0].args[0]
```

### Test Invocation Pattern

**File**: `crm/src/tests/test_quick_outcome_cockpit_post.py:121–140` (example test)

```python
def test_call_cockpit_source_returns_fragment_no_redirect():
    import asyncio

    activity_log_mock = MagicMock()
    activity_log_mock.log_activity.return_value = MagicMock(activity_id="act-cockpit-1")

    handler = _get_log_activity_handler(activity_log_mock)

    response = asyncio.run(handler(**_base_kwargs(
        contact_outcome="no_answer",
        source="call_cockpit",
    )))

    assert "HX-Redirect" not in response.headers, (
        "call_cockpit source must NOT redirect — outcome bar swaps a small fragment"
    )
```

### Pattern Summary
1. **Import the screen module** and call its factory function (`make_task_modal_router` in this case)
2. **Pass MagicMock implementations** of all dependencies (TaskSvc, ProfileSvc, AppUserRepo, templates)
3. **Extract the handler** from the router's decorator call_args_list
4. **Invoke via `asyncio.run(handler(...))`** with explicit keyword arguments
5. **Assert on response headers and body** (for HTML responses, use `.body.decode("utf-8")`)

### Fixture Setup for M05 Tests
For `post_task` (line 147–192 in screen_modal_task.py):

```python
def _get_task_modal_handler():
    from adapters.inbound.web.screens.modals.screen_modal_task import make_task_modal_router
    router_mock = MagicMock()
    templates_mock = MagicMock()
    
    make_task_modal_router(
        templates_mock,
        profile=MagicMock(),  # ProfileSvc
        task_svc=MagicMock(),  # TaskSvc
        app_users=MagicMock(),  # AppUserRepo
    )
    
    # Extract POST handler (line 146: @router.post("/customers/{party_id}/tasks"))
    post_calls = router_mock.post.return_value.call_args_list
    # Find the handler for "/customers/{party_id}/tasks" route
    return post_calls[X].args[0]  # where X is the decorator index
```

---

## 5. M05 Customer Field UI — Picker or Read-Only?

**File**: `crm/src/adapters/inbound/web/templates/fragments/modal_m05_create_task.html:63–81`

```html
{# ── Khách hàng (optional) ── #}
<label class="field">
  <span class="field__label">Khách hàng</span>
  <div class="inp-sel">
    <select name="task_party_display" disabled style="pointer-events:none">
      {% if party_id and party_name %}
      <option value="{{ party_id }}" selected>{{ party_name }}</option>
      {% else %}
      <option value="">— (không gắn)</option>
      {% endif %}
    </select>
    <span class="inp-sel__chev" aria-hidden="true">
      <svg width="11" height="11" viewBox="0 0 12 12" fill="none"
           stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
        <path d="M2 4l4 4 4-4"/>
      </svg>
    </span>
  </div>
</label>
```

### UI Status
- **`disabled` attribute**: Disabled
- **`style="pointer-events:none"`**: Unclickable
- **Display logic**: Shows `party_name` if `party_id` exists, else "— (không gắn)" (unlinked)
- **No picker**: NO search field, NO multiselect, NO dynamic customer lookup UI

### Verdict
M05's customer field is **READ-ONLY display only**. Adding a customer picker would require **NEW UI development** (search input, autocomplete, selection logic). Not just a simple routing fix.

---

## Summary of Minimal Changes Needed

### Option A: Route to `/tasks` (simplest, loses stay-in-place)
1. Template: Conditional `hx-post` target: `{% if party_id %}/customers/{{ party_id }}/tasks{% else %}/tasks{% endif %}`
2. Handler `/tasks`: Accept `return_to` param and honor it (like `/customers/{party_id}/tasks` does)
3. Handler `/tasks`: Accept `priority`, `task_kind`, `source`, `source_ref` OR strip them from form before posting
4. **Regression**: Worklist no-party creates won't stay in place (hardcoded `HX-Redirect: /tasks`)

### Option B: Route to `/customers/{party_id}/tasks` (preserves stay-in-place, requires customer)
1. Template: Require customer selection when opening from worklist OR prefill from context
2. Worklist button: Pass `party_id` from current row context (if exists) or open customer-picker first
3. **UI work**: Customer picker for no-party case

### Option C: Hybrid (stay + no-party)
1. Both handlers coexist: `/tasks` for no-party (updated per Option A), `/customers/{party_id}/tasks` for with-party
2. M05 template: Conditional routing based on party_id presence
3. `/tasks` updated to support `return_to`, accept optional missing fields gracefully

---

## Unresolved Questions

- Does worklist context provide `party_id` from the current row (if row selected) or only on demand? (Affects whether Option B's prefill is feasible)
- Is the "stay in place" behavior desired for no-party creates, or is redirecting to `/tasks` acceptable for that flow?
- Should `/tasks` derive `task_kind` from context (like `/customers/{party_id}/tasks` does via `derive_task_kind()`), or is "manual" source sufficient?
