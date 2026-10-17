---
title: "Module hoá suite data platform đang vận hành (Fine Japan là tenant #1)"
description: "Tách suite đang chạy thành connectors, CDM, core, packs, taxonomy module và tenant overlay Fine Japan, trong khi hệ thống vẫn vận hành hằng ngày và không đổi bất kỳ con số hay tên bảng public nào."
status: completed
priority: P1
effort: 15d
branch: refactor/modularize-suite
tags: [refactor, infra, tech-debt, critical]
blockedBy: []
blocks: []
created: 2026-10-13
---

# Module hoá suite data platform đang vận hành

## Overview

Đây là **Đợt 1** trong [long-vision roadmap](roadmap.md): biến hệ thống đang chạy cho Fine Japan thành các module có ranh giới rõ ràng ngay trong repo hiện tại, theo kiến trúc đích của [research report](../reports/research-261013-1610-sme-commerce-data-platform-modularization.md). Fine Japan là tenant đầu tiên. Đóng gói image (Đợt 2), dbt package/contract/đa nguồn (Đợt 3), taxonomy thành dữ liệu và bàn đầu ra (Đợt 4) cùng các đợt sau được liệt kê trong roadmap.

## Yêu cầu thiết kế và tài liệu hoá (bắt buộc)

Vì mục tiêu là đóng gói và module hoá, **làm tới đâu thì thiết kế và tài liệu hoá chi tiết tới đó** (yêu cầu của user 13/10/2026, ghi ở đầu mọi phase). Thiết kế authority/boundary chi tiết từng component: [architecture-boundaries.md](architecture-boundaries.md). Từ phase 1, bản sống nằm ở `docs/architecture/modules.md` và mỗi phase cập nhật mục của mình cùng commit với code. Phase 7 chỉ còn rà soát và viết ADR.

## Yêu cầu vận hành liên tục (bắt buộc)

Hệ thống đang chạy **tiếp tục vận hành hằng ngày như cũ** trong suốt plan:

1. Không làm việc trên checkout prod `/home/vantt/app/fg-dataware-house` (được bind-mount vào container). Mọi việc trên worktree `refactor/modularize-suite`; kiểm chứng trên shadow lake cô lập (`--network none`, dữ liệu từ backup).
2. Prod chỉ đổi qua runbook deploy ở [phase 0](phase-00-safety-harness.md) §D: dừng `data_platform` vài phút, fast-forward, start lại. Gián đoạn tối đa một lần dừng ngắn mỗi phase, ngoài khung nightly 02:30–04:00.
3. Sau mỗi deploy: nightly kế tiếp phải xanh, số dòng các bảng public trong ngưỡng `row_trend_checks`, trạng thái schedule/sensor giống trước deploy. Nếu không: rollback ngay theo runbook, không sửa nóng trên prod.
4. **Đóng băng:** khi nightly prod đỏ vì lý do khác (nguồn lỗi, Sapo đổi API…), không deploy phase nào cho đến khi prod xanh trở lại.
5. Không đổi `requirements`, Dockerfile hay image prod trong plan này.

## Bất biến dữ liệu

Không đổi một con số nào trên dashboard và không đổi tên bất kỳ bảng/view public nào (76 serving view, 11 bảng Rill, các bảng CRM/detailView/Evidence đọc). Mọi phase chứng minh bằng gate ở phase 0 trước khi deploy.

## Phases

| # | Phase | File | Effort | Phụ thuộc | Gate |
|---|---|---|---|---|---|
| 0 | Safety harness: worktree, shadow lake, golden, inventory, runbook deploy/rollback ✅ (prod 13/10 23:38) | [phase-00](phase-00-safety-harness.md) | 3d | — | — |
| 1 | Ranh giới nhanh: cắt import chéo, sửa macro hỏng, `check_boundaries.py` ✅ | [phase-01](phase-01-boundary-quick-wins.md) | 0.5d | 0 | M |
| 2 | Bố cục module cho dbt (chỉ di chuyển file) ✅ | [phase-02](phase-02-dbt-module-layout.md) | 2.5d | 0, 1 | M |
| 3 | CDM: đóng rò core → nguồn, test schema mức warn ✅ (prod 14/10 09:22) | [phase-03](phase-03-cdm-close-leaks.md) | 1.5d | 2 | S |
| 4 | ✅ (prod 14/10 13:27) Taxonomy rút gọn: đặc tả `TAXONOMY.md`, check cảnh báo, dời seed (không tách macro; xem [thiết kế bộ máy](taxonomy-engine-design.md)) | [phase-04](phase-04-taxonomy-module.md) | 2d | 2, 3 | M |
| 5 | Orchestration: mỗi connector là một package ✅ (prod 14/10 10:35) | [phase-05](phase-05-orchestration-connector-packages.md) | 2.5d | 1 | M |
| 6 | ✅ (prod 14/10 22:28, `64103e50`) Pack sản phẩm (CRM, HUG, finance gồm chi phí/lợi nhuận, kịch bản bán hàng) + tenant Fine Japan tối thiểu (chỉ US shipment + dữ liệu/cấu hình) | [phase-06](phase-06-fine-japan-tenant-overlay.md) | 3d | 3, 4, 5 | M |
| 7 | ✅ (prod 14/10 22:49, `8eb9920f`) Tài liệu, ADR, cưỡng chế, dọn shadow | [phase-07](phase-07-docs-adr-enforcement.md) | 1d | 1–6 | — |

Gate M = golden + inventory dbt + so SQL đã compile + inventory Dagster (gồm selection từng job) + pytest + build trên lake trống. Gate S = Gate M + golden sau `--full-refresh` (16 model incremental và mọi thứ phía sau). Chạy bằng một lệnh: `scripts/shadow/gate.sh M|S` (xem `scripts/shadow/README.md`). Phase 5 có thể chạy song song với 2–4 (khác thư mục), nhưng deploy tuần tự.

## Kiến trúc sau Đợt 1

```text
transformation/models/
  connectors/<sapo_v2|shopee|misa|gsheet|hug|crm|facebook_*>/   # src_/stg_ (relation giữ nguyên)
  cdm/                          # std_* = canonical layer (pass-through + source_system)
  core/{dims,facts,customer,product,cogs,inventory}/
  packs/{finance,marketplace,facebook_*,crm,hug,sales_playbook}/  # finance gồm overhead + dòng tiền
  tenants/fine_japan/           # chỉ US shipment
  monitoring/
transformation/seeds/taxonomy/  # seed phân loại; seeds/tenants/fine_japan/ (dữ liệu doanh nghiệp cho các pack)
orchestration/connectors/<id>/  # assets, jobs, schedules, sensors, dữ liệu phụ trợ
orchestration/packs/<crm|sales_playbook>/
orchestration/tenants/fine_japan/   # cấu hình riêng (URL sheet, domain Sapo)
orchestration/config/modules.yaml
(sensors/ops/asset_checks/notifications, dbt, serving giữ nguyên vị trí = kernel)
```

## Quyết định đã chốt (13/10/2026)

| Quyết định | Nội dung |
|---|---|
| Phạm vi taxonomy | Chỉ gom về một module, SQL giữ nguyên; luật thành dữ liệu để Đợt 4. **Cập nhật 14/10:** phase 4 chỉ đặc tả + dời seed, không tách macro; bộ máy phân loại là plan riêng ngay sau Đợt 1 ([taxonomy-engine-design.md](taxonomy-engine-design.md), [tổng hợp phản biện](reports/taxonomy-review/synthesis.md)) |
| Contract `std_*` | Chưa enforce; dùng test schema mức warn |
| Đóng gói | Tách thư mục trong một dbt project + package Python theo connector; image/GHCR ở Đợt 2 (plan 260705) |
| Red team | Áp dụng 13 sửa đổi ([red-team-review](reports/red-team-review.md)) |
| Vận hành | Hệ thống chạy hằng ngày như cũ trong suốt plan (mục trên) |
| Pack vs tenant (14/10) | CRM, HUG, phân bổ chi phí chung, dòng tiền là pack sản phẩm không phụ thuộc ngành; kịch bản bán hàng là pack thử nghiệm (chuẩn hoá sau); chỉ US shipment là riêng Fine Japan. Logic là pack, dữ liệu/cấu hình là tenant. Lõi giữ doanh thu; pack finance giữ toàn bộ chi phí và lợi nhuận. Connector lấy dữ liệu, pack dùng dữ liệu, gặp nhau ở `std_*` |

## Quan hệ với plan 260705-1704 (DRAFT, chưa phase nào chạy)

Plan này thay thế phase 2 (cắt import crm → orchestration), phase 3 (kiểm tra import) và phase 6 (boundary doc) của 260705. Phase 0, 1, 4, 5 của 260705 là **Đợt 2** trong roadmap, chạy sau plan này.

## Acceptance Criteria

1. Gate của mọi phase sạch trên shadow trước deploy.
2. Prod: sau mỗi deploy, nightly kế tiếp xanh, không asset check mới đỏ, 76 serving view còn đủ, trạng thái schedule/sensor không đổi.
3. `scripts/checks/check_boundaries.py` pass trên main và fail khi cố ý thêm ref core → `stg_*`, import crm → orchestration, seed trùng tên, hoặc URL cứng trong `orchestration/connectors/**`.
4. Bỏ một connector khỏi `orchestration/config/modules.yaml` chỉ cần sửa file đó, Definitions vẫn load.
5. `transformation/docs/TAXONOMY.md` kiểm kê mọi luật phân loại (vị trí, hash nội dung, dạng luật, đặc trưng, thuộc tính bộ máy, Known divergences); `scripts/checks/check_taxonomy_inventory.py` cảnh báo khi khối đã kiểm kê đổi hoặc có khối phân loại mới; seed phân loại nằm trong `transformation/seeds/taxonomy/`. (Sửa 14/10/2026: bỏ yêu cầu macro hoá, vì bộ máy phân loại sẽ thay các khối `CASE`.)
6. Shadow lake và worktree đã xoá khi đóng plan.

Kết quả đối chiếu (đóng plan 14/10/2026 ~23:00): 1, 3, 4, 5, 6 đạt; 2 đạt với nightly chạy tay sau mỗi deploy (152 serving view; số "76" ở trên là số lúc lập plan), nightly theo lịch 03:00 ngày 15/10 trên `8eb9920f` (`ffb92b66`) xanh, 0 check đỏ mới: **cả 6 tiêu chí đạt**. Chi tiết: [reports/deploy-261014-2249-phase-7-and-closing-report.md](reports/deploy-261014-2249-phase-7-and-closing-report.md).

## Risks chính

| Rủi ro | Giảm thiểu |
|---|---|
| Deploy giữa lúc lịch `*/3` đang chạy | Runbook: dừng container → fast-forward → start; không merge khi container đang chạy |
| Seed bị job prod ghi lại đường dẫn cũ → trùng tên → container không khởi động | `seed_paths.py` + check trùng basename (phase 1, 4) |
| Thư mục rolling không được tạo sau khi đổi thư mục model | Tạo theo manifest (phase 2) + kiểm tra lake trống |
| Golden "sạch" giả | Xoá rolling trước build, kiểm tra `run_results`, checksum cấp dòng, pass full-refresh |
| PII trong bản sao shadow | Thư mục 0700, chạy theo uid, dọn sau mỗi compare và khi đóng plan |

## Ngoài phạm vi (xem roadmap)

Đóng gói image/GHCR/dev-prod, dbt local package, contract enforce, đổi tên `std_*` → `cdm_*`, luật phân loại thành dữ liệu, thống nhất Known divergences, connector mới, report chuẩn ngành, heartbeat, Facebook ingestion.

## Red Team Review

### Session — 2026-10-13
**Findings:** 15 sau gộp trùng (13 accepted, 2 chuyển user quyết và đã quyết) · **Severity:** 6 Critical, 6 High, 3 Medium · Chi tiết: [reports/red-team-review.md](reports/red-team-review.md)

## Reports

- [Scout: orchestration / ingestion / deploy](reports/scout-orchestration-ingestion-deploy.md)
- [Scout: dbt graph / consumers](reports/scout-dbt-graph-consumers.md)
- [Red team review](reports/red-team-review.md)
- [Long-vision roadmap](roadmap.md)
- [Authority & boundary theo component](architecture-boundaries.md)
- [Thiết kế bộ máy phân loại (v2)](taxonomy-engine-design.md) · [tham chiếu](references/taxonomy/) · [phản biện](reports/taxonomy-review/synthesis.md)
