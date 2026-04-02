# Visual Language — Color & Size Semantic Tokens

> **Analyst brain**: file này định nghĩa hệ thống semantic token cho COLOR và SIZE.
> Không chứa hex code, pixel value, hay tool name — chỉ có semantic tokens.
> Engineer đọc tokens này và dịch sang giá trị cụ thể của tool (Metabase, Superset, Looker...).

---

## 0. Foundational Design Principles

Bảy nguyên tắc nền tảng — mọi quyết định visual trong skill này đều trace back về đây.
Dẫn chiếu từ Edward Tufte ("The Visual Display of Quantitative Information") và Cole Nussbaumer Knaflic ("Storytelling with Data").

### Principle 1: Data-Ink Ratio (Tufte)

Maximize tỷ lệ "ink dùng để truyền tải data" / "tổng ink trên trang". Loại bỏ mọi thứ không mang thông tin:
- Bỏ gridlines trừ khi cần thiết cho đọc giá trị chính xác
- Bỏ borders/boxes quanh charts trừ khi phân tách logic groups
- Bỏ legend nếu chart chỉ có 1 series (dùng title thay thế)
- Bỏ axis labels nếu đã rõ ràng từ context (ví dụ: trục X là tháng, ai cũng hiểu)

### Principle 2: Chartjunk Elimination (Tufte)

KHÔNG BAO GIỜ dùng:
- 3D charts — bóp méo perception, không thêm thông tin
- Decorative images/icons trong data area
- Shadow, gradient, bevel trên data elements (bars, lines, slices)
- Animated transitions chỉ vì đẹp mà không giúp hiểu data

### Principle 3: Pre-attentive Attributes (Knaflic)

Não xử lý một số visual attributes TRƯỚC khi ý thức nhận ra — dùng chúng có chủ đích:
- **Color intensity**: đậm = quan trọng, nhạt = background
- **Size**: lớn = focal, nhỏ = supporting
- **Position**: top-left = đọc đầu tiên (F-pattern reading)
- **Enclosure**: border/background nhẹ để nhóm related elements

Chỉ dùng 1-2 pre-attentive attributes cho mỗi card. Dùng nhiều hơn = hủy tác dụng.

### Principle 4: Cognitive Load Minimization

Mỗi dashboard có "quỹ chú ý" hữu hạn:
- Tối đa 5-7 data elements cần reader xử lý cùng lúc trên một card
- Tối đa 3-4 cards visible cùng lúc mà không cần scroll
- Mọi text label phải đọc được trong < 2 giây
- Nếu cần giải thích dài → tách thành annotation card riêng

### Principle 5: Whitespace is Data (Tufte)

Khoảng trống KHÔNG phải lãng phí — nó giúp reader:
- Phân biệt groups (spacing > borders cho separation)
- Nghỉ mắt giữa các data-dense sections
- Tạo visual hierarchy (Hero card nổi bật nhờ space xung quanh)

Không lấp đầy mọi pixel — dashboard quá đầy = reader bỏ cuộc.

### Principle 6: Context Over Decoration (Knaflic)

Thay vì trang trí chart cho đẹp, hãy thêm CONTEXT:
- Reference line (target, average, benchmark) > gradient fill
- Annotation callout giải thích anomaly > icon decorative
- Comparison period (previous month) > background pattern

Mỗi visual element phải trả lời: "element này giúp reader hiểu data TỐT HƠN không?"

### Principle 7: Consistency Across Dashboard

Cùng một thứ phải trông GIỐNG nhau trên toàn dashboard:
- Cùng metric → cùng color token (xem Rule 4 trong Color Usage Rules)
- Cùng time axis → cùng date format, cùng grain
- Cùng unit → cùng number format (abbreviation, decimal places)
- Cùng viz type cho cùng loại question (tất cả breakdown đều dùng bar, không mix bar + donut + table)

---

## 1. Color Semantics

Mọi color trong design spec phải dùng một trong các semantic token dưới đây.
Không bao giờ viết hex code (#FF0000) hay color name (red) trong spec.

### 1.1 Status Colors — trạng thái tốt/xấu (truyền đạt đánh giá)

| Token | Meaning | When to use |
|-------|---------|-------------|
| `positive` | Good — met target, growth, healthy | KPI above target, upward trend when up = good |
| `negative` | Bad — below threshold, decline, unhealthy | KPI below target, downward trend when down = bad |
| `warning` | Needs attention — near threshold, unusual | KPI near threshold, unusual variation, approaching limit |
| `neutral` | No judgment — purely descriptive | Metric with no clear good/bad evaluation, informational only |

### 1.2 Structural Colors — non-data elements (không mang dữ liệu)

| Token | Meaning | When to use |
|-------|---------|-------------|
| `structural` | Background, dividers, headings, non-data text | Text annotations, section dividers, card borders, axis labels |

### 1.3 Hierarchy Colors — visual importance (mức độ nổi bật)

| Token | Meaning | When to use |
|-------|---------|-------------|
| `primary` | Most prominent — eye catches this first | Hero metric value, main series in chart, focal data point |
| `secondary` | Important but not focal — supporting role | Supporting metrics, secondary series, related context |
| `muted` | Background — not attention-drawing | Baseline, reference lines, previous period, benchmark |
| `accent` | Special highlight — draw attention to specific item | Highlight specific data point, anomaly, annotation callout |

### 1.4 Series Colors — phân biệt categories (categorical distinction)

| Token | Meaning | When to use |
|-------|---------|-------------|
| `series-1` .. `series-N` | Visual distinction between N categories | Multi-series line, stacked bar, donut slices, grouped bars |
| `series-emphasis` | Emphasize 1 series against dimmed rest | Highlight specific category in a group, focus-and-context |

### 1.5 Conditional Colors — dynamic based on data values (thay đổi theo giá trị)

| Token | Meaning | When to use |
|-------|---------|-------------|
| `conditional-above` | Value exceeds upper threshold | Table cell formatting, bar highlight above target |
| `conditional-below` | Value falls below lower threshold | Table cell formatting, bar highlight below target |
| `conditional-range` | Gradient across value range | Heatmap cells, intensity encoding, progress fill |

---

## 2. Color Usage Rules

Bảy quy tắc bắt buộc khi dùng color tokens trong design spec.

### Rule 1: Status colors only when evaluation criteria are clear
Chỉ dùng `positive`/`negative`/`warning` khi có tiêu chí đánh giá rõ ràng (target, threshold, direction).
Nếu không xác định được "good" hay "bad" — dùng `neutral`.

### Rule 2: Max 2 status colors per card
Tránh hiệu ứng "Christmas tree" — quá nhiều màu status trên một card gây rối mắt.
Một card chỉ nên dùng tối đa 2 trong 4 status tokens (`positive`, `negative`, `warning`, `neutral`).

### Rule 3: Series colors max 5-7
Con người khó phân biệt nhiều hơn 7 màu. Nếu có >7 categories, gom nhóm thành "Others"
hoặc dùng `series-emphasis` để highlight 1-2 categories quan trọng, dimmed phần còn lại.

### Rule 4: Hierarchy colors consistent across entire dashboard
`primary` luôn mang cùng ý nghĩa trên toàn dashboard — không đổi giữa các cards.
Nếu card A dùng `primary` cho Revenue, tất cả cards khác cũng phải dùng `primary` cho Revenue.

### Rule 5: Color is NEVER the sole communication channel
Luôn kết hợp color với text, icon, hoặc position để truyền đạt thông tin (accessibility).
Ví dụ: không chỉ dùng đỏ/xanh — phải kèm ▲/▼ hoặc label "+12%" / "-5%".

### Rule 6: Colorblind safety
Trong cùng một card/chart, không dùng 2+ colors chỉ khác nhau trên phổ red-green.
Khi `positive` + `negative` xuất hiện cùng card — BẮT BUỘC phải có text label hoặc icon ▲/▼.

### Rule 7: `structural` replaces `neutral` for non-data elements
Text annotations, headings, dividers dùng `structural` — không dùng `neutral`.
`neutral` chỉ dành cho metrics không có đánh giá tốt/xấu, vẫn là data element.

---

## 3. Size Semantics

Mọi size trong design spec phải dùng semantic token — không dùng pixel, point, hay grid unit cụ thể.

### 3.1 Text/Number Size — prominence level (mức nổi bật của text)

| Token | Meaning | Suitable Card Role |
|-------|---------|-------------------|
| `prominent` | Largest — catches eye immediately | Hero metric value, primary KPI number |
| `standard` | Normal reading size — comfortable scan | Supporting KPI values, chart axis labels |
| `compact` | Small — space-saving, dense display | Detail table values, secondary info, tooltips |
| `caption` | Very small — supplementary context | Subtitle, footnote, last-updated timestamp, source note |

### 3.2 Card Width — relative horizontal space (chiều ngang tương đối)

Tool-agnostic — không gắn với grid system cụ thể nào.

| Token | Meaning |
|-------|---------|
| `full-width` | Entire horizontal space available |
| `two-thirds` | ~2/3 of horizontal space |
| `half` | ~1/2 of horizontal space |
| `one-third` | ~1/3 of horizontal space |
| `one-quarter` | ~1/4 of horizontal space (grid-constrained: actually ~22% on 18-col grid) |
| `one-sixth` | ~1/6 of horizontal space |

### 3.3 Card Height — vertical space (chiều dọc)

| Token | Meaning | Suitable for |
|-------|---------|-------------|
| `tall` | High — viz needing vertical space | Funnel, vertical bar with many categories, long table |
| `medium` | Moderate height — standard viz | Line chart, area chart, bar chart, pie/donut |
| `short` | Low — compact display | KPI scalars, progress bars, sparklines |
| `minimal` | Very low — barely visible as card | Text annotations, section headings, dividers |

---

## 4. Size Usage Rules

Năm quy tắc bắt buộc khi dùng size tokens trong design spec.

### Rule 1: Hero card must be visually dominant
Hero card phải dùng `one-third` hoặc rộng hơn, kết hợp `prominent` text size.
Hero là điểm focal đầu tiên — phải nổi bật nhất trên dashboard.

### Rule 2: Supporting cards must be smaller than Hero
Nếu Hero = `one-third` thì Supporting = `one-quarter` hoặc `one-sixth`.
Supporting không bao giờ bằng hoặc lớn hơn Hero về width.

### Rule 3: Trend/Breakdown cards should be wide
Cards chứa data series (line, bar, area, table) cần `two-thirds` hoặc `full-width`
để các data points có đủ không gian render rõ ràng.

### Rule 4: Annotations always `full-width` + `minimal` height
Section headings và dividers luôn chiếm toàn bộ chiều ngang nhưng chiều cao tối thiểu.
Chúng phục vụ navigation — không tiêu tốn không gian hiển thị dữ liệu.

### Rule 5: Total cards in a row must equal `full-width`
Không để gap hoặc overflow. Mọi card trong cùng row phải cộng lại = `full-width`.

Valid combinations (ví dụ trên 18-col grid):
- `one-third` + 3 × `one-quarter` = 6 + 4 + 4 + 4 = 18
- `half` + `half` = 9 + 9 = 18
- `one-third` + `two-thirds` = 6 + 12 = 18
- 6 × `one-sixth` = 3 × 6 = 18
- 3 × `one-third` = 6 × 3 = 18

Invalid: `4 × one-quarter` = 4 × 4 = 16 (not 18 — leaves gap).

---

## 5. Using Visual Language in Design Spec

Color và Size tokens được viết trực tiếp trong Composition table của Design Spec.

### Composition table format:

```
| # | Row | Card | Role | Viz Type | Color | Size | Communication | Comparison |
|---|-----|------|------|----------|-------|------|---------------|------------|
| 1 | A | "Section Heading" | annotation | text-annotation | structural | full-width × minimal | ... | — |
| 2 | B | Revenue vs Target | hero | gauge | positive/warning/negative (zones) | one-third × medium, prominent | ... | vs target |
| 3 | B | Orders Today | supporting | scalar | positive or negative (vs yesterday) | one-quarter × short, prominent | ... | vs previous |
| 4 | C | Revenue Trend | trend | line-chart | primary + muted (prev period) | two-thirds × medium, standard | ... | vs previous period |
| 5 | C | Revenue by Channel | breakdown | donut | series-1..series-4 | one-third × medium, standard | ... | composition |
```

### Reading the tokens:

- **Color column**: lists which color tokens apply and when (e.g., "positive/negative" means conditional)
- **Size column**: `width × height, text-size` format (e.g., "one-third × medium, prominent")
- **Multiple color tokens** separated by `/` mean conditional — value determines which applies
- **Multiple color tokens** separated by `+` mean simultaneous — both appear in same viz

### Engineer translation:

Engineer reads these semantic tokens and translates to concrete tool values using the tool's
viz catalog. For example:
- `positive` → tool-specific green hex code
- `one-third` → tool-specific grid columns (e.g., 6 on 18-col grid)
- `prominent` → tool-specific font size (e.g., 2rem or 32px)

---

## 6. Visual Polish Checklist

Checklist cuối cùng trước khi finalize Design Spec. Scan nhanh — nếu vi phạm bất kỳ mục nào, sửa trước khi chuyển cho Engineer.

### 6a. Chart Hygiene

- [ ] **No 3D charts** — tuyệt đối không, dù client/user yêu cầu (Principle 2)
- [ ] **No dual-pie/donut** — không đặt 2 pie charts cạnh nhau để so sánh (dùng stacked-bar hoặc grouped-bar)
- [ ] **Y-axis starts at 0 cho bar charts** — truncated axis bóp méo perception
- [ ] **Line chart Y-axis**: có thể không bắt đầu từ 0 nếu range hẹp, nhưng phải ghi rõ
- [ ] **Max 5-7 colors trên 1 chart** — nếu >7 categories, gom "Others" (Rule 3)
- [ ] **No gridlines nếu không cần** — giữ lại chỉ khi reader cần đọc giá trị chính xác
- [ ] **Legend chỉ khi >1 series** — single series dùng chart title, không cần legend

### 6b. Typography & Labels

- [ ] **Mọi chart có title** — title mô tả insight, không chỉ metric name ("Revenue đang tăng 15% WoW" > "Revenue")
- [ ] **Axis labels có unit** — "Revenue (M VND)" không chỉ "Revenue"
- [ ] **Number formatting nhất quán** — cùng abbreviation style xuyên suốt (1.2M vs 1,200,000 — chọn 1)
- [ ] **Date format nhất quán** — DD/MM, MMM DD, hoặc YYYY-MM — chọn 1 cho toàn dashboard
- [ ] **Text size hierarchy rõ** — prominent > standard > compact > caption, không skip levels

### 6c. Layout & Whitespace

- [ ] **Row width = full-width** — không gap, không overflow (Rule 5 trong Size)
- [ ] **Hero visually dominant** — lớn nhất, top position (Rule 1 trong Size)
- [ ] **Related cards adjacent** — cards cùng topic nằm cạnh nhau
- [ ] **Không lấp đầy mọi pixel** — breathing room giữa sections (Principle 5)
- [ ] **Scroll depth hợp lý** — Executive Pulse: no scroll. Cockpit: max 2-3 scrolls

### 6d. Color & Accessibility

- [ ] **Color KHÔNG phải kênh duy nhất** — luôn kèm text/icon ▲/▼ (Rule 5)
- [ ] **Colorblind safe** — không dùng red+green mà thiếu text label (Rule 6)
- [ ] **Max 2 status colors per card** — tránh Christmas tree effect (Rule 2)
- [ ] **Consistent color meaning** — `primary` = cùng metric trên mọi card (Rule 4)

### 6e. Data Integrity

- [ ] **Mọi KPI có ≥1 comparison** — vs previous period ở minimum (xem COMPARATIVE_FRAMING.md)
- [ ] **Không so sánh periods không tương đương** — "3 ngày tuần này vs 7 ngày tuần trước" = misleading
- [ ] **Source/timestamp visible** — ghi rõ "Data updated: ..." hoặc "Source: ..." ở footer

---

## 7. Title & Copy Discipline

Quy tắc viết text trên dashboard — tạo cảm giác professional, nhất quán.

### Card Titles

- Pattern: `[Metric] [Comparison]` — ví dụ: "Net Revenue vs Last Week"
- KHÔNG dùng "Chart of...", "Graph showing...", "A look at..."
- KHÔNG dùng viết tắt trừ khi là term chuẩn (KPI, WoW, MoM, YoY, ARPU, AOV, CLV)
- Max 50 ký tự. Nếu dài hơn → rút gọn hoặc dùng subtitle
- Title mô tả insight khi có thể: "Revenue tăng 15% WoW" > "Revenue" (chỉ áp dụng cho annotation, không áp dụng cho dynamic card titles)

### Card Subtitles

- Chỉ dùng khi cần giải thích điều kiện lọc hoặc đơn vị
- Pattern: `[Filter context] · [Unit]` — ví dụ: "Excluding US channel · VND"
- Max 80 ký tự
- Không lặp lại thông tin đã có trong title

### Section Headings (Text Annotations)

- Dùng imperative voice: "Monitor revenue trends" không phải "Revenue Trends Section"
- Dùng sentence case, KHÔNG dùng Title Case (trừ proper nouns)
- Không kết thúc bằng dấu chấm
- Mỗi section heading giải thích WHY section này quan trọng, không chỉ WHAT nó chứa

### Annotation Content

- 1-2 câu ngắn. Mỗi câu < 15 từ.
- Giải thích WHY section này quan trọng, không phải WHAT nó chứa
- Tone: direct, professional, không casual
- KHÔNG dùng emoji trong annotation (trừ khi user yêu cầu rõ ràng)

---

## 8. Spacing & Density Budget

Quy tắc về mật độ thông tin — quá nhiều card = reader bỏ cuộc.

### Row Spacing

- Giữa các row: 0 (tool tự thêm gap)
- Text annotation luôn bắt đầu ở col 0, width full-width
- Sau mỗi annotation heading: cards bắt đầu ở row tiếp theo

### Density Limits by Archetype

| Archetype | Max cards/view | Max rows | Max tabs | Scroll depth |
|-----------|---------------|----------|----------|-------------|
| Executive Pulse | 10 | 5 | 2 | Không scroll (above the fold) |
| Operational Cockpit | 16 | 8 | 4 | Max 2-3 scrolls |
| Exploratory Tool | 20 | 10 | 5 | Tùy ý nhưng có section dividers |

### Whitespace Rules

- Hero row: max 3 cards (hero + 1-2 supporting)
- Không đặt > 4 cards cùng 1 row (trừ data-table full-width)
- Mỗi view PHẢI có ít nhất 1 text annotation làm section divider
- Giữa các nhóm logic (e.g., Revenue group vs Channel group): luôn có annotation separator

---

## 9. Chart Labeling Rules

Quy tắc label cho từng loại chart — giảm cognitive load, tăng readability.

### Axes

- Y-axis: luôn có label + unit — "Revenue (VND)", "Orders (#)"
- X-axis: ẩn label nếu là thời gian (tháng/tuần/ngày hiển thị tự động)
- Luôn bắt đầu y-axis từ 0 cho bar charts (truncated axis bóp méo perception)
- Line charts có thể KHÔNG bắt đầu từ 0 nếu range hẹp, nhưng phải ghi rõ trong spec

### Legends

- Ẩn legend nếu chỉ có 1 series (dùng title thay thế)
- Đặt legend ở bottom nếu > 3 series
- Không để legend che chart area

### Data Labels

- BẬT cho: donut (%), horizontal-bar (value), progress (goal value)
- TẮT cho: line-chart, area-chart (dùng tooltip thay thế)
- Gauge: hiển thị value + unit trong center
- Scalar: hiển thị comparison arrow + % change

### Number Formatting

- Chọn 1 abbreviation style cho toàn dashboard: "1.2M" hoặc "1,200,000" — KHÔNG mix
- Currency: luôn kèm ký hiệu (₫, $) hoặc suffix (VND, USD)
- Percentage: 1 decimal place (12.3%), không dùng 12.34%
- Đếm (orders, customers): không decimal, có thousands separator

---

## 10. Dashboard Finish Checklist

Checklist toàn diện trước khi finalize Design Spec. Mở rộng từ Section 6 (Visual Polish Checklist).

### Content

- [ ] Mỗi card có title theo Title Discipline (Section 7)
- [ ] Mỗi KPI có ít nhất 1 comparison (xem COMPARATIVE_FRAMING.md)
- [ ] Text annotations dùng imperative voice
- [ ] Không có card orphan (không thuộc narrative flow nào)
- [ ] Action Map trong design spec đầy đủ cho cards có signal quan trọng

### Layout

- [ ] Hero card ở row đầu tiên, nổi bật nhất
- [ ] Row widths sum = full-width (18 cols)
- [ ] Density trong giới hạn archetype (Section 8)
- [ ] Mỗi view có ít nhất 1 section divider (text annotation)
- [ ] Scroll depth phù hợp archetype

### Visual

- [ ] Color tokens nhất quán trong toàn dashboard
- [ ] Không dùng > 5 màu distinct trong 1 view
- [ ] Structural color cho elements phụ (dividers, muted labels)
- [ ] Size hierarchy rõ: hero > supporting > detail
- [ ] Number formatting nhất quán (Section 9)

### Action

- [ ] Action Triggers table trong playbook đầy đủ
- [ ] Action Map trong design spec đầy đủ
- [ ] Reading Flow mô tả đường đi từ hero → investigation → escalation

---

## Style Notes

- Document này dùng CHỈ semantic tokens — không hex codes, không pixel values, không tool names
- Bilingual Vietnamese + English descriptions throughout
- Nếu chuyển từ Metabase sang Superset/Looker, file này KHÔNG THAY ĐỔI
- Chỉ thay đổi viz catalog của tool (nơi map token → giá trị cụ thể)
- Tokens này là ngôn ngữ chung giữa Analyst (người thiết kế) và Engineer (người implement)
