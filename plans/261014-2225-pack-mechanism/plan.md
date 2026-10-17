---
title: "Cơ chế pack: pack_ref, bật/tắt pack, tenant_ref, khai báo khả năng connector, lớp nhãn chuẩn"
description: "Cho phép bật/tắt từng pack mà lõi vẫn build, cắt mọi hook lõi → pack/seed tenant qua điểm cắm có hợp đồng cột, khai báo connector cung cấp gì và thêm cột *_std xem trước cho report chuẩn, không đổi một con số nào của Fine Japan."
status: completed
priority: P1
effort: 4d
branch: feat/pack-mechanism
tags: [refactor, dbt, orchestration, modularization]
blockedBy: [261013-1751-modularize-data-platform-suite]
blocks: []
created: 2026-10-14
---

# Cơ chế pack

## Overview

Việc số 1 trong "Thứ tự ưu tiên sau Đợt 1" của [roadmap](../261013-1751-modularize-data-platform-suite/roadmap.md) (user chốt 14/10/2026). Sau Đợt 1, pack (`crm`, `hug`, `finance`, `sales_playbook`, `marketplace`, `facebook_*`) đã có thư mục riêng nhưng **chưa tắt được**: lõi vẫn `ref()` thẳng vào model của pack, lõi đọc seed của tenant, và job của connector import asset của pack `crm`. Plan này làm cho:

1. Mỗi pack bật/tắt bằng một danh sách (`modules.yaml` → biến dbt `enabled_packs` + `+enabled` theo thư mục pack; Dagster đã nạp pack theo `modules.yaml`).
2. Lõi đọc pack chỉ qua `pack_ref(pack, model, columns)`: pack bật → `ref()`; pack tắt → quan hệ rỗng đúng kiểu cột. Danh sách cột là hợp đồng lõi ↔ pack, có test.
3. Lõi đọc seed tenant chỉ qua `tenant_ref`: lõi có seed mặc định rỗng đúng cột, tenant ghi đè.
4. Connector không import pack; pack `crm` tự đăng ký asset chạy sau serving.
5. Có khai báo "connector cung cấp gì" và model `mart_capabilities` (khai báo / bật / quan sát được), đầu vào cho catalog report.
6. Có lớp ánh xạ "nhãn hiện có → mã chuẩn" (`taxonomy_label`, `taxonomy_canonical`) và model `lbl_<domain>` mang cột `*_std` (bản xem trước, chưa chốt).

Với Fine Japan (mọi pack bật): golden 0 khác biệt, tên relation và cột của mọi bảng public giữ nguyên.

## Yêu cầu thiết kế và tài liệu hoá (bắt buộc)

**Làm tới đâu, thiết kế và tài liệu hoá chi tiết tới đó** (yêu cầu của user 13/10/2026, ghi ở đầu mọi phase). Bản sống là `docs/architecture/modules.md`; mỗi phase cập nhật mục của mình **cùng commit** với code, cùng README của pack/connector bị đụng và `transformation/AGENTS.md` khi quy tắc đổi. Phase 9 chỉ còn rà soát và viết ADR.

## Yêu cầu vận hành liên tục (bắt buộc, kế thừa Đợt 1)

1. Không làm việc trên checkout prod `/home/vantt/app/fg-dataware-house`. Làm trên worktree nhánh `feat/pack-mechanism` (tạo từ `main` sau khi Đợt 1 đóng), kiểm chứng trên shadow lake cô lập.
2. Prod chỉ đổi qua runbook "Refactor deploys (shadow-verified)" trong `docs/operations/deployment.md`: dừng `data_platform`, `merge --ff-only`, start lại. Không deploy trong khung nightly 02:30–04:00, không deploy khi nightly prod đang đỏ vì lý do khác.
3. Sau mỗi deploy: nightly kế tiếp xanh, không asset check mới đỏ, đủ serving view, trạng thái schedule/sensor giống trước deploy. Nếu không: rollback theo runbook, không sửa nóng trên prod.
4. Không đổi `requirements`, Dockerfile hay image prod.
5. **Không thêm serving view nào** trong plan này: model mới đều là `table` trong warehouse (cùng mẫu `int_product_velocity_trend`), nên `build_serving_db` không gặp `SCHEMA_DRIFT: new table` (`scripts/provisioning/refresh_rolling.py:203-209`) và không cần chạy `bootstrap_serving_views.py`. Đưa `lbl_*`/`mart_capabilities` lên serving là việc của plan report.

## Bất biến dữ liệu

Profile Fine Japan (mọi pack bật, tenant `fine_japan`): không đổi một con số nào, không đổi tên/cột/kiểu/thứ tự cột của 83 bảng public trong `scripts/checks/public_models.yaml`. Mọi phase đều trả lời "có đổi số không" và câu trả lời phải là **không**.

## Phases

| # | Phase | File | Effort | Phụ thuộc | Gate | Đổi số |
|---|---|---|---|---|---|---|
| 1 | Dựng lại shadow + spike cơ chế dbt (ref trong `if`, `+enabled` theo biến, seed rỗng, test trỏ node tắt) | [phase-01](phase-01-spike-and-shadow-setup.md) | 0.25d | Đợt 1 xong | — (không deploy) | Không |
| 2 | Công tắc pack: `enabled_packs`, `+enabled`, `pack_enabled`/`pack_ref`, hợp đồng cột, check đồng bộ `modules.yaml` ↔ dbt | [phase-02](phase-02-pack-switch-mechanism.md) | 0.5d | 1 | M | Không |
| 3 | Áp `pack_ref` cho 4 hook lõi đơn giản (`dim_customers`, `dim_staff`, `dim_sku_alias`, `mart_data_quality`) | [phase-03](phase-03-pack-ref-core-hooks.md) | 0.5d | 2 | M + compiled SQL giống hệt | Không |
| 4 | Tách `mart_sku_economics_monthly` (lõi: doanh số/tốc độ; finance: giá vốn/biên) + profile "lõi trần" vào gate | [phase-04](phase-04-split-sku-economics.md) | 0.75d | 3 | M `--allow-new --allow-code-change` | Không |
| 5 | `tenant_ref` cho 3 seed tenant mà lõi đọc | [phase-05](phase-05-tenant-ref-seeds.md) | 0.5d | 2 (dùng profile của 4) | M + compiled SQL giống hệt | Không |
| 6 | Đảo chiều `crm_cache_refresh`: pack đăng ký asset sau serving | [phase-06](phase-06-orchestration-pack-registration.md) | 0.25d | 2 | M (inventory Dagster giống hệt) | Không |
| 7 | Khai báo khả năng của connector + `mart_capabilities` | [phase-07](phase-07-connector-capabilities.md) | 0.5d | 2 | M `--allow-new` | Không |
| 8 | Lớp nhãn chuẩn: `taxonomy_canonical`, `taxonomy_label`, `lbl_<domain>` | [phase-08](phase-08-label-std-mapping.md) | 0.5d | 5 | M `--allow-new` | Không |
| 9 | ADR, rà tài liệu, allowlist cuối, dọn shadow | [phase-09](phase-09-docs-adr-close.md) | 0.25d | 1–8 | — | Không |

**Tổng ~4 ngày công**, lớn hơn mức 1–2 ngày dự kiến ở roadmap. Mức roadmap tính `pack_ref` + 2 hook + khai báo connector; phạm vi user chốt nay gồm thêm tách `mart_sku_economics_monthly`, 2 hook phát hiện thêm (`dim_sku_alias`, `mart_data_quality`, bắt buộc để lõi build được khi tắt pack), `tenant_ref`, đảo chiều orchestration, `mart_capabilities` và lớp nhãn. Thời gian chạy gate (mỗi lần build vài lake) đã tính trong từng phase.

**Thứ tự và song song.** Chạy tuần tự 1 → 9 trên một worktree. Phase 6 chỉ đụng `orchestration/` nên về nguyên tắc làm song song với 3–5 được, nhưng gate và deploy vẫn tuần tự vì baseline luôn là commit được chấp nhận gần nhất (`refactor-safety-harness.md` §9.2).

**Điểm deploy (gộp để ít lần dừng):** D1 sau phase 4 (cơ chế + hook + tách mart), D2 sau phase 6 (`tenant_ref` + orchestration), D3 sau phase 8 (model mới). Mỗi điểm deploy chạy lại gate trên commit đầu của lô. Phase nào gate fail thì lô dừng ở phase trước đó.

## Nhật ký deploy (tiêu chí 7)

| Đợt | Nội dung | Commit / main | Thời điểm | Kết quả |
|---|---|---|---|---|
| D1 + D2 (gộp một lần dừng, user duyệt 15/10) | Phase 1–6 | `b6bb06b6` | 15/10/2026 10:34 (stop 10:34:05 → start 10:34:16) | Xanh: instigator 26/26, serving 152, nightly tay `770f86bd` 55/55, 498 check (11 mới, xanh), 0 run lỗi. Báo cáo `reports/deploy-261015-1034-phases-1-6-report.md` |
| D3 | Phase 7 + 8 + `mart_capabilities` chỉ nightly + phase 9 (`32fcaa17`), deploy cùng bản sửa freshness (`91dacc2a`) | `9c25d02a` | 15/10/2026 11:28 (stop 11:28:09 → start 11:28:20) | Xanh: instigator 0 diff, 0 run lỗi, nightly tay `bf000c1b` 55/55, 539 check, 0 đỏ mới; `products_batch` freshness hết đỏ. Gate M PASS (golden 83/83, compiled model cũ 0 đổi, labels_mapped 5/5, lõi trần xanh). Nghiệm thu: `reports/phase-09-acceptance.md` |

## Phụ thuộc giữa các phase

```text
Đợt 1 (phase 7 xong, shadow đã xoá) ─► 1 spike ─► 2 công tắc ─┬─► 3 hook ─► 4 tách mart + profile lõi trần ─► D1
                                                              ├─► 5 tenant_ref (cần profile của 4) ─┐
                                                              ├─► 6 orchestration ──────────────────┴─► D2
                                                              └─► 7 capabilities ─► 8 nhãn (cần tenant_ref) ─► D3 ─► 9
```

## Luồng dữ liệu sau plan

```text
modules.yaml ──(check đồng bộ)── dbt_project.yml vars: enabled_packs, enabled_connectors, tenant
      │                                   │
      ▼                                   ▼
Dagster: load_enabled()          dbt: +enabled theo thư mục pack
  connectors/<id>/jobs ─► job_support.after_serving_selection() ◄─ pack AFTER_SERVING_ASSETS
                                  │
std_* ─► core ──pack_ref(pack, model, columns)──► packs/<id>   (tắt → SELECT rỗng đúng kiểu)
          │  └─tenant_ref(seed)──► seeds/tenants/<tenant>/     (không có tenant → seed __default rỗng)
          ├─► lbl_<domain> (nhãn + *_std) ◄── taxonomy_label (tenant) + taxonomy_canonical (sản phẩm)
          └─► monitoring/mart_capabilities ◄── connector_capabilities + capability_catalog (seed)
```

## Acceptance Criteria

1. Profile Fine Japan: gate pass ở mọi phase; golden 0 khác biệt (83/83); với phase 3 và 5, `dbt_inventory.py compiled-diff` **không cờ** trả 0 (SQL đã compile giống hệt sau chuẩn hoá khoảng trắng).
2. Profile "lõi trần" (`--vars '{enabled_packs: [], tenant: ""}'`) build xanh trên lake mất thư mục rolling; không còn model pack nào trong manifest; danh sách bảng public khác baseline trùng khớp danh sách dự kiến trong phase 4 (chỉ cột lấy từ pack thành NULL/0 và bảng của pack vắng mặt).
3. `scripts/checks/boundary_allowlist.yaml` không còn dòng `core -> pack:*` nào, không còn 3 dòng `dbt-seed` lõi → seed tenant, không còn 4 dòng `orch-import` connector → `orchestration.packs.crm`. `check_boundaries.py` fail khi cố ý thêm `ref()` thẳng từ lõi vào model pack, `ref()` thẳng vào seed tenant, hoặc khi `modules.yaml` lệch biến dbt.
4. Mọi hợp đồng cột trong `pack_contracts()` có test dbt khớp tên và kiểu với model pack thật.
5. `mart_capabilities` có một dòng cho mỗi khả năng trong catalog với 3 mức `is_declared`, `is_pack_enabled`, `is_observed` và `status`; trên Fine Japan mọi khả năng mà connector đang bật khai báo đều `is_observed = true` (khả năng nào không có dữ liệu thì ghi lý do trong phase 7).
6. `taxonomy_label`: test (domain, label) duy nhất pass; mọi `label_std` thuộc `taxonomy_canonical` cùng domain; mọi nhãn Fine Japan của 5 domain đều có mã (0 dòng `UNMAPPED` trên shadow).
7. Prod: sau mỗi điểm deploy, nightly kế tiếp xanh, không asset check mới đỏ, 76 serving view còn đủ, trạng thái schedule/sensor không đổi, job connector vẫn chạy `crm_cache_refresh`.
8. Tài liệu khớp code: `docs/architecture/modules.md` (§3, §5, §8, §9, §10), README các pack và `orchestration/packs/README.md` (mục "Turning a pack off"), `transformation/AGENTS.md`, `transformation/docs/TAXONOMY.md`, ADR mới.

## Risks chính

| Rủi ro | Khả năng × Tác động | Giảm thiểu |
|---|---|---|
| `ref()` trong khối `if` không cho lineage như mong đợi, hoặc `+enabled` dạng Jinja không ra kiểu bool | Thấp × Cao | Spike phase 1 trước mọi code; dự phòng đã định: hai bản model bật/tắt bằng `enabled` (phase 1 §Dự phòng), lọc `as_bool` |
| Tách `mart_sku_economics_monthly` làm lệch số thực (thứ tự cộng số thực, kiểu sau khi ghi parquet) | Trung bình × Cao | Lõi tính mọi cột doanh số một lần, finance chỉ đọc lại; golden làm tròn 6 chữ số; gặp lệch thì `golden_snapshot.py keyed-diff` trước khi sửa; không deploy khi chưa 0 khác biệt |
| `modules.yaml` và `dbt_project.yml` lệch nhau (hai nơi khai báo) | Trung bình × Trung bình | Check đồng bộ trong `check_boundaries.py` (chạy trong gate và `run-all.sh`); lỗi in sẵn khối cần dán |
| Test mới mức `error` làm đỏ nightly prod | Thấp × Cao | Test hợp đồng là `error` (gate chứng minh pass trước deploy); test "nhãn đã ánh xạ" là `warn` để nhãn mới do seed đổi không làm đỏ nightly, gate đọc `run_results.json` và đòi 0 cảnh báo cho test đó |
| Model mới tạo thư mục rolling → `SCHEMA_DRIFT` đỏ job đầu tiên sau deploy | Thấp × Trung bình | Mọi model mới là `materialized='table'`, không có `location`; gate kiểm không có thư mục rolling mới |
| Bật một pack mà không bật pack nó phụ thuộc (hug → finance, finance → marketplace, sales_playbook → crm) | Trung bình × Thấp | Ngoài phạm vi: cạnh pack → pack vẫn là `ref()`; dbt parse báo lỗi rõ (fail closed). Ghi trong `modules.md` §8 cùng các phụ thuộc đã biết |

## Rollback

Mỗi phase revert được độc lập bằng `git revert` theo runbook; không phase nào xoá hay đổi tên relation đang có. Thứ bị bỏ lại sau rollback (vô hại, xoá được bằng tay): bảng `int_sku_sales_monthly`, `lbl_*`, `mart_capabilities` và các seed mới trong `main_marts`/`main` của warehouse. Chi tiết từng phase ở mục Rollback của phase.

## Ngoài phạm vi

Bộ máy luật phân loại (taxonomy rule engine), registry/catalog report, chuẩn hoá CRM/HUG, chuyển cạnh pack → pack sang `pack_ref`, bật/tắt tenant model (US shipment) và hook `mart_data_quality` → `fact_us_shipment_economics`, đưa model mới lên serving, CLI `doctor` kiểm khả năng lúc cài (Đợt 5), dbt package thật cho từng pack (Đợt 3).

## Nguồn

- Plan cha và quyết định: [plan.md](../261013-1751-modularize-data-platform-suite/plan.md), [roadmap.md](../261013-1751-modularize-data-platform-suite/roadmap.md) (mục "Thứ tự ưu tiên sau Đợt 1", "Module sản phẩm từ Fine Japan", đoạn "Cơ chế pack"), [phase-06](../261013-1751-modularize-data-platform-suite/phase-06-fine-japan-tenant-overlay.md), [phase-07](../261013-1751-modularize-data-platform-suite/phase-07-docs-adr-enforcement.md).
- Thiết kế: [taxonomy-engine-design.md](../261013-1751-modularize-data-platform-suite/taxonomy-engine-design.md) §3.3–3.4, §3.7, §8; [report-product-design.md](../261013-1751-modularize-data-platform-suite/report-product-design.md) §4 ②.
- Vận hành: `docs/operations/deployment.md` mục "Refactor deploys (shadow-verified)"; `docs/operations/refactor-safety-harness.md` (§6, §9) và `scripts/shadow/gate.sh`.

## Ghi nhận từ phase 1 (spike, 14/10/2026 23:20)

Spike đạt cả 7 cơ chế (báo cáo `reports/spike-dbt-pack-switch.md`). Điều chỉnh cho các phase sau:

- `var()` trong `dbt_project.yml` không đọc được khối `vars:` của chính nó → lặp danh sách mặc định trong `+enabled` của từng pack; check đồng bộ `modules.yaml` ↔ `vars.enabled_packs` ↔ mặc định mỗi pack.
- Node tắt vẫn có trong `manifest.nodes` (`enabled=false`) → script inventory/boundaries phải lọc (phase 2).
- **Phụ thuộc pack → pack phải khai báo:** `hug` cần `finance` (tắt finance mà không tắt hug thì parse lỗi). Ghi trong `modules.yaml` và kiểm tự động.
- **Tắt finance làm suy giảm lõi:** `dim_sku_alias` mất alias (đang inner join dữ liệu MISA) và `int_product_velocity_trend` / `mart_product_health` rỗng cho tới khi tách `mart_sku_economics_monthly` (phase 4). Phase 3–4 phải làm cho lõi không phụ thuộc MISA ở các chỗ này (alias SKU không có MISA thì vẫn có alias từ nguồn khác hoặc rỗng nhưng không làm rỗng bảng sản phẩm); profile "lõi trần" kiểm số dòng các bảng này.

## Đã chốt (user, 14/10/2026 ~22:46)

- `implied_gross_margin_pct`, `is_below_cost` tạm giữ ở lõi, ghi ngoại lệ (không đổi bảng public).
- Tắt pack finance: cột lợi nhuận của khách để trống (NULL), không 0; Fine Japan không đổi số.
- Thêm vào phạm vi 2 hook mới phát hiện: `dim_sku_alias` → `int_misa_sales_lines`, `mart_data_quality` → `fact_order_economics`.
- Nhãn neo tạm: CROSSBORDER → OTHER, PARTNER → TRADE, System và CrossBorder Fulfillment → NON_SALES, Other → OTHER.
- `lbl_*` và `mart_capabilities` chưa đưa ra serving, chờ plan report.

## Câu hỏi mở cho user

1. **`implied_gross_margin_pct`, `is_below_cost` (bảng public `fact_variant_prices_snapshot`).** Dời hai cột sang finance buộc đổi một bảng public: bảng này tích luỹ ảnh chụp hằng ngày và serving view đọc gộp mọi file parquet theo `union_by_name`, nên bỏ cột làm các ngày cũ vẫn có giá trị còn ngày mới thành NULL. Hai cột không đọc pack nào (chỉ là phép tính trên giá nhập GIANHAP của Sapo) và không có người đọc nào trong repo. Đề xuất: **giữ nguyên trong plan này**, ghi là ngoại lệ có lối ra trong `modules.md` §7, dời khi plan report định nghĩa chỉ tiêu biên theo bảng giá trong finance. Phương án khác: dời ngay, chấp nhận đổi bảng public (gate S, đọc khác biệt thay vì đòi PASS). Xem phase 4 §"Quyết định cần user".
2. **Giá trị khi tắt finance:** `dim_customers.lifetime_gross_profit`/`lifetime_contribution_margin` hiện `COALESCE(..., 0)`. Đề xuất: tắt finance thì **NULL** (đúng nguyên tắc "thiếu giá vốn thì để trống, không coi là 0" của report-product-design §4 ①); Fine Japan không đổi vì nhánh bật giữ nguyên SQL. Đồng ý?
3. **Hai hook chưa có trong danh sách của user** nhưng phải cắt để lõi build được khi tắt finance: `dim_sku_alias` → `int_misa_sales_lines` (mã MISA cho alias VTS→VCS) và `mart_data_quality` → `fact_order_economics` (đếm đơn có giá vốn/phí sàn). Plan áp `pack_ref` cho cả hai (phase 3). Đồng ý đưa vào phạm vi?
4. **Neo nhãn chưa rõ** (bản xem trước, đổi được sau): `customer_type = CROSSBORDER` (đề xuất `OTHER`, chờ nghiệp vụ theo taxonomy-engine-design §9), `PARTNER` (đề xuất nút cha `TRADE`), `channel_format = CrossBorder Fulfillment` và `System` (đề xuất `NON_SALES`), `Other` (đề xuất `OTHER`). Chi tiết ở phase 8.
5. **Đưa `lbl_*` và `mart_capabilities` lên serving ngay** (cần chạy `bootstrap_serving_views.py` lúc dừng Metabase trong cửa sổ deploy) hay để plan report làm? Đề xuất: để plan report, theo quyết định #1 của taxonomy-engine-design §8 (`*_std` chưa lên mart public cho tới khi có dữ liệu doanh nghiệp thứ hai).
