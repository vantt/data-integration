# Plan: Standalone Export DuckDB + Rolling KEEP=3

**Date:** 2026-05-08 23:05+07
**Status:** Draft — chờ approve
**Source research:** [`plans/reports/research-260508-2305-serving-layer-design-applicability.md`](../reports/research-260508-2305-serving-layer-design-applicability.md)

## Goal

Áp dụng 2 cơ chế từ nu-data-pipeline serving-layer-design (đã filter):

1. **Standalone Export DuckDB** — file `.duckdb` materialize toàn bộ marts, expose qua HTTP cho offline / AI analysis ngoài hệ thống.
2. **Rolling KEEP=3** — giữ 3 versions parquet thay vì 1, để rollback + audit trail.

## Decisions

| Decision | Choice | Rationale |
|---|---|---|
| HTTP expose | **Option B**: inline `caddy:alpine` + `caddy/Caddyfile` (basic_auth) + label `caddy: files.etl.lan.fwg.vn` cho external Caddy reverse-proxy | Caddy chính KHÔNG handle basic_auth → service tự gắn auth. Vẫn join `caddy_net` để có TLS từ Caddy chính. |
| GC retention | KEEP=3 (env-overridable) | Rollback + audit; storage cost negligible (~vài GB) |
| Atomic write | KHÔNG làm | Phức tạp dbt-duckdb override; chưa có incident thực |
| Schedule | Nightly sau `sapo_serving_db` | Đồng bộ với nightly batch nightly cycle |
| Scope | Toàn bộ views trong `olap.duckdb` | User confirm |
| Filename | `sapo_export_<ts>.duckdb` + `sapo_export_latest.duckdb` (atomic copy) | Versioning + stable URL |

## Phases

| # | Title | Status | Detail |
|---|---|---|---|
| 1 | Standalone export script + Dagster asset | DONE | [phase-01-standalone-export.md](phase-01-standalone-export.md) |
| 2 | Fileserver service (Caddy via label) | DONE | [phase-02-fileserver.md](phase-02-fileserver.md) |
| 3 | Rolling KEEP=3 | DONE | [phase-03-rolling-keep3.md](phase-03-rolling-keep3.md) |
| 4 | Docs update | DONE | [phase-04-docs.md](phase-04-docs.md) |

## Dependencies

```
Phase 1 (script) ─┐
                  ├──► Phase 2 (fileserver) — output dir is fileserver root
Phase 3 (KEEP=3) ─┘
Phase 4 (docs) ── after all
```

Phase 1 + 3 độc lập, có thể làm song song. Phase 2 cần Phase 1 trước (cần biết output path để mount). Phase 4 cuối.

## Key files affected

- **NEW**: `scripts/provisioning/build_standalone_export.py`
- **MODIFY**: `orchestration/assets/serving.py` — thêm asset `sapo_standalone_export`
- **MODIFY**: `docker-compose.yml` — thêm service `fileserver`
- **NEW**: `caddy/Caddyfile` (nếu Option A vẫn cần basic_auth riêng) hoặc skip nếu Caddy chính handle auth
- **MODIFY**: `scripts/provisioning/refresh_rolling.py` — env `ROLLING_KEEP_VERSIONS`
- **MODIFY**: `.env.docker.example` (nếu có) — thêm `FILESERVER_USER`, `FILESERVER_PASSWORD_HASH`, `ROLLING_KEEP_VERSIONS`
- **MODIFY**: `docs/architecture/data-flow.md` — thêm standalone export branch
- **MODIFY**: `.skills/data-pipeline/playbooks/03-serve.md` — pattern documentation

## Out of scope

- Atomic `.tmp + rename` cho rolling export (defer until incident).
- Refactor `bootstrap_serving_views.py` / `refresh_rolling.py` (đã clean).
- Migrate sang full nu-pipeline architecture (đã ahead).

## Success criteria

1. `docker compose up` → asset `sapo_standalone_export` runs OK trong nightly job.
2. File `sapo_export_latest.duckdb` xuất hiện trong `app_data/data_lake/serving/standalone/`.
3. URL `https://files.etl.lan.fwg.vn/standalone/sapo_export_latest.duckdb` tải được, query được bằng DuckDB CLI ngoài container.
4. `ls rolling/<table>/` thấy ≤ 3 files sau nightly.
5. Metabase vẫn hoạt động bình thường (không lock contention).

## Resolved (user 2026-05-08 23:20)

1. Caddy chính KHÔNG handle basic_auth → use Option B (inline Caddyfile).
2. Hostname `files.etl.lan.fwg.vn` KHÔNG conflict.
3. KHÔNG cần access log cho audit.
4. Scope: toàn bộ marts (auto-pickup tất cả views trong olap.duckdb).

## Execution

Parallel via 3 fullstack-developer agents (sonnet):
- Agent A → Phase 1 (script + asset)
- Agent B → Phase 2 (fileserver, Option B)
- Agent C → Phase 3 (rolling KEEP=3)

After Phase 1-3 complete → verify + smoke test → Phase 4 docs.

File ownership (no overlap):
- A: `scripts/provisioning/build_standalone_export.py` (NEW), `orchestration/assets/serving.py` (MODIFY)
- B: `docker-compose.yml` (MODIFY), `caddy/Caddyfile` (NEW), `.env.docker` example doc (UPDATE if exists)
- C: `scripts/provisioning/refresh_rolling.py` (MODIFY) — KHÔNG touch `.env.docker` (default in code)
