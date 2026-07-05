# Phase 5 — Dev/Prod split: 2 stacks CÙNG MÁY (prod = máy hiện tại)

**Depends on:** Phase 4 (images trên GHCR) + [runtime inventory report](../reports/prod-runtime-inventory-260705-2000-containers-data-locations-report.md)
**Mục tiêu:** Prod stack (thư mục hiện tại) chạy thuần image GHCR pinned tag. Dev stack = clone riêng tại `D:\Vantt\app\data-integration-dev`, build local + bind-mount source, data riêng, port riêng, hostname riêng. Hai stack song song không đụng nhau. Thiết kế này dùng lại nguyên vẹn khi dev chuyển sang máy thứ 2 (chỉ bỏ port offset).

## Context (từ inventory — đọc report trước khi làm)

7 blockers đã xác định: (1) `container_name:` hardcode 8 services; (2) host ports 3000-3007 hardcode; (3) Caddy hostnames hardcode; (4) named volumes isolate theo project name — OK khi clone dir khác; (5) nguồn ingestion Sapo/MISA/webhook là MỘT — dev không được chạy sensors; (6) crm_drill_runner spawn sibling container theo tên qua docker.sock; (7) detail_view retired.

## Design

| | PROD (dir hiện tại) | DEV (`data-integration-dev` clone) |
|---|---|---|
| Compose command | `docker compose -f docker-compose.yml up -d` | `docker compose up -d` (override auto-áp) |
| Images | `ghcr.io/vantt/<c>:${TAG_<C>}` pull | build local, tag `dev` |
| Source mounts | không | có (bind-mount, flow restart-not-rebuild giữ nguyên) |
| Container names | `${STACK_PREFIX}` = rỗng → tên như cũ (crm, metabase…) | `STACK_PREFIX=dev-` → dev-crm, dev-metabase… |
| Ports | 3000-3007 (như cũ) | 4000-4007 (dải trống đã verify trên host) |
| Caddy hostnames | etl/bi/rill/evidence.lan.fwg.vn | etl.dev/bi.dev/… .lan.fwg.vn |
| Data | `./app_data` + volumes prefix `data-integration_*` (nguyên trạng) | `./app_data` của clone (seed từ snapshot) + volumes prefix `data-integration-dev_*` (tự isolate) |
| Dagster sensors/schedules | ON | **OFF mặc định** (env flag — điều tra cơ chế: `dagster_home/` config hoặc env gate trong `orchestration/definitions.py`; nếu chưa có gate thì thêm, đó là 1 sub-task) |
| crm_drill_runner | chạy | **tắt** (compose `profiles: ["prod"]`) |
| detail_view | giữ nguyên chờ quyết định | không có |

## Files

- **Modify** `docker-compose.yml` (base):
  - `container_name: crm` → `container_name: ${STACK_PREFIX:-}crm` (giữ container_name vì backup/restore/drill scripts gọi theo tên; prefix rỗng ở prod = không đổi hành vi).
  - `ports: "3007:8090"` → `"${PORT_CRM:-3007}:8090"` (tương tự 8 services).
  - Caddy labels → `caddy: ${HOST_ETL:-etl.lan.fwg.vn}` (tương tự).
  - `build:` sections + source mounts → chuyển sang override; `image: ghcr.io/vantt/<component>:${TAG_<COMPONENT>:-latest}`.
  - `crm_drill_runner`: thêm `profiles: ["prod"]`... **lưu ý**: profiles làm service không chạy mặc định kể cả prod — dùng cách khác: env `COMPOSE_PROFILES=prod` trong `.env` prod, dev không set.
- **Modify** `docker-compose.override.yml` (dev-only, file này KHÔNG có ở nhánh checkout prod? — không, cùng repo: override luôn tồn tại. Prod tránh nó bằng `-f docker-compose.yml` tường minh — convention đã ghi sẵn trong header file):
  - build sections (contexts Phase 1), source mounts, `image: <component>:dev` local tag.
- **Modify** `.env.example` — sections: `# Stack identity` (STACK_PREFIX, COMPOSE_PROFILES), `# Ports`, `# Hostnames`, `# Image tags` (TAG_*), `# Secrets` (trỏ sang .env.docker giữ nguyên vai trò). Dev clone có `.env` riêng điền bộ dev.
- **Modify** `orchestration/definitions.py` (hoặc cơ chế Dagster tương đương) — env gate `DAGSTER_SENSORS_ENABLED=false` → mọi sensor/schedule default STOPPED khi dev.
- **Create** `tools/seed-dev-data.ps1` — copy snapshot tối thiểu sang dev clone: `app_data/data_lake/` (~1.1GB, LOẠI `backup/`), `app_data/input_source/` (49MB), `app_data/metabase_data/` (680MB — giữ dashboards). KHÔNG copy: `backups/` (12GB), `dagster_home/` (6.4GB — dev khởi tạo mới). CRM data: khởi tạo rỗng qua migrations, hoặc restore từ `crm_backups` nếu cần data thật (script backup/restore đã có).
- **Create/Modify** `docs/deployment-guide.md` — quy trình đầy đủ (xem Steps 6).

## Steps

1. Parameterize compose (container_name, ports, hostnames, profiles) — deploy lên prod với `.env` prefix rỗng → `docker compose up -d` → **zero drift**: verify `docker inspect` tên/port/label y hệt trước.
2. Tách build+source mounts sang override; prod path `-f docker-compose.yml` với images GHCR 1.0.0 (đã validate ở Phase 4); chạy prod bằng image pull thay build local. Đây là điểm chuyển prod thật sự — làm lúc pipeline nghỉ, giữ image local cũ làm fallback.
3. Điều tra + thêm sensor gate Dagster (env flag), test flag hoạt động: set false → Dagster UI hiện mọi sensor STOPPED.
4. Clone repo sang `D:\Vantt\app\data-integration-dev`, viết `.env` dev (STACK_PREFIX=dev-, ports 4000-4007, hostnames *.dev, `DAGSTER_SENSORS_ENABLED=false`, không COMPOSE_PROFILES).
5. Chạy `tools/seed-dev-data.ps1`, `docker compose up -d` ở dev clone → 2 stacks song song. **DUCKDB CẢNH BÁO:** tuyệt đối không mount chung file duckdb giữa 2 stacks (single-writer) — seed là COPY, không share.
6. Viết deployment guide: release flow (dev build → test → release script → prod đổi TAG → pull+up), rollback (đổi TAG về trước), seed/refresh dev data, DNS setup cho *.dev hostnames.
7. Kiểm tra caddy-global nhận route dev (phụ thuộc Unresolved Q4 của plan — wildcard vs per-host DNS).

## Validation

- Prod sau step 2: `docker compose -f docker-compose.yml config` không còn `build:`/source mounts; 8 services healthy từ image GHCR; Dagster chạy 1 job; CRM login; Metabase dashboard load; backup script chạy OK.
- Dev sau step 5: `docker ps` thấy `dev-*` containers ports 4000-4007; sửa file `crm/src` trong clone → restart dev-crm → thay đổi ăn; Dagster dev: sensors STOPPED, chạy tay 1 dbt job trên data snapshot thành công; **prod không suy chuyển** (webhook consumer prod vẫn nhận, cursor dlt không bị đụng).
- Isolation test: `docker volume ls | grep data-integration-dev` — volumes riêng; xóa dev stack (`compose down`) không ảnh hưởng prod.

## Risks & Rollback

- Sai 1 biến env → container name/port đè prod: mitigate bằng step 1 zero-drift verify trước khi có stack thứ 2.
- Dev vô tình chạy ingestion thật: sensor gate (step 3) + `.env` dev không có Sapo credentials (bỏ trống SOURCES__SAPO__* trong dev .env.docker) — 2 lớp chặn.
- Disk: dev seed ~1.9GB + images ~11GB đã có sẵn (dev dùng chung image layers khi build từ cùng base). Kiểm tra disk trống trước seed.
- Rollback prod về build-local: `docker compose up -d --build` với override — flow cũ còn nguyên trong override.
