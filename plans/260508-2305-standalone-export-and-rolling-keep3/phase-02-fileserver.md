# Phase 02 — Fileserver Service (Caddy via Label)

## Context Links

- Plan: [plan.md](plan.md)
- Source pattern: `D:/Vantt/app/nu-data-pipeline/docker-compose.yml` service `fileserver` + `caddy/Caddyfile`
- Existing convention: `data-integration/docker-compose.yml` service labels `caddy: bi.local`, `caddy: rill.local`

## Overview

- **Priority:** P1
- **Status:** Pending
- **Description:** Thêm service `fileserver` (caddy:alpine, file-browse mode) mount `serving/standalone:ro`, đăng ký vào external Caddy proxy qua label `caddy: files.etl.local` để có URL ổn định + auth/cert quản lý tập trung.

## Key Insights

- `data-integration` đã có external Caddy chạy trên `caddy_net` network — service mới chỉ cần label, không cần expose port host.
- nu-pipeline expose port 13004:8080 + Caddyfile inline + basic_auth biến env. Adapt sang label-based: bỏ port mapping, để Caddy chính handle TLS + auth.
- Internal port của caddy file_server: dùng 8080 — Caddy chính reverse_proxy tới `{{upstreams 8080}}`.
- Basic_auth có thể đặt ở Caddy chính (preferred) hoặc inline trong service nhỏ (fallback).

## Requirements

### Functional
- URL `https://files.etl.local/standalone/sapo_export_latest.duckdb` resolve được trong LAN/VPN.
- Index page liệt kê file (Caddy `file_server browse`).
- Read-only mount — không cho phép upload/delete.

### Non-functional
- Restart-resilient (`restart: unless-stopped`).
- Service không depend on data_platform start (Caddy nhẹ, idempotent).
- Auth: basic_auth ở Caddy chính (chia sẻ cùng cơ chế của bi.local/etl.local).

## Architecture

```
Internet/LAN
      │
      ▼
┌─────────────────────────────────┐
│ External Caddy (caddy_net)      │
│ TLS, basic_auth, label discovery│
└────────────┬────────────────────┘
             │ reverse_proxy upstream:8080
             ▼
┌─────────────────────────────────┐
│ fileserver (caddy:alpine)       │
│ file_server browse, /data:ro    │
└────────────┬────────────────────┘
             │ mount :ro
             ▼
   app_data/data_lake/serving/standalone/
```

## Related Code Files

**MODIFY:**
- `docker-compose.yml` — append service `fileserver`
- `.env.docker.example` (hoặc README) — document `FILESERVER_USER`, `FILESERVER_PASSWORD_HASH` IF ta vẫn muốn local basic_auth

**CREATE (CONDITIONAL):**
- `caddy/Caddyfile` — chỉ tạo nếu **không** dùng auth của Caddy chính. Nếu Caddy chính handle auth thì service fileserver chỉ cần default config.

## Implementation Steps

1. **Confirm Caddy chính config:**
   - Tìm Caddy chính: `docker ps | grep caddy` hoặc check `D:/Vantt/app/caddy*` cho compose riêng.
   - Verify nó pickup labels `caddy: <hostname>` + `caddy.reverse_proxy: ...` từ services chung network.
   - Verify hostname `files.etl.local` chưa conflict (resolve nội bộ DNS / `/etc/hosts`).

2. **Decide auth location:**
   - **A (preferred):** Caddy chính handle basic_auth bằng global directive trong Caddyfile (xem caddy global config nếu có).
   - **B (fallback):** Inline auth trong fileserver — copy `caddy/Caddyfile` từ nu-pipeline, set env `FILESERVER_USER`/`FILESERVER_PASSWORD_HASH`. Sinh hash bằng `docker run --rm caddy:alpine caddy hash-password --plaintext '<pwd>'`.

3. **Append service block to `docker-compose.yml`:**
   ```yaml
   fileserver:
     image: caddy:alpine
     container_name: data_fileserver
     restart: unless-stopped
     networks:
       - caddy_net
     volumes:
       # Standalone export (read-only)
       - ./app_data/data_lake/serving/standalone:/data:ro
       # Optional: Caddyfile if Option B
       # - ./caddy/Caddyfile:/etc/caddy/Caddyfile:ro
     # Default Caddy config serves /srv. Override CMD nếu cần custom.
     command: ["caddy", "file-server", "--listen", ":8080", "--browse", "--root", "/data"]
     labels:
       caddy: files.etl.local
       caddy.reverse_proxy: "{{upstreams 8080}}"
       # If basic_auth at central Caddy: add caddy.basic_auth + caddy.basic_auth.<user> labels
   ```

4. **Test sequence:**
   - `docker compose up -d fileserver`
   - `docker compose logs fileserver` — confirm starts without error
   - `curl -I http://data_fileserver:8080/` từ container khác trên `caddy_net` — expect 200/401
   - Trigger Phase 1 manual run để có file
   - `curl -u user:pwd https://files.etl.local/sapo_export_latest.duckdb -o /tmp/test.duckdb`
   - `duckdb /tmp/test.duckdb -c "SHOW TABLES;"`

5. **Browse page check:** Mở `https://files.etl.local/` trong browser → thấy listing file `sapo_export_*.duckdb`.

## Todo List

- [ ] Identify central Caddy + decide auth location (A or B)
- [ ] Append `fileserver` service to docker-compose.yml
- [ ] (Conditional B) Create `caddy/Caddyfile` + env vars
- [ ] Up service, verify reachable trên caddy_net
- [ ] Verify URL `files.etl.local` resolve đúng
- [ ] Auth working
- [ ] Download + open .duckdb file successfully

## Success Criteria

- `https://files.etl.local/sapo_export_latest.duckdb` tải được.
- Listing page (browse) hiện đầy đủ snapshots timestamped + `_latest`.
- File tải về có thể attach DuckDB CLI/Python ngoài container (không cần parquet path).
- Auth required (401 nếu thiếu credentials).
- Service auto-restart sau `docker compose down/up`.

## Risk Assessment

| Risk | Mitigation |
|---|---|
| Hostname conflict | Pre-check DNS / `/etc/hosts` / Caddy chính routing |
| Port 8080 trùng trong container | Internal-only — không expose host port; conflict chỉ nếu trong cùng container (impossible với image này) |
| Public exposure leak | Mount `:ro`; Caddy chính bắt buộc auth; document trong AGENTS.md |
| Caddy label syntax sai | Test `docker compose config` parse OK; xem `etl.local` working sample |

## Security Considerations

- File chứa toàn bộ business data → **MANDATORY** basic_auth.
- Đảm bảo `files.etl.local` chỉ resolve trong LAN/VPN, không expose public.
- Document credential rotation procedure.
- Log access log của Caddy để audit ai download.
- Cân nhắc IP allowlist trong Caddy chính nếu có teammate ngoài VPN.

## Next Steps

- Phase 4: Document URL + auth procedure trong `docs/operations/`.
