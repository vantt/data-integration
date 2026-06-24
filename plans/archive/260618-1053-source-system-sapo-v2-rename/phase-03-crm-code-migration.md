# Phase 3: CRM Code + SQLite Data Migration

**Priority:** P1  
**Status:** DONE  
**Depends on:** Phase 1 (docs)  
**Parallel với:** Phase 2, Phase 4  

## Overview

Hai việc phải làm **atomic cùng nhau**: đổi code Python + migrate data trong `crm.db`.  
Nếu chỉ đổi code mà không migrate data → existing rows vẫn có `source_system='sapo'` → inconsistency.

## Files cần thay đổi

### Python code

| File | Dòng | Thay đổi |
|---|---|---|
| `crm/src/adapters/outbound/sqlite/party_repository.py` | 215 | `"sapo"` → `"sapo_v2"` |
| `crm/src/application/party_service.py` | 127 | `"sapo"` → `"sapo_v2"` |
| `crm/src/domain/entities/party.py` | 111 | Comment: `# sapo_v2\|messenger\|zalo\|manual` |
| `crm/src/tests/test_domain_entities.py` | 63 | `source_system="sapo"` → `"sapo_v2"` |

### SQLite migration (tạo mới)

File: `crm/migrations/00XX_rename_source_system_sapo_to_sapo_v2.up.sql`  
(XX = số thứ tự tiếp theo sau migration hiện tại cao nhất)

```sql
-- Migration XXXX UP: rename source_system 'sapo' → 'sapo_v2' in crm_party_identity
-- Reason: source_system is a combined {system}_{version} identifier; bare 'sapo' is ambiguous.

UPDATE crm_party_identity
SET source_system = 'sapo_v2'
WHERE source_system = 'sapo';

-- Update party_external_id if exists and has sapo rows
UPDATE crm_party_external_id
SET source_system = 'sapo_v2'
WHERE source_system = 'sapo';
```

**Cần verify trước:** số migration hiện tại cao nhất để đặt tên đúng.  
```bash
ls crm/migrations/*.up.sql | sort | tail -3
```

### Migration comments

- `crm/migrations/0002_party_identity_golden_record.up.sql` dòng 31: update comment
- `crm/migrations/0009_party_external_id.up.sql` dòng 8: update comment

## Implementation Steps

1. Check số migration hiện tại cao nhất
2. Edit 4 Python files
3. Tạo migration file mới
4. Update 2 migration comments
5. Verify: `SELECT DISTINCT source_system FROM crm_party_identity` sau khi apply migration

## Success Criteria

- [x] `grep -r '"sapo"' crm/src/` → 0 kết quả liên quan đến source_system
- [x] Migration apply thành công không lỗi
- [ ] `SELECT source_system, COUNT(*) FROM crm_party_identity GROUP BY 1` chỉ còn `sapo_v2`
- [ ] Tests pass: `python -m pytest crm/src/tests/`
