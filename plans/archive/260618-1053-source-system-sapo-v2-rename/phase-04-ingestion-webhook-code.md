# Phase 4: Ingestion + Webhook Consumer Code

**Priority:** P1  
**Status:** CODE_DONE_AWAIT_DEPLOY  
**Depends on:** Phase 1 (docs)  
**Parallel với:** Phase 2, Phase 3  

## Overview

Hai subsystem cần đổi `'sapo'` → `'sapo_v2'`:
- `ingestion/` — cookie manager dùng `'sapo'` làm source key
- `webhook_consumer/cloudflared1_consumer/` — realtime consumer filter `SOURCE_SYSTEM = "sapo"`

**Webhook là realtime consumer** (while-loop poll D1 liên tục, queue depth ≈ 0 bình thường).  
Không có historical data migration. Cutover đơn giản: switch sender → stop → deploy → start.

## Files cần thay đổi

### Ingestion

| File | Dòng | Thay đổi |
|---|---|---|
| `ingestion/src/sapo/client.py` | 64 | `get_cookie_manager('sapo', ...)` → `get_cookie_manager('sapo_v2', ...)` |
| `ingestion/src/utils/shared_cookie_manager.py` | 58 | `source='sapo'` → `source='sapo_v2'` |
| `ingestion/src/utils/shared_cookie_manager.py` | 84 | Update docstring example `'sapo'` → `'sapo_v2'` |

**Lưu ý cookie store:** Kiểm tra cơ chế lưu cookie trong `shared_cookie_manager` trước khi đổi key — nếu persist theo tên key trên disk/DB cần rename entry cũ để không mất session.

### Webhook Consumer — cloudflared1

| File | Dòng | Thay đổi |
|---|---|---|
| `webhook_consumer/cloudflared1_consumer/src/main.py` | 11 | `SOURCE_SYSTEM = "sapo"` → `SOURCE_SYSTEM = "sapo_v2"` |

### Dead code — archive hoặc xoá

Supabase DDL files không còn được dùng (hệ thống đã chuyển sang Cloudflare D1):
- `webhook_consumer/supabase_consumer/src/sql/ddl/webhook_logs.sql`
- `webhook_consumer/supabase_consumer/src/sql/ddl/webhook_logs_duplicated.sql`

→ Thêm comment `-- ARCHIVED: system migrated to Cloudflare D1` hoặc move vào `archive/`

## Webhook Cutover Sequence

Consumer đang chạy realtime — cần phối hợp với user:

```
[Dev] Commit code mới (SOURCE_SYSTEM = "sapo_v2") nhưng CHƯA deploy

[User] Switch Sapo sender → source_system='sapo_v2'
       (Sapo ngừng gửi 'sapo', D1 drain tự nhiên trong ~10 giây)

[Dev] Stop consumer → deploy code mới → start consumer
      (window này vài giây, backlog nhỏ, xử lý ngay khi start)
```

**Không cần drain step, không có data migration, không có constraint change.**

## Implementation Steps

1. Kiểm tra cookie store mechanism trong `shared_cookie_manager.py`
2. Edit 3 ingestion files
3. Edit `main.py` consumer
4. Archive Supabase DDL files
5. Coordinate với user: user switch sender → dev deploy consumer (cùng lúc)

## Success Criteria

- [x] `grep -r "'sapo'" ingestion/src/` → 0 kết quả liên quan source_system
- [ ] Cookie không bị mất session sau khi deploy  *(requires manual rename of sapo_cookies.json → sapo_v2_cookies.json before deploy, or accept re-login — see concerns)*
- [ ] Consumer nhận được messages với `source_system='sapo_v2'` sau cutover
- [ ] Không còn messages `'sapo'` trong D1 sau ~30 giây cutover
