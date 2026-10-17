---
phase: 13
title: "Trang chủ theo vai trò, phân quyền theo chức năng (≤ 7 nhóm), cưỡng chế cờ nhạy cảm chi phí, 2 bộ persona mẫu"
status: pending
priority: P2
effort: "3d"
dependencies: [12]
---

# Phase 13: Trang chủ vai trò, phân quyền, persona

> **Yêu cầu bắt buộc của user (13/10/2026): làm tới đâu, thiết kế và tài liệu hoá chi tiết tới đó.** Trước khi code: ghi mô hình quyền (chức năng → khu vực Evidence, nhóm Metabase, kênh tin; persona → chức năng + quyền chi phí) vào `analytics/README.md` và `docs/architecture/modules.md`. Trong lúc làm: tài liệu đi cùng commit.
>
> **Tài liệu phải cập nhật trong phase này:** `analytics/README.md` (quyền, persona, trang chủ); `docs/operations/deployment.md` (thêm người dùng: gán persona → tài khoản Evidence + nhóm Metabase; thu hồi); `tenants/fine_japan/analytics/README.md` (bảng người → persona); `docs/architecture/modules.md`.

## Mục tiêu

Một mô hình quyền dùng chung cho Evidence, Metabase và tin tóm tắt: **theo chức năng, tối đa 7 nhóm**, cộng **cờ nhạy cảm chi phí** (quyết định 4); trang chủ theo vai trò 6–8 thẻ ghép từ `kpi_tiles`; 2 bộ persona mẫu (quyết định 7). Không phân quyền theo dòng ở v1.

## Thiết kế

- **Persona mẫu** `analytics/personas/shop_nho.yml` (Chủ shop, Nhân viên) và `analytics/personas/doanh_nghiep_vua.yml` (Giám đốc, Kế toán, Marketing, Trưởng bán hàng, Kho/vận hành, CSKH): mỗi persona `{id, functions[], can_view_cost, home_tiles_order}`. Đề xuất ô gán lấy từ hội đồng BI §(d) và sản phẩm §(e); Nhân viên và CSKH `can_view_cost: false`.
- **Hồ sơ khách** chọn một bộ và gán người: `personas.bundle`, `people[] {login, personas[]}` (không mật khẩu). Từ đó sinh:
  - Evidence: danh sách khu vực mỗi người được vào (chức năng) + khu vực trang chủ của persona `home-<persona>`; `evidence/site/Caddyfile` sinh lại; file hash vẫn do người vận hành tạo.
  - Metabase: nhóm `fn-<chức năng>` (≤ 7) và collection theo chức năng dưới collection gốc; quyền collection: nhóm chức năng chỉ xem collection của mình; deployer áp qua `GET/PUT /api/collection/graph` với kế hoạch và bản sao nguội như mọi lần ghi. Việc thêm người dùng vào nhóm làm tay trong UI admin (Metabase OSS), ghi trong runbook.
  - Tin tóm tắt: kênh gắn chức năng và `can_view_cost`.
- **Cưỡng chế cờ chi phí (tĩnh, lúc render/deploy):** card dùng metric `cost_sensitive` chỉ vào khu vực/collection/kênh có `can_view_cost: true`; validator lỗi nếu catalog đặt report có chỉ tiêu chi phí bắt buộc vào chức năng không có quyền; renderer bỏ card và hiện "Cần quyền xem chi phí" ở nơi không có quyền.
- **Trang chủ vai trò** (Evidence, thân thiện điện thoại, build sau nightly): khu vực `home-<persona>`, 6–8 thẻ lấy từ `kpi_tiles` của report trong các chức năng của persona, theo `home_tiles_order`, mỗi thẻ link sang report; dải trạng thái dữ liệu (từ UTL-1) ở đầu trang. Trang "Chủ shop" ưu tiên thẻ hôm qua/7 ngày (thiết kế §6). Overlay được đổi thứ tự thẻ.

## Các bước

1. Schema persona + hồ sơ; validator (≤ 7 nhóm chức năng; mỗi người có ít nhất một persona; cờ chi phí nhất quán).
2. Renderer trang chủ, sinh `Caddyfile` theo người; renderer Metabase nhóm/collection/quyền (IR mở rộng); test.
3. Diễn tập trên Metabase bóng: áp quyền, đăng nhập bằng tài khoản thử thuộc nhóm không có quyền chi phí, không thấy collection tài chính.
4. User gán người FJ vào persona (bảng trong README tenant).
5. Deploy: Evidence (sinh lại site, build tay một lần qua `report_site_build_job`), Metabase (bản sao nguội → `--plan` → duyệt → `--apply`), giờ user duyệt.

## Files

- Tạo: `analytics/personas/{shop_nho,doanh_nghiep_vua}.yml`, `analytics/schema/persona.schema.json`, `analytics/renderers/home.py`.
- Sửa: `analytics/renderers/{site,evidence,metabase_ir,message}.py`, `.skills/metabase-automation/lib/deploy-core.js` (nhóm, collection, collection graph), `tenants/fine_japan/analytics/profile.yml`, tài liệu ở đầu file.

## Verification

- Evidence: với mỗi persona thử, `curl` vào khu vực được phép = 200, khu vực khác = 401 (trang và file dữ liệu); grep build của khu vực/trang chủ không có quyền chi phí không có id metric `cost_sensitive`.
- Metabase bóng rồi prod: kiểm kê quyền sau deploy đúng bảng thiết kế; collection không thuộc chức năng không đổi quyền; `--plan` lần hai `noop`.
- Tin tóm tắt tới kênh không có quyền chi phí không có thẻ chi phí (dry-run log).
- Trang chủ "Chủ shop" hiển thị tốt trên màn hình điện thoại (kiểm bằng trình duyệt ở độ rộng 390 px).

## Đổi số?

Không.

## Rủi ro

| Rủi ro | Khả năng × Tác động | Giảm thiểu |
|---|---|---|
| Đổi quyền làm mất truy cập của người đang dùng | Trung bình × Trung bình | Kiểm kê quyền trước; bảng người → persona user duyệt trước deploy; rollback snapshot collection graph |
| Lộ chi phí qua thẻ trang chủ | Thấp × Cao | Cưỡng chế tĩnh ở validator + renderer; grep build |

## Rollback

Metabase: `rollback <deploy_id>` (collection graph về snapshot), hoặc bản sao H2 nguội. Evidence: gỡ khu vực trang chủ khỏi hồ sơ, sinh lại `Caddyfile`, `docker compose restart report_site`. Revert commit.
