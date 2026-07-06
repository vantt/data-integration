# CRM Clean Code Phase 2 — DDD Patterns

**Status:** Done (Phase 1 ✅ | Phase 2 ✅ | Phase 3 ✅ | Phase 4 skipped — optional/low-priority)  
**Branch:** main  
**Created:** 2026-06-29  
**Prerequisite:** Phase 1 done (commit 1f10407 — hexagonal cleanup, shared/timestamps, import standardization)

---

## Scope

Triển khai 4 DDD/clean-code concepts còn lại từ architecture review, ưu tiên theo value/risk:

| # | Concept | File | Priority |
|---|---|---|---|
| 1 | Value Object — `PhoneNumber`, `Email` | phase-01 | Cao |
| 2 | Unit of Work — centralize `commit()` | phase-02 | Trung |
| 3 | Result type — `update_custom()` | phase-03 | Thấp |
| 4 | Light CQRS — split `ProfileService` | phase-04 | Thấp |

---

## Phase 1 — Value Objects: `PhoneNumber` và `Email`

**File:** `plans/260629-1322-crm-clean-code-phase2/phase-01-value-objects.md`

**Vấn đề:**
- `normalize_phone()`, `phone_to_e164()`, `normalize_email()` là free functions trong `application/party_service.py`
- Logic normalization thuộc về chính giá trị đó, không thuộc service
- `Party.primary_phone: str` — có thể gán bất kỳ string nào, không ai validate

**Approach (pragmatic — giữ str trong entity):**
- Tạo `domain/value_objects/phone.py` — `PhoneNumber(frozen=True)` với `normalize()` classmethod
- Tạo `domain/value_objects/email.py` — `Email(frozen=True)` với `normalize()` classmethod  
- Giữ `Party.primary_phone: str` (không thay đổi entity schema → không ảnh hưởng SQLite, không cần migration)
- `PartyService` dùng `PhoneNumber.normalize(raw)` thay vì `normalize_phone(raw)`
- Free functions `normalize_phone`, `phone_to_e164`, `normalize_email` trong `party_service.py` → delegate sang VO hoặc xóa

**Files thay đổi:**
- Tạo: `domain/value_objects/__init__.py`, `domain/value_objects/phone.py`, `domain/value_objects/email.py`
- Sửa: `application/party_service.py` (thay free functions bằng VO calls)

**Không thay đổi:**
- `domain/entities/party.py` — giữ `primary_phone: str` (pragmatic, tránh migration)
- Tất cả callers hiện tại — public API không đổi

---

## Phase 2 — Unit of Work: centralize `commit()`

**File:** `plans/260629-1322-crm-clean-code-phase2/phase-02-unit-of-work.md`

**Vấn đề:**
- 37+ `self._conn.commit()` calls rải rác trong 15 SQLite repos
- Không thể group nhiều operations thành 1 transaction từ service layer
- Ví dụ: `ActivityService.log_activity()` gọi `activity_repo.save()` + `last_contact_repo.upsert()` — hai commit riêng, không atomic

**Approach:**
- Thêm `CRMDatabase.transaction()` context manager (dùng `sqlite3` built-in transaction)
- Xóa `self._conn.commit()` khỏi từng repo method — repos chỉ `execute()`, không `commit()`
- Thêm `commit()` ở cuối mỗi service method (hoặc dùng `with db.transaction():` trong service)
- `DedupRepository.merge()` đã có atomic transaction pattern — giữ nguyên làm reference

**Files thay đổi:**
- Sửa: `adapters/outbound/sqlite/connection.py` — thêm `transaction()` context manager
- Sửa: 15 SQLite repo files — xóa `commit()` calls
- Sửa: Service files cần cross-repo atomicity — wrap với `with db.transaction():`

**Risk:** Medium — nhiều file, dễ miss một `commit()`. Cần test kỹ.

---

## Phase 3 — Result Type: `update_custom()`

**File:** `plans/260629-1322-crm-clean-code-phase2/phase-03-result-type.md`

**Vấn đề:**
- `ProfileService.update_custom()` raise `ValueError` khi validation fail
- Caller phải dùng try/except — exception-driven control flow
- Không rõ error structure từ signature

**Approach (minimal — không dùng thư viện ngoài):**
```python
# domain/result.py
@dataclass
class ValidationResult:
    errors: list[CustomFieldError] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors
```
- `update_custom()` trả về `ValidationResult` thay vì raise
- Caller check `result.ok` — explicit, no exception
- Giữ `CustomFieldError` trong `profile_service.py` hoặc move vào `domain/`

**Files thay đổi:**
- Tạo: `domain/result.py`
- Sửa: `application/profile_service.py` — `update_custom()` trả `ValidationResult`
- Sửa: callers của `update_custom()` (HTTP handler, web screen)

**Scope nhỏ** — chỉ ảnh hưởng `update_custom()`, không lan rộng.

---

## Phase 4 — Light CQRS: split `ProfileService`

**File:** `plans/260629-1322-crm-clean-code-phase2/phase-04-light-cqrs.md`

**Vấn đề:**
- `ProfileService` làm cả read (get_party_360, get_profile, list_notes...) lẫn write (upsert_profile, attach_tag, add_note...)
- Một số callers chỉ cần đọc nhưng nhận dependency đầy đủ

**Approach (naming-based split, không tách class):**
- Option A (nhẹ): Thêm type alias Protocol `ProfileReader` và `ProfileWriter` — callers type-hint theo role
- Option B (đầy đủ): Tách `ProfileQueryService` và `ProfileCommandService`, giữ `ProfileService` là re-export facade

**Khuyến nghị:** Option A trước — có ngay benefit về type expressiveness, không cần refactor lớn.

**Ưu tiên thấp** — scale hiện tại (10 users, single SQLite) không cần. Làm sau Phase 1-3.

---

## Thứ tự triển khai

```
Phase 1 (Value Objects)  ← làm trước, không phụ thuộc gì
    ↓
Phase 2 (Unit of Work)   ← làm sau Phase 1, nhiều file nhất
    ↓
Phase 3 (Result Type)    ← độc lập, có thể song song Phase 2
    ↓
Phase 4 (Light CQRS)     ← làm sau cùng, optional
```

## Acceptance criteria chung

- `docker compose restart crm` → healthy, `/healthz` 200
- Existing tests pass (`pytest crm/src/tests/`)
- Không thay đổi SQLite schema (không cần migration)
- Không thay đổi public API (HTTP endpoints giữ nguyên)
