# Phase 02 — File Adapter + Tests

**Priority:** P0 · **Status:** ⬜ · Depends: Phase 01.

## Overview
`FileApproachScriptRepository` đọc `{scripts_dir}/{customer_id}.json`, parse → `ApproachScript`. Read-only, không ghi.

## Requirements
- Lookup O(1) theo tên file `{customer_id}.json`.
- Graceful: file thiếu → `None`; JSON hỏng → log warning + `None` (KHÔNG raise, để màn hiện empty state ST-CALL-NO-SCRIPT).
- `refreshed_at` = file mtime → ISO-8601 UTC.

## Related code files
- **Create** `crm/src/adapters/outbound/file/__init__.py`
- **Create** `crm/src/adapters/outbound/file/approach_script_file_repository.py`
- **Create** `crm/tests/adapters/outbound/file/test_approach_script_file_repository.py`

## Implementation steps
1. `FileApproachScriptRepository(scripts_dir: str | Path)`:
   - `get_by_customer_id(cid)`: `p = scripts_dir / f"{cid}.json"`; `if not p.exists(): return None`
   - đọc + `json.loads`; bọc try/except → log + `None` khi lỗi/đọc fail
   - `refreshed_at = datetime.utcfromtimestamp(p.stat().st_mtime).isoformat()+"Z"`
   - `return ApproachScript.from_json(cid, data, refreshed_at)`
2. Implements port `ApproachScriptRepository` (Protocol — duck-typed, không cần kế thừa).

## Tests (pytest, dùng tmp_path)
- found: ghi `{cid}.json` hợp lệ → trả entity, `recommended` đúng.
- missing: cid không có file → `None`.
- malformed: file JSON rác → `None` (không raise) + log.
- mtime → `refreshed_at` không rỗng.
- ca Leflair (recommended=false trong data) → entity.recommended == False.

## Todo
- [ ] adapter `approach_script_file_repository.py`
- [ ] tests (4-5 case)
- [ ] `pytest crm/tests/.../test_approach_script_file_repository.py` xanh

## Success criteria
- Tất cả test pass; đọc 1 file pilot thật ra entity đúng.

## Risks
- Encoding: đọc `encoding="utf-8"` (tên/lời thoại tiếng Việt).
- customer_id kiểu: file tên theo int; entity `customer_id:int` — cast nhất quán.
