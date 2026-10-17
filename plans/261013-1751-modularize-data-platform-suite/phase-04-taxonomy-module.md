---
phase: 4
title: "Taxonomy: đặc tả phân loại và dời seed (rút gọn, không tách macro)"
status: pending
priority: P1
effort: "2d"
dependencies: [2, 3]
---

# Phase 4: Taxonomy (rút gọn)

> **Yêu cầu bắt buộc của user (13/10/2026): làm tới đâu, thiết kế và tài liệu hoá chi tiết tới đó.** Trước khi code: cập nhật thiết kế của component bị đụng trong `docs/architecture/modules.md` (bản sống trên nhánh). Trong lúc làm: tài liệu đi cùng commit với code. Phase chỉ được coi là xong khi tài liệu khớp với code thật.
>
> **Tài liệu phải cập nhật trong phase này:**
> - Tạo `transformation/docs/TAXONOMY.md` (bản đặc tả, mục "Đầu ra" bên dưới).
> - `docs/architecture/modules.md` §9: taxonomy hiện là đặc tả + seed; bộ máy phân loại là plan sau Đợt 1, link tới `docs/architecture/taxonomy-engine.md`.
> - Tạo `docs/architecture/taxonomy-engine.md` (bản thiết kế đã duyệt, chép từ [taxonomy-engine-design.md](taxonomy-engine-design.md) bản v2) và `docs/reference/taxonomy/` (4 file tham chiếu từ [references/taxonomy/](references/taxonomy/)).
> - Trong **cùng commit** dời seed, sửa mọi đường dẫn `transformation/seeds/ref_*.csv` sang `transformation/seeds/taxonomy/ref_*.csv`: `docs/context/order-customer-classification-staff-guide.md` (L220, L288), `docs/context/sales-segmentation-guide.md` (L125, L588, L646, L676), `docs/analytics-handbook/guides/channel_classification_implementation_prompt.md` (L19), `transformation/docs/TAG_HANDLING.md` (L524, L555, L689, L702), `.skills/data-pipeline/SKILL.md` (L184, cây thư mục), `.skills/data-pipeline/references/lessons-learned.md` (L2952). Tài liệu nghiệp vụ đang chép SQL kèm tên file thì thay đoạn chép bằng link tới mục tương ứng trong `TAXONOMY.md`; nội dung nghiệp vụ giữ nguyên. Chi tiết dòng: [reports/taxonomy-docs-gap-261014.md](reports/taxonomy-docs-gap-261014.md).
> - **Không** sửa comment trong `transformation/models/monitoring/monitor_uncategorized_tags.sql` L10 ở phase này (đổi comment làm khác compiled SQL); ghi vào mục việc sau của `TAXONOMY.md`.

## Vì sao đổi phạm vi (user duyệt 14/10/2026)

Bản cũ của phase này tách mỗi khối `CASE WHEN` thành một macro trả về nguyên văn SQL. User đã duyệt thiết kế bộ máy phân loại ([taxonomy-engine-design.md](taxonomy-engine-design.md), tổng hợp phản biện ở [reports/taxonomy-review/synthesis.md](reports/taxonomy-review/synthesis.md)): luật sẽ thành dữ liệu, mỗi domain một model sinh từ macro chung. Bộ máy sẽ thay các khối `CASE`, nên tách macro nguyên văn bây giờ là làm hai lần. Phase này chỉ còn:

1. **Đặc tả**: kiểm kê đầy đủ mọi luật phân loại thành `TAXONOMY.md`, viết theo đúng các thuộc tính mà bộ máy cần, để `TAXONOMY.md` là bản đặc tả trực tiếp cho plan bộ máy.
2. **Dời seed phân loại** vào `transformation/seeds/taxonomy/` qua helper `seed_paths.py` (vẫn cần, độc lập với bộ máy).
3. **Kiểm tra tự động** để khối `CASE` phân loại không âm thầm đổi hoặc mọc thêm trong lúc chờ bộ máy.

Không đổi số, không đổi SQL logic. Bộ máy là plan riêng sau khi Đợt 1 đóng (thứ tự: phase 4 → 6 → 7 → plan bộ máy). Mốc dự phòng: nếu khoảng 6 tuần sau khi Đợt 1 đóng mà bộ máy chưa chạy song song được `customer_type` trên prod, làm lại bước tách macro nguyên văn như bản cũ.

## Đầu ra: `transformation/docs/TAXONOMY.md`

Kiểm kê bằng grep lại toàn bộ code (không tin danh sách cũ). Với **mỗi domain**, ghi:

| Trường | Nội dung |
|---|---|
| Domain, subject | Tên cột kết quả; gắn cho đối tượng nào (order_source / order / customer / product / discount_line / gl_account) |
| Vị trí | Mọi file:dòng có luật, kèm **hash nội dung** (sha256 của khối sau chuẩn hoá khoảng trắng) để phát hiện thay đổi |
| Biến thể | Số logic **thực sự khác nhau** (chứng minh bằng diff); khối giống từng ký tự là một biến thể |
| Dạng luật | Ánh xạ trực tiếp / dò mẫu có ưu tiên / chia ngưỡng / bảng quyết định (kết hợp trên domain khác) / gán tay / phân cấp |
| Đã là dữ liệu hay còn trong SQL | Seed nào, hay khối `CASE` nào |
| Đặc trưng cần dùng | Cột đầu vào mà luật đọc (vd. `customer_group_code`, `recency_days`); luật chéo bảng thì ghi đặc trưng cần tạo (vd. "khách có đơn trên nguồn US") |
| Ngữ nghĩa nguyên văn | Thứ tự ưu tiên thật, toán tử thật (`LIKE` với `_` là wildcard, `ILIKE`, so sánh hoa/thường), giá trị mặc định ở `ELSE`, cách xử lý NULL |
| Thuộc tính bộ máy (đề xuất) | `cardinality`, `hit_policy`, `stickiness`, `time_semantics`, `versioning` theo [taxonomy-engine-design.md](taxonomy-engine-design.md) §3.2 |
| Giá trị Fine Japan | Danh sách nhãn đang ra |
| Mã chuẩn đề xuất | Theo thiết kế §5; ghi rõ **chưa chốt** cho tới khi có dữ liệu doanh nghiệp thứ hai |
| Giá trị tenant viết cứng | Literal riêng Fine Japan trong SQL (đầu vào phase 6 và plan bộ máy) |
| Model incremental lưu nhãn | Model nào lưu nhãn này dưới dạng incremental (ảnh hưởng chế độ restate) |

**Danh sách domain tối thiểu phải có** (gồm các chỗ scout cũ bỏ sót; bằng chứng file:dòng ở báo cáo khoảng trống):

- Kênh: `channel_format`, `channel_category` (`dim_channels.sql` L114-125), `is_sales_channel` (L138), `platform`, `source_type`, cây 4 tầng.
- Phạm vi đơn: `scope_sales`, `scope_retail`, `scope_b2b` (`fact_orders.sql` L206-219; `scope_b2b` có thêm `OR channel_format = 'B2B'` mà tài liệu không ghi).
- Khách: `customer_type`, `value_group`, `lifecycle_stage`, `customer_status` (`'Active'`), `channel_preference`, `product_affinity`, `payment_behavior`, `geo_region`, `acquisition_source`, `is_us_gift_recipient` (có thể NULL; hai action queue CRM dựa vào NULL này).
- Giảm giá: `primary_discount_type` (10 loại, `MAX_BY`) và gom 4 nhóm trong `int_customer_discount_metrics.sql`; khối ILIKE trong `fact_order_costs`.
- Tag đơn: `ref_tag_categories` + `int_order_tags`.
- Seed `ref_misa_channel_codes`, `ref_gl_accounts`, `gl_cashflow_line`; gán team (Google Sheet, SCD2) ghi là dữ liệu tổ chức, không phải domain phân loại.
- Các domain trong inventory scout cũ còn tồn tại thật: `next_purchase_signal`, `promo_dependency`, `strategic_tier`, `entry_basket`, `product_matrix`, `product_lifecycle`, `dim_sku_alias` VTS prefix, `dim_time` buckets, action-queue contact results. Tên `customer_value_tier`, `recency_status` không tồn tại, bỏ.

**Các điểm phải ghi đúng** (đã kiểm với code 14/10, phản biện kỹ sư dữ liệu):

- `customer_type` có **2** logic, không phải 3: `fact_orders` và `int_customer_benchmarks` giống nhau về logic (văn bản chỉ khác tiền tố bí danh `c.` ở bản benchmarks, nên sha256 của hai khối khác nhau; xem `transformation/docs/TAXONOMY.md` mục `customer_type`) (so khớp trên blob JSON `customer_group`); `dim_customers` dùng `customer_group_code`/`customer_group_name` cộng tín hiệu đơn kênh US.
- Thứ tự ưu tiên thật của `customer_type`: WHOLESALE > PARTNER > STAFF > KOL > CROSSBORDER > RETAIL (mặc định).
- Hai chỗ `value_group` cần diff lại: rà soát trước nói khác nhau ở `COALESCE`, phản biện nói tương đương về ngữ nghĩa; ghi kết luận có chứng minh.
- `lifecycle_stage` mang hai nghĩa (khách ở `dim_customers`, sản phẩm ở `mart_product_health`).

**Known divergences** (chỉ ghi, không sửa số): MISA `DAILY`/`CS` (tài liệu `rules.md` ngược với seed); `scope_retail` loại thêm `channel_format = 'B2B'`; `scope_b2b` có thêm điều kiện kênh B2B; `source_type` của CS/Telesale (`team` trong tài liệu, `channel` trong seed); `lifecycle_stage` hai nghĩa; CROSSBORDER; `'Active'`/`'ACTIVE'`.

**Rủi ro đang có trên prod, ghi lại để xử lý riêng (không sửa trong phase này):** 28 dòng `ref_tag_categories` cùng priority 10 và `int_order_tags` không có quy tắc phá hoà, nên nhãn tag có thể không tất định giữa các lần chạy. Sửa là việc độc lập, có thể đổi số, đi qua gate S và cần user duyệt.

**Chỉ ghi nhận cho plan bộ máy:** `order_nature` / domain cấp đơn `sales_line`; seed `ref_customer_tags`; 36 khách sỉ ẩn chờ Sales xác nhận; lưu trữ kênh không còn hoạt động; cờ `likely_wholesale`; mặc định sản phẩm "đơn chưa phân loại vẫn tính doanh thu" (khác luật Fine Japan loại "Other").

## Kiểm tra tự động: `scripts/checks/check_taxonomy_inventory.py`

- Đọc bảng vị trí + hash trong `TAXONOMY.md` (hoặc một file máy đọc đi kèm, vd. `transformation/docs/taxonomy_inventory.yaml`, nếu dễ bảo trì hơn; chọn một và ghi trong `scripts/checks/README.md`).
- **Cảnh báo** (exit 0, in WARN) khi hash của một khối đã kiểm kê thay đổi, hoặc khi xuất hiện khối `CASE ... END AS <cột>` mới gán vào cột thuộc danh sách domain mà chưa có trong kiểm kê.
- Mức cảnh báo, không chặn build (theo quyết định "chỉ warn" của plan); chạy trong `gate.sh` và ghi trong `transformation/AGENTS.md` cạnh `check_boundaries.py`.
- Có test pytest: khối bị sửa → WARN; khối mới → WARN; không đổi → im lặng.

## Seeds phân loại

Dời vào `transformation/seeds/taxonomy/` (tên seed giữ nguyên để relation không đổi): `ref_order_sources`, `ref_brands`, `ref_misa_channel_codes`, `ref_payment_methods`, `ref_spend_category`, `ref_tag_categories`, `ref_gl_accounts`, `ref_branch_locations`.

Bắt buộc đi kèm:

- Create: `ingestion/src/utils/seed_paths.py` — `seed_path(name) -> Path` tra cứu thư mục thật của seed (quét `transformation/seeds/**/<name>.csv`, lỗi nếu 0 hoặc >1 file).
- Modify: `ingestion/src/gsheet_budget_sync/fetch.py:50`, `ingestion/src/gsheet_marketing_spend.py:52-61`, `scripts/maintenance/sync_seeds.py` (L12, 25, 79, 88, 104), `orchestration/connectors/sheets/assets.py`, và mọi chỗ khác tìm được bằng `grep -rn "seeds" ingestion orchestration scripts --include=*.py`.
- Modify: `transformation/dbt_project.yml` khối `seeds:` — `+column_types` khoá theo đường dẫn fqn, phải đặt lại dưới `taxonomy:`.
- `check_boundaries.py` đã chặn trùng basename (phase 1).

## Files

- Create: `transformation/docs/TAXONOMY.md`, `scripts/checks/check_taxonomy_inventory.py` (+ test), `ingestion/src/utils/seed_paths.py`, `docs/architecture/taxonomy-engine.md`, `docs/reference/taxonomy/*.md`.
- Move: 8 seed ở trên. Modify: các file Python ở trên, `dbt_project.yml`, `scripts/shadow/gate.sh` (gọi check mới), các tài liệu ở khối đầu file.
- **Không** tạo `transformation/macros/taxonomy/`, **không** sửa model nào.

## Verification

- **Gate M** đủ (không sửa model): golden giống hệt, compiled SQL giống hệt, inventory dbt chỉ đổi đường dẫn file seed. Nếu inventory báo khác vì đường dẫn seed, ghi rõ đó là di chuyển file, không phải đổi relation.
- Trong shadow, chạy budget sync của `orchestration/connectors/sheets/assets.py` và `sync_seeds.py` với đầu vào mẫu (không mạng, CSV giả lập đã lưu) → ghi đúng vào `seeds/taxonomy/`, không tạo file trùng tên; `dbt parse` sau đó vẫn thành công.
- `check_taxonomy_inventory.py` im lặng trên nhánh; test pytest của nó pass.
- Đối chiếu ngẫu nhiên ≥ 5 mục trong `TAXONOMY.md` với code (vị trí, hash, thứ tự ưu tiên) và ghi kết quả vào báo cáo phase.

Trước khi chạy gate: baseline là commit được chấp nhận gần nhất (≥ `b718befc`, đã deploy), build cùng ngày (`docs/operations/refactor-safety-harness.md` §9.2).

## Rollback

Revert commit. Nếu job sheets (02:30) đã ghi seed vào thư mục mới, chuyển nội dung về lại trước khi start container (ghi rõ trong báo cáo deploy).
