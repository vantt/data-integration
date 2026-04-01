# Comparative Framing

> Quy tắc ngữ cảnh hóa số liệu — Every KPI needs context. A number alone means nothing.

## The Mandatory Rule

**Mỗi KPI phải có ít nhất 1 phép so sánh (comparison).**

"Net Revenue: 500M" alone tells nothing — is it good? Bad? Trending up or down? Một con số đơn lẻ không có ý nghĩa nếu thiếu ngữ cảnh. Rule này áp dụng cho mọi KPI trong mọi blueprint.

## Four Comparison Types

| Type | Khi nào dùng | Cho biết điều gì | Ví dụ |
|---|---|---|---|
| **vs Previous Period** | Every periodic KPI | "tăng/giảm bao nhiêu %" | This week vs last week, this month vs last month |
| **vs Target/Goal** | When clear target exists | "đạt bao nhiêu % mục tiêu" | Revenue vs monthly target, completion rate vs SLA |
| **vs Benchmark** | When internal/external benchmark available | "so với trung bình" | Revenue vs industry avg, this store vs chain avg |
| **Rank/Position** | When comparing categories | "đứng thứ mấy" | Channel A is #1 by revenue, Product X ranks 3rd |

**vs Previous Period** là comparison mặc định — luôn có sẵn nếu metric có time dimension và dữ liệu lịch sử.

## Decision Table — Chọn Comparison Type

| Đặc điểm của metric | Comparison được khuyến nghị | Fallback nếu không có |
|---|---|---|
| Has time dimension + historical data | vs Previous Period | — (always available if data exists) |
| Has explicit business target | vs Target/Goal + vs Previous Period | vs Previous Period only |
| Part of a set of similar entities | Rank/Position + vs Previous Period | vs Previous Period only |
| Industry/internal benchmark exists | vs Benchmark | vs Previous Period |
| Brand new metric, no history yet | None available — accept single-value, add note "comparison available after 1+ period" | — |

## Data Completeness Requirements by Viz Type

Mỗi viz type cần dữ liệu cụ thể để render comparison đúng cách:

| Viz Type (standard) | Required data | Notes |
|---|---|---|
| `gauge` | min, max, goal value, zone boundaries | Without zones, gauge is meaningless |
| `progress-toward-goal` | goal value | Without goal, use `single-value` instead |
| `single-value-with-trend` | previous period value | Engineer calculates in SQL using CTE pattern |
| `funnel` | ordered stages with values | Each stage must have a clear sequence |
| `combo-chart` | 2+ metrics on shared axis | Must share a common dimension (usually time) |
| `stacked-bar` / `stacked-area` | dimension column for series breakdown | Need a categorical dimension to split |

**Nếu data chưa đủ cho viz type đã chọn** — chuyển sang viz type đơn giản hơn thay vì render nửa vời. Ví dụ: `gauge` thiếu zones thì dùng `single-value-with-trend`.

## Enrichment Checklist (Phase 6)

Với mỗi card trong design spec, kiểm tra:

- [ ] KPI has at least 1 comparison type assigned
- [ ] Comparison data is available (or noted as "planned")
- [ ] Viz type can render the comparison (e.g., gauge needs zones, progress needs goal)
- [ ] Narrative support: text cards or labels explain what comparison means
- [ ] Colorblind-safe: comparison uses both color AND text/icon (▲/▼)

## Common Patterns

### Period-over-Period trong SQL

Dùng CTE pattern để tính previous period value. Query trả về cả current và previous value để viz type `single-value-with-trend` có thể render trend arrow.

### Target Lines

Khi có target, thêm goal line vào chart hoặc dùng `progress-toward-goal` viz type. Target values nên được quản lý ngoài query (config hoặc parameter) để dễ cập nhật.

### Rank Labels

Khi dùng Rank/Position comparison, luôn hiển thị cả rank number và value. "Channel A: #1 — 500M" rõ nghĩa hơn "#1" alone.

## Anti-patterns

| Anti-pattern | Vấn đề | Cách sửa |
|---|---|---|
| Single number without any comparison | Reader cannot assess performance | Add vs Previous Period at minimum |
| Gauge without defined zones | Zones are arbitrary, misleading | Define zones from business rules or remove gauge |
| Comparing incompatible periods | "This week (3 days in) vs last week (7 days)" | Normalize to same duration or add caveat |
| Too many comparisons on one card | Visual clutter, reader overwhelmed | Max 2 comparisons per card |
| Color-only comparison (red/green) | Inaccessible to colorblind users | Always pair color with text/icon (▲/▼/→) |
