# Phase 2: card Metabase, blueprint, tài liệu

**Effort:** 0.5d · **Phụ thuộc:** phase 1 · **Gate:** `node .skills/metabase-automation/scripts/validate-analytics-artifacts.js --blueprints-only` và `deploy_from_markdown.js <blueprint> --dry-run` · **Đụng prod:** không (chỉ sửa file trên nhánh; card được deploy ở phase 4)

## Bối cảnh

- Dashboard "Product Inventory & Stock Health [All]" (`docs/analytics-handbook/blueprints/metabase/product_inventory_stock_health.md`) có 3 tab và 23 question. Mọi card "hôm nay" lọc `snapshot_date = (SELECT MAX(snapshot_date) ...)` (ví dụ dòng 91, 118, 145). Các card xu hướng lọc `snapshot_date >= current_date - INTERVAL '90 days'` (dòng 634, 672, 706, 741, 781). Khi dữ liệu dày (mỗi ngày đủ mọi cặp), các bộ lọc này cho đúng nghĩa mà **không cần sửa SQL**.
- Cần sửa SQL ở bốn chỗ:
  - Card "OOS SKUs" (dòng 84-100) và "Danh Sách SKU OOS" (dòng 293-312) theo QĐ-TK-03.
  - Ba card "Chu kỳ báo cáo" (dòng 62, 345, 603) đang hiện `current_date` thay vì ngày của dữ liệu.
- Hai text card "Source & Freshness" (dòng 332-335, 590-593, 805-808) ghi "snapshot_date = latest available" và cần mô tả nguồn mới.
- Dashboard "Product Health Overview [Cross]" (`product_health_overview.md`) đọc `mart_product_health` và `mart_product_action_queue`. SQL không cần đổi; số đổi theo QĐ-TK-04/05. Text "Source Freshness Tab1" (dòng 480-482) ghi "Daily snapshot" và cần thêm "tồn kho theo ảnh chụp đêm qua".
- Deployer tìm card **theo tên trong collection** rồi PUT tại chỗ (`.skills/metabase-automation/scripts/deploy_from_markdown.js:428-454`). Vì vậy **không được đổi tên card**: đổi tên sẽ tạo card mới, và card cũ mồ côi.

## Yêu cầu

1. **Đồng bộ blueprint với bản thật trước.** Nếu phase 0 thấy drift giữa card thật và blueprint, đưa bản thật vào blueprint trong một commit riêng không đổi số. Sau đó mới sửa theo các mục dưới, để diff chỉ chứa đúng thay đổi có chủ đích.
2. **OOS (theo QĐ-TK-03, đề xuất (c)):**
   - "OOS SKUs": đếm SKU có `SUM(on_hand) ≤ 0` trên các kho đang lọc **và** `bool_or(NOT is_dead_stock)`, `GROUP BY sku` trong subquery. Giữ các bộ lọc `[[AND {{location_name}}]]` và `[[AND {{category}}]]` bên trong subquery.
   - "Danh Sách SKU OOS": lọc theo cùng tập SKU. Giữ nguyên cột hiển thị.
   - Giữ nguyên tên card.
3. **"Chu kỳ báo cáo"** (3 card): `SELECT '📅 Dữ liệu tồn đến hết ngày ' || strftime(MAX(snapshot_date), '%d/%m/%Y') FROM main_marts.mart_inventory_health`. Giữ nguyên tên card.
4. **Text "Source & Freshness"** (3 chỗ): nguồn là ảnh chụp tồn kho Sapo hằng đêm, khoảng 03:00, đại diện cho cuối ngày hôm trước; xu hướng có từ ngày chụp đầu tiên (ghi ngày cụ thể); lịch sử `on_hand` trước ngày đó xem ở `fact_inventory_balance`; cờ hàng chậm/tồn chết dùng tốc độ bán hiện tại (QĐ-TK-06). Giữ `text-id`.
5. **Số cặp lệch sổ kho:** thêm một dòng vào text nguồn dữ liệu là chưa đủ, vì text không chạy SQL. Đổi card "Chu kỳ báo cáo" của tab Current Stock thành hai dòng: ngày dữ liệu, và "Lệch sổ kho: N cặp" (`COUNT(*) FILTER (WHERE on_hand_recon_status = 'mismatch')` ở ngày mới nhất, đọc từ `main_marts.fact_inventory_snapshot`). Không thêm card mới.
6. **Product Health Overview:** chỉ sửa text nguồn nếu nó mô tả nguồn tồn kho. Không đổi SQL.
7. **Frontmatter và Semantic Contract** của `product_inventory_stock_health.md` (dòng 1-28): sửa tên bảng sai `fact_inventory_snapshots` thành `fact_inventory_snapshot` ở dòng 25.

## Tài liệu (cùng commit)

| File | Sửa |
|---|---|
| `docs/analytics-handbook/semantic/freshness.md` | Dòng 28-29 và sơ đồ dòng 73-76: nguồn là ảnh chụp hằng đêm, `snapshot_date` = ngày được đại diện |
| `docs/analytics-handbook/semantic/entities.md` | Mục `fact_inventory_snapshot` (dòng 413-453) và `mart_inventory_health` (dòng 459-499): grain dày theo ngày; ba cột mới; quy tắc nguồn gốc và đối soát |
| `docs/analytics-handbook/semantic/metrics.md` | Mục `is_oos`/OOS rate (dòng 2063-2083): ghi rõ là mức (SKU, kho); định nghĩa card OOS theo QĐ-TK-03 |
| `docs/analytics-handbook/domains/product.md` | Dòng 210-316: nguồn tồn kho; các ví dụ SQL lọc theo ngày mới nhất; giới hạn lịch sử |
| `docs/architecture/data-model.md` | Dòng 91: nguồn và cột mới của `fact_inventory_snapshot` |

## Các bước

1. Đồng bộ drift (nếu có), commit riêng.
2. Sửa blueprint theo yêu cầu 2-7.
3. Chạy validator và `--dry-run` cho hai blueprint. Dry-run phải báo **update** cho mọi card, không có **create**.
4. Chạy SQL mới của từng card đã sửa trên lake-B shadow (bỏ các mệnh đề `[[...]]`), để chắc rằng SQL chạy được. Số được lấy ở phase 3.
5. Sửa tài liệu và kiểm lại mọi liên kết.

## Ma trận test

| Mức | Nội dung |
|---|---|
| Tĩnh | Validator blueprint xanh; `--dry-run` chỉ có update |
| Shadow | SQL các card đã sửa chạy được trên lake-B, có và không có bộ lọc kho |
| Tài liệu | Liên kết hợp lệ; mô tả khớp SQL ở phase 1 |

## Rủi ro

| Rủi ro | K × T | Giảm thiểu |
|---|---|---|
| Ba card cùng tên "Chu kỳ báo cáo" trong một collection bị deployer gộp nhầm | Trung bình × Trung bình | Dry-run phải cho ba id khác nhau, khớp với kiểm kê ở phase 0. Nếu không, sửa card qua API theo id (`manage-metabase-resources`) thay vì deploy cả dashboard |
| Bộ lọc Metabase không còn đúng sau khi đưa vào subquery | Thấp × Trung bình | Thử có và không có bộ lọc kho trên shadow; sau deploy thử trên UI |
| Plan report-productization phase 12/14 sửa cùng blueprint | Thấp × Trung bình | Coordinator xếp thứ tự; phase deploy sau thì rebase |

## Rollback

Trước phase 4: bỏ commit. Sau phase 4: deploy lại blueprint ở commit trước (PUT tại chỗ), hoặc khôi phục từ `reports/metabase-before/`.
