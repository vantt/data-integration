# Visual Language — Color & Size Semantic Tokens

> **Analyst brain**: file này định nghĩa hệ thống semantic token cho COLOR và SIZE.
> Không chứa hex code, pixel value, hay tool name — chỉ có semantic tokens.
> Engineer đọc tokens này và dịch sang giá trị cụ thể của tool (Metabase, Superset, Looker...).

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

## Style Notes

- Document này dùng CHỈ semantic tokens — không hex codes, không pixel values, không tool names
- Bilingual Vietnamese + English descriptions throughout
- Nếu chuyển từ Metabase sang Superset/Looker, file này KHÔNG THAY ĐỔI
- Chỉ thay đổi viz catalog của tool (nơi map token → giá trị cụ thể)
- Tokens này là ngôn ngữ chung giữa Analyst (người thiết kế) và Engineer (người implement)
