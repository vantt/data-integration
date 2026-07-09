---
title: "Customer Product Affinity (SKU-level) — Implementation Spec"
created: 2026-06-13
status: done
completed: 2026-06-13
# (updated 2026-07-08: verified shipped in commit 55b178b3, same day as spec — all 5 cols
#  in int_customer_metrics/dim_customers/mart_customer_action_queue, docs updated, consumed
#  downstream by CRM S01 worklist + task detail + c360 panel)
parent_plan: ../260604-1125-retail-reactivation/05-action-plans/b2c-reactivation-phases.md (P1)
owner: Data
---

# Customer Product Affinity (SKU-level) — Spec

> Bổ sung cột "sản phẩm khách hay mua / lần trước mua" ở cấp **SKU cụ thể** để cá nhân hóa
> script reorder/cross-sell cho CSKH & Sales. Thay phần `last_product_affinity_sku` (P1) của
> [b2c-reactivation-phases](../260604-1125-retail-reactivation/05-action-plans/b2c-reactivation-phases.md).

## 1. Vấn đề & mục tiêu

`dim_customers.product_affinity` hiện chỉ ở mức **BRAND**, 4 giá trị (`PRODUCT_FINE_JAPAN`,
`PRODUCT_FG_CARE`, `PRODUCT_FINE_CARE`, `PRODUCT_MULTI`) → KHÔNG nói được khách mua **sản phẩm gì**.
Script P0 cần điền tên SP thật: *"Lần trước anh/chị mua [X]…"*, *"nhắc bổ sung [Y]"*.

**Mục tiêu:** mỗi khách có 3 sản phẩm neo (last / top affinity / second affinity) ở mức SKU,
hiển thị tên cho script + mã SKU cho Sales đặt hàng.

## 2. Output — 5 cột mới trên `dim_customers`

| Cột | Kiểu | Nghĩa |
|---|---|---|
| `last_purchased_product` | VARCHAR | Tên SP của **đơn paid gần nhất** (đơn nhiều SKU → SKU quantity cao nhất) |
| `top_affinity_product` | VARCHAR | Tên SP **mua lặp nhiều đơn nhất** (món tiêu hao chủ lực) |
| `second_affinity_product` | VARCHAR | Tên SP hạng #2 — dùng cross-sell. NULL nếu khách chỉ từng mua 1 SKU |
| `top_affinity_sku` | VARCHAR | Mã SKU của `top_affinity_product` — cho Sales đặt hàng/đối chiếu tồn |
| `last_purchased_sku` | VARCHAR | Mã SKU của `last_purchased_product` |

> Bỏ sku của `second_affinity` (tên đủ cho gợi ý cross-sell; cần mã thì tra `dim_products`).
> Tên hiển thị = `product_name` (+ `variant_name` nếu khác NULL).

## 3. Logic tính

### 3.1 Nguồn & filter (CRITICAL)

```sql
FROM fact_sales s
JOIN dim_products p  ON s.product_key = p.product_key
JOIN fact_orders  o  ON s.order_id   = o.order_id
WHERE o.is_active_order            -- loại đơn huỷ (brand_revenue hiện THIẾU filter này — xem §7)
  AND s.net_revenue > 0            -- loại quà tặng + swag (xem §3.3)
  AND p.product_name IS NOT NULL
```

### 3.2 Ranking key (dùng chung cho top & second affinity)

Per `(customer_key, product_key)`, xếp hạng:

| Ưu tiên | Tiêu chí | Lý do |
|---|---|---|
| 1 | `COUNT(DISTINCT order_id)` DESC | tần suất tái mua = tín hiệu reorder mạnh nhất |
| 2 | `SUM(quantity)` DESC | xử lý đơn multi-SKU (42.6% đơn) |
| 3 | `MAX(ordered_at)` DESC | tie-break recency |
| 4 | `SUM(net_revenue)` DESC | tie-break giá trị |
| 5 | `product_key` ASC | deterministic — chống flap giữa các run |

→ `ROW_NUMBER() OVER (PARTITION BY customer_key ORDER BY …)`: rn=1 → top, rn=2 → second.

### 3.3 `last_purchased_product` — logic riêng (recency)

- Lấy **đơn paid gần nhất** của khách (`MAX(ordered_at)` trên dòng `net_revenue>0`).
- Đơn đó nhiều SKU → chọn SKU `quantity` cao nhất (tie-break `net_revenue`, rồi `product_key`).
- Nếu đơn cuối toàn quà tặng → tự nhiên lùi về đơn paid gần nhất trước đó (vì đã lọc `net_revenue>0`).

### 3.4 Quy tắc loại quà tặng (semantic phi-hiển-nhiên)

`net_revenue = line_amount × VAT_ratio` ⟹ `net_revenue=0` ⟺ `line_amount=0` ở Sapo = **dòng tặng/KM**
(giá niêm yết bị giảm 100%). **43.9% dòng đơn** rơi vào đây, gồm 2 loại — **cả hai đều loại:**

- **A. SP thật được tặng kèm** (Cordyceps Plus, Metabo Green Tea…) — khách không trả tiền → không phải sở thích.
- **B. Swag/giấy tờ** (Dù in logo, "Công Văn Giấy Tờ", Bát tre, Túi vải logo) — không bao giờ bán → noise.

Filter `net_revenue > 0` quét cả A lẫn B bằng 1 điều kiện. **Nhất quán** với brand `product_affinity`
(đã rank theo `SUM(net_revenue)` share, dòng 0đ vốn đóng góp 0).

## 4. Hành vi edge-case (kỳ vọng để viết test)

| Tình huống | last | top | second |
|---|---|---|---|
| One-time, 1 SKU paid | SKU đó | = last | NULL |
| One-time, multi-SKU paid | SKU qty cao nhất | = last | SKU qty hạng 2 |
| Repeat buyer | SKU đơn cuối | SKU hay mua nhất | SKU hạng 2 |
| Đơn cuối toàn quà, đơn trước paid | SP paid gần nhất | theo freq | hạng 2 |
| Chỉ từng nhận quà (all-0đ, gồm CrossBorder) | NULL | NULL | NULL |

NULL ở khách all-gift là **đúng** — chưa mua gì để reorder; thuộc play US-gift (P4), không phải reorder.

## 5. Layering — tính 1 nơi, lưu ở dim, đọc-xuyên ở mart

```
int_customer_metrics.sql  ──►  dim_customers.sql  ──►  mart_customer_action_queue.sql
   (TÍNH: CTE mới)               (LƯU: 5 cột)            (ĐỌC: SELECT từ dim, không tính lại)
```

- **`int_customer_metrics.sql`**: thêm CTE `sku_affinity` (rank §3.2) + `last_purchase_sku` (§3.3),
  LEFT JOIN vào SELECT cuối. Tái dùng scan `sales`/`products` sẵn có (cạnh `brand_revenue`).
- **`dim_customers.sql`**: thêm 5 cột từ `m.*` (giống cách lấy `product_affinity`).
- **`mart_customer_action_queue.sql`**: thêm 5 cột vào CTE `customers` + SELECT cuối (đọc từ `dim_customers`,
  khớp cách đang đọc `product_affinity`).

## 6. Các bước thực thi — ✅ DONE (commit 55b178b3, 2026-06-13)

1. [x] `int_customer_metrics.sql`: thêm CTE `sku_affinity` + `last_purchase_sku`; join vào output.
2. [x] `dim_customers.sql`: thêm 5 cột (joined_data + SELECT cuối) + comment mô tả.
3. [x] `mart_customer_action_queue.sql`: thêm 5 cột (CTE `customers` + SELECT cuối).
4. [x] Restart `data_platform` container (manifest pre-parse — node mới cần reload).
5. [x] Chạy `dbt run --full-refresh` cho `int_customer_metrics`, `dim_customers`, `mart_customer_action_queue`
       trong container, kèm lock-retry (incremental + cột mới chỉ backfill row đổi).
6. [x] Verify (§8).
7. [x] Cập nhật docs (§9).

**Đã build thêm** (ngoài scope spec ban đầu, cùng commit): `dim_customers.is_contactable` +
`is_us_gift_recipient`, `dim_channels.is_marketplace`, `mart_retention_waterfall_monthly` segment dims.
5 cột affinity hiện được CRM tiêu thụ tại S01 worklist row, task detail, c360 insight panel.

## 7. Lưu ý kỹ thuật

- **`brand_revenue` thiếu `is_active_order`** (int_customer_metrics.sql:133-145) — affinity brand hiện tính cả
  đơn huỷ. CTE mới SẼ lọc đúng (`JOIN fact_orders … is_active_order`). KHÔNG sửa brand_revenue trong scope này
  (pre-existing, ngoài phạm vi) — chỉ ghi nhận.
- **Incremental + cột mới** → bắt buộc `--full-refresh`, không tự backfill (memory: dim_customers_incremental).
- **DuckDB single-writer** → chạy full-refresh khi pipeline rảnh, lock-retry.
- **Packsize**: giữ SKU variant, KHÔNG gộp `packsize_root` — khách tái mua đúng quy cách quen.

## 8. Verify (parquet trực tiếp — Windows)

```sql
-- 8.1 Phủ: bao nhiêu % RETAIL có top_affinity (kỳ vọng = % khách có ≥1 đơn paid)
SELECT COUNT(*) FILTER (WHERE top_affinity_product IS NOT NULL)*100.0/COUNT(*)
FROM dim_customers WHERE customer_type='RETAIL' AND order_count>0;

-- 8.2 Không SKU swag/giấy tờ lọt vào (phải = 0)
SELECT COUNT(*) FROM dim_customers
WHERE top_affinity_product IN ('Dù in logo công ty FG & Fine Japan','Công Văn Giấy Tờ');

-- 8.3 Spot-check 1 khách repeat: top khớp SKU mua nhiều đơn nhất khi query tay fact_sales
```

## 9. Docs phải cập nhật (sau khi code+verify)

| Doc | Nội dung |
|---|---|
| `docs/analytics-handbook/semantic/dimensions.md` | 3 entry cột (format `product_affinity`) + ghi chú NULL=chưa mua paid |
| `docs/analytics-handbook/domains/customer.md` | Thêm thuộc tính + use-case script |
| `docs/analytics-handbook/guides/revenue_terminology.md` | Mục "Dòng `net_revenue=0` nghĩa là gì" (quà/swag, 43.9% dòng) — giá trị rộng |
| `docs/architecture/data-dictionary.md` | Dòng cột nếu doc liệt kê schema dim_customers |

## 10. Câu hỏi mở — ĐÃ CHỐT (2026-06-13)

- ✅ Rank `top_affinity` = **frequency trước, quantity sau** (chốt: đúng tín hiệu "món hay mua lại").
- ✅ Tên hiển thị: **kiểm `variant_name` lúc code** — query xem có nhiễu (`Mặc định`/rỗng) không; sạch thì
  ghép `product_name + variant_name`, nhiễu thì chỉ `product_name`. Quyết theo data thật.
