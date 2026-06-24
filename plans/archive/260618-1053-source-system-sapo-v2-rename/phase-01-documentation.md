# Phase 1: Documentation & LLM Hints

**Priority:** P0 — làm trước tất cả  
**Status:** DONE  
**Depends on:** nothing  

## Overview

Update tất cả docs hiện tại đang document sai convention, tạo anchor doc cho convention mới, inject hint vào AGENTS.md để agent không nhầm.

## Files cần thay đổi

### 1. `docs/architecture/naming-conventions.md` (UPDATE)

Dòng 45 hiện tại:
```
source_system ('sapo', 'misa', 'shopee'), source_version ('v2' / 'v3')
```
Đổi thành:
```
source_system = combined identifier '{system}_{version}' — e.g. 'sapo_v2', 'sapo_v3', 'shopify_v1'.
Không có cột source_version riêng. Version là load-bearing cho logic mapping.
```

### 2. `docs/architecture/std-layer-conventions.md` (UPDATE)

Dòng 20 hiện tại document: `'sapo' AS source_system` và `'v2' AS source_version`.  
Đổi thành: `'sapo_v2' AS source_system` (loại bỏ source_version hoàn toàn).

### 3. `docs/architecture/order-pl/order-pl-schema-design.md` (UPDATE)

Dòng 80: `-- 'sapo' | 'misa' | 'shopee' | ...` → `-- 'sapo_v2' | 'misa' | 'shopee' | ...`

### 4. `transformation/docs/TAG_HANDLING.md` (UPDATE)

Thêm section ngắn về `source_system` convention khi mô tả tag flow.

### 5. `AGENTS.md` (UPDATE — inject hint)

Thêm vào section data conventions hoặc "Common Pitfalls":

```markdown
## source_system Convention (IMPORTANT for agents)

`source_system` = `{system}_{version}` — combined identifier.  
- ✅ `'sapo_v2'` — Sapo API v2 ingestion  
- ✅ `'sapo_v3'` — Sapo API v3 (future)  
- ❌ `'sapo'` — WRONG, bare name without version is meaningless for mapping logic  
- ❌ `'sapo'` + separate `source_version = 'v2'` column — also WRONG, no such column exists  

**Never use bare `'sapo'` as a source_system value anywhere in code or SQL.**
```

### 6. Tạo mới: `docs/decisions/014-source-system-combined-identifier.md`

ADR documenting the decision to use combined `{system}_{version}` identifier.  
Format chuẩn theo các ADR hiện có trong `docs/decisions/`.

## Implementation Steps

1. Đọc file hiện tại trước khi edit (bắt buộc)
2. Update `naming-conventions.md`
3. Update `std-layer-conventions.md`
4. Update `order-pl-schema-design.md`
5. Update `TAG_HANDLING.md`
6. Update `AGENTS.md`
7. Tạo `014-source-system-combined-identifier.md`

## Success Criteria

- [ ] Không còn `source_version` xuất hiện trong docs hiện hành
- [ ] `AGENTS.md` có warning rõ về bare `'sapo'`
- [ ] ADR mới tồn tại với rationale đầy đủ
- [ ] Grep `'sapo'` trong docs không còn entry nào là value chuẩn (chỉ còn trong ví dụ sai/archive)
