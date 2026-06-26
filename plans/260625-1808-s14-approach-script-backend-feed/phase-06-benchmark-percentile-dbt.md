# Phase 06 — Customer benchmark mining (percentile, chuyên sâu) — dbt

> Trạng thái: ⬜ chưa làm. Chốt 2026-06-26: materialize ở dbt (đường chuẩn), thiết kế CHẤT LƯỢNG — định nghĩa dân số sạch + chuẩn hóa tenure + encode an toàn cho LLM. KHÔNG chỉ `percent_rank` thô.

## Vấn đề & vì sao phải làm kỹ
Script gán tier thô (`value_group`, CASE ngưỡng cứng `dim_customers.sql:124`) — không có vị thế tương đối → under/over-value (khách "SILVER" thực ra top ~5–6% chi tiêu). Nhưng **percentile thô trên toàn base là RÁC** vì dân số bẩn (đo trên parquet 25/06, n=7576):

| Vấn đề dân số | Số | Hệ quả nếu không xử |
|---|---|---|
| `lifetime_value<=0` | **3312 (44%)** | refund/hủy/0đ kéo đáy phân phối → percentile vô nghĩa |
| one-order (trong CLV>0) | **3190/4264 (75%)** | one-timer nén đáy → khách lặp lại 3M bị thổi thành "top 25%" giả |
| type lẫn (CROSSBORDER 662, WHOLESALE 161) | | nhận-hộ + sỉ ≠ bán lẻ → so táo-cam |
| tenure bias (<90d med 2.7M vs 2y+ 14.9M) | | CLV thô PHẠT khách mới giá-trị-cao |
| Đại Lý lẫn trong RETAIL | (memory) | dealer B2B đội hạng |

→ **Đòn bẩy chất lượng #1 KHÔNG phải nhiều frame, mà là ĐỊNH NGHĨA DÂN SỐ RANKABLE đúng + chuẩn hóa tenure.**

## Thiết kế

### A. Rankable population (nền tảng)
Chỉ xếp hạng khách **đủ tư cách so sánh**. Khách ngoài pop → benchmark NULL + cờ trạng thái (KHÔNG ép vào phân phối):

```
rankable = lifetime_value>0 AND order_count>=2
           AND customer_type='RETAIL'
           AND COALESCE(acquisition_source,'')<>'Đại Lý'
```
(verify: **939 khách**, median CLV 3.69M, p90 18.9M — khớp cohort outreach của `build_approach_prompts.py`.)

`benchmark_status`:
| Cờ | Điều kiện | Script dùng |
|---|---|---|
| `ranked` | thuộc rankable | có percentile đầy đủ |
| `single_purchase` | RETAIL, order_count=1, CLV>0 | "mới/mua 1 lần — chưa đủ lịch sử xếp hạng" |
| `inactive_zero_value` | CLV<=0 | không xếp; cân nhắc xác minh data |
| `non_retail` | WHOLESALE/CROSSBORDER/PARTNER | xếp trong frame type riêng (nếu cần), không chung |

### B. Metric × frame (chiều sâu — ship v1 GỌN, mở rộng sau)
**Metric (v1):** `lifetime_value` (monetary), `clv_per_active_month` = `lifetime_value / GREATEST(lifespan_days/30,1)` (tenure-fair). **Sau:** `order_count` (freq), `avg_order_spend` (AOV), `lifetime_contribution_margin`.

**Peer frame (v1):** `all_rankable` (toàn 939) + `in_value_group`. **Sau:** `in_geo_region` (đủ lớn, min 300), `in_acquisition_cohort` (theo năm first_order — fairness tenure), `in_affinity_category`.

**Min-group guard:** frame có `n<30` → fallback frame cha + ghi `*_frame_used`. (Geo hiện đều ≥300 → ít kích hoạt; cần cho cohort/affinity nhỏ.)

### C. Chuẩn hóa & robust
- Headline dùng **percentile/median** (robust outlier), KHÔNG dùng tỉ lệ vs-mean (whale 57M bóp méo).
- Cung cấp CẢ raw-CLV percentile VÀ `clv_per_active_month` percentile → khách mới giá-trị-cao không bị chôn.
- `clv_vs_rankable_median` = `lifetime_value / median(rankable)` — diễn giải "gấp N× khách lặp lại điển hình".

### D. Encode AN TOÀN cho LLM (chống lộ số thô + chống bịa)
Mỗi metric×frame xuất 3 thứ:
1. số percentile `round(...,1)`;
2. **nhãn bucket** (`top_5pct`|`top_decile`|`top_quartile`|`above_median`|`below_median`);
3. **cụm từ Việt sẵn dùng** (vd "thuộc nhóm ~6% chi tiêu cao nhất trong khách mua lặp lại") để LLM verbalize KHÔNG đọc số nội bộ ra khách.
→ Diệt luôn lỗi in `0.7526163537659895` ở `profile_read`.

### E. Momentum (v2 — gác)
Rank delta vs snapshot trước (đang lên/xuống nhóm). Cần bảng lưu percentile lịch sử → phase riêng, KHÔNG v1.

## Files
- **Tạo:** `transformation/models/marts/core/intermediate/int_customer_benchmarks.sql` — single-responsibility: định nghĩa rankable, tính percentile multi-metric/frame, min-group fallback, xuất số + bucket + cụm-từ + `benchmark_status`. (KHÔNG nhồi vào `dim_customers`.)
- **Sửa:** `transformation/models/marts/core/dim_customers.sql` — LEFT JOIN `int_customer_benchmarks` theo customer_key; select cột benchmark + status. KHÔNG đụng `value_group`.
- **Tạo:** `transformation/models/marts/core/intermediate/_int_customer_benchmarks.yml` — schema tests (mục Validation).
- **Sửa:** `scripts/build_approach_prompts.py` — thêm cột benchmark + status vào `COLS` (dòng 25–30); inject cụm-từ vào `customer_json`.
- **Sửa:** `plans/260624-1917-customer-insight-prompt-template/customer-insight-prompt-template.md` —
  - INPUT CONTRACT: field benchmark + `benchmark_status` + ý nghĩa.
  - QUY TẮC: "khách `ranked` percentile cao mà `value_group` thấp → nâng `invest_level`, coi cận-tier-trên; `single_purchase` → giọng khách mới đúng nghĩa; verbalize bằng cụm-từ sẵn, KHÔNG đọc số nội bộ."
  - OUTPUT `value_assessment.relative_standing` (additive) — **chỉ thêm khi S14 render** (xem rủi ro WS-B).

## Steps
1. Verify tầng có `lifetime_value`(=`monetary_value`)/`lifespan_days`/`first_order_date`: đọc `int_customer_metrics.sql`, `int_customer_economics.sql` (`marts/core/intermediate/`).
2. Viết `int_customer_benchmarks` (CTE: rankable → window percentile mỗi metric×frame → min-group fallback → bucket/cụm-từ → status).
3. JOIN vào `dim_customers`.
4. **Full-refresh** `dim_customers` (memory `feedback_dim_customers_incremental_full_refresh`): `dbt run --select int_customer_benchmarks+ dim_customers --full-refresh` trong container `data_platform` + lock-retry.
5. **Manifest reload** (thêm model/test → memory `feedback_dbt_node_needs_manifest_reload`): restart `data_platform`.
6. Thêm cột vào `COLS` builder + quy tắc template.
7. (Nếu expose Metabase) rebuild serving view (memory `feedback_duckdb_view_rebuild`) — không bắt buộc cho prompt.

## Validation
- **Tests (dbt):** percentile ∈ [0,100]; không row `ranked` nào CLV<=0; mọi khách có `benchmark_status`; bucket khớp ngưỡng percentile; `*_frame_used` fallback đúng khi n<30; `rankable` count ~939 (±drift snapshot).
- **Re-baseline** (đừng hardcode số cũ): percentile của `603264280`/`895489673` sẽ KHÁC "93.6/94.8" cũ — vì giờ so trên 939 khách LẶP LẠI, không phải 4264 base. Đo lại sau khi build, ghi giá trị thật làm mốc test.
- Rerun `build_approach_prompts.py --ids 603264280` → grep thấy cụm-từ benchmark.
- 1 prompt qua GPT → `invest_level` nâng đúng; KHÔNG lộ số thô; khách one-order ra giọng "mới".

## Rủi ro / rollback
- **Field `relative_standing` vô dụng nếu S14 không render** → để LLM nhét `profile_read`, hoặc gộp render vào WS-B. Quyết khi làm.
- Full-refresh dim_customers nặng + lock-retry → chạy ngoài giờ pipeline.
- Percentile đổi nhẹ mỗi snapshot (dân số đổi) — đây là ảnh chụp, document rõ.
- Over-scope: v1 CHỈ 2 metric × 2 frame. Thêm frame/metric khi sale thực sự cần (YAGNI). Đừng build cả 6 frame.
- Rollback: drop model + cột, full-refresh lại; builder/template revert độc lập.

## Unresolved
- One-order (3190) — chỉ gắn nhãn `single_purchase`, hay lập frame xếp hạng riêng cho họ?
- `non_retail` — có cần percentile trong-type cho WHOLESALE/CROSSBORDER (script B2B) hay để sau?
- Expose benchmark ra Metabase (rebuild view) hay chỉ phục vụ prompt?
- Momentum/rank-delta: cần bảng snapshot lịch sử — làm phase riêng khi nào?
