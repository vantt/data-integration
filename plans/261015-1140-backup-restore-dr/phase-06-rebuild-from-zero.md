---
phase: 6
title: "Ghim image + dựng lại từ con số 0 (bootstrap host, runbook) + diễn tập Fine Japan trên máy khác"
status: pending
priority: P1
effort: "1.5d + 1 ngày diễn tập"
dependencies: [5]
---

# Phase 6: Dựng lại từ con số 0

> **Yêu cầu bắt buộc của user (13/10/2026): làm tới đâu, thiết kế và tài liệu hoá chi tiết tới đó.** Trước khi code: cập nhật thiết kế của component bị đụng. Trong lúc làm: tài liệu đi cùng commit với code.
>
> **Tài liệu phải cập nhật trong phase này:** `docs/operations/backup-and-recovery.md` mục **Dựng lại từ con số 0** (runbook từng bước có thời gian mục tiêu, khác nhau giữa drill và thật, dọn máy sau diễn tập, chuyển tunnel/DNS khi thật, xoay `key-host`) và nhật ký diễn tập Fine Japan (thời gian thực từng bước, vướng mắc, sửa gì); `docs/operations/deployment.md` mục "Prerequisites"/"Docker Deployment" (trỏ về runbook mới; mục "Docker Deployment (Windows Production)" ghi là lỗi thời, phase 8 dọn); ADR 019 (D10 kết quả thật; D12 đã chốt không lưu image, ghi kết quả build lại thật).

## Mục tiêu

Một người có Recovery Sheet và một máy Linux mới dựng lại được hệ thống Fine Japan từ repo ngoài máy trong ≤ 8 giờ làm việc, và điều đó đã được làm thật một lần trên máy khác prod mà prod không bị ảnh hưởng. Công cụ là cùng công cụ Đợt 5 sẽ dùng để cài khách mới.

## Thiết kế

### Ghim image (điều kiện để dựng lại cho ra cùng hệ thống)

| Image | Hiện tại | Ghim |
|---|---|---|
| `fileserver` | `caddy:alpine` (`docker-compose.yml:149`) | `caddy:<phiên bản>-alpine@sha256:<digest đang chạy>` |
| `cloudflared` | `cloudflare/cloudflared:latest`, compose ở `/home/vantt/cloudflared-tunnel/docker-compose.yml` (ngoài repo, không có git; F-Q10), `network_mode: host`, user 65532, tunnel quản lý tại chỗ bằng credentials file, ingress gồm cả `vnflow`, `hermes`, `fgos` ngoài dự án | Ghi compose với digest vào runbook và `host-state/` (file nằm ngoài repo nên plan không sửa nó; ghim do người vận hành theo runbook trong giờ duyệt) |
| Metabase | `FROM eclipse-temurin:21-jre-jammy` (`Dockerfile.metabase:1`), `METABASE_VERSION=0.62.3` (`:8`), jar tải lúc build | Base theo digest; kiểm sha256 của jar Metabase và driver DuckDB khi tải |
| `data_platform`, `crm`, `detail_view`, các image khác | `FROM python:3.10-slim` (`Dockerfile.dataplatform:1`), `python:3.12-slim` (`Dockerfile.crm:4`), `python:3.11-slim` (`Dockerfile.detailview:3`) | Base theo digest đang có trong cache; ghim thêm phiên bản dependency đang chạy (lấy `pip freeze` từ image hiện tại vào file constraints, ví dụ dlt 1.29.1 dù `ingestion/requirements.txt:1` không ghim và comment `Dockerfile.dataplatform:33-37` ghi 1.25.0), vì không còn lưu image (D12) |
| Caddy toàn cục (`caddy-global:dns01`) | Stack riêng nhưng **trong repo**: `caddy-global/{docker-compose.yml,Dockerfile.caddy,base.Caddyfile}`, token DNS-01 lấy từ `.env.docker` (F-Q10) | Ghim base trong `caddy-global/Dockerfile.caddy` theo digest; runbook ghi lệnh `docker compose --env-file .env.docker -f caddy-global/docker-compose.yml up -d` |

Ghim theo digest **đang chạy** nên không đổi image prod; deploy D3 chỉ merge, không cần recreate container (kiểm `docker compose up -d --no-recreate` không đổi gì; `docker compose config` cho digest khớp `docker inspect`).

### Không lưu image (D12)

User chốt 15/10: không `docker save` lên off-site (image dự án ~13,5 GB chưa nén, ~5–7 GB nén, F-Q18). `restore.sh full` luôn build từ git ở đúng sha; độ tin cậy dựa vào ghim ở bảng trên và việc diễn tập dưới đây build lại thật trên máy khác. Thời gian build ghi vào `restore-timeline.json`.

### Bootstrap host (`scripts/host/bootstrap-host.sh`)

Idempotent, chạy được nhiều lần: kiểm Ubuntu LTS và kiến trúc; cài Docker Engine + compose plugin từ kho chính thức (phiên bản tối thiểu ghi trong script), `git`, `curl`, `zstd`; thêm user vào nhóm `docker`; bật linger; tạo `${FG_BACKUP_CONFIG_DIR}` (0700); tạo mạng ngoài `caddy_net` nếu chưa có (compose khai báo `external: true`, `docker-compose.yml:1-3`). Không cài restic/rclone trên host (đã có trong image `backup`). Đợt 5 `init` gọi script này.

### Runbook (mục tiêu thời gian, tổng ≤ 8 giờ làm việc)

| # | Bước | Mục tiêu |
|---|---|---|
| 0 | Chuẩn bị: Recovery Sheet, máy Ubuntu LTS có mạng, quyền Cloudflare/DNS (chỉ khi thật) | — |
| 1 | `bootstrap-host.sh` | 20 phút |
| 2 | `git clone` repo FG, checkout đúng tag/sha ghi trên Recovery Sheet (tag snapshot `git=<sha>` là nguồn chuẩn sau bước 4) | 10 phút |
| 3 | Cấu hình backup từ Recovery Sheet: `rclone.conf` (SA JSON do FJ cấp lại, hoặc `rclone authorize` cho OAuth), `restic.pass` tạm = `key-customer` | 20 phút |
| 4 | `restore.sh snapshots` → `extract latest --into` → `verify` | 30–60 phút (tuỳ mạng) |
| 5 | `restore.sh full --from <dir> --confirm --mode drill` (thật: `--mode real`): secret, checkout đúng sha, seed, build image, volume (dagster, monitoring, crm), H2, lake, bảng exports | 60–90 phút |
| 6 | `dbt build` + serving qua Dagster (thời gian theo T3 đã đo) | theo T3 |
| 7 | Kéo bù (thật): chạy ingestion tiếp từ cursor trong snapshot (design §8.3, không lùi theo giờ); drill: chỉ chạy nếu bật lại biến Sapo cho riêng bước này, consumer webhook **không bao giờ** chạy ở drill (ack xoá hàng đợi prod) | 30 phút |
| 8 | Kiểm: Metabase mở dashboard, số collection/card/dashboard khớp manifest; CRM `/healthz` + diễn tập CRM; Evidence build; nightly chế độ drill xanh; instigator so với snapshot | 60 phút |
| 9 | Thật: khôi phục credentials tunnel (`restore.sh apply --component cloudflared`, chỉ `--mode real`), start `cloudflared` (tunnel tự chuyển sang máy mới; chỉ khi máy cũ đã chết), sửa DNS LAN `*.lan.fwg.vn`, Caddy toàn cục, Tailscale; `key add` khoá host mới, `key remove` khoá host cũ; cài timer; ping healthchecks | 60 phút |
| 10 | Diễn tập: **dọn máy** (xoá `${FG_BACKUP_CONFIG_DIR}`, scratch, volume, checkout, `docker system prune -a --volumes` trên máy diễn tập); biên bản | 20 phút |

Mỗi bước ghi vào `restore-timeline.json`; tổng thời gian là con số RTO đo được.

### Diễn tập cho Fine Japan

Máy theo câu hỏi mở 1. Chạy `--mode drill`: không `cloudflared`, biến ra ngoài rỗng, schedule/sensor dừng, máy không nằm trong DNS LAN của prod. Người làm theo **đúng runbook**, không dùng kiến thức ngoài runbook; chỗ nào phải ứng biến thì ghi lại và sửa runbook ngay sau buổi diễn tập. Có người FJ chứng kiến bước 3–4 (mở repo bằng khoá khách).

## Files

- Create: `scripts/host/bootstrap-host.sh`, test cú pháp (`shellcheck` trong pytest hoặc CI hiện có).
- Modify: `docker-compose.yml` (dòng `image:` của `fileserver`), `Dockerfile.metabase`, `Dockerfile.dataplatform`, `Dockerfile.crm`, `Dockerfile.detailview` và các `Dockerfile.*` còn lại (`FROM` theo digest), `caddy-global/Dockerfile.caddy` (`FROM` theo digest), file constraints dependency Python, `scripts/backup/restore.sh` (nhánh `--mode real`), tài liệu ở khối đầu.

## Verification

- `docker compose config` cho digest khớp image đang chạy; deploy D3 (giờ user duyệt) không recreate container nào (`docker compose up -d` báo "up-to-date"); nightly kế tiếp xanh.
- `bootstrap-host.sh` chạy hai lần trên một VM sạch, lần hai không đổi gì.
- Diễn tập Fine Japan: tiêu chí 5 của plan.md (≤ 8 giờ, dashboard 43/888/23 hoặc số manifest hiện hành, CRM xanh, nightly drill xanh, prod không đổi: không có connector tunnel lạ trong Cloudflare dashboard trong lúc diễn tập, dấu vân tay prod không đổi); máy diễn tập đã dọn (kiểm `docker volume ls` rỗng, thư mục cấu hình không còn).

**Đụng prod:** có (deploy D3 ghim image, không recreate). Diễn tập không đụng prod nhưng đọc repo ngoài máy của FJ. **Cần giờ user duyệt:** có, cho D3 và ngày diễn tập.

## Rủi ro

| Rủi ro | Giảm thiểu |
|---|---|
| Build lại image trên máy mới ra dependency khác, pipeline lỗi | Không lưu image (D12); ghim base theo digest và constraints từ `pip freeze` của image đang chạy; diễn tập build lại thật; phần còn lại là Đợt 2 |
| Máy diễn tập giữ dữ liệu và secret của FJ sau buổi diễn tập | Bước 10 bắt buộc, có trong biên bản; máy diễn tập không dùng chung cho việc khác trong lúc có dữ liệu |
| Tunnel bị gắn nhầm vào máy diễn tập | Drill không start `cloudflared`; `.env.drill` để rỗng token tunnel; kiểm Cloudflare dashboard trong lúc diễn tập |
| Evidence build cần ~3,5 GiB RAM (roadmap) | Máy diễn tập ≥ 16 GB RAM; ghi yêu cầu phần cứng vào runbook (đầu vào benchmark Đợt 5) |
| RTO vượt 8 giờ | Ghi bước nào chậm; đề xuất đưa `olap.duckdb` lên off-site hằng tuần (nghiên cứu §7.4) làm phương án, trình user |

## Rollback

Revert dòng ghim image (image cũ vẫn trong cache, digest không đổi nên không có gì phải recreate). Script bootstrap và nhánh `--mode real` không ảnh hưởng prod.
