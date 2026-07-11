# Phase 03 — HTTP Endpoint + Wiring + Tests

**Priority:** P0 · **Status:** ⬜ · Depends: Phase 01, 02.

## Overview
Expose `GET /api/parties/{id}/approach-script` + wire repo vào app. Đây là **contract `ui-port` consume**. Mirror `insight_handler.py`.

## Requirements
- Resolve party→customer_id qua `sapo_customer` identity (giống insight).
- Graceful-empty: không có script → `{"script": null}` HTTP 200. Không có identity → 404.
- Response: `{ "script": <data dict> | null, "meta": { "recommended": bool, "confidence": str|null, "refreshed_at": str } }`.

## Related code files
- **Create** `crm/src/adapters/inbound/http/approach_script_handler.py`
- **Modify** `crm/src/composition.py` — khởi tạo repo + wire router + include_router
- **Create** `crm/tests/adapters/inbound/http/test_approach_script_handler.py`

## Implementation steps
1. Handler theo pattern insight:
   - module-level `_party_repo`, `_approach_repo`; `wire_approach_script_router(party_repo, approach_repo)`; `_repos()` guard.
   - `@router.get("/parties/{party_id}/approach-script")`:
     - `list_identities(party_id)` → tìm `identity_type=="sapo_customer"` → `int(identity_value)`
     - không có → `HTTPException(404)`
     - `script = approach_repo.get_by_customer_id(customer_id)`
     - `None` → `{"script": null, "meta": null}` (200)
     - else → `{"script": script.data, "meta": {recommended, confidence, refreshed_at}}`
2. `composition.py`:
   - `scripts_dir = os.getenv("CRM_APPROACH_SCRIPT_DIR", os.path.join(data_dir, "approach_scripts"))`
   - `approach_repo = FileApproachScriptRepository(scripts_dir)`
   - `wire_approach_script_router(party_repo, approach_repo)` + `app.include_router(approach_script_handler.router)`

## Tests (FastAPI TestClient)
- party có `sapo_customer` + file tồn tại → 200, `script` đúng, `meta.recommended` đúng.
- party không có identity → 404.
- party hợp lệ nhưng không có file → 200 `{"script": null}`.

## Todo
- [ ] handler + wiring trong composition
- [ ] tests 3 case
- [ ] restart CRM container (handler load lúc startup), curl thử 1 customer_id thật

## Success criteria
- `curl /api/parties/{id}/approach-script` trả JSON đúng cho khách pilot; 404/null đúng nhánh.

## Risks
- Reuse helper resolve identity: KISS — copy vòng lặp nhỏ từ insight, hoặc tách `_resolve_customer_id(party_repo, party_id)` dùng chung (cân nhắc, đừng over-abstract).
- Router phải `return router` / include đúng — lỗi im lặng nếu quên (xem cảnh báo trong screen_hug_*).
