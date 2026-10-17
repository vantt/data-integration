---
phase: 2
title: "Macro bộ máy: hit policy, logic ba giá trị, hai lớp, ruleset_version, selftest"
status: pending
priority: P2
effort: "2d"
dependencies: [1]
---

# Phase 2: Macro bộ máy

> **Yêu cầu bắt buộc của user (13/10/2026): làm tới đâu, thiết kế và tài liệu hoá chi tiết tới đó.** Tài liệu đi cùng commit với code.
>
> **Tài liệu phải cập nhật trong phase này:** `docs/architecture/taxonomy-engine.md` mục "Hiện thực MVP" (ngữ nghĩa đánh giá, hit policy, mã dành riêng, cột đầu ra, `ruleset_version`, cách chạy selftest); `docs/architecture/modules.md` §9 (macro `macros/taxonomy/`, số model theo bucket ở §3 tăng 4 model tắt); `transformation/docs/TAXONOMY.md` §2.2 (dòng "luật dữ liệu qua bộ máy" và trỏ tới tài liệu bộ máy).

## Mục tiêu

Một macro sinh toàn bộ SQL của `lbl_<domain>` từ registry, đánh giá luật đúng logic SQL ba giá trị, hỗ trợ FIRST/UNIQUE/COLLECT, trộn hai lớp, và tự kiểm bằng dbt unit test trên các domain selftest. Phase này **không** tạo domain thật nào.

## Ngữ nghĩa phải hiện thực (đặc tả)

1. **Đối tượng:** tập khoá của model đặc trưng đầu tiên trong `features` của domain; các model đặc trưng khác `LEFT JOIN` theo khoá.
2. **Điều kiện:** mỗi dòng luật có `feature` cho ra `TRUE`/`FALSE`/`NULL` giống hệt biểu thức SQL tương ứng: `like` → `f LIKE value` (không `ESCAPE`, phân biệt hoa thường); `eq` → `f = value`; `in`/`not_in` → `f IN (...)`/`f NOT IN (...)` (NULL khi `f` NULL); `between` → `f >= value AND f < value_to` (đầu trống bỏ qua); `starts_with`, `contains` → `starts_with`/`contains` của DuckDB (NULL khi `f` NULL); `regex` → `regexp_matches`; `is_null` → `f IS NULL` (không bao giờ NULL); `has` → `list_contains(f, value)` với `f` không NULL. `value` ép về kiểu khai báo của đặc trưng.
3. **AND trong luật (ba giá trị):** `FALSE` nếu có điều kiện `FALSE`; ngược lại `NULL` nếu có điều kiện `NULL`; ngược lại `TRUE`. **Không** dùng `bool_and` (bỏ qua NULL). Luật không có điều kiện là `TRUE`.
4. **Luật hiệu lực:** hợp hai seed, gắn `source_layer` (`tenant`, `product`), loại mọi `rule_id` có dòng `enabled=false` ở bất kỳ lớp nào. Thứ tự xét: lớp tenant trước, rồi `priority`, rồi `rule_id`.
5. **Hit policy** (chỉ luật có kết quả `TRUE` mới tính là khớp, giống `CASE WHEN`):
   - FIRST: luật khớp đầu tiên theo thứ tự ở mục 4.
   - UNIQUE: như FIRST (tất định), kèm cột `n_hits`; test `n_hits <= 1` mức `warn`.
   - COLLECT (`cardinality: multi`): mỗi nhãn khớp một dòng, `rule_id` là luật khớp đầu tiên của nhãn đó.
6. **Mã dành riêng:** thiếu đặc trưng trong `required_features` → `UNKNOWN`, không xét luật; không luật nào khớp → `UNMAPPED`, `rule_id` NULL. `label_std` của hai mã này là chính nó.
7. **Cờ khớp:** với mỗi nhãn `X` trong `matched_flags`, cột `matched__<x>`: `TRUE` nếu có luật nhãn `X` khớp, ngược lại `NULL` nếu có luật nhãn `X` cho `NULL`, ngược lại `FALSE`. Không phụ thuộc thứ tự ưu tiên (đúng ngữ nghĩa phép OR của `is_us_gift_recipient`).
8. **Đầu ra** `lbl_<domain>`: `<khoá>`, `label` (đặt tên cột là tên domain gốc, ví dụ `customer_type`), `label_std` (join `taxonomy_label` theo `label_set`), `rule_id`, `source_layer`, `ruleset_version`, các `matched__*`, `n_hits` (UNIQUE).
9. **`ruleset_version`:** `md5` của chuỗi ghép có thứ tự mọi dòng luật hiệu lực của domain (gồm cả hai lớp và các dòng tắt), một giá trị cho cả domain.

Phác thảo SQL tham chiếu: review-data-architect §A.4 (đã kiểm trên code thật). Không sao chép phác thảo đó vào code mà không giữ đủ chín điểm trên.

## Files

- Create: `transformation/macros/taxonomy/taxonomy_registry.sql` — đọc `var('taxonomy')`, trả domain/feature, `exceptions.raise_compiler_error` khi domain hoặc đặc trưng không khai báo.
- Create: `transformation/macros/taxonomy/taxonomy_rules.sql` — CTE luật hiệu lực của một domain (mục 4) và `ruleset_version` (mục 9).
- Create: `transformation/macros/taxonomy/taxonomy_condition.sql` — biểu thức đánh giá một điều kiện theo `(feature, op)`; chỉ sinh nhánh cho đặc trưng khai báo của domain và toán tử hợp kiểu.
- Create: `transformation/macros/taxonomy/taxonomy_label_model.sql` — macro chính (mục 1–8).
- Create: `transformation/macros/taxonomy/taxonomy_entity_labels.sql` — sinh `UNION ALL` các `lbl_*` của domain không phải selftest (model dùng ở phase 3).
- Create: `transformation/models/core/intermediate/taxonomy/selftest/feat_taxonomy_selftest.sql`, `lbl_selftest_first.sql`, `lbl_selftest_unique.sql`, `lbl_selftest_collect.sql` — mỗi file là `config(enabled=var('taxonomy_selftest'), materialized='table', tags=['taxonomy_selftest'])` cộng một lời gọi macro.
- Create: `transformation/models/core/intermediate/taxonomy/selftest/_taxonomy_selftest.yml` — unit test.
- Create: `transformation/tests/fixtures/` — CSV fixture cho selftest nếu dict quá dài.
- Modify: `transformation/dbt_project.yml` — `vars.taxonomy_selftest: false`; registry thêm đặc trưng `feat_taxonomy_selftest` (cột `s_text varchar`, `s_text2 varchar`, `s_num double`, `s_list varchar[]`) và ba domain selftest (`selftest: true`).
- Modify: `scripts/checks/model_buckets.yaml` — 4 model selftest → `core`.
- Modify: `scripts/checks/run-all.sh` (do Đợt 1 phase 7 tạo) — thêm bước chạy unit test selftest. [UNVERIFIED: tên và nội dung file sau Đợt 1.]
- Modify: tài liệu ở đầu file.

## Các bước

1. Viết `taxonomy_registry` và `taxonomy_rules`; kiểm bằng `dbt compile --select lbl_selftest_first --vars '{taxonomy_selftest: true}'` trên shadow rằng `ref()` tới hai seed luật, bảng nhãn và model đặc trưng có trong `depends_on` của manifest.
2. Viết `taxonomy_condition` theo mục 2; viết `taxonomy_label_model` theo mục 3–9.
3. Khai báo ba domain selftest: `selftest_first` (FIRST, `required_features: [s_text2]`, `matched_flags: [A]`), `selftest_unique` (UNIQUE), `selftest_collect` (COLLECT, multi).
4. Viết unit test (mỗi ca một test, tên mô tả hành vi, không mã plan):
   - mỗi toán tử với giá trị khớp, không khớp, và đặc trưng NULL (kết quả NULL hay FALSE đúng như SQL);
   - `like` với `_` khớp ký tự bất kỳ; `like` phân biệt hoa thường;
   - luật hai điều kiện: `TRUE AND NULL` không khớp, rơi xuống luật sau;
   - FIRST: hai luật cùng khớp chọn luật lớp tenant trước luật lớp sản phẩm, rồi `priority` nhỏ hơn;
   - luật lớp sản phẩm bị tắt bởi dòng `enabled=false` của lớp tenant;
   - luật không điều kiện làm mặc định;
   - không luật nào khớp → `UNMAPPED`; đặc trưng bắt buộc NULL → `UNKNOWN`;
   - UNIQUE: hai luật khớp cho `n_hits = 2`;
   - COLLECT: một đối tượng ra hai dòng hai nhãn; đối tượng không khớp ra một dòng `UNMAPPED`;
   - `matched__a`: TRUE / NULL / FALSE đúng ba trường hợp;
   - `ruleset_version` khác nhau giữa hai bộ luật chỉ khác một `priority`.
5. Chạy selftest trong shadow: `run-shadow.sh <worktree> <lake-B> dbt build --select tag:taxonomy_selftest --vars '{taxonomy_selftest: true}'`.
6. Đo thời gian chạy unit test; ghi lại để quyết định ở phase 3 có cần loại unit test khỏi prod không.
7. Cập nhật tài liệu, commit.

## Verification

- Mọi unit test selftest pass (bước 5).
- Gate: `scripts/shadow/gate.sh S --allow-new`: golden 83/83, compiled SQL model hiện có không đổi; model selftest xuất hiện trong inventory dưới dạng tắt; lake trống và full-refresh pass. Prod build (var mặc định) không tạo bảng selftest nào.
- `check_boundaries.py` pass (model mới có bucket).
- `check_taxonomy_inventory.py` không có `WARN new` (macro không có `CASE ... END AS <cột taxonomy>`).

## Đổi số?

**Không.** Model selftest tắt ở mọi build thật; macro chưa được model thật nào gọi.

## Rollback

Chưa lên prod. Revert commit trên nhánh.

## Rủi ro

| Rủi ro | Giảm thiểu |
|---|---|
| Unit test trên model tắt không chạy được | Bật bằng `--vars` khi chạy test; nếu dbt bỏ qua unit test của model bật bằng var, chuyển selftest thành model bật luôn nhưng đọc fixture rỗng (vẫn không ảnh hưởng mart) |
| `CASE` sinh theo mọi cặp đặc trưng × toán tử làm SQL dài | Chỉ sinh nhánh hợp kiểu; với subject khách (khoảng 7 nghìn dòng × khoảng 20 điều kiện) không đáng kể. Tối ưu `UNION ALL` theo toán tử (review-data-architect §B.3) để tới domain cấp đơn |
| Hit policy UNIQUE vi phạm làm nightly đỏ | Test mức `warn`; kết quả vẫn tất định |
| Chỗ lệch ngữ nghĩa NULL của hàm DuckDB (`contains`, `list_contains`) | Mỗi toán tử có unit test với đầu vào NULL; bọc `CASE WHEN f IS NULL THEN NULL` ở những toán tử cần |

## Effort

2 ngày (1 macro, 0.75 selftest và unit test, 0.25 tài liệu và gate).
