# Modular Monorepo — Boundary Hardening + GHCR + Dev/Prod Split

**Status:** DRAFT — awaiting approval
**Created:** 2026-07-05
**Goal:** Giữ monorepo nhưng cưỡng chế ranh giới component bằng máy móc (build context, import-linter, per-component versioned images trên GHCR), chuẩn bị chạy 2 máy Dev/Prod. Không tách repo — nhưng mọi bước đều là đường một chiều về phía tách repo sau này nếu cần.

## Components (bounded contexts)

| Component | Dirs | Image | Ghi chú |
|---|---|---|---|
| `data-platform` | ingestion, transformation, orchestration, webhook_consumer, scripts | ghcr.io/…/data-platform | Coupling nội bộ có chủ đích (orchestration import 2 dir kia) — coi là MỘT component |
| `crm` | crm/ | ghcr.io/…/crm + ghcr.io/…/crm-drill-runner | Gần như tự chứa; 1 import chéo cần cắt |
| `metabase`, `rill`, `evidence` | config-only | ghcr.io/…/{metabase,rill,evidence} | Serving layer, Dockerfile mỏng |
| `deployment` (root) | docker-compose*, caddy/, .env | — | Vai trò "deployment project" |
| `detailView` | — | — | RETIRED — không đụng, không publish |

## Phases

| # | Phase | File | Phụ thuộc |
|---|---|---|---|
| 0 | Đánh giá + tái cơ cấu data storage: bind mount → named volume (benchmark trước, migrate chọn lọc; code-as-volume loại trừ — code prod đi bằng image) | [phase-00](phase-00-data-volume-restructure.md) | [runtime inventory](../reports/prod-runtime-inventory-260705-2000-containers-data-locations-report.md) |
| 1 | Component self-containment (di chuyển Dockerfiles, thu hẹp build context) | [phase-01](phase-01-dockerfile-relocation.md) | Prereq A |
| 2 | Cắt import crm → orchestration (inline Lark alert) | [phase-02](phase-02-cut-crm-orchestration-import.md) | — |
| 3 | Cưỡng chế boundary bằng import-linter + CI | [phase-03](phase-03-import-linter-enforcement.md) | Phase 2 |
| 4 | GHCR publish + per-component versioning | [phase-04](phase-04-ghcr-publish-versioning.md) | Phase 1 |
| 5 | Dev/Prod compose split — **2 stacks cùng máy** (base = prod images, override = dev build+mounts, parameterize names/ports/hostnames) | [phase-05](phase-05-dev-prod-compose-split.md) | Phase 4, [runtime inventory](../reports/prod-runtime-inventory-260705-2000-containers-data-locations-report.md) |
| 6 | Boundary doc + cập nhật docs/AGENTS.md | [phase-06](phase-06-boundary-doc.md) | Phase 1–5 |

Phase 0 chạy TRƯỚC TIÊN (ổn định tầng data trước khi các phase khác sửa compose; phase-05 seed script phụ thuộc kết quả Phase 0). Sau đó Phase 2+3 độc lập với 1+4+5, có thể làm song song. Phase 6 chốt cuối.

## Prerequisites

- **A. Working tree sạch:** ~40 file ui-spec/crm đang modified trên `main` — commit hoặc stash xong trước Phase 1.
- **B. GHCR access:** GitHub PAT (classic) scope `write:packages` trên máy dev; `read:packages` trên máy prod. `docker login ghcr.io`.

## Acceptance Criteria (toàn plan)

1. `docker compose up -d` trên máy dev hoạt động y hệt hiện tại (bind mounts, restart-not-rebuild flow của crm giữ nguyên).
2. Máy prod: `docker compose -f docker-compose.yml up -d` chạy hoàn toàn từ images pull GHCR, không build, không mount source.
3. `import-linter` pass và fail đúng khi cố tình thêm import chéo crm→orchestration.
4. Mỗi component có tag version riêng dạng `<component>-vX.Y.Z`; rollback prod = đổi tag trong `.env` + `docker compose up -d`.
5. Không service nào đổi hành vi runtime (data mounts `app_data/*` giữ nguyên cả 2 env).

## Risks

- Đổi build context làm sai COPY path → image thiếu file. Mitigation: build + smoke test từng image trước khi commit (phase 1 có checklist).
- `data_platform` mount `./docker-compose.yml` + `./Dockerfile.dataplatform` vào container (`:ro`) — có code đọc chúng. Dockerfile.dataplatform GIỮ Ở ROOT để không phá; điều tra kỹ trước khi di chuyển bất cứ thứ gì nó đọc.
- Metabase serving views: KHÔNG đụng olap.duckdb / bootstrap trong plan này.
- crm image rebuild: theo memory, crm là restart-not-rebuild; Phase 1 chỉ đổi vị trí Dockerfile — cần 1 lần `--build` sau khi đổi, sau đó flow cũ giữ nguyên.

## Decisions (chốt 2026-07-05)

1. GHCR owner = **`vantt`** → images `ghcr.io/vantt/<component>`.
2. Images GHCR: **private**.
3. **Máy hiện tại = PROD.** Giai đoạn đầu: dev + prod là **2 stacks chạy cùng máy này** (máy thứ 2 là bước sau). Runtime inventory đã hoàn thành: [prod-runtime-inventory report](../reports/prod-runtime-inventory-260705-2000-containers-data-locations-report.md) — bao gồm data map (bind mounts + named volumes + sizes) và 7 blockers dual-stack (container_name/ports/hostnames hardcode, sensors double-ingest, drill runner docker.sock…).

## Unresolved Questions

1. `scripts/` chứa lẫn pipeline scripts (data-platform) và deploy/ops scripts (deployment). Plan KHÔNG reorganize (YAGNI) — chỉ ghi ownership trong boundary doc. OK?
2. Orphan volumes (`crm_data` không prefix, anonymous `45f95…`) + `app_data/metabase_data.backup.20260423/` (140MB) — xóa không?
3. detail_view RETIRED vẫn đang chạy trên prod — stop hẳn?
4. DNS cho dev stack (`*.dev.lan.fwg.vn`): caddy-global đang wildcard DNS01 hay per-host? (quyết cách khai báo hostname dev)
