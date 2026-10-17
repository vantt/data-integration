---
title: "Lịch sử giá và tồn kho theo ngày"
description: "Chụp hằng đêm toàn bộ giá và vị trí tồn từ Sapo vào raw append-only (nguồn sự thật, lên off-site), rồi dựng các bảng lịch sử giá, nhật ký đổi giá và vị trí tồn theo ngày, dựng lại được, không đổi số của bảng public hiện có."
status: pending
priority: P2
effort: 2.5d
branch: feat/price-inventory-history
tags: [transformation, ingestion, sapo, inventory, pricing, history, backup]
blockedBy: []
blocks: []
created: 2026-10-15
---

# Lịch sử giá và tồn kho theo ngày

## Overview

User chốt ngày 15/10/2026 là cần lịch sử giá và tồn kho theo ngày. Hiện chưa có lịch sử nào: GC rolling chỉ giữ 3 lần build (F-Q2). Nguồn của hai bảng snapshot cũng đã cũ: payload sản phẩm chỉ được lấy lại khi Sapo đổi `modified_on`, nên `fact_inventory_snapshot` mang tồn kho từ 2023 đến 15/09/2026, có 25 cặp lệch so với sổ kho, và giá có thể đổi mà không ai thấy. Nếu chỉ tích luỹ model hiện có thì sẽ tích luỹ đúng các số cũ đó.

Plan này làm ba việc:
1. Thêm một bước quét đủ sản phẩm Sapo mỗi đêm vào raw append-only `sapo_v2_raw/product_daily_snapshot`. Đây là dữ liệu duy nhất không dựng lại được, và nó nằm trong vùng raw mà plan DR đưa lên off-site.
2. Dựng ba bảng core phái sinh, dựng lại được: `fact_variant_price_daily`, `fact_variant_price_changes` (SCD2, có backfill từ 28/05/2026), `fact_inventory_position_daily`.
3. Dùng `fact_inventory_balance` hiện có cho lịch sử `on_hand` từ 2021.

Thiết kế, số đo và các phương án đã loại: **[design.md](design.md)**.

## Yêu cầu bắt buộc

1. Không làm trên checkout prod. Dùng worktree nhánh `feat/price-inventory-history`; chỉ thử trên shadow hoặc bản sao trong scratch.
2. **Không đổi số của bảng public hiện có.** Chỉ thêm model hoặc asset. Gate S phải cho golden 0 khác biệt trên mọi bảng public hiện có (`scripts/shadow/gate.sh S --allow-new`, thêm `--allow-code-change` ở phase 2 vì có sửa comment).
3. Ranh giới: raw chỉ connector `sapo_v2` đọc, core đọc `cdm/std_*`. Hàng `GIANHAP` và `mac` ở core (số liệu do nguồn cung cấp). Không thêm cột biên; phép tính biên thuộc pack finance.
4. Tài liệu cập nhật **cùng commit** với code của từng phase.
5. Deploy theo runbook "Refactor deploys (shadow-verified)" (`docs/operations/deployment.md:667-748`), vào giờ user duyệt, ngoài khung 02:30–04:00.
6. Không ghi plan ID, số phase hay mã finding vào comment code, tên test hay commit message.
7. Không đọc `.env*`, không đưa dữ liệu khách hàng vào plan, report hay test fixture. Fixture chỉ chứa sản phẩm giả.

## Phases

| # | Phase | File | Effort | Phụ thuộc | Gate | Đụng prod | Cần giờ user duyệt |
|---|---|---|---|---|---|---|---|
| 0 | Chốt ẩn số và câu trả lời của user | [phase-00](phase-00-verify-and-decide.md) | 0.25d | — | — | Chỉ đọc | Không |
| 1 | Chụp hằng đêm vào raw (ingestion + asset + check) | [phase-01](phase-01-nightly-capture-ingestion.md) | 0.75d | 0 | S `--allow-new` (dbt không đổi) | Có (deploy D1) | **Có** |
| 2 | Model lịch sử (connector, cdm, core) + sửa comment sai + tài liệu | [phase-02](phase-02-history-models.md) | 1.25d | 1 (≥2 đêm raw thật trên prod, lake-base làm mới) | S `--allow-new --allow-code-change` | Có (deploy D2) | **Có** |
| 3 | Phối hợp DR, theo dõi 7 đêm, đóng | [phase-03](phase-03-dr-integration-and-observation.md) | 0.25d + 7 đêm | 2; plan DR phase 2 (off-site) để xác minh mục 5 | — | Chỉ đọc | Không |

**Thứ tự ưu tiên:** phase 1 tự nó đã có giá trị và nên deploy sớm nhất, vì mỗi đêm chưa chụp là một ngày mất vĩnh viễn với giá và vị trí tồn. Phase 2 có thể làm sau mà không mất gì, vì nó dựng lại toàn bộ từ raw.

## Phụ thuộc và quyền sở hữu file

```text
0 ─► 1 ─(D1, ≥2 đêm chụp)─► 2 ─(D2)─► 3
                                     └─ chờ DR phase 2 để kiểm off-site
```

| Phase | File sở hữu |
|---|---|
| 1 | `ingestion/src/sapo/products.py` (chỉ tách hàm lấy trang), `ingestion/src/sapo/products_daily_snapshot.py` (mới), `ingestion/run_sapo_v2_product_daily_snapshot.py` (mới), `ingestion/tests/test_products_daily_snapshot.py` (mới), `orchestration/connectors/sapo_v2/{assets.py,__init__.py}`, `orchestration/config/ingestion_sla.yaml`, `docs/architecture/modules.md` §5.2, `docs/analytics-handbook/semantic/freshness.md` |
| 2 | `transformation/models/connectors/sapo_v2/staging/{_sources.yml,_sapo_v2__models.yml}` + 4 model mới, `transformation/models/cdm/staging/` 2 view mới, `transformation/models/core/marts/sales/` (2 model giá mới; sửa comment `fact_variant_prices_snapshot.sql`), `transformation/models/core/marts/inventory/` (1 model mới; sửa comment `fact_inventory_snapshot.sql` nằm ở `marts/sales/`), `transformation/macros/source_or_empty.sql` (mới), `transformation/tests/` (singular test SCD2), `transformation/dbt_project.yml` (biến), `transformation/seeds/capabilities/*.csv`, `orchestration/job_support.py` (`NIGHTLY_ONLY_ASSETS`), `orchestration/connectors/sapo_v2/__init__.py` (`DBT_SOURCE_KEYS`), `scripts/checks/{model_buckets.yaml,public_models.yaml}`, tài liệu (`docs/architecture/modules.md` §7 và mục ngoại lệ dòng 487, `docs/architecture/data-model.md`, `docs/analytics-handbook/domains/product.md`, `docs/analytics-handbook/semantic/{freshness.md,entities.md}`) |
| 3 | Tài liệu DR dùng chung (`docs/operations/backup-and-recovery.md` nếu đã có); cập nhật `roadmap.md` mục lịch sử giá/tồn. Plan DR do chủ của nó sửa |

Phase 1 và 2 cùng đụng `orchestration/connectors/sapo_v2/__init__.py`, nhưng chạy tuần tự (2 sau 1), nên không có sửa song song.

## Tiêu chí chấp nhận (đo được)

1. **Chụp:** trong 7 đêm liên tiếp sau D1, mỗi đêm có đúng một file mới trong `sapo_v2_raw/product_daily_snapshot/`. Số sản phẩm ≥ 98% tổng của Sapo (metadata asset). Asset check freshness xanh, dòng digest buổi sáng có mặt.
2. **Không đổi số:** gate S của phase 1 và phase 2 PASS, golden 0 khác biệt trên mọi bảng public hiện có. Dagster inventory chỉ báo phần thêm (asset mới, selection nightly lớn thêm). Tập `unique_id` dbt của các job `*/3`, `*/10`, `:25` không đổi.
3. **Bảng mới:** sau D2, đêm kế tiếp `fact_variant_price_daily` và `fact_inventory_position_daily` mỗi đêm có thêm đúng một `as_of_date` (= ngày hôm trước theo giờ ICT). Số dòng mỗi ngày nằm trong ±5% của 1.460 và 2.052 (số đo ngày 15/10), hoặc trong mức thay đổi danh mục mà user xác nhận. Test unique và test không chồng khoảng xanh.
4. **Backfill:** `fact_variant_price_changes` có khoảng hiệu lực từ 28/05/2026 cho ≥ 95% cặp (variant, bảng giá) đang có giá > 0. Ở các cặp chỉ có ảnh chụp, giá hiện hành khớp 100% với `fact_variant_prices_snapshot` (cùng ngày, giá > 0).
5. **Idempotent:** chạy tay capture lần thứ hai trong cùng ngày (trong shadow, bằng fixture) không tạo `as_of_date` mới và không nhân đôi dòng. Bản mới nhất được giữ.
6. **Dựng lại được:** xoá rolling và bảng `src_` mới rồi build lại trên shadow, ba bảng mới cho golden giống hệt bản trước. Build trên lake không có raw mới (lake-P và lake rỗng) vẫn xanh, ba bảng mới rỗng.
7. **Backup:** `restic ls latest` (khi DR phase 2 đã chạy) có đường dẫn `sapo_v2_raw/product_daily_snapshot/`. Bảng phân loại của DR có dòng cho nó.
8. **Tài liệu:** comment sai ở `fact_variant_prices_snapshot.sql:6-8,16` và `fact_inventory_snapshot.sql:10-11`, cùng `modules.md:487`, đã được sửa cho đúng thực tế.

## Rủi ro chính

| Rủi ro | Khả năng × tác động | Giảm thiểu |
|---|---|---|
| Nightly lỡ một đêm thì mất vĩnh viễn ngày đó (giá, vị trí tồn) | Trung bình × Cao | Freshness check SLA 28h, dòng digest, Lark khi asset fail. Chạy lại trước 06:00 vẫn giữ được ngày D. `on_hand` vẫn có từ sổ kho |
| Sapo dời trang trong lúc quét, gây thiếu hoặc trùng sản phẩm | Thấp × Trung bình | Khử trùng `entity_id`; so với tổng Sapo, thiếu > 2% thì WARN |
| Tách hàm lấy trang làm hỏng batch sản phẩm hiện có | Thấp × Cao | Chỉ dời code, có pytest với fixture HTTP cho cả hai resource. Shadow không có mạng, nên theo dõi nightly đầu tiên |
| Model mới làm vỡ build khi raw chưa có (shadow, cài mới, dựng lại DR) | Trung bình × Trung bình | Macro `source_or_empty`; gate chạy lake-P và lake rỗng |
| Off-site chưa chạy, lịch sử chỉ ở cùng ổ | Cao (tạm thời) × Cao | 7 bản backup cục bộ; DR phase 2/5 là phụ thuộc đóng plan |
| Người dùng hiểu nhầm số ở `fact_inventory_snapshot` cũ | Có sẵn × Trung bình | Ghi rõ trong tài liệu; Q6 để user quyết |

## Rollback

Mỗi deploy rollback theo runbook (`git revert` phạm vi đã deploy, `deployment.md:732-748`). Phần còn lại sau rollback được liệt kê trong từng phase. Raw đã chụp **không xoá** khi rollback: nó là lịch sử, và không có ai khác đọc nó.

## Câu hỏi mở cho user

1. **Q1. Cần lịch sử xa đến đâu?** Lịch sử `on_hand` có từ 2021. Giá chắc chắn có từ 28/05/2026. Vị trí tồn (khả dụng, đang giữ, đang về) chỉ có từ ngày deploy phase 1. Như vậy có đủ chưa, hay cần tìm thêm nguồn cho giá trước 28/05/2026 (phase 0 kiểm API Sapo)?
2. **Q2. Giữ raw ảnh chụp bao lâu?** Đề xuất: giữ mãi, khoảng 70–275 MB/năm tuỳ Q3. Có muốn đặt giới hạn, ví dụ 3 năm, không?
3. **Q3. Payload đầy đủ hay gọn?** Gọn (chỉ giá và tồn theo variant) nhỏ hơn khoảng 2–4 lần. Đầy đủ giữ được thêm tên, trạng thái, thuộc tính, phòng khi sau này cần lịch sử danh mục. Đề xuất: gọn.
4. **Q4. Giờ chốt ngày (`history_day_cutoff_hour`)** mặc định 06:00. Nightly chạy muộn sau giờ này thì ngày hôm trước bị coi là thiếu. Có cửa hàng nào mở hoặc bán trước 06:00 không?
5. **Q5. Deploy phase 1 sớm**, tách khỏi phase 2, để bắt đầu tích luỹ ngay. User đồng ý không, và chọn giờ deploy nào?
6. **Q6. `fact_inventory_snapshot` và `mart_inventory_health` đang dùng tồn kho cũ** (25 cặp lệch sổ kho, mốc dữ liệu tới 15/09). Có muốn một plan riêng chuyển hai bảng này sang đọc ảnh chụp mới không? Việc đó **đổi số** dashboard tồn kho, nên cần gate S và user duyệt.

## Đã chốt (user, 15/10/2026 ~17:50)

- Q1: lịch sử giá từ 28/05/2026 là đủ; không tìm thêm nguồn.
- Q2: giữ raw ảnh chụp **vĩnh viễn** (~70–275 MB/năm).
- Q3: payload **gọn** (chỉ giá và tồn).
- Q4: giờ chốt ngày **06:00**.
- Q5: deploy **phase 1 tách riêng, sớm nhất có thể** (mỗi đêm chưa chụp là mất dữ liệu); cần user duyệt giờ.
- Q6: **có** — lập plan riêng, ưu tiên, chuyển `fact_inventory_snapshot` / `mart_inventory_health` / dashboard tồn kho sang dữ liệu chụp mới (đổi số từ cũ sang đúng; qua gate S, user duyệt danh sách đổi).
