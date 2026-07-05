# Phase 1 — Component Self-Containment (Dockerfile relocation, narrow build context)

**Depends on:** Prereq A (working tree sạch)
**Mục tiêu:** Mỗi component chứa Dockerfile của chính nó, build context thu hẹp về thư mục component. Root chỉ giữ `Dockerfile.dataplatform` (có chủ đích — component data-platform trải 5 dirs root-level).

## Context

- Hiện tại 7 Dockerfiles ở root, tất cả build `context: .` → mọi build đều gửi cả repo làm context, và không có gì ngăn Dockerfile COPY chéo component.
- `data_platform` service mount `./docker-compose.yml` + `./Dockerfile.dataplatform` + `./Dockerfile.metabase` (`:ro`) để backup script (`scripts/backup/backup.sh` chạy trong container) copy config. Di chuyển file nào phải cập nhật cả mount + backup script.
- crm image layout `/app/crm/*` phải GIỮ NGUYÊN — bind mounts dev (`./crm/src:/app/crm/src`, …) overlay lên đúng path đó.

## Files

| Action | From | To | Build context mới |
|---|---|---|---|
| Move + sửa COPY | `Dockerfile.crm` | `crm/Dockerfile` | `./crm` |
| Move (không COPY, chỉ sửa comment) | `Dockerfile.drillrunner` | `crm/Dockerfile.drillrunner` | `./crm` |
| Move + sửa COPY | `Dockerfile.evidence` | `evidence/Dockerfile` | `./evidence` |
| Move (FROM-only) | `Dockerfile.rill` | `rill/Dockerfile` | `./rill` |
| Move (không COPY local) | `Dockerfile.metabase` | `metabase/Dockerfile` (tạo dir mới, 1 file) | `./metabase` |
| GIỮ Ở ROOT | `Dockerfile.dataplatform` | — | `.` (không đổi) |
| Skip | `Dockerfile.detailview` | — | detailView RETIRED, không đụng |

Modify:
- `docker-compose.yml` — build.context + build.dockerfile của 6 services; mount `./Dockerfile.metabase` trong data_platform đổi thành `./metabase/Dockerfile`.
- `scripts/backup/backup.ps1:113`, `scripts/backup/backup.sh:186`, `scripts/backup/README.md` — đường dẫn Dockerfile.metabase mới (giữ Dockerfile.dataplatform nguyên).
- Tạo `crm/.dockerignore` (loại `__pycache__`, `data/`, `plans/`, `docs/`, `*.pyc`) và `evidence/.dockerignore` (`node_modules`, `.evidence`) — context nhỏ, build nhanh.

## Steps

1. Move từng Dockerfile, rewrite COPY paths tương đối context mới:
   - crm: `COPY crm/src/requirements.txt ./crm/src/` → `COPY src/requirements.txt ./crm/src/`; `COPY crm/ ./crm/` → `COPY . ./crm/`; entrypoint/refresh tương tự. Image layout đích `/app/crm/*` không đổi.
   - evidence: `COPY evidence/package*.json ./` → `COPY package*.json ./`, v.v.
2. Cập nhật compose build sections, ví dụ:
   ```yaml
   crm:
     build: { context: ./crm, dockerfile: Dockerfile }
   ```
3. Cập nhật backup scripts + mount như trên.
4. Build tuần tự từng image, smoke test (xem Validation).
5. Commit: `refactor(build): move per-component Dockerfiles into component dirs, narrow build contexts`

## Validation

- `docker compose build crm crm_drill_runner evidence rill metabase` — build sạch.
- So sánh nội dung image trước/sau: `docker run --rm <img> sh -c "ls -R /app/crm | head -50"` khớp layout cũ (đặc biệt crm: `/app/crm/src`, `/app/entrypoint.sh`).
- `docker compose up -d` → tất cả service healthy; CRM UI mở được; bind-mount dev flow: sửa 1 file `crm/src`, `docker compose restart crm`, thay đổi ăn.
- Chạy backup script 1 lần → config files được copy đủ với path mới.

## Risks & Rollback

- COPY path sai → file thiếu trong image: bắt bằng smoke test layout trước khi up.
- Rollback: revert commit (chỉ moves + path strings, không đổi logic).
