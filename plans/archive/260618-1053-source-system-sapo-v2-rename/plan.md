# Plan: source_system `sapo` → `sapo_v2` rename

**Status:** Draft  
**Date:** 2026-06-18  
**Branch:** main  

## Mục tiêu

Chuẩn hoá `source_system` convention: `{system}_{version}` (e.g. `sapo_v2`, `sapo_v3`, `shopify_v1`).  
Bare `'sapo'` không còn tồn tại ở bất kỳ đâu trong codebase.

## Design Decision

`source_system` = **combined identifier** = tên hệ thống + version API/ingestion.  
Không có cột `source_version` riêng. Version là load-bearing cho mapping logic.

| Giá trị | Ý nghĩa |
|---|---|
| `sapo_v2` | Sapo POS, ingestion qua API v2 |
| `sapo_v3` | Sapo POS, ingestion qua API v3 (tương lai) |
| `misa` | MISA AMIS |
| `shopee` | Shopee marketplace |

**Đổi toàn bộ sapo* prefix trong source_system:**
- `'sapo_mac'` → `'sapo_v2_mac'`
- `'sapo_mac+misa'` → `'sapo_v2_mac+misa'`

**Giữ nguyên (không phải source_system identifier):**
- `address_source = 'sapo_sync'` — flag cách địa chỉ được set
- `identity_type = 'sapo_customer'` — tên loại identity

## Phases

| # | Phase | Status | Mô tả |
|---|---|---|---|
| 1 | [Documentation & LLM hints](phase-01-documentation.md) | DONE | Update docs, AGENTS.md, convention anchor |
| 2 | [Warehouse SQL models](phase-02-warehouse-sql.md) | DONE | std_*.sql (13 files) + fact_order_costs |
| 3 | [CRM code + SQLite migration](phase-03-crm-code-migration.md) | DONE | Python code + data migration crm.db |
| 4 | [Ingestion + Webhook consumer code](phase-04-ingestion-webhook-code.md) | DONE | client.py + cloudflared1 consumer; webhook switched + Dagster realtime job verified |
| 5 | ~~Supabase webhook DB migration~~ | REMOVED | Hệ thống không dùng Supabase; realtime D1, không có data migration |
| 6 | [Deploy + Dagster full run + verify](phase-06-deploy-verify.md) | DONE | Real run, verify outputs, cleanup old parquet ✅; realtime job verified GREEN |

## Dependencies

```
Phase 1 (docs)
  ↓
Phase 2 + Phase 3 + Phase 4   [parallel — independent codebases]
  ↓
Phase 6 (deploy + run)
         ↑
         Phase 4 webhook cutover: user switches Sapo sender → dev deploys consumer
         (coordinated manually, không block Dagster run)
```

## Open Questions

1. ~~`'sapo_mac'` và `'sapo_mac+misa'`~~ — **RESOLVED:** đổi thành `'sapo_v2_mac'` / `'sapo_v2_mac+misa'`

2. ~~Metabase hardcoded filters~~ — **RESOLVED:** scan blueprints sạch, không có card nào filter `source_system='sapo'`.

3. **DuckDB rolling parquet** — `data_lake/export/marts/rolling/fact_order_costs/` có 3 snapshot files cũ với `source_system='sapo'`. Sau Phase 6 (Dagster run), snapshot mới sẽ có `'sapo_v2'`. Cần xoá snapshot cũ để DuckDB không đọc lẫn.
