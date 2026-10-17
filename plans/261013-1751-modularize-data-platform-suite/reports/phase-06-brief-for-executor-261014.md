# Phase 6 brief cho session thực thi (14/10/2026)

Phase 6 đã được viết lại theo các quyết định user chốt chiều 14/10. Chỉ bắt đầu khi user cho giờ.

## Đọc trước (thư mục plan)

- `phase-06-fine-japan-tenant-overlay.md`: viết lại, công sức 3 ngày, gate M.
- `plan.md`: bảng phase, sơ đồ thư mục, mục "Pack vs tenant".
- `roadmap.md`: mục "Module sản phẩm từ Fine Japan" và đoạn "Cơ chế pack".

## Khác với phase 6 cũ

1. **Phần lớn đi vào pack, không vào tenant.** CRM, HUG, finance và kịch bản bán hàng là pack sản phẩm. `tenants/fine_japan/` chỉ còn US shipment và cấu hình riêng (URL Google Sheet, domain Sapo, webhook). Dữ liệu của Fine Japan cho các pack nằm ở `seeds/tenants/fine_japan/`.
2. **Tên pack:** `crm`, `hug` (giữ tên, README mở đầu bằng định nghĩa "nối lại khách từ sàn thương mại điện tử về mua trực tiếp với shop"), `finance` (đã có), `sales_playbook` (ghi "thử nghiệm, chưa chuẩn hoá").
3. **Pack finance nhận toàn bộ chi phí và lợi nhuận:** `int_order_cogs_reconciled`, `int_order_promo_goods_cost`, `fact_order_costs`, `fact_order_economics`, `mart_order_cogs_summary`, `int_customer_economics`; thêm overhead và dòng tiền/ngân sách. Lõi chỉ giữ doanh thu. Phải grep lại các model chi phí khác trong `core/`.
4. **Hook sinh từ manifest, ghi vào `boundary_allowlist.yaml`. Không sửa hook nào.**
   - Tenant hook: `dim_customers` (CROSSBORDER), `mart_data_quality` → US shipment.
   - Pack hook (core → pack): `dim_customers` → `int_customer_economics`, `dim_staff` → `stg_crm__app_user`. `check_boundaries.py` thêm quy tắc: core → packs chỉ được qua allowlist.
   - Pack → pack được phép nếu có khai báo: `mart_hug_attribution` → `fact_order_economics`.
5. **Orchestration:**
   - `orchestration/packs/crm/` nhận crm_sync, crm_writeback và CRM backup.
   - `orchestration/packs/sales_playbook/` nhận approach_script_generation.
   - `modules.yaml` thêm `packs: [...]` và `tenants: [fine_japan]`.
   - Không dùng URL/domain viết cứng trong `orchestration/connectors/**` và `orchestration/packs/**`.
6. **Không làm trong phase này:**
   - macro `pack_ref` và cơ chế bật/tắt pack (làm ngay sau Đợt 1);
   - tách giảm giá khỏi dòng chi phí;
   - chuẩn hoá CRM/HUG theo hướng API/CLI/MCP.

## Ràng buộc

- Chỉ dời thư mục và dời hằng số. Tên relation, cột, tên asset, job và selection giữ nguyên.
- Gate M phải sạch: golden 83/83, compiled SQL không đổi, inventory dbt chỉ đổi đường dẫn file, inventory Dagster không đổi.
- `check_taxonomy_inventory.py` không được cảnh báo. Model nào dời thì cập nhật bảng vị trí trong `TAXONOMY.md`; hash giữ nguyên.
- Trước khi dời các model mà CRM đọc, phải đọc `crm/sync/` và adapter để biết CRM đọc từ đâu.
- Gặp model không có đích rõ ràng thì hỏi user, không tự xếp.
- Baseline của gate là commit được chấp nhận gần nhất (≥ `111f1386`, đang chạy trên prod), build cùng ngày.

## Sau deploy

Chạy nightly bằng tay như phase 4. Kiểm thêm: các job CRM sync/writeback và HUG chạy thành công, CRM vẫn đọc được mọi bảng nó cần.
