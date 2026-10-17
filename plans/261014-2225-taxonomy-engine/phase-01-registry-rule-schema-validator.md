---
phase: 1
title: "Nền: registry domain, schema bảng luật, validator, dựng lại shadow"
status: pending
priority: P2
effort: "0.75d"
dependencies: ["Đợt 1 đóng", "plan cơ chế pack đã deploy"]
---

# Phase 1: Registry, schema luật, validator

> **Yêu cầu bắt buộc của user (13/10/2026): làm tới đâu, thiết kế và tài liệu hoá chi tiết tới đó.** Tài liệu đi cùng commit với code.
>
> **Tài liệu phải cập nhật trong phase này:** `docs/architecture/taxonomy-engine.md` (mục mới "Hiện thực MVP": registry, schema luật, thứ tự lớp), `docs/architecture/modules.md` §9 (bảng thành phần: hai seed luật, validator), `transformation/docs/TAXONOMY.md` §5 (hai seed mới, ai đọc/ghi), `transformation/AGENTS.md` mục "Classification rules" (luật mới là dòng seed, chạy validator), `scripts/checks/README.md` (validator).

## Mục tiêu

Có chỗ khai báo domain và đặc trưng (đọc lúc compile), hai seed luật rỗng đúng schema cho hai lớp, và một validator chặn luật sai **trước khi nạp**. Chưa có model nào mới; không SQL nào của model hiện có đổi.

## Bối cảnh đã kiểm

- Đợt 1 phase 7 xoá shadow và worktree (`phase-07-docs-adr-enforcement.md` bước 3), nên plan này dựng lại môi trường theo `scripts/shadow/README.md` § One-time setup.
- `+column_types` của seed trong thư mục con đặt dưới khoá thư mục (`transformation/dbt_project.yml` L14–48; `transformation/AGENTS.md` L39–40). Tiền lệ mất `_` khi cột bị suy kiểu số: comment ở `dim_channels.sql` L21–24 (review-data-architect §B.4 mục 5), nên **mọi cột luật khai varchar**, trừ `priority` (integer) và `enabled` (boolean).
- Tên seed phải duy nhất toàn repo (luật `seed-duplicate`, `check_boundaries.py` L20–21).
- dbt-core 1.11.12 / dbt-duckdb 1.10.1 (`ingestion/requirements.txt` L15–16).
- Registry phải là YAML đọc lúc compile, không phải seed (thiết kế §6; review-data-architect C9). Jinja của dbt không đọc được file YAML tuỳ ý, còn `vars` của `dbt_project.yml` có sẵn lúc parse, nên `ref()` mà macro sinh từ registry được ghi vào DAG.
- Hợp đồng `taxonomy_label` do plan cơ chế pack tạo (roadmap "Thứ tự ưu tiên sau Đợt 1" mục 1). [UNVERIFIED: tên, vị trí, cột; plan pack chưa có file lúc lập plan này.]

## Files

- Modify: `transformation/dbt_project.yml` — khối `seeds:` thêm `+column_types` cho `taxonomy_rule_product` (dưới `taxonomy:`) và `taxonomy_rule_tenant` (dưới `tenants: fine_japan:`); khối `vars:` thêm `taxonomy:` với `features: {}` và `domains: {}` (rỗng, có comment mô tả schema).
- Create: `transformation/seeds/taxonomy/taxonomy_rule_product.csv` — chỉ dòng tiêu đề (lớp mặc định sản phẩm; pilot không có luật sản phẩm cho `customer_type`).
- Create: `transformation/seeds/tenants/fine_japan/taxonomy_rule_tenant.csv` — chỉ dòng tiêu đề (phase 3 điền).
- Modify: `transformation/seeds/properties.yml`, `transformation/seeds/tenants/fine_japan/_fine_japan__seeds.yml` — mô tả cột, test `not_null` cho `rule_id`, `domain`, `label` khi có `feature` (mức `warn`; chặn cứng là validator).
- Create: `scripts/checks/check_taxonomy_rules.py` — validator (stdlib + PyYAML, cùng kiểu `check_taxonomy_inventory.py`).
- Create: `scripts/tests/test_check_taxonomy_rules.py`.
- Modify: `scripts/checks/README.md`, `transformation/AGENTS.md`, `transformation/docs/TAXONOMY.md` §5, `docs/architecture/taxonomy-engine.md`, `docs/architecture/modules.md` §9.

## Schema

**Seed luật** (cùng cột cho hai lớp; một dòng là một điều kiện):

| Cột | Kiểu | Ý nghĩa |
|---|---|---|
| `rule_id` | varchar | Khoá luật, duy nhất trong lớp. Nhiều dòng cùng `rule_id` là các điều kiện nối bằng AND; các cột `domain`, `priority`, `label`, `enabled` phải giống nhau giữa các dòng đó |
| `domain` | varchar | Tên domain trong registry |
| `priority` | integer | Số nhỏ xét trước, trong cùng lớp |
| `label` | varchar | Nhãn riêng của doanh nghiệp, phải có trong `taxonomy_label` của `label_set` |
| `feature` | varchar | Tên đặc trưng khai báo cho domain; **để trống** = luật không điều kiện (luôn đúng), dùng làm mặc định |
| `op` | varchar | `like`, `eq`, `in`, `not_in`, `between`, `starts_with`, `contains`, `regex`, `is_null`, `has` |
| `value`, `value_to` | varchar | Giá trị; `in`/`not_in` tách bằng `|`; `between` là `[value, value_to)`, ô trống là không chặn |
| `enabled` | boolean | `false` tắt luật có `rule_id` này ở **mọi lớp** (cách lớp tenant tắt luật kế thừa) |
| `note` | varchar | Ghi chú cho người đọc, không dùng trong tính toán |

**Registry** (`vars.taxonomy` trong `dbt_project.yml`):

```yaml
taxonomy:
  features:            # danh mục đặc trưng, hợp đồng công khai
    <feature_model>: {subject: customer, key: customer_key, columns: {<tên>: <kiểu DuckDB>}}
  domains:
    <domain>:
      subject: customer
      cardinality: single          # single | multi
      hit_policy: FIRST            # FIRST | UNIQUE | COLLECT
      features: [<feature_model>, ...]   # khai báo TĨNH; model đầu tiên là tập đối tượng đầy đủ
      label_set: <domain>          # bộ nhãn trong taxonomy_label (biến thể dùng chung bộ nhãn)
      required_features: []        # thiếu thì UNKNOWN (pilot: rỗng)
      matched_flags: []            # nhãn cần cột matched__<nhãn> ba giá trị
      survey: {features: [...], metrics_model: ..., order_count: ..., revenue: ...}
      selftest: false
```

## Các bước

1. Đọc plan cơ chế pack đã deploy: ghi lại tên seed/model của bảng nhãn, cột khoá (`domain` hay `label_set`), bảng mã chuẩn và vị trí. Nếu khác giả định `(domain, label, label_std)`, sửa mục Schema của phase 2–3 trước khi làm tiếp.
2. Dựng lại môi trường: tạo worktree nhánh `feat/taxonomy-engine` từ `main` và worktree baseline tại commit `main` hiện hành; `prepare-shadow.sh <backup mới> <backup trước>`; build lake-A, chụp golden, xuất hai inventory baseline (theo `scripts/shadow/README.md`).
3. Thêm `vars.taxonomy` rỗng và `+column_types` cho hai seed; tạo hai CSV chỉ có tiêu đề.
4. Kiểm seed rỗng: build trên lake trống (`clone-lake.sh lake-E --empty-rolling`, `build-lake.sh`) phải tạo được hai bảng 0 dòng đúng kiểu. Nếu dbt-duckdb không nạp được CSV chỉ có tiêu đề, dùng một dòng giữ chỗ `enabled=false`, `domain=__none__` và cho validator bỏ qua domain này.
5. Viết `check_taxonomy_rules.py`: đọc registry từ `dbt_project.yml`, hai seed luật, và bảng nhãn của plan pack. Lỗi (thoát 1) khi: domain không có trong registry; `feature` không thuộc đặc trưng của domain; `op` không hợp kiểu đặc trưng (`has` chỉ cho cột danh sách, `between` chỉ cho số/ngày); `value` không ép được về kiểu; `between` thiếu cả hai đầu; `label` không có trong bộ nhãn; thuộc tính luật lệch giữa các dòng cùng `rule_id`; hai `rule_id` khác nhau cùng `(domain, lớp, priority)` trong domain FIRST/UNIQUE; luật không điều kiện trong domain COLLECT; dòng `enabled=false` trỏ tới `rule_id` không tồn tại ở lớp nào. Dòng lệnh: `python3 scripts/checks/check_taxonomy_rules.py`.
6. Viết pytest: mỗi lỗi ở bước 5 có một CSV tạm sai tương ứng; seed thật (rỗng) pass.
7. Thêm khai báo vào `model_buckets.yaml`: chưa cần (chưa có model). Chạy `check_boundaries.py` để chắc luật `seed-duplicate` pass.
8. Cập nhật tài liệu (danh sách ở đầu file) và commit.

## Verification

- Gate: `scripts/shadow/gate.sh M --allow-new` (seed mới là node mới; không model nào đổi SQL). Nếu `gate.sh M` không nhận cờ `--allow-new` thì chạy `S --allow-new`. [UNVERIFIED: tổ hợp cờ với `M`.]
- Golden 83/83, compiled SQL của mọi model hiện có không đổi, inventory Dagster không đổi.
- Pytest validator pass trong bước 5 của gate; `check_taxonomy_rules.py` thoát 0 trên seed đã commit.
- Lake trống build được (bước 6 của gate) với hai seed rỗng.

## Đổi số?

**Không.** Chỉ thêm seed rỗng, biến chưa ai đọc, script và tài liệu.

## Rollback

Chưa lên prod. Revert commit trên nhánh.

## Rủi ro

| Rủi ro | Giảm thiểu |
|---|---|
| Seed chỉ có tiêu đề không nạp được | Bước 4 kiểm sớm; phương án dòng giữ chỗ |
| Hợp đồng bảng nhãn của plan pack khác giả định | Bước 1 làm trước mọi thứ; validator đọc đúng bảng của plan pack |
| `vars` lớn làm `dbt_project.yml` khó đọc | Chỉ khai báo domain đang dùng; mô tả schema ở `taxonomy-engine.md`, không lặp trong YAML |

## Effort

0.75 ngày (0.25 dựng lại shadow, 0.25 schema + seed, 0.25 validator + test + tài liệu).
