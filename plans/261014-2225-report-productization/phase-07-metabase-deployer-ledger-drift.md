---
phase: 7
title: "Deployer Metabase an toàn II: sổ deploy, chỉ đụng object của mình, drift, cập nhật có chọn lọc, --render-only/--plan, snapshot + rollback, khoá, runbook"
status: pending
priority: P1
effort: "3.5d"
dependencies: [6]
---

# Phase 07: Sổ deploy, drift, kế hoạch, snapshot, runbook Metabase

> **Yêu cầu bắt buộc của user (13/10/2026): làm tới đâu, thiết kế và tài liệu hoá chi tiết tới đó.** Trước khi code: viết mục "Report deploys (Metabase)" vào `docs/operations/deployment.md` theo khuôn snapshot → khoá → plan → deploy → kiểm → rollback, và vẽ thuật toán nhận diện vào `.skills/metabase-automation/STRATEGY.md`. Trong lúc làm: tài liệu đi cùng commit.
>
> **Tài liệu phải cập nhật trong phase này:** `docs/operations/deployment.md` (mục mới "Report deploys (Metabase)", liên kết tới §"Metabase: backup and restore"); `.skills/metabase-automation/STRATEGY.md`, `SKILL.md`; `.skills/debug-metabase/SKILL.md` Bước 4 (tra spec theo marker `spec:` trước, rồi tới registry, thay vì grep tên trong `blueprints/`); `docs/architecture/modules.md`.

## Mục tiêu

Hoàn thành 11 hàng rào của thiết kế §4 ⑦ (trừ tra field, làm ở phase 08), để từ đây không có lần ghi nào vào Metabase prod mà thiếu bản sao lưu, kế hoạch đã duyệt và danh tính rõ ràng.

## Ánh xạ 11 hàng rào

| # (§4 ⑦) | Hiện thực | Phase |
|---|---|---|
| 1 | Sửa D1–D4 | 06 |
| 2 | **Sổ deploy** làm nguồn danh tính: marker trong `description` (`[[spec:<report_id>#<card_id>]]` cho card, `[[spec:<report_id>@<version>]]` cho dashboard; cùng kỹ thuật `text-id` của `lib/text-card-helpers.js`) + file `tenants/<t>/analytics/deployed/metabase.lock.json` `{catalog_version, registry_hash, params_hash, objects: {spec_key → {kind, metabase_id, entity_id, content_hash, deployed_at}}}`. Không dùng `entity_id` làm khoá chính. Marker và file lệch nhau → `--plan` báo drift, không tự tạo bản trùng | 07 |
| 3 | Chỉ đụng object có trong sổ, trong cây collection gốc khai báo ở hồ sơ (`metabase.root_collection_id`); collection "Tự làm" (phase 11) nằm ngoài danh sách được phép | 07 |
| 4 | **Drift:** trước khi PUT, băm nội dung live (SQL, viz, vị trí, bộ lọc của object) và so `content_hash` lần ghi trước; khác → người dùng đã sửa → từ chối, in diff; chỉ ghi khi `--force <spec_key>` đích danh | 07 |
| 5 | Cập nhật có chọn lọc: PUT `dashcards` = dashcard của mình (đã cập nhật) + dashcard không thuộc sổ (giữ nguyên như đọc được); tham số bộ lọc chỉ thêm/sửa id thuộc spec, giữ phần còn lại; không còn "clearing all" (`deploy_from_markdown.js:353`) ở đường mới. Object có trong sổ mà không còn trong render → **archive**, không xoá | 07 |
| 6 | Tra field theo `schema.bảng.cột` | 08 |
| 7 | `--render-only` (offline, in IR + SQL) và `--plan` (chỉ GET, in `create / update(trường đổi) / archive / noop / drift`) **bắt buộc trước `--apply`**; `--apply` nhận `--plan-file` đã duyệt và từ chối nếu kế hoạch tính lại khác file | 07 |
| 8 | **Snapshot trước mỗi deploy:** GET đầy đủ JSON của mọi object sắp chạm → `app_data/backups/metabase/deploys/<deploy_id>/`; lệnh `rollback <deploy_id>` PUT lại từ snapshot cho object đã sửa và archive object do lần deploy đó tạo. Với Metabase prod, `--apply` **từ chối** nếu không có bản sao H2 nguội `metabase-pre-deploy-*.mv.db` trong 60 phút gần nhất có dòng thành công trong `app_data/backups/metabase/cold-backup.log` (do `scripts/backup/metabase_cold_backup.sh pre-deploy` tạo) | 07 |
| 9 | Khoá một người ghi (`flock` trên `tenants/<t>/analytics/deployed/.lock`); timeout cho mọi request; GET thử lại có giới hạn và giãn cách; **không tự thử lại POST**; lỗi một bước ghi → dừng toàn bộ, in trạng thái dở dang và lệnh rollback | 07 |
| 10 | Test: phần nối card trên Metabase tạm; so số bằng SQL mới và SQL blueprint trên cùng bản chụp DuckDB | 06–08 |
| 11 | Ghi phiên bản catalog/registry/tham số đã cài ở cả file khoá và `description` của collection gốc; hai nơi lệch → `--plan` báo | 07 |

Thêm: **khung cấm ghi** trong hồ sơ (`metabase.blackout`: 02:30–04:00 hằng ngày, thứ Hai 07:00–10:00); `--apply` vào prod trong khung cấm bị từ chối.

## Kiểm kê phụ thuộc theo id (chỉ đọc)

`scripts/inventory_metabase_dependencies.js`: với một danh sách dashboard, liệt kê subscription (`/api/pulse`), alert, câu hỏi dựa trên câu hỏi (`card__<id>` trong `dataset_query`), link nội bộ trong text card, quyền collection. Đầu vào bắt buộc trước mọi lần chuyển giao FJ (phase 12, 14). Chạy chỉ đọc trên prod được, vì chỉ có GET.

## Metabase bóng (shadow) để diễn tập

`.skills/metabase-automation/scripts/test/shadow-metabase.sh up|down`: container `metabase-shadow` từ image `metabase-test`, mount **bản sao** của bản H2 nguội mới nhất vào thư mục tạm quyền 0700, mount bản chụp catalog `olap.duckdb` chỉ đọc, chạy trên một mạng Docker `--internal` (không ra ngoài, nên subscription không gửi được thư); script deploy chạy trong một container `node:20.20.2-slim` cùng mạng. `down` xoá container và bản sao (PII người dùng trong H2). Dùng để diễn tập: drift bị chặn, rollback từ snapshot, adopt (phase 12).

## Hình dạng code

- `lib/deploy-core.js`: `deployConfig(ir, {client, ledger, mode: 'render'|'plan'|'apply', planFile, force})`; IR đúng dạng object mà `lib/markdown_parser.js` trả về (`{collections, dashboards[{questions{sql, viz, pos, tab}, filters, textCards}]}`) cộng `spec_key` cho từng phần tử.
- `lib/ledger.js`, `lib/drift.js`, `lib/snapshot.js`, `lib/lock.js`, `lib/guards.js` (allowlist collection, khung cấm, kiểm bản sao nguội).
- `scripts/deploy_report.js` (đường mới, nhận IR JSON). `deploy_from_markdown.js` giữ nguyên hành vi (đã vá ở phase 06), chỉ đổi phần cuối sang gọi `deployConfig` ở mode `apply` không sổ, để hai đường dùng chung tầng API.

## Files

- Tạo: các file `lib/*` ở trên, `scripts/deploy_report.js`, `scripts/inventory_metabase_dependencies.js`, `scripts/test/shadow-metabase.sh`, test `node --test` cho từng hàng rào.
- Sửa: `scripts/deploy_from_markdown.js` (tách `main()` sang `deployConfig`), `lib/resources/Dashboard.js` (`syncCards` nhận danh sách dashcard giữ nguyên), tài liệu ở đầu file.
- Tạo: `analytics/schema/tenant-profile.schema.json` thêm khối `metabase {url, database, root_collection_id, environment, blackout, tls_insecure}`.

## Verification

Trên Metabase tạm (fixture) và Metabase bóng (bản sao H2):

- Deploy IR hai lần: lần hai `--plan` = toàn `noop`; `--apply` không gửi PUT/POST (đếm request); id và `updated_at` giữ nguyên.
- Sửa tay một card trong UI bóng → `--plan` báo `drift`, `--apply` từ chối; `--force <spec_key>` mới ghi.
- Thêm tay một card vào dashboard của mình → deploy giữ card đó; bộ lọc tay giữ nguyên.
- Bỏ một card khỏi IR → card bị archive, không bị xoá.
- `rollback <deploy_id>` đưa object về đúng JSON trước deploy (so từng trường).
- `--apply` vào profile `environment: prod` khi không có bản sao nguội < 60 phút → từ chối; trong khung cấm → từ chối.
- Hai lệnh `--apply` cùng lúc → lệnh thứ hai thoát ngay vì khoá.
- Kiểm kê phụ thuộc chạy chỉ đọc trên prod cho dashboard Weekly Pulse: in subscription/alert/câu hỏi phái sinh (kết quả ghi vào báo cáo phase, đầu vào phase 14).
- Container bóng và bản sao H2 đã xoá; cổng trống.

## Đổi số?

Không. Không ghi vào Metabase prod (kiểm kê chỉ GET).

## Rủi ro

| Rủi ro | Giảm thiểu |
|---|---|
| PUT `dashcards` của 0.62.3 thay toàn phần nên card tay vẫn mất | Kiểm trên Metabase bóng; giữ card không thuộc sổ bằng cách gửi lại nguyên văn |
| Marker trong `description` hiện ra cho người dùng | Kiểm cách hiển thị trên 0.62.3; nếu hiện, dùng dòng chữ nhỏ cuối mô tả |
| Bản sao H2 trong bóng chứa email người dùng | Thư mục 0700, xoá trong `down` |

## Rollback

Revert commit. Không có gì ghi vào prod trong phase này.
