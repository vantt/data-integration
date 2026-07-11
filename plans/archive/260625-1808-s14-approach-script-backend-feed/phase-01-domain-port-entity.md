# Phase 01 — Domain Entity + Port

**Priority:** P0 · **Status:** ⬜ · Nền tảng cho mọi phase sau.

## Overview
Định nghĩa entity `ApproachScript` + port `ApproachScriptRepository`. Không phụ thuộc backend (file/db).

## Key insight
Entity giữ `data: dict` (parsed JSON nguyên vẹn) thay vì map từng field — vì schema kịch bản **còn đang đổi** khi test. Chỉ rút vài field cần cho gate/queue/freshness.

## Requirements
- Entity bất biến (frozen dataclass), serialize được ra JSON cho HTTP.
- Port là `Protocol` (giống `domain/ports/cache_repository.py`).

## Related code files
- **Create** `crm/src/domain/entities/approach_script.py`
- **Create** `crm/src/domain/ports/approach_script_repository.py`

## Implementation steps
1. `ApproachScript` (frozen dataclass):
   - `customer_id: int`
   - `data: dict` — full parsed JSON (profile_read, value_assessment, opportunity, risk, approach{...}, confidence, data_gaps, recommended)
   - `recommended: bool` — rút từ `data["approach"]["recommended"]` (default True nếu thiếu)
   - `confidence: str | None` — `data.get("confidence")`
   - `refreshed_at: str` — ISO-8601 (UTC) lúc file mtime; UI hiển thị ICT (R6)
   - `model: str | None`, `template_version: str | None` (optional meta)
   - classmethod `from_json(customer_id, data, refreshed_at, ...)` để build + rút field an toàn (try/except quanh truy cập lồng).
2. `ApproachScriptRepository(Protocol)`:
   - `def get_by_customer_id(self, customer_id: int) -> ApproachScript | None: ...`

## Todo
- [ ] entity `approach_script.py` + `from_json`
- [ ] port `approach_script_repository.py`
- [ ] compile check (`python -c "import ..."` trong container/venv)

## Success criteria
- Import sạch, `from_json` rút đúng `recommended`/`confidence` từ payload mẫu (ca 03 Leflair → recommended=False).

## Risks
- Schema đổi → vì giữ `data: dict` nên chỉ `from_json` cần chỉnh khi đổi field rút; entity ổn định.
