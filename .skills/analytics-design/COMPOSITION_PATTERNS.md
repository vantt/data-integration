# Composition Patterns

> **Scope**: Phase 3-4 — từ Design Brief đến Card Layout.
> Document này là **tool-agnostic** — không chứa Metabase, Superset, hay bất kỳ BI tool cụ thể nào.

---

## 1. Dashboard Archetypes

Ba archetype chuẩn — mỗi dashboard thuộc **đúng 1** archetype.

| Archetype | Purpose | Layout Pattern | Time Budget | Typical Cards |
|-----------|---------|----------------|-------------|---------------|
| **Executive Pulse** | High-level health check — "on-track hay không?" | Top: Hero KPI + Supporting KPIs. Mid: Trend lines (wide). Bottom: No tables, alerts only. | Glanceable — ≤ 5 min | ≤ 10 cards, single view |
| **Operational Cockpit** | Daily management — "hôm nay cần làm gì?" | Top: Global Filters. Mid: Bar Charts (categorical breakdowns). Bottom: High-density Table (transaction details). | Working session — 10-30 min | 10-20 cards, multi-view |
| **Exploratory Tool** | Deep-dive analysis — "tại sao số liệu thế này?" | Sidebar: Many filters. Main: Pivot Table or Scatter Plot. Goal: cho phép slice/dice tự do. | Ad-hoc — variable | > 15 cards, multi-view |

### Chọn archetype

- **Executive Pulse**: Audience là leadership, đọc nhanh, cần answer Yes/No hoặc On-track/Off-track.
- **Operational Cockpit**: Audience là manager/team lead, cần actionable breakdown hàng ngày.
- **Exploratory Tool**: Audience là analyst, cần tự do khám phá data.

**Default rule**: Nếu user yêu cầu "Sales Dashboard" mà không chỉ rõ archetype → default **Operational Cockpit**.

---

## 2. Card Roles

Mỗi card trên dashboard có đúng 1 role. 6 roles chuẩn:

| Role | Function | Visual Characteristics |
|------|----------|----------------------|
| **Hero** | Con số quan trọng nhất — trả lời Primary Question | Largest size, top position, most visually prominent |
| **Supporting KPI** | Metrics bổ sung context cho Hero | Smaller than Hero, cùng row hoặc row tiếp theo |
| **Trend** | Biến động theo thời gian — hướng đi, momentum | Wide (two-thirds hoặc full-width), mid-section |
| **Breakdown** | Phân tích theo dimension (kênh, sản phẩm, vùng) | Medium size, middle of dashboard |
| **Detail** | Dữ liệu chi tiết cho drill-down | Table format, bottom position, full-width |
| **Annotation** | Text card — heading, ghi chú, cảnh báo | No data, text only, full-width, minimal height |

### Rules

1. Mỗi dashboard **PHẢI** có đúng **1 Hero** — không hơn, không thiếu.
2. Hero trả lời **Primary Question** từ Design Brief.
3. Supporting KPIs cung cấp context cho Hero — thường 2-4 cards.
4. Annotations phải có nội dung **CỤ THỂ** ("Revenue Performance This Week"), không generic ("KPIs").
5. Detail cards luôn ở **bottom** — người đọc scroll xuống khi muốn đào sâu.

---

## 3. Narrative Flow

Dashboard kể một câu chuyện — từ tổng quan đến chi tiết. Pattern storytelling:

```
[Annotation: Section heading — cụ thể, mô tả nội dung]
  → Hero + Supporting KPIs     "Chúng ta đang ở đâu?"

[Annotation: Section heading]
  → Trends                     "Chúng ta đang đi theo hướng nào?"

[Annotation: Section heading]
  → Breakdowns                 "Điều gì đang drive kết quả này?"

  → Details                    "Chi tiết cho ai muốn đào sâu"
```

### Nguyên tắc

- Mỗi section heading là **Annotation card** với nội dung cụ thể cho dashboard đó.
  - Tốt: "Weekly Revenue vs Target Pace"
  - Xấu: "Overview" hoặc "KPIs"
- Flow đi từ **trên xuống dưới**, từ **summary đến detail**.
- Người đọc có thể dừng ở bất kỳ section nào mà vẫn nhận được giá trị.
- Executive Pulse: chỉ cần section 1-2. Operational Cockpit: đầy đủ 4 sections.

---

## 4. View Grouping (Phase 4d)

Khi nào dùng single view vs multi-view:

| Pattern | When | Example |
|---------|------|---------|
| **Single view** | ≤ 10 cards (bao gồm text annotations), glanceable audience | Executive Pulse: 10 cards (7 data + 3 annotations) |
| **Multi-view** | > 10 cards, hoặc nhiều audiences/purposes khác nhau | Daily Ops: Overview → Trends → Analysis → Details |

### Multi-view structure

Mỗi view-group bao gồm:

| Field | Description |
|-------|-------------|
| **Name** | Tên view — tool-agnostic (engineer sẽ translate thành tab/page) |
| **Narrative flow** | View có narrative flow riêng (Hero → Trend → Breakdown) |
| **Assigned cards** | Danh sách cards thuộc view này |

### Ví dụ multi-view

```
View 1 — "Overview"
  → Hero: Net Revenue (Number)
  → Supporting: Order Count, AOV, Return Rate (Number)
  → Trend: Revenue WoW (Line)

View 2 — "Channel Analysis"
  → Breakdown: Revenue by Channel (Bar)
  → Breakdown: Order Count by Channel (Bar)
  → Detail: Channel Performance Table (Table)

View 3 — "Product Deep Dive"
  → Breakdown: Top Products by Revenue (Bar)
  → Detail: Product-level Table (Table)
```

**Quan trọng**: `view-group` là **composition concept** — nó KHÔNG xuất hiện trong Phase 5 decision tree. Phase 5 chỉ quyết định viz type cho từng card riêng lẻ.

---

## 5. Spatial Grouping (Phase 4c)

Quy tắc positioning tương đối — dùng 18-column grid.

### Nguyên tắc chung

- Cards cùng logic group → **adjacent** (cạnh nhau).
- Row concept: cards cùng Row letter (A, B, C...) = cùng horizontal line.
- Tổng width mỗi row **PHẢI = full-width** (18 columns).
- Hero phải **visually dominant** — kích thước lớn hơn Supporting KPIs.

### Valid row combinations (18-col grid)

| Combination | Column math | Use case |
|-------------|-------------|----------|
| `full-width` | 18 | Trend line, Detail table, Annotation |
| `half + half` | 9 + 9 | Hai charts so sánh song song |
| `one-third + two-thirds` | 6 + 12 | Hero + Supporting group |
| `one-third + 3 × one-quarter` | 6 + 4 + 4 + 4 | Hero + 3 Supporting KPIs |
| `6 × one-sixth` | 3 × 6 | Nhiều small KPIs trên 1 row |

> **Density Budget**: Xem `VISUAL_LANGUAGE.md` Section 8 cho giới hạn số card/row/tab theo archetype. Executive Pulse max 10 cards/view, Cockpit max 16, Exploratory max 20.

### Invalid combinations

| Combination | Column math | Why invalid |
|-------------|-------------|-------------|
| `4 × one-quarter` | 4 × 4 = 16 | 16 ≠ 18, thiếu 2 columns |
| `one-third + one-half` | 6 + 9 = 15 | 15 ≠ 18, thiếu 3 columns |

### Ví dụ layout

```
Row A: [Annotation: "Weekly Revenue Performance"]     → full-width (18)
Row B: [Hero: Net Revenue] + [AOV] + [Orders] + [Growth]  → one-third + 3×one-quarter (6+4+4+4)
Row C: [Annotation: "Revenue Trend"]                  → full-width (18)
Row D: [Revenue WoW Trend]                            → full-width (18)
Row E: [Annotation: "Channel Breakdown"]              → full-width (18)
Row F: [By Channel] + [By Product]                    → half + half (9+9)
Row G: [Detail Table]                                 → full-width (18)
```

---

## 6. Constraints & Filter Design (Phase 4e)

Hai loại data scoping — cả hai đều là **analyst decisions**:

### Business Constraints

Luôn luôn applied, hardcoded bởi engineer trong SQL WHERE. User không thay đổi được.

| Field | Description | Example |
|-------|-------------|---------|
| **Constraint name** | Tên ngắn gọn | "Exclude US channel" |
| **Rule** | Filter logic | `channel_category != 'US'` |
| **Applies to** | Cards nào bị ảnh hưởng | "All cards" |
| **Rationale** | Tại sao cần constraint này | "Internal orders, 100% discount — skew revenue metrics" |

### Interactive Filters

User-changeable trên dashboard. Engineer translates thành parameters.

| Field | Description | Example |
|-------|-------------|---------|
| **Filter name** | Tên hiển thị cho user | "Date Range" |
| **Filter type** | Loại filter | date/range, category/single-select, text, number |
| **Default value** | Giá trị mặc định khi mở dashboard | "Last 7 days" |
| **Applies to** | Cards nào bị ảnh hưởng | "All cards" |
| **Business rationale** | Tại sao user cần filter này | "View different time periods for comparison" |

### Phân chia trách nhiệm

| Decision | Who | Example |
|----------|-----|---------|
| **WHAT** to scope (loại bỏ data nào, filter gì) | Analyst (Design Spec) | "Exclude internal orders" |
| **HOW** to implement (SQL WHERE vs parameter) | Engineer (Blueprint) | `WHERE channel_category != 'US'` |

Analyst quyết định WHAT. Engineer quyết định HOW.

---

## 7. Companion Card Identification (Phase 4f)

Sau khi layout xong, kiểm tra xem dashboard còn thiếu card nào không:

### Checklist

- [ ] **Text cards cho section headings** — mỗi group cần 1 Annotation card với nội dung CỤ THỂ.
- [ ] **Comparison cards** — nếu Hero cần "vs target" nhưng chưa có card nào cung cấp comparison → thêm.
- [ ] **Summary/conclusion text** — cuối dashboard, nếu cần recap hoặc cảnh báo.
- [ ] **Missing Supporting KPIs** — Hero có đủ context chưa? Cần thêm metric bổ trợ nào không?

### Quy tắc Annotation content

| Pattern | Annotation | Verdict |
|---------|-----------|---------|
| Cụ thể, descriptive | "Revenue Performance vs Weekly Target" | Tốt |
| Generic, vô nghĩa | "Overview" | Xấu — đổi thành cụ thể |
| Quá dài | "This section shows revenue performance compared to..." | Xấu — rút gọn |

---

## 8. Insight Communication Templates

Khi viết nội dung cho Annotation cards, Playbook findings, hoặc Dashboard descriptions — dùng các template dưới đây thay vì free-form text.

### 8a. "What / So What / Now What" — cho từng Insight

Compact format — dùng cho mỗi finding trong Playbook, hoặc cho Annotation cards cần giải thích insight.

```markdown
**What:** [Phát hiện — 1 câu mô tả sự thật từ data]
**So What:** [Tại sao quan trọng — impact lên business]
**Now What:** [Hành động đề xuất — next step cụ thể]
```

#### Ví dụ

```markdown
**What:** Tỷ lệ hủy đơn tăng từ 5% lên 12% trong 2 tuần qua, tập trung ở kênh Online.
**So What:** Mất ~80M VND/tuần doanh thu, ảnh hưởng trực tiếp đến target Q2.
**Now What:** Kiểm tra UX checkout flow kênh Online + review inventory sync.
```

### 8b. Presentation Flow — cho Playbook "How to Read" section

Khi viết phần "How to Read" trong Playbook, follow structure này:

```
1. CONTEXT    — Tại sao dashboard này tồn tại? Đang trả lời câu hỏi gì?
2. KEY FINDING — Nhìn đâu trước? Hero metric cho biết điều gì?
3. EVIDENCE    — Trend/Breakdown nào support finding đó?
4. IMPLICATIONS — Nếu số liệu thế này thì business bị ảnh hưởng thế nào?
5. ACTIONS     — Viewer nên làm gì tiếp theo?
```

### 8c. Dashboard Subtitle Template

Mỗi dashboard nên có subtitle (Annotation card đầu tiên) theo format:

```
[Audience] — [Primary Question] — [Default Time Range]
```

Ví dụ:
- "CEO Weekly Brief — Tuần qua kinh doanh có on-track không? — Last 7 days"
- "Sales Ops Daily — Hôm nay cần xử lý đơn hàng nào? — Today"

### 8d. Annotation Card Content Patterns

| Vị trí | Content Pattern | Ví dụ |
|--------|----------------|-------|
| Dashboard header | Subtitle (8c format) | "CEO Weekly — Revenue vs Target pace — Last 7 days" |
| Section divider | Section purpose + what to look for | "Revenue Trend — xem hướng đi và momentum WoW" |
| Callout (next to chart) | "What / So What" mini (bỏ "Now What") | "Online channel đang drive 68% tổng revenue, tăng từ 55% tháng trước" |
| Footer | Data source + freshness + caveats | "Source: fact_orders · Updated hourly · Excludes internal orders" |

### Quy tắc chung

- **Lead with insight, not description** — "Revenue tăng 15%" > "Biểu đồ này thể hiện revenue"
- **Dùng số cụ thể** — "tăng 15% WoW" > "tăng đáng kể"
- **Action-oriented khi có thể** — "Cần review kênh Online" > "Kênh Online có vấn đề"
- **Ngắn gọn** — mỗi annotation tối đa 2 dòng. Nếu cần dài hơn → tách thành Playbook/Guide

---

## 9. Design Brief Template (Phase 3)

Design Brief là output đầu tiên của Phase 3 — xác định mục đích trước khi thiết kế.

| Field | Description | Example |
|-------|-------------|---------|
| **Audience** | Ai đọc, vai trò gì, context đọc | CEO — đọc 5 phút sáng thứ Hai |
| **Primary Question** | Câu hỏi chính dashboard trả lời | "Tuần qua kinh doanh có on-track không?" |
| **Decision Enabled** | Decision nào được unlock | "Can thiệp khẩn cấp hay tiếp tục như hiện tại" |
| **Hero Metric** | Con số quan trọng nhất (từ domain) | Net Revenue vs Target pace |
| **Comparison Frame** | So sánh với cái gì | WoW (tuần này vs tuần trước) |
| **Time Budget** | Thời gian đọc dashboard | Glanceable — under 5 min |
| **Archetype** | Pulse / Cockpit / Tool | Executive Pulse |

### Từ Design Brief đến Composition

```
Design Brief
  → Archetype      (determines layout pattern + card count)
  → Primary Question (determines Hero card)
  → Audience        (determines time budget + detail level)
  → Comparison Frame (determines trend/comparison cards)
```

Mọi quyết định composition ở Phase 4 đều **trace back** được đến Design Brief.
