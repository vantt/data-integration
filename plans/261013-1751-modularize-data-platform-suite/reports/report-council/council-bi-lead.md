---
title: "Hội đồng phản biện — góc nhìn Trưởng BI/phân tích cho SME thương mại điện tử"
reviewer: council-bi-lead
date: 2026-10-14
reviews: ../../report-product-design.md (draft v1)
inputs: references/reports/handbook-inventory.md, references/reports/external-references.md, docs/analytics-handbook/semantic/metrics.md, docs/analytics-handbook/semantic/rules.md, roadmap.md (Đợt 7)
---

# Phản biện: thiết kế "xưởng report" — góc nhìn Trưởng BI

Người dùng tôi đại diện là chủ shop, giám đốc, kế toán/CFO, marketer và vận hành. Với họ, sản phẩm chỉ có giá trị khi số **đúng, giải thích được, và khớp với con số họ thấy ở Sapo/Shopee/MISA**. Tôi chấm thiết kế theo tiêu chí đó.

## (a) Những điểm thiết kế làm đúng

1. **Một registry chỉ tiêu, tính sẵn trong mart dbt.** Đây là cách duy nhất để Metabase, Evidence và Rill ra cùng một số. Chọn YAML tự quản lý, viết gần cú pháp MetricFlow, là quyết định đúng với DuckDB on-prem và Metabase OSS.
2. **Overlay không được sửa định nghĩa metric.** Muốn khác thì tạo metric mới có id riêng. Đây là mẫu Daasity/Rill đã được chứng minh, và nó bảo vệ tính nhất quán của chỉ tiêu giữa các khách.
3. **Mở khoá theo tập capability, thiếu dữ liệu thì hiện "–" kèm lý do, không hiện 0.** Đây là điểm quan trọng nhất về độ tin cậy với người dùng kinh doanh.
4. **Trang chủ vai trò ghép từ thẻ KPI của report**, không phải report riêng. Cách này tránh nhân bản số và giữ một nguồn định nghĩa.
5. **Chạy song song và so số với dashboard FJ trước khi chuyển người dùng.** Đây là quy trình đúng cho mọi thay đổi định nghĩa.
6. **Weekly Pulse làm thí điểm** là lựa chọn tốt vì nó thử cả nhánh `enhances` (target, MISA) chứ không chỉ nhánh dễ.

## (b) Những điểm sai hoặc thiếu

### B1. Tên `net_revenue` đang mang hai nghĩa khác nhau — rủi ro lớn nhất của Phase 1
- Trong `semantic/metrics.md` hiện tại, `net_revenue` = tiền thu sau giảm giá, **đã tách VAT, chưa trừ hàng trả** (neo `ordered_at`, lọc `is_active_order`). Trả hàng nằm ở `refund_amount`/`realized_revenue` (neo `return_date`).
- Trong `external-references.md` §6.3, `net_revenue` = gross − discount − **return**. Theo chuẩn kế toán Việt Nam (B02-DN), "Doanh thu thuần" cũng là sau các khoản giảm trừ, **gồm hàng bán bị trả lại**.
- Nếu Phase 1 "hợp nhất" mà không xử lý, cùng một id sẽ cho số khác nhau giữa FJ và khách mới, và kế toán của khách sẽ thấy "Doanh thu thuần" không khớp sổ. Đề xuất ở mục (d).

### B2. Bộ tham số ghi nhận doanh thu vừa thiếu vừa thừa
- **Thiếu VAT.** Đây là khác biệt lớn nhất giữa các SME Việt: công ty kê khai VAT, hộ kinh doanh nộp thuế khoán không có VAT tách riêng, giá niêm yết có hoặc không gồm VAT. Hiện `/1.08` đang ghi cứng. Cần tham số `vat_mode`.
- **Thiếu trục thời gian theo report.** Một dashboard đang trộn `ordered_at`, `return_date`, `payout_released_at`. Spec v2 phải khai báo `time_axis` cho từng khối và hiển thị nó.
- **Thừa "sàn trợ giá" như một tham số.** Đây là câu hỏi kế toán có đáp án đúng (phân loại theo bên chịu tiền), không phải sở thích của khách. Mỗi tham số thêm vào là một chiều làm mất khả năng so sánh giữa khách và tăng tổ hợp cần test.
- **Đổi tham số = đổi số quá khứ.** Thiết kế chưa nói đổi tham số thì làm gì với số đã báo cáo. Cần ghi phiên bản quy ước vào hồ sơ khách và hiện ngày hiệu lực.

### B3. Thiếu cơ chế "giải thích được" cho người dùng kinh doanh
- Mỗi thẻ KPI cần **tooltip sinh tự động từ registry**: tên Việt, công thức bằng lời, quy ước đang áp dụng (ghi nhận theo ngày nào, có VAT không, có trừ hoàn không), và độ phủ dữ liệu.
- Cần **bảng chú giải Việt ↔ Anh** sinh từ registry, đặc biệt cặp "Doanh số / Doanh thu / Doanh thu thuần / Thực nhận", vì Pancake, Sapo, Haravan dùng các từ này khác nhau.
- Mỗi report cần một dòng chân trang "Quy ước số liệu" sinh tự động. Không có dòng này, cuộc gọi hỗ trợ đầu tiên của mọi khách sẽ là "sao số không khớp Sapo".

### B4. Thiếu chỉ báo độ phủ dữ liệu đi kèm chỉ tiêu biên lợi nhuận
- `gross_margin_pct` hiện chỉ tính trên dòng `has_cogs = true`. Nếu độ phủ giá vốn chỉ 60%, biên lợi nhuận vẫn trông "đẹp". Registry cần thuộc tính `coverage_metric` để mọi thẻ biên/CM hiện kèm "% doanh thu có giá vốn". Tương tự cho tỉ lệ `UNMAPPED` khi nhóm theo `*_std`.

### B5. Phân quyền theo ô không bảo vệ được dữ liệu nhạy cảm theo cột
- Giá vốn và biên lợi nhuận rất nhạy cảm với SME (nhân viên bán hàng không được thấy). Nếu report ô "Bán hàng" có thẻ CM1, hoặc trang chủ vai trò kéo thẻ biên vào, quyền theo ô bị vô hiệu.
- Đề xuất: thêm thuộc tính `sensitivity: cost` trên metric; deployer **từ chối** đặt metric `cost` vào report ngoài ô Tài chính và Điều hành cấp chiến lược/quản lý. Đây là kiểm tra tĩnh, rẻ, và không cần row-level security.

### B6. Catalog thiếu một số thuộc tính và capability
- Catalog cần `primary_cell` (mỗi report có đúng một ô chính; thẻ của nó có thể lên trang chủ khác) để chặn trùng lặp tái phát.
- Spec v2 cần `comparison` (so tuần trước, cùng kỳ năm trước, so mục tiêu) vì cấp quyết định khác nhau chủ yếu ở kỳ so sánh, không ở chỉ tiêu.
- Danh sách capability thiếu `targets` (mục tiêu/kế hoạch; scorecard phụ thuộc), `promotions`, `cash_settlement` (COD/sàn/ngân hàng), `staff`. Không có chúng thì không mở khoá đúng các report STD-cfg.

### B7. Con số "14–18 report" là mục tiêu tuỳ ý
- Lưới có 21 ô. Số report nên suy ra từ ô và câu hỏi, không định trước. Đề xuất ở (c) cho 19 report chuẩn + 2 report tiện ích, trong đó 2 ô để trống có chủ đích. Gộp thêm để về 14 sẽ tạo ra report "đa năng" khó đọc.

### B8. Ranh giới Marketing và Khách hàng chưa được định nghĩa
- Cohort, RFM, khách mới/quay lại đang được cả hai chức năng nhận. Đề xuất: **Marketing = thu hút và chi tiêu** (spend, MER, CAC, khuyến mãi); **Khách hàng = giữ chân, giá trị, chăm sóc** (cohort, RFM, LTV, hàng đợi). CAC payback thuộc Khách hàng (enhances `ad_spend`).

### B9. Thiếu report "niềm tin" trong catalog
- Đối soát danh sách đơn với Sapo admin (`order_listing_reconciliation`), tra cứu một đơn (`order_detail_view`) và sức khoẻ dữ liệu (`ingestion_health` + `UNMAPPED` + độ phủ giá vốn) phải là report tiện ích cài mặc định. Đây là thứ giúp kế toán tin số trong tuần đầu.

## (c) Catalog chuẩn đề xuất theo lưới 7 chức năng × 3 cấp

Capability dùng dưới đây: `orders`, `order_lines`, `products`, `customers`, `staff`, `stores`, `promotions`, `targets`, `inventory_snapshot`, `fulfillment_events`, `return_events`, `marketplace_settlement`, `cash_settlement`, `unit_cost`, `shipping_cost`, `ledger`, `ad_spend`, `crm_contacts`, `care_tasks`. Cấp: CL = Chiến lược/tháng, QL = Quản lý/tuần, TN = Tác nghiệp/ngày.

| Ô | Mã | Report | Câu hỏi | requires | enhances | Artifact dùng lại (gộp) |
|---|---|---|---|---|---|---|
| Điều hành × CL | EXE-M | Scorecard tháng | Tháng có đạt mục tiêu, sức khoẻ tổng thể? | orders | targets, unit_cost, marketplace_settlement, ad_spend, return_events | `ceo_monthly_scorecard` |
| Điều hành × QL | EXE-W | Nhịp tuần | Tuần này so tuần trước/cùng kỳ, kênh nào kéo? | orders | targets, unit_cost, ad_spend | `ceo_weekly_pulse` (MB + EV) |
| Điều hành × TN | — | **Để trống có chủ đích** | Màn "hôm nay" của chủ shop là **trang chủ vai trò** ghép từ SAL-D, LOG-D, INV-D, CUS-D, không phải report riêng | — | — | Trang chủ "Chủ shop" |
| Bán hàng × CL | SAL-M | Bán hàng tháng theo kênh × sản phẩm × vùng | Bán gì, ở đâu, xu hướng ra sao? | orders, order_lines, products | targets, stores | `sales_monthly_review` + `sales_ops_monthly_summary` |
| Bán hàng × QL | SAL-W | Review bán hàng tuần và nhân viên | Kênh/cửa hàng/nhân viên nào lệch so với tuần trước? | orders | staff, stores, targets | `sales_ops_weekly_review` + `social_commerce_ops` (phần chuẩn) |
| Bán hàng × TN | SAL-D | Bán hàng hôm nay và chốt ca | Hôm nay/hôm qua bán bao nhiêu, ca nào khớp tiền? | orders | staff, stores, cash_settlement | Gộp 4 biến thể `sales_daily_*`, `yesterday_operation`, `sales_today_operation`, trang EV |
| Marketing × CL | MKT-M | Hiệu quả marketing tháng | Tiền quảng cáo có ra lãi? MER, NC-ROAS, CM3 theo kênh | orders, ad_spend | unit_cost, customers | `marketing_roi` + `marketing_monthly_analysis` |
| Marketing × QL | MKT-W | Kênh, chiến dịch và khuyến mãi tuần | Kênh/chiến dịch/mã giảm giá nào hiệu quả tuần này? | orders | ad_spend, promotions, unit_cost | `marketing_weekly_tracker` + `sales_promotion_analysis` (khối khuyến mãi) |
| Marketing × TN | — | **Để trống có chủ đích ở v1** | Theo dõi chi tiêu trong ngày đã có sẵn trong Ads Manager; giá trị xuyên nguồn của ta chỉ xuất hiện ở cấp tuần trở lên | — | — | — |
| Tài chính × CL | FIN-M | P&L tháng và lợi nhuận theo kênh × SKU × đơn | Lãi thật sau mọi chi phí ở đâu? CM1 → CM2 → CM3 → lãi sau chi phí chung | orders, unit_cost | marketplace_settlement, shipping_cost, ad_spend, ledger, return_events | `finance_pl` + `finance_cost_ledger` (drill) + `channel_profitability_monthly` + `channel_p_l_deep_dive` + `order_profitability_all` + `product_profitability` + `finance_return_impact` (dòng trả hàng) |
| Tài chính × QL | FIN-W | Dòng tiền, công nợ và ngân sách tuần | Tiền còn bao nhiêu, sắp thu/chi gì, lệch ngân sách? | ledger | cash_settlement, targets | `finance_cashflow` (MB + EV) + `finance_cashflow_budget` |
| Tài chính × TN | FIN-D | Đối soát tiền về | Sàn/COD/ngân hàng đã trả chưa, lệch đơn nào? | orders, cash_settlement hoặc marketplace_settlement | ledger | `finance_accounting_recon` + phần thực nhận của `shopee_channel_economics` |
| Hàng hoá × CL | INV-M | Sức khoẻ danh mục tháng | SKU nào nên đẩy, giữ, bỏ? ABC, biên, sell-through | order_lines, products | unit_cost, inventory_snapshot, marketplace_settlement | `product_health_overview` + `shopee_channel_economics` (phần SKU) |
| Hàng hoá × QL | INV-W | Tốc độ bán và tồn kho tuần | Hàng nào bán chậm, tồn lâu, cần nhập? | order_lines, inventory_snapshot | unit_cost (giá trị tồn) | `product_performance_velocity` + `inventory_stock_health` |
| Hàng hoá × TN | INV-D | Hàng sắp hết và hết hàng hôm nay | Cần nhập/điều chuyển gì ngay? | inventory_snapshot | order_lines | `inventory_stock_health` (khối OOS) + `mart_product_action_queue` |
| Giao vận × CL | LOG-M | Chất lượng giao vận tháng theo hãng VC × tỉnh | Hãng nào, tỉnh nào giao kém, phí VC/đơn bao nhiêu? | orders, fulfillment_events | shipping_cost, return_events | `logistics_shipping` / carrier |
| Giao vận × QL | LOG-W | Hoàn, huỷ và SLA tuần | Tỉ lệ hoàn/huỷ, trễ xử lý tuần này vì đâu? | orders | fulfillment_events, return_events | `finance_return_impact` (khối vận hành) + `order_lifecycle_transitions` |
| Giao vận × TN | LOG-D | Trung tâm xử lý đơn hôm nay | Đơn nào chờ, trễ, kẹt COD? | orders | fulfillment_events, cash_settlement | `logistics_operations` (Ops Center) |
| Khách hàng × CL | CUS-M | Cohort, giữ chân và giá trị khách | Khách mới có quay lại? LTV, CAC payback theo cohort | orders, customers | unit_cost, ad_spend | `customer_retention_cohorts` + 2 blueprint cohort trùng + `customer_profitability` |
| Khách hàng × QL | CUS-W | Phân khúc RFM và khách có nguy cơ rời | Nhóm khách nào đang dịch chuyển? | orders, customers | crm_contacts | `customer_intelligence` |
| Khách hàng × TN | CUS-D | Hàng đợi chăm sóc hôm nay | Gọi ai hôm nay, vì sao? | orders, customers | crm_contacts, care_tasks | `customer_daily_action_queue` |

**Tiện ích, cài mặc định, ngoài lưới:** UTL-1 Sức khoẻ dữ liệu (`ingestion_health` + `UNMAPPED` + độ phủ giá vốn); UTL-2 Tra cứu và đối soát đơn với nguồn (`order_listing_reconciliation` + `order_detail_view`).

**Không vào catalog chuẩn:**
- Sang overlay FJ: `finance_services_revenue`, `b2b_sales_daily`, `b2b_orders_tracking`, Rill `orders_b2b_ops`, `us_crossborder_operations`, `welcome_landing`, phần social theo tên nhân viên FJ.
- Chờ chuẩn hoá CRM: `crm_outreach_effort_weekly`.
- Chuyển thành công cụ phân tích tự do (Rill, sinh từ registry), không phải report: `order_revenue_explorer`, Rill Executive/Retail Ops/Sales Items, `cohort_calendar_trend`.
- Cần đọc trước khi phân loại: Evidence `theme-mvp`.

**Tổng:** 19 report chuẩn + 2 tiện ích, 2 ô trống có chủ đích. Report chỉ cần `orders` (mở cho mọi shop chỉ có POS): EXE-M, EXE-W, SAL-W, SAL-D, MKT-W, LOG-W, LOG-D, cộng các report cần thêm `customers`/`order_lines` mà mọi POS đều có. Như vậy shop nhỏ nhất vẫn nhận ~12 report có nghĩa.

## (d) Đề xuất cho §9

### Quyết định 1: quy ước doanh thu mặc định

**Nguyên tắc chung:** ít tham số nhất có thể. Mặc định phải trùng cách mart FJ đang tính (để không đổi số FJ, đúng "Không làm") và trùng báo cáo mặc định của Sapo/Haravan (để chủ shop đối chiếu được).

1. **Thời điểm ghi nhận: khi tạo đơn (đơn đã xác nhận, không huỷ, không nháp).** Lý do: mart hiện neo `ordered_at` và lọc `is_active_order`; Sapo/Haravan mặc định theo ngày tạo đơn; số có ngay trong ngày cho cấp tác nghiệp. Tham số `revenue_recognized_at` vẫn cho chọn `delivered`, nhưng ngoài ra registry nên có sẵn metric riêng `delivered_net_revenue` (requires `fulfillment_events`) để CFO của shop COD xem P&L theo giao thành công mà không đổi số toàn hệ thống.
2. **Trả hàng: trừ vào kỳ hoàn tất trả hàng (`return_date`), hiện thành dòng riêng trong thác doanh thu.** Lý do: khớp kế toán (hàng bán bị trả lại ghi giảm trừ trong kỳ phát sinh), khớp neo thời gian hiện có của `refund_amount`/`return_rate`, và không làm số tháng đã chốt thay đổi về sau. Bổ sung một góc nhìn "tỉ lệ hoàn theo cohort ngày đặt" ở LOG-W/INV-M cho mục đích chất lượng.
3. **Đặt tên để giải B1 (cần user duyệt):**
   - `net_sales` — "Doanh thu bán hàng (trước trả hàng)" = tiền hàng − giảm giá do shop chịu, chưa VAT, neo ngày đơn. Đây chính là `net_revenue` hiện tại của FJ, đổi id và giữ alias `net_revenue` → `net_sales` trong thời gian chuyển.
   - `returns_amount` — "Hàng bán bị trả lại", neo ngày hoàn.
   - `net_revenue` — "Doanh thu thuần" = `net_sales` − `returns_amount`, khớp B02-DN. Mọi biên lợi nhuận và CM dùng `net_revenue`.
   - Cách này không đổi số nào của FJ, chỉ đổi tên; dashboard FJ đang dùng `net_revenue` nghĩa cũ được ánh xạ sang `net_sales` khi chuyển.
4. **VAT: mặc định doanh thu không gồm VAT.** Tham số `vat_mode` ∈ {`included_in_price`, `excluded_from_price`, `not_applicable`}; tỉ suất lấy từ dữ liệu dòng hàng, không ghi cứng 8%. Lý do: chuẩn kế toán; hộ kinh doanh chọn `not_applicable`.
5. **Sàn trợ giá: không phải tham số.** Phân loại theo bên chịu tiền: voucher/trợ giá do sàn chịu **được tính vào doanh thu** (shop vẫn nhận đủ giá bán qua settlement), nhưng hiện thành dòng riêng "Sàn trợ giá" trong thác; voucher do shop chịu là giảm giá; voucher đồng tài trợ tách theo tỉ lệ. Lý do: đúng bản chất kinh tế, giữ AOV và biên giữa kênh sàn và POS so sánh được, khớp "Doanh thu bán hàng" của Pancake. Phí sàn không trừ vào doanh thu mà vào CM2.
6. **AOV = `net_sales` / số đơn ghi nhận, tỉ số của tổng, không gồm phí ship và VAT.** Lý do: AOV đo giá trị giỏ lúc mua; trừ hoàn (neo kỳ khác) làm AOV dao động khó giải thích; khớp Shopify (gross − discount, không điều chỉnh), Pancake (không trừ hoàn) và FJ hiện tại. Tooltip ghi rõ "không gồm VAT, nên thấp hơn số trên Sapo" và trỏ sang `avg_order_spend` (góc nhìn khách, gồm VAT).
7. **Chốt luôn hai định nghĩa hay gây tranh cãi:** `mer` = `net_revenue` toàn kênh / tổng `ad_spend` (chiều doanh thu/chi phí, ghi chú là nghịch đảo của Triple Whale); thang lợi nhuận CM1 = `net_revenue` − COGS; CM2 = CM1 − phí sàn − phí VC shop trả − phí thanh toán; CM3 = CM2 − `ad_spend`; Lãi vận hành = CM3 − chi phí chung (`ledger`). Ánh xạ: `channel_net_profit` hiện tại ≈ CM2 thiếu phí VC; `fully_loaded_net_profit` cần kiểm xem có trừ quảng cáo không trước khi gán.

### Quyết định 3: catalog và registry đặt ở đâu
**Module code có JSON Schema và kiểm tra trong CI**, không phải trong `docs/`. Renderer, deployer và kiểm tra `sensitivity`/`requires` đều đọc nó; tài liệu không được kiểm tra thì sẽ trôi như 11 mâu thuẫn hiện có. `metrics.md` và bảng chú giải được sinh ra vào `docs/analytics-handbook/`. Kèm "golden query test": mỗi metric × một kỳ mẫu phải ra cùng số ở mart và ở query sinh cho Metabase.

### Quyết định 4: phân quyền theo dòng ở v1
**Không.** Metabase OSS không có sandboxing; tự làm view theo nhóm là chi phí lớn cho nhu cầu chưa có khách thứ hai xác nhận. Rủi ro thật ở v1 là **lộ giá vốn theo cột**, và nó được xử lý bằng quy tắc `sensitivity: cost` ở B5. Nếu một khách cần lọc chi nhánh, làm bằng overlay: report riêng có bộ lọc khoá cứng trong collection riêng.

### Quyết định 5: persona mẫu
Sáu persona, đặt tên theo việc chứ không theo chức danh lớn, kèm hai bộ cài sẵn theo cỡ:

| Persona | Ô được gán |
|---|---|
| Chủ shop | EXE-M, EXE-W, SAL-D, LOG-D, INV-W, CUS-D; FIN-M nếu có `unit_cost` |
| Giám đốc | Mọi ô CL + EXE-W, FIN-W |
| Kế toán / Tài chính | FIN-M, FIN-W, FIN-D, UTL-2 |
| Marketing | MKT-M, MKT-W, CUS-M, CUS-W |
| Vận hành / Kho | LOG-*, INV-W, INV-D, SAL-D |
| Trưởng nhóm bán hàng / CSKH | SAL-W, SAL-D, CUS-W, CUS-D (không ô nào có metric `cost`) |

Bộ "shop nhỏ": Chủ shop + Kế toán. Bộ "doanh nghiệp vừa": cả sáu. Mỗi trang chủ giới hạn 6–8 thẻ, thẻ lấy theo `kpi_tiles` của report trong ô được gán, theo thứ tự cấp TN → QL → CL cho persona tác nghiệp và ngược lại cho persona lãnh đạo.

## (e) Rủi ro hàng đầu

1. **Đổi nghĩa chỉ tiêu khi hợp nhất registry (cao).** 56 + 53 định nghĩa có trùng tên khác nghĩa (B1). Giảm thiểu: Phase 1 phải xuất "bảng đối chiếu tên cũ → id mới → số mẫu" và chạy so số FJ trước khi sinh lại `metrics.md`.
2. **Tham số theo khách làm mất khả năng so sánh và đổi số quá khứ (cao).** Giảm thiểu: chỉ ba tham số (`revenue_recognized_at`, `vat_mode`, `return_deducted_at`), ghi phiên bản quy ước có ngày hiệu lực, chân trang "Quy ước số liệu" trên mọi report.
3. **Số "đẹp giả" do thiếu dữ liệu (cao).** Biên tính trên 60% đơn có giá vốn, kênh `UNMAPPED` lớn. Giảm thiểu: `coverage_metric` bắt buộc cho metric biên và cho mọi khối nhóm theo `*_std`.
4. **Lộ giá vốn qua trang chủ hoặc report bán hàng (trung bình–cao).** Giảm thiểu: `sensitivity: cost` kiểm tĩnh trong deployer.
5. **Catalog phình lại qua "promote" (trung bình).** Giảm thiểu: chỉ promote khi ≥ 2 khách dùng, chỉ dùng metric chuẩn, có `primary_cell` chưa bị report khác chiếm câu hỏi.
6. **Phụ thuộc taxonomy (trung bình).** Report chuẩn nhóm theo `*_std` nhưng bộ mã chuẩn chưa chốt vì thiếu khách thứ hai. Giảm thiểu: v1 chỉ dùng `channel_std` và `order_status_std`; hiện tỉ lệ `UNMAPPED` ở UTL-1.
7. **Trộn trục thời gian trong một dashboard (trung bình).** Doanh thu theo ngày đơn, hoàn theo ngày hoàn, tiền về theo ngày payout nằm cạnh nhau sẽ không cộng trừ được với nhau. Giảm thiểu: `time_axis` bắt buộc trong spec v2 và hiện trên tiêu đề khối.

## Câu hỏi còn mở
- User có chấp nhận đổi id `net_revenue` hiện tại thành `net_sales` (giữ số, đổi tên) để "Doanh thu thuần" khớp chuẩn kế toán không?
- Dữ liệu Shopee hiện có tách voucher theo bên chịu tiền (sàn/shop/đồng tài trợ) không? Nếu không, quy tắc ở (d)5 cần một bước ánh xạ trong pack marketplace.
- `fully_loaded_net_profit` hiện có trừ chi phí quảng cáo không? Cần trước khi gán vào thang CM.

Status: DONE
Summary: Đã phản biện thiết kế từ góc độ Trưởng BI, đề xuất catalog 19 report chuẩn + 2 tiện ích phủ lưới 7×3 (2 ô trống có chủ đích), quy ước doanh thu mặc định khớp mart FJ hiện tại, và trả lời quyết định 3–5.
Concerns: Xung đột nghĩa `net_revenue` giữa `metrics.md` (trước trả hàng) và tham chiếu ngoài/VAS (sau trả hàng) phải được user chốt trước Phase 1; quy tắc trợ giá sàn phụ thuộc dữ liệu voucher Shopee chưa được kiểm.
