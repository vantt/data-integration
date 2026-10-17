# Phase 4 brief cho session thực thi (14/10/2026)

Phase 4 được mở lại với **phạm vi rút gọn** (user duyệt 14/10). Chỉ bắt đầu khi user cho giờ.

## Đọc trước (thư mục plan)

- `phase-04-taxonomy-module.md` (viết lại, công sức 2 ngày, gate M)
- `taxonomy-engine-design.md` (v2)
- `reports/taxonomy-review/synthesis.md`
- `reports/taxonomy-docs-gap-261014.md`

`plan.md` đã sửa tiêu chí nghiệm thu #5 và bảng phase. `roadmap.md` ghi bộ máy phân loại là plan riêng ngay sau Đợt 1.

## Khác với phase 4 cũ

1. **Không tách macro, không sửa model nào.** Sản phẩm chính là `transformation/docs/TAXONOMY.md`, viết như bản đặc tả cho bộ máy sau này. Mỗi domain ghi:
   - subject;
   - mọi vị trí file:dòng kèm sha256 của từng khối `CASE` (sau chuẩn hoá khoảng trắng);
   - số biến thể thật, có diff chứng minh. `customer_type` có 2 logic: `fact_orders` và `int_customer_benchmarks` giống nhau về logic (văn bản chỉ khác tiền tố bí danh `c.` ở bản benchmarks, nên sha256 của hai khối khác nhau; xem `transformation/docs/TAXONOMY.md` mục `customer_type`). Thứ tự ưu tiên thật: WHOLESALE > PARTNER > STAFF > KOL > CROSSBORDER > RETAIL;
   - dạng luật, đã là dữ liệu hay còn trong SQL, đặc trưng đọc vào;
   - ngữ nghĩa nguyên văn: `LIKE` với `_` là wildcard, giá trị `ELSE`, xử lý NULL;
   - thuộc tính bộ máy đề xuất, giá trị Fine Japan, mã chuẩn đề xuất (**chưa chốt**), literal riêng của tenant, model incremental lưu nhãn.

   Danh sách domain và Known divergences nằm trong phase file.
2. **Tạo `scripts/checks/check_taxonomy_inventory.py`** kèm pytest. Chỉ cảnh báo (WARN) khi hash của khối đã kiểm kê đổi, hoặc khi có khối `CASE` mới gán vào cột taxonomy đã biết. Gọi check này trong `gate.sh` và ghi vào `transformation/AGENTS.md`.
3. **Dời seed** sang `seeds/taxonomy/`, kèm `seed_paths.py`, `column_types` trong `dbt_project.yml` và sửa đường dẫn trong tài liệu, như phase cũ. **Không** sửa comment trong `monitor_uncategorized_tags.sql`, vì sửa sẽ làm compiled SQL khác.
4. **Chép tài liệu sang nhánh:**
   - `taxonomy-engine-design.md` (v2) → `docs/architecture/taxonomy-engine.md`
   - `references/taxonomy/*.md` → `docs/reference/taxonomy/`
   - `modules.md` §9 link tới hai chỗ trên.
5. **Chỉ ghi lại, không sửa:** lỗi không tất định trên prod. 28 dòng `ref_tag_categories` cùng priority 10, và `int_order_tags` không có quy tắc phá hoà.

## Lưu ý của user

Sapo là một nguồn, nhưng Fine Japan bán qua nhiều gian hàng: nhiều shop Shopee, Lazada, Tiki, TikTok, nhiều page Facebook, mang 6 thương hiệu kênh. Trong `TAXONOMY.md`:
- ghi `storefront` (`channel_name`, tầng 4) và `channel_brand` thành domain riêng;
- ghi rõ đơn Shopee về từ hai nguồn: Sapo, và connector Shopee (dùng cho phí).

## Gate

Gate M phải sạch hoàn toàn, vì phase không sửa model nào. Baseline ≥ `b718befc`, build cùng ngày.
