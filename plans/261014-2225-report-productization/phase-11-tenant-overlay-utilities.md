---
phase: 11
title: "Hồ sơ + overlay khách đầy đủ, collection \"Tự làm\", report riêng qua cùng đường, 2 report tiện ích, lần ghi Metabase prod đầu tiên"
status: pending
priority: P2
effort: "3d"
dependencies: [10]
---

# Phase 11: Overlay khách, report tiện ích, ghi Metabase prod lần đầu

> **Yêu cầu bắt buộc của user (13/10/2026): làm tới đâu, thiết kế và tài liệu hoá chi tiết tới đó.** Trước khi code: viết quy trình report riêng L0–L3 và luật overlay vào `analytics/README.md` (mục "Report riêng cho khách"). Trong lúc làm: tài liệu đi cùng commit.
>
> **Tài liệu phải cập nhật trong phase này:** `analytics/README.md` (overlay, L0–L3, luật đưa lên chuẩn, kiểm overlay trước nâng cấp); `tenants/fine_japan/analytics/README.md` (mới: hồ sơ FJ, tham số ghi tường minh, collection gốc); `docs/operations/deployment.md` mục "Report deploys (Metabase)" (lần chạy thật đầu tiên, ví dụ lệnh); `docs/analytics-handbook/README.md` (collection "Tự làm"); `docs/architecture/modules.md`.

## Mục tiêu

1. Hồ sơ và overlay khách ở dạng cuối (thiết kế §4 ④ ⑥), có validator.
2. Report riêng cho khách đi qua đúng đường deploy chuẩn (thước đo 3 trên prod thật).
3. Hai report tiện ích luôn cài: **UTL-1 Sức khoẻ dữ liệu** (độ tươi, nguồn lỗi, tỉ lệ `UNMAPPED`, độ phủ giá vốn) và **UTL-2 Tra cứu và đối soát đơn với Sapo** (gộp `order_listing_reconciliation` + `order_detail_view`).
4. Lần ghi đầu tiên vào Metabase prod bằng deployer an toàn, vào một collection **mới** (không chạm dashboard FJ hiện có).

## Thiết kế

- **Hồ sơ** `tenants/<t>/analytics/profile.yml`: `tenant_id`, `locale`, `revenue` (tham số ghi tường minh, phase 09), `segments`, `metabase` (phase 07), `access.areas`, `message.channels`, `personas` (phase 13), `installed` (do deployer ghi). Không chứa secret.
- **Overlay** `tenants/<t>/analytics/overlay.yml` chỉ được: thêm report riêng (`reports/*.yml`), ẩn report chuẩn, đổi nhãn, đổi ngưỡng, đổi thứ tự trang chủ. Metric riêng ở `tenants/<t>/analytics/metrics/*.yml` có id tiền tố `<tenant>__`. Validator chặn mọi định nghĩa lại id chuẩn; overlay trỏ tới report/metric không còn tồn tại → **lỗi cứng** (không âm thầm bỏ qua).
- **Collection "Tự làm"**: deployer tạo một lần, ghi id vào hồ sơ, đưa vào danh sách **cấm chạm** của guard (phase 07); không bảo hành số ở đó.
- **Report riêng L0–L3** (thiết kế §5): L0 bật report có sẵn; L1 overlay; L2 spec mới trên chỉ tiêu có sẵn, agent (`analytics-design`) soạn, analyst duyệt; L3 chỉ tiêu mới hoặc `inline_sql`, mình làm. Mọi loại đi qua `python -m analytics install`.
- **Kiểm trước nâng cấp:** `python -m analytics validate --all-tenants` biên dịch mọi spec của mọi khách; một khách hỏng thì không nâng cấp khách đó.
- **Luật đưa lên chuẩn:** ≥ 3 khách cần, chỉ dùng chỉ tiêu chuẩn, không `inline_sql`, so số đạt trên dữ liệu 2 khách; ghi trong README, chưa cần công cụ.
- **Repo cấu hình riêng:** tạm giữ `tenants/` trong repo này; cấu trúc thư mục giữ nguyên khi chuyển sang repo riêng (câu hỏi mở 5).

## Các bước

1. Schema overlay + validator + test (overlay hợp lệ; định nghĩa lại id chuẩn; trỏ report đã xoá).
2. Spec UTL-1, UTL-2 (capture-first từ dashboard `order_listing_reconciliation`, design `order_detail_view.md`, `ingestion_health`); so số với blueprint cũ bằng harness (`--engine metabase`, theo `as_of`).
3. Một report riêng L2 mẫu của FJ do analyst chọn (ví dụ một bảng tuần đang được làm tay), qua đúng đường.
4. Thử toàn bộ trên Metabase bóng (bản sao H2): `install --plan`, `--apply`, chạy lại `noop`, rollback.
5. **Deploy prod (giờ user duyệt, ngoài khung cấm):** `scripts/backup/metabase_cold_backup.sh pre-deploy` → `install --plan` → user duyệt file kế hoạch → `install --apply --plan-file …` vào collection gốc mới (ví dụ "Báo cáo chuẩn") + "Tự làm" → kiểm kê trước/sau.

## Files

- Tạo: `analytics/schema/tenant-overlay.schema.json`, `analytics/specs/{utl_data_health,utl_order_lookup_recon}.yml`, `tenants/fine_japan/analytics/{overlay.yml,README.md,reports/<report riêng>.yml}`, test.
- Sửa: `analytics/catalog/catalog.yml` (UTL-1, UTL-2 `active`), `analytics/compiler/validate.py`, `tenants/fine_japan/analytics/profile.yml`, tài liệu ở đầu file.
- Sinh/ghi bởi deployer: `tenants/fine_japan/analytics/deployed/metabase.lock.json`.

## Verification

- Validator xanh với FJ; ba fixture overlay hỏng bị chặn.
- Harness: UTL-1, UTL-2 khớp blueprint cũ ở mọi card tương ứng (card mới không có mốc thì ghi rõ).
- Prod: kế hoạch đã duyệt chỉ có `create` trong collection mới; kiểm kê sau deploy cho thấy 0 object ngoài collection gốc mới và "Tự làm" thay đổi (so `updated_at` của mọi dashboard/card hiện có); chạy lại `--plan` = `noop`.
- Sổ deploy ghi phiên bản catalog/registry/tham số; `description` collection gốc cùng phiên bản.

## Đổi số?

Không. Chỉ thêm dashboard mới; dashboard FJ cũ không đổi.

## Rủi ro

| Rủi ro | Khả năng × Tác động | Giảm thiểu |
|---|---|---|
| Collection mới thừa hưởng quyền rộng của collection cha | Trung bình × Trung bình | Đặt dưới collection đã có quyền đúng; quyền theo chức năng làm ở phase 13; kiểm quyền trong kiểm kê |
| Người dùng thấy hai bản tra cứu đơn | Trung bình × Thấp | Bản cũ giữ nguyên tới phase 12; báo nhóm dùng |

## Rollback

`rollback <deploy_id>` (archive object vừa tạo theo snapshot); nếu cần, khôi phục bản sao H2 nguội theo `deployment.md` §"Restore the H2 file". Revert commit.
