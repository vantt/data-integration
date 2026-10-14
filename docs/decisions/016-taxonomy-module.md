# ADR-016: Taxonomy module Đợt 1: đặc tả + dời seed, không tách macro

> **Trạng thái:** Accepted
> **Ngày:** 2026-10-14 (thay kế hoạch 13/10/2026 "tách mỗi khối `CASE` phân loại thành macro nguyên văn")
> **Tham chiếu:** [`transformation/docs/TAXONOMY.md`](../../transformation/docs/TAXONOMY.md) (đặc tả), [`docs/architecture/taxonomy-engine.md`](../architecture/taxonomy-engine.md) (thiết kế bộ máy, chưa triển khai), [`docs/architecture/modules.md` mục 9](../architecture/modules.md#9-taxonomy-module), [`scripts/checks/README.md`](../../scripts/checks/README.md#check_taxonomy_inventorypy), [ADR-015](./015-module-boundaries.md)

## Bối cảnh

Phân loại (loại khách, nhóm giá trị, kênh cấp 1, phạm vi đơn, loại giảm giá, nhóm tag...) là phần khác nhau nhất giữa các doanh nghiệp. Ở Fine Japan mỗi luật là một khối `CASE` rải trong SQL của core hoặc một seed, có luật tồn tại nhiều biến thể lệch nhau (ví dụ `customer_type`: `dim_customers` coi khách có đơn kênh US là `CROSSBORDER`, `fact_orders` thì không).

Kế hoạch ban đầu (13/10/2026) là tách mỗi khối `CASE` thành một macro trả về nguyên văn SQL, gom về một module. Ngày 14/10 user duyệt hướng thiết kế bộ máy phân loại (luật là dữ liệu, mỗi domain một model sinh từ macro chung, nhãn riêng của doanh nghiệp + mã chuẩn) sau bốn bản phản biện; cả bốn đồng ý bỏ bước tách macro nguyên văn:

1. Bộ máy sẽ **thay** các khối `CASE`, nên tách macro nguyên văn bây giờ là làm hai lần.
2. Việc cần ngay là **biết đủ và không để luật trôi** trong lúc chờ bộ máy: vị trí, hash, biến thể và chỗ lệch của từng luật.

## Quyết định

Taxonomy trong Đợt 1 là **đặc tả + dời seed + kiểm tra cảnh báo**, không tách macro, không sửa SQL của luật:

| Thành phần | Nội dung |
|---|---|
| `transformation/docs/TAXONOMY.md` | Đặc tả mọi luật phân loại đang chạy (46 domain): vị trí `file:dòng`, **sha256 của từng khối**, dạng luật, biến thể thật, ngữ nghĩa nguyên văn (thứ tự ưu tiên, `LIKE` với `_`, `ELSE`, NULL), literal riêng Fine Japan, thuộc tính đề xuất cho bộ máy, và **Known divergences** (các chỗ lệch, giữ nguyên, không sửa trong Đợt 1). Là đặc tả đầu vào của bộ máy |
| `scripts/checks/taxonomy_inventory.yaml` + `check_taxonomy_inventory.py` | Bản máy đọc của đặc tả (79 khối). Check **chỉ cảnh báo** (luôn thoát 0): khối đã kiểm kê đổi hash, khối `CASE` mới gán cột taxonomy, file mất. Shadow gate in kết quả ở bước 3c |
| `transformation/seeds/taxonomy/` | 8 seed phân loại (`ref_order_sources`, `ref_brands`, `ref_misa_channel_codes`, `ref_payment_methods`, `ref_spend_category`, `ref_tag_categories`, `ref_gl_accounts`, `ref_branch_locations`); `+column_types` dưới khoá `taxonomy:` của `dbt_project.yml` |
| `ingestion/src/utils/seed_paths.py` | `seed_path(name)` tìm seed theo tên (quét `transformation/seeds/**`), lỗi khi không có hoặc trùng; writer Python không viết cứng thư mục. Luật `seed-duplicate` của `check_boundaries.py` chặn hai seed trùng basename |

Bộ máy phân loại (luật là dữ liệu, một model mỗi domain sinh từ macro chung, nhãn riêng + mã chuẩn) là **plan riêng ngay sau Đợt 1**, thiết kế v2 đã duyệt hướng ở [taxonomy-engine.md](../architecture/taxonomy-engine.md); bộ mã chuẩn **chưa chốt** cho tới khi có dữ liệu của doanh nghiệp thứ hai. Ưu tiên domain theo danh mục report chuẩn (roadmap, thứ tự sau Đợt 1).

Mốc dự phòng: nếu khoảng 6 tuần sau khi Đợt 1 đóng mà bộ máy chưa chạy song song được `customer_type` trên prod, làm lại bước tách macro nguyên văn như kế hoạch 13/10.

## Hệ quả

- Không đổi con số nào; Known divergences được ghi lại thay vì bị "sửa" lặng lẽ.
- Sửa một luật phân loại không còn vô hình: check cảnh báo, và quy tắc là cập nhật `TAXONOMY.md` + inventory trong cùng thay đổi; thay đổi số đi qua gate S.
- Luật vẫn là SQL trong core; literal Fine Japan (`CTN00014`, `KY_GUI`, `'Đại Lý'`, kênh `US`...) vẫn nằm trong lõi cho tới bộ máy (danh sách ở `TAXONOMY.md` mục 6). Nhánh `CROSSBORDER` của `dim_customers` là "logic hook" Fine Japan, checker ranh giới không thấy (không phải cạnh `ref`).
- Check chỉ cảnh báo nên không chặn commit; người sửa phải đọc output (gate in ra).

## Alternatives Rejected

- **Tách macro nguyên văn các khối `CASE` trong Đợt 1** (kế hoạch 13/10): không đổi số nhưng là việc làm hai lần, vì bộ máy thay các khối này; giữ làm phương án dự phòng (mốc 6 tuần ở trên).
- **Check fail khi hash đổi**: luật được phép đổi có chủ đích; chặn cứng sẽ dẫn tới cập nhật hash máy móc. Chọn cảnh báo + quy tắc cập nhật đặc tả.
- **Inventory parse trực tiếp từ markdown**: hash dễ lệch do định dạng; chọn YAML riêng, test đối chiếu.

## Khi nào xem xét lại

- Khi plan bộ máy phân loại bắt đầu: `TAXONOMY.md` là đặc tả đầu vào; khối nào chuyển thành dữ liệu thì xoá khỏi inventory.
- Khi chạm mốc dự phòng 6 tuần mà bộ máy chưa chạy song song `customer_type`.
- Khi có doanh nghiệp thứ hai: chốt bộ mã chuẩn, chuyển literal Fine Japan sang tenant.
- Nếu cảnh báo bị bỏ qua lặp lại: cân nhắc cho check fail trên `WARN new`.
