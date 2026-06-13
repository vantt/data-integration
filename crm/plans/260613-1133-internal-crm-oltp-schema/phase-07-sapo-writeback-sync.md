# Phase 07 — Sapo 2-Chiều Write-Back (GATED)

**Context:** [plan.md](plan.md) · Report: `../reports/schema-scan-260613-1133-raw-serving-semantic-integration-report.md`

## Overview
- **Priority:** P2 — **hoãn sau v1** (user xác nhận làm sau)
- **Status:** ⬜ Deferred
- Đẩy một số field enrichment/chuẩn hoá từ CRM ngược về Sapo qua Sapo API (**user xác nhận CÓ API cho order + customer**), theo **transactional outbox** + **hexagonal outbound adapter** (`adapters/outbound/sapo`).

## Key Insights
- **API tồn tại** (order + customer) — khác với scan ban đầu (repo chỉ có code GET read-only). Nhưng **field nào ghi được vẫn cần xác nhận** (tags/notes/customer_group format) → vẫn nên spike nhẹ trước khi bật từng field.
- Triển khai kiểu **hexagonal**: domain phát "enrichment changed" → port `SapoWriter` → adapter gọi API. Đổi/đóng Sapo không ảnh hưởng domain.
- Nếu field mong muốn không ghi được → enrichment ở lại CRM (fallback), không ảnh hưởng v1.
- Khoá gọi API: `customer_id` (natural Sapo) lưu ở `crm_party_identity (sapo_customer)`.

## Requirements
- **FR:** chọn cấu hình field nào của CRM map sang field nào của Sapo; outbox ghi thay đổi → worker gọi API có retry/backoff; log request/response; idempotent; conflict-aware (không đè update mới hơn từ Sapo).
- **NFR:** at-least-once + idempotent key; rate-limit; không chặn ghi CRM nếu Sapo down (eventual).

## Architecture
### Bước 0 — API Capability Spike (làm TRƯỚC)
```
crm/spikes/sapo_writeback_probe.py
  - xác thực credential admin có scope WRITE?
  - thử PUT customer: tags, note, customer_group — field nào nhận?
  - ghi nhận: endpoint, field writable, format, rate-limit, lỗi
  → Output: bảng "Sapo writable fields" (xác nhận thực tế) → quyết định scope Phase 07
```
### Core DDL (sau spike)
> Map **SQLite** theo Quy ước [plan.md](plan.md): `crm_*` prefix, `uuid`→`TEXT`, `timestamptz`→`TEXT` UTC, `payload jsonb`→`TEXT`+JSON1, ở `crm.db`. Outbox poll dùng index `(status, created_at)`.
```sql
CREATE TABLE crm.sapo_writeback_map (
  field_key text PRIMARY KEY,       -- crm field (tag/note/group/custom.x)
  crm_source text NOT NULL,         -- party_tag|note|customer_profile.custom.x
  sapo_endpoint text NOT NULL,      -- PUT /admin/customers/{id}.json
  sapo_field text NOT NULL,
  enabled boolean DEFAULT false     -- bật theo kết quả spike
);
CREATE TABLE crm.sync_outbox (
  outbox_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  entity_type text NOT NULL,        -- party
  entity_id uuid NOT NULL,
  target_system text NOT NULL DEFAULT 'sapo',
  operation text NOT NULL,          -- update_customer
  payload jsonb NOT NULL,
  idempotency_key text UNIQUE,
  status text NOT NULL DEFAULT 'pending',  -- pending|sent|failed|skipped
  attempts int DEFAULT 0, last_error text,
  created_at timestamptz NOT NULL DEFAULT now(),
  sent_at timestamptz
);
CREATE TABLE crm.sync_log (
  log_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  outbox_id uuid REFERENCES crm.sync_outbox(outbox_id),
  request jsonb, response jsonb, status_code int,
  at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ON crm.sync_outbox (status, created_at);
```
### Worker
```
crm/sync/sapo_writeback_worker.py  (hoặc Go)
  poll outbox(status=pending) → build payload theo writeback_map(enabled)
  → gọi Sapo API → success: sent; lỗi: attempts++, backoff; >N: failed
  conflict guard: so modified_on Sapo > thời điểm CRM đổi → skip + cảnh báo
```

## Related Code Files
- **Tạo:** `crm/spikes/sapo_writeback_probe.py` (TRƯỚC), `crm/migrations/0010_sapo_writeback_outbox.up.sql`, `crm/sync/sapo_writeback_worker.py`, trigger điền outbox khi tag/note/custom đổi.
- **Đọc:** `ingestion/` Sapo source (base URL, auth, rate-limit), `docs/context/sapo-platform.md`.

## Implementation Steps
1. **Spike** xác nhận field writable (chặn các bước sau).
2. Migration 0010 (outbox + map + log) — chỉ bật field spike xác nhận.
3. Trigger/app-logic: thay đổi enrichment được duyệt → chèn `sync_outbox`.
4. Worker: poll → call API → retry/backoff → log.
5. Conflict guard theo `modified_on` Sapo.
6. Dashboard nhỏ: outbox pending/failed.

## Todo
- [ ] **Spike API Sapo (BẮT BUỘC trước)**
- [ ] Migration 0010
- [ ] Outbox enqueue trigger
- [ ] Worker retry/backoff
- [ ] Conflict guard
- [ ] Monitor outbox

## Success Criteria
- Spike trả bảng field writable rõ ràng; đổi tag CRM (field enabled) → outbox → Sapo nhận đúng; retry khi lỗi tạm; không đè update Sapo mới hơn; field chưa xác nhận giữ `enabled=false`.

## Risk Assessment
- **Sapo không cho ghi / field giới hạn** (cao) → fallback enrichment-only ở CRM; KHÔNG chặn v1. Cần **câu hỏi mở #1** (credential write).
- **Vòng lặp sync** (Sapo→warehouse→CRM→Sapo) → conflict guard + chỉ ghi field CRM-owned, không ghi field do warehouse tính.
- **Rate-limit Sapo** → batch + backoff.

## Security
- Chỉ field được duyệt + `enabled` mới ghi. Credential write scope tối thiểu. Log đầy đủ payload (ẩn PII nhạy cảm nếu cần).

## Next Steps
- Sau v1: cân nhắc luồng CRM enrichment → warehouse (re-analysis) — câu hỏi mở #4.
- Mở rộng write-back sang order/note nếu spike cho phép.
