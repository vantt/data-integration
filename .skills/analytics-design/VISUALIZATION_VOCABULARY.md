# Standard Visualization Vocabulary

## Purpose

25 tool-agnostic visualization terms + 1 composition concept.
Used by the Analyst skill in **Phase 5 — Visualization Selection**.

This vocabulary is the **contract** between the Analyst and Engineer skills:
- Analyst chọn term từ danh sách này (Phase 5).
- Engineer đọc term và map sang tool-specific implementation.
- Không bên nào sử dụng term ngoài danh sách.

---

## Vocabulary Table (25 Viz Types)

| # | Standard Term | Communication Strength | Metabase Support |
|---|--------------|----------------------|------------------|
| 1 | `single-value` | Snapshot — "con số hiện tại" | ✅ Native (`scalar`) |
| 2 | `single-value-with-trend` | Snapshot + direction — "đang tăng hay giảm" | ✅ Native (`scalar` + comparison) |
| 3 | `progress-toward-goal` | Linear progress — "đã đạt bao nhiêu % mục tiêu" | ✅ Native (`progress`) |
| 4 | `gauge` | Position in range — "đang ở vùng nào (nguy hiểm/cảnh báo/tốt)" | ✅ Native (`gauge`) |
| 5 | `line-chart` | Trend — "biến động theo thời gian" | ✅ Native (`line`) |
| 6 | `multi-line-chart` | Multi-series trend — "so sánh xu hướng nhiều đối tượng" | ✅ Native (`line` multi-series) |
| 7 | `area-chart` | Volume trend — "xu hướng với emphasis vào khối lượng" | ✅ Native (`area`) |
| 8 | `stacked-area` | Composition over time — "thành phần nào drive thay đổi tổng" | ✅ Native (`area` + stack) |
| 9 | `vertical-bar` | Categorical comparison — "cái nào lớn hơn" | ✅ Native (`bar`) |
| 10 | `horizontal-bar` | Ranked comparison — "top N, bottom N" | ✅ Native (`row`) |
| 11 | `stacked-bar` | Categorical composition — "cấu thành của mỗi category" | ✅ Native (`bar` + stack) |
| 12 | `grouped-bar` | Side-by-side comparison — "so sánh trực tiếp 2+ nhóm" | ✅ Native (`bar` grouped) |
| 13 | `stacked-bar-time` | Composition over time (discrete) — "cấu thành thay đổi qua từng kỳ" | ✅ Native (`bar` + stack + time) |
| 14 | `combo-chart` | Dual-metric correlation — "2 metrics có tương quan không" | ✅ Native (`combo`) |
| 15 | `donut` | Part-to-whole (static) — "tỷ lệ phần trăm" (<=5 phần) | ✅ Native (`pie`) |
| 16 | `funnel` | Sequential conversion — "drop-off ở bước nào" | ✅ Native (`funnel`) |
| 17 | `waterfall` | Additive contributions — "yếu tố nào tăng/giảm tổng" | ✅ Native (`waterfall`) |
| 18 | `data-table` | Detail & lookup — "dữ liệu đầy đủ cho drill-down" | ✅ Native (`table`) |
| 19 | `data-table-formatted` | Detail + alerts — "highlight dòng/ô cần chú ý" | ✅ Native (`table` + conditional formatting) |
| 20 | `pivot-table` | Multi-dimensional — "cross-tab analysis" | ✅ Native (`pivot`) |
| 21 | `scatter-plot` | Correlation — "2 biến có liên hệ gì" | ✅ Native (`scatter`) |
| 22 | `geographic-map` | Spatial distribution — "phân bố theo địa lý" | ✅ Native (`map`) |
| 23 | `heatmap` | Intensity matrix — "đậm/nhạt theo 2 chiều" | ⚠️ Fallback (`pivot` + conditional formatting) |
| 24 | `sparkline` | Inline mini-trend — "trend nhỏ gọn kèm theo số" | ⚠️ Fallback (`scalar` + trend) |
| 25 | `text-annotation` | Narrative — "heading, ghi chú, giải thích" | ✅ Native (text dashcard) |

> **Lưu ý**: Cột Metabase Support chỉ dùng để quick feasibility check. Analyst không cần quan tâm chi tiết implementation.

---

## Composition Concept (NOT a Viz Type)

| Concept | Description | Metabase Support |
|---------|-------------|------------------|
| `view-group` | Logical grouping of cards into separate views. Decided in Phase 4d, NOT Phase 5. | ✅ Native (dashboard tabs) |

`view-group` KHÔNG phải viz type. Analyst quyết định view-group ở Phase 4d (Layout Design), trước khi chọn viz type ở Phase 5.

---

## Detailed Definitions

### 1. `single-value`

- **Communication strength**: Cho biết con số hiện tại của một metric quan trọng.
- **Data shape**: 1 measure (single row, single column).
- **Best for**:
  - KPI headline (doanh thu hôm nay, tổng đơn hàng).
  - Metric cần nhìn nhanh trong 1 giây.
  - Hero card trên dashboard.
- **Avoid when**: Cần ngữ cảnh (tăng hay giảm); dùng `single-value-with-trend` thay thế.

### 2. `single-value-with-trend`

- **Communication strength**: Cho biết con số hiện tại VÀ hướng thay đổi so với kỳ trước.
- **Data shape**: 1 measure + 1 comparison measure (hoặc auto-calculated % change).
- **Best for**:
  - KPI headline kèm context (doanh thu tháng này vs tháng trước).
  - Khi viewer cần biết "đang tốt lên hay xấu đi".
- **Avoid when**: Metric không có kỳ trước để so sánh; dùng `single-value`.

### 3. `progress-toward-goal`

- **Communication strength**: Cho biết đã đạt bao nhiêu phần trăm mục tiêu.
- **Data shape**: 1 measure + 1 target value.
- **Best for**:
  - Theo dõi tiến độ KPI vs target (doanh thu vs quota).
  - Linear progress (0% -> 100%).
- **Avoid when**: Target không rõ ràng hoặc không có target cố định; dùng `single-value-with-trend`.

### 4. `gauge`

- **Communication strength**: Cho biết giá trị đang nằm ở vùng nào trong range (nguy hiểm / cảnh báo / tốt).
- **Data shape**: 1 measure + defined ranges (min, max, thresholds).
- **Best for**:
  - Metrics có vùng rõ ràng (tỷ lệ hủy đơn: xanh < 5%, vàng 5-10%, đỏ > 10%).
  - Hero card cần visual impact mạnh.
- **Avoid when**: Không có range rõ ràng; dùng `single-value-with-trend`.

### 5. `line-chart`

- **Communication strength**: Cho biết metric biến động như thế nào theo thời gian.
- **Data shape**: Time series + 1 measure.
- **Best for**:
  - Trend doanh thu theo ngày/tuần/tháng.
  - Phát hiện seasonal patterns.
  - Continuous data over time.
- **Avoid when**: Chỉ có vài thời điểm rời rạc (dùng `vertical-bar`); data không phải time series.

### 6. `multi-line-chart`

- **Communication strength**: So sánh xu hướng của nhiều đối tượng trên cùng timeline.
- **Data shape**: Time series + 1 measure + 1 category dimension (2-7 series).
- **Best for**:
  - So sánh doanh thu theo kênh bán hàng qua thời gian.
  - So sánh performance nhiều sản phẩm.
- **Avoid when**: Quá nhiều series (> 7) gây rối mắt; dùng `data-table` hoặc filter.

### 7. `area-chart`

- **Communication strength**: Thể hiện xu hướng với emphasis vào khối lượng tổng.
- **Data shape**: Time series + 1 measure.
- **Best for**:
  - Khi muốn nhấn mạnh volume (số lượng đơn hàng theo ngày).
  - Single series mà viewer cần cảm nhận "lớn hay nhỏ".
- **Avoid when**: Có nhiều series chồng lên nhau gây khó đọc; dùng `line-chart`.

### 8. `stacked-area`

- **Communication strength**: Cho biết thành phần nào drive thay đổi của tổng theo thời gian.
- **Data shape**: Time series + 1 measure + 1 category dimension.
- **Best for**:
  - Doanh thu theo kênh, muốn thấy tổng VÀ cấu thành.
  - Khi phần đóng góp thay đổi theo thời gian là insight chính.
- **Avoid when**: Series quá nhiều hoặc values xấp xỉ nhau; dùng `multi-line-chart`.

### 9. `vertical-bar`

- **Communication strength**: So sánh giá trị giữa các category — cái nào lớn hơn.
- **Data shape**: Categories (<=7) x 1 measure.
- **Best for**:
  - So sánh doanh thu theo chi nhánh.
  - Discrete time periods (doanh thu Q1 vs Q2 vs Q3).
  - Default choice cho categorical comparison.
- **Avoid when**: Quá nhiều categories (> 7); dùng `horizontal-bar` hoặc `data-table`.

### 10. `horizontal-bar`

- **Communication strength**: Ranking — top N hoặc bottom N.
- **Data shape**: Categories x 1 measure, sorted by value.
- **Best for**:
  - Top 10 sản phẩm bán chạy.
  - Bottom 5 chi nhánh doanh thu thấp nhất.
  - Category labels dài (tên sản phẩm, tên nhân viên).
- **Avoid when**: Không cần ranking; categories ít (<=5) thì `vertical-bar` trực quan hơn.

### 11. `stacked-bar`

- **Communication strength**: Cho biết cấu thành của mỗi category.
- **Data shape**: Categories x 1 measure x 1 sub-category dimension.
- **Best for**:
  - Doanh thu theo chi nhánh, chia theo phương thức thanh toán.
  - Khi cần thấy tổng VÀ breakdown cùng lúc.
- **Avoid when**: Chỉ có 1 series (dùng `vertical-bar`); quá nhiều sub-categories.

### 12. `grouped-bar`

- **Communication strength**: So sánh trực tiếp 2+ nhóm bên cạnh nhau.
- **Data shape**: Categories x 1 measure x 1 grouping dimension (2-4 groups).
- **Best for**:
  - So sánh doanh thu online vs offline theo chi nhánh.
  - Khi giá trị tuyệt đối của từng group quan trọng hơn tổng.
- **Avoid when**: Quá nhiều groups (> 4); dùng `stacked-bar` hoặc `data-table`.

### 13. `stacked-bar-time`

- **Communication strength**: Cấu thành thay đổi qua từng kỳ (discrete time).
- **Data shape**: Time periods x 1 measure x 1 category dimension.
- **Best for**:
  - Doanh thu theo tháng, chia theo loại sản phẩm.
  - Khi cần thấy cả tổng và cấu thành theo từng kỳ.
- **Avoid when**: Quá nhiều categories; continuous trend quan trọng hơn cấu thành (dùng `stacked-area`).

### 14. `combo-chart`

- **Communication strength**: Cho biết 2 metrics có tương quan không (dual axis).
- **Data shape**: Time series (or categories) + 2 measures (different scales).
- **Best for**:
  - Doanh thu (bar) + margin % (line) trên cùng chart.
  - Số đơn hàng (bar) + giá trị trung bình đơn (line).
- **Avoid when**: 2 metrics cùng scale; dùng `multi-line-chart` hoặc `grouped-bar`.

### 15. `donut`

- **Communication strength**: Tỷ lệ phần trăm — part-to-whole snapshot.
- **Data shape**: Categories (<=5) x 1 measure.
- **Best for**:
  - Tỷ lệ doanh thu theo kênh (khi <=5 kênh).
  - Phân bổ ngân sách theo department.
- **Avoid when**: Hơn 5 slices (dùng `vertical-bar`); cần so sánh chính xác giữa parts (bar tốt hơn).

### 16. `funnel`

- **Communication strength**: Drop-off ở bước nào trong quy trình tuần tự.
- **Data shape**: Sequential stages x 1 measure (descending).
- **Best for**:
  - Conversion funnel: Visit -> Add to cart -> Checkout -> Payment -> Complete.
  - Quy trình tuyển dụng: Apply -> Interview -> Offer -> Accept.
- **Avoid when**: Stages không tuần tự; data không descending tự nhiên.

### 17. `waterfall`

- **Communication strength**: Yếu tố nào làm tăng / giảm tổng.
- **Data shape**: Categories x 1 measure (positive/negative contributions) + starting/ending total.
- **Best for**:
  - Bridge chart: Doanh thu Q1 + các yếu tố = Doanh thu Q2.
  - Phân tích variance: Budget vs Actual, breakdown theo factors.
- **Avoid when**: Không có logic cộng dồn; dùng `vertical-bar` cho simple comparison.

### 18. `data-table`

- **Communication strength**: Dữ liệu đầy đủ cho tra cứu và drill-down.
- **Data shape**: Multiple dimensions x multiple measures (tabular).
- **Best for**:
  - Chi tiết đơn hàng, danh sách khách hàng.
  - Khi viewer cần tra cứu giá trị cụ thể.
  - Supporting detail cho summary cards.
- **Avoid when**: Chỉ có 1-2 số; dùng `single-value`. Chỉ cần trend; dùng chart.

### 19. `data-table-formatted`

- **Communication strength**: Dữ liệu chi tiết + highlight dòng/ô cần chú ý.
- **Data shape**: Multiple dimensions x multiple measures + conditional rules.
- **Best for**:
  - Danh sách đơn hàng, highlight đơn quá hạn (đỏ).
  - Performance table, highlight top performers (xanh) và under-performers (đỏ).
- **Avoid when**: Không có logic conditional rõ ràng; dùng `data-table` đơn giản.

### 20. `pivot-table`

- **Communication strength**: Phân tích cross-tab nhiều chiều.
- **Data shape**: 2+ dimensions x 1+ measures (matrix layout).
- **Best for**:
  - Doanh thu theo chi nhánh (rows) x tháng (columns).
  - Cross-tab analysis cần flexible slicing.
- **Avoid when**: Chỉ có 1 dimension; dùng `data-table` hoặc `vertical-bar`.

### 21. `scatter-plot`

- **Communication strength**: 2 biến có liên hệ gì — correlation.
- **Data shape**: 2 measures (x-axis, y-axis) + optional category dimension.
- **Best for**:
  - Mối quan hệ giữa chi tiêu marketing và doanh thu.
  - Phân bổ khách hàng theo frequency vs monetary value.
- **Avoid when**: 1 trong 2 biến là time (dùng `line-chart`); data points quá ít.

### 22. `geographic-map`

- **Communication strength**: Phân bố theo địa lý.
- **Data shape**: Geographic dimension (lat/lng, region, country) + 1 measure.
- **Best for**:
  - Doanh thu theo tỉnh/thành.
  - Mật độ khách hàng theo khu vực.
- **Avoid when**: Không có geographic dimension; dùng chart/table thông thường.

### 23. `heatmap`

- **Communication strength**: Cường độ theo 2 chiều — đậm/nhạt.
- **Data shape**: 2 category dimensions x 1 measure (intensity).
- **Best for**:
  - Doanh thu theo ngày trong tuần x giờ trong ngày.
  - Activity matrix: nhân viên x loại task.
- **Avoid when**: 1 dimension ít giá trị (< 3); dùng `vertical-bar` với color encoding.

### 24. `sparkline`

- **Communication strength**: Trend nhỏ gọn kèm theo con số chính.
- **Data shape**: Time series + 1 measure (condensed).
- **Best for**:
  - Mini-trend inline cạnh KPI number.
  - Dashboard header cần density cao.
- **Avoid when**: Cần đọc giá trị cụ thể từ trend; dùng `line-chart` full-size.

### 25. `text-annotation`

- **Communication strength**: Heading, ghi chú, giải thích cho dashboard.
- **Data shape**: Static text (no data query).
- **Best for**:
  - Section heading chia dashboard thành vùng.
  - Ghi chú methodology hoặc caveats.
  - Giải thích context cho viewer.
- **Avoid when**: Có data cần hiển thị; dùng viz type phù hợp.

---

## Decision Tree (Phase 5)

Analyst sử dụng decision tree này để chọn viz type cho mỗi card.

```
1. Card là Annotation? -> text-annotation, kết thúc

2. Data shape?
   |-- Single value              -> single-value / gauge / progress-toward-goal
   |-- Single value + target     -> progress-toward-goal / gauge
   |-- Time series               -> line-chart / area-chart / vertical-bar
   |-- Categories (<=7)          -> vertical-bar / donut / horizontal-bar
   |-- Categories (>7)           -> data-table / horizontal-bar (top N)
   |-- Categories x Time         -> stacked-bar-time / stacked-area
   |-- Sequential stages         -> funnel
   |-- Additive parts            -> waterfall
   +-- Two measures              -> scatter-plot / combo-chart

3. Refine by Communication Goal:
   |-- "position vs target"      -> gauge (range) / progress-toward-goal (linear)
   |-- "trend direction"         -> line-chart / single-value-with-trend
   |-- "compare categories"      -> horizontal-bar
   |-- "composition"             -> donut (<=5) / stacked-bar (>5 or over time)
   |-- "ranking"                 -> horizontal-bar (sorted)
   +-- "detail lookup"           -> data-table-formatted

4. Cross-check with Role:
   |-- Hero                      -> prefer visual impact (gauge > single-value)
   +-- Detail                    -> prefer density (data-table, pivot-table)

5. Anti-pattern check:
   |-- donut > 5 slices?                -> vertical-bar
   |-- line-chart for non-temporal?     -> vertical-bar
   |-- gauge without clear range?       -> single-value-with-trend
   +-- stacked-bar with 1 series?       -> vertical-bar
```

### Ví dụ áp dụng Decision Tree

| Scenario | Step 2 | Step 3 | Step 4 | Final Choice |
|----------|--------|--------|--------|-------------|
| Doanh thu hôm nay (Hero card) | Single value | "position vs target" | Hero -> visual impact | `gauge` (nếu có range) hoặc `single-value-with-trend` |
| Doanh thu 12 tháng qua | Time series | "trend direction" | -- | `line-chart` |
| Top 10 sản phẩm bán chạy | Categories (10 > 7) | "ranking" | -- | `horizontal-bar` (top N) |
| Tỷ lệ doanh thu theo 4 kênh | Categories (4 <= 5) | "composition" | -- | `donut` |
| Doanh thu theo tháng x loại SP | Categories x Time | "composition" | -- | `stacked-bar-time` |
| Chi tiết đơn hàng | Tabular data | "detail lookup" | Detail | `data-table-formatted` |

---

## Edge-case Terms

6 terms được giải quyết bằng analyst judgment, KHÔNG nằm trong decision tree chính:

| Term | When to Use (Analyst Judgment) |
|------|-------------------------------|
| `multi-line-chart` | Khi `line-chart` có >=2 series cần so sánh trên cùng timeline. Analyst chọn thay `line-chart` khi series > 1. |
| `grouped-bar` | Khi cần so sánh side-by-side thay vì stacked. Analyst chọn thay `stacked-bar` khi giá trị tuyệt đối của từng group quan trọng hơn tổng. |
| `pivot-table` | Khi cần cross-tab 2+ dimensions. Analyst chọn thay `data-table` khi matrix layout phù hợp hơn flat table. |
| `geographic-map` | Khi data có geographic dimension (tỉnh/thành, quốc gia, lat/lng). Chỉ analyst mới biết data có geo hay không. |
| `heatmap` | Rare. Khi cần intensity matrix theo 2 chiều (thời gian x category). Analyst cân nhắc khi `pivot-table` cần visual encoding mạnh hơn. |
| `sparkline` | Rare. Khi cần mini-trend inline cạnh `single-value`. Analyst chọn khi dashboard cần density cao và full `line-chart` quá lớn. |

> **Rule**: Decision tree cho 19 terms chính. 6 terms trên do analyst override khi context yêu cầu.

---

## Quick Reference: Data Shape to Viz Type

| Data Shape | Primary Choices | Secondary Choices |
|-----------|----------------|-------------------|
| 1 measure | `single-value` | `single-value-with-trend`, `gauge`, `progress-toward-goal` |
| 1 measure + target | `progress-toward-goal` | `gauge` |
| Time series + 1 measure | `line-chart` | `area-chart`, `vertical-bar` |
| Time series + 1 measure + categories | `stacked-bar-time` | `stacked-area`, `multi-line-chart` |
| Categories (<=7) + 1 measure | `vertical-bar` | `horizontal-bar`, `donut` (<=5) |
| Categories (>7) + 1 measure | `horizontal-bar` (top N) | `data-table` |
| Categories + sub-categories + 1 measure | `stacked-bar` | `grouped-bar` |
| Sequential stages + 1 measure | `funnel` | -- |
| Additive contributions + 1 measure | `waterfall` | -- |
| 2 measures (different scale) | `combo-chart` | `scatter-plot` |
| 2 measures (correlation) | `scatter-plot` | -- |
| Multiple dims + multiple measures | `data-table` | `pivot-table`, `data-table-formatted` |
| Geographic + 1 measure | `geographic-map` | -- |
| 2 categories + 1 intensity measure | `heatmap` | `pivot-table` |
| Static text | `text-annotation` | -- |
