---
id: "OPP-###"
title: "<Tên opportunity ngắn gọn>"
stage: 4
status: idea
type: opportunity
source: "<link tới finding/lens nguồn>"
from:
  - "<LENS/FIND/INV/Q/source-id hoặc path>"
moves_to:
  - "<PLAN/stage tiếp theo hoặc pending>"
canonical_anchor: "opp-..."
depends_on:
  - "<optional: blocker / prerequisite>"
created: YYYY-MM-DD
updated: YYYY-MM-DD
owner: "<optional>"
---

<a id="opp-..."></a>

# OPP-### — <Tên opportunity>

> **Template intent:** Opportunity là không gian brainstorm có kỷ luật. Giữ identity + lineage + lý do tồn tại; không ép ý tưởng phải vừa một form cứng. Thêm section nếu cần để làm rõ cơ chế, customer segment, GTM path, data requirement, hoặc experiment design.

**Registry:** `OPP-### -> ../REGISTRY.md#opp-...` *(chỉ bật link thật khi registry row đã tồn tại)*  
**Status:** `idea / evaluating / promoted / dropped` — <1 câu mô tả trạng thái>.  
**From:** <finding/lens/investigation tạo ra opportunity>.  
**Moves to:** <stage 05 plan nào, hoặc `pending` nếu chưa chấm>.

---

## Required Contract

| Field | Nội dung |
|---|---|
| User / segment | <ai là đối tượng chính> |
| Job / pain / leverage | <cơ hội này giải việc gì, đau ở đâu, đòn bẩy nào> |
| Source evidence | <lens/finding/data/VOC/research nào hỗ trợ> |
| Proposed move | <làm gì ở mức 1-3 câu> |
| Success signal | <KPI/observable result để biết có đáng promote không> |
| Main risk / blocker | <điều gì có thể làm opportunity sai hoặc chưa chạy được> |

---

## Ý Tưởng

<Mô tả ngắn gọn cơ hội. Làm gì? Cho ai? Kỳ vọng kết quả gì? Có thể viết dạng narrative, wedge, experiment, hoặc play.>

---

## Vì Sao Cơ Hội Này Tồn Tại

<First principle, finding, contradiction, gap, hoặc market signal. Nói rõ cái gì đang bị bỏ qua / sai / thiếu hiện tại.>

---

## Cách Có Thể Triển Khai

Đây là phác thảo mở, không phải committed plan. Không cần đúng 3 bước; dùng format phù hợp.

- <Hướng triển khai / experiment / wedge #1>
- <Hướng triển khai / experiment / wedge #2>

---

## Nguồn & Lineage

| Loại | Link / ID | Ghi chú |
|---|---|---|
| Perspective/Lens | <link hoặc ID> | <vì sao liên quan> |
| Finding/Investigation | <link hoặc ID> | <bằng chứng chính> |
| Decision/Blocker | <link hoặc ID> | <nếu có> |

---

## Chấm Điểm Sơ Bộ

> Điền khi đưa qua [../03-evaluate/RUBRIC-001-evaluation-framework.md](../03-evaluate/RUBRIC-001-evaluation-framework.md). Nếu còn brainstorm thô, có thể để `not scored yet` và ghi điều kiện để chấm.

| Tiêu chí | Điểm (1-5) | Ghi chú |
|---|---|---|
| **Impact** | — | |
| **Effort** *(điểm cao = dễ)* | — | |
| **Confidence** | — | |
| **Time-to-cash** | — | |

**Tổng / Quyết định:** `idea / evaluating / promoted / dropped`

**Điều kiện để promote:**

- <blocker phải gỡ / evidence phải có / owner phải chốt>

---

## Optional Expansion

Dùng các section dưới nếu giúp brainstorm tốt hơn. Xóa nếu không cần.

### Variants

<Các biến thể của cùng cơ hội: quick win, high-touch, automation, offline, partnership, etc.>

### Experiment Design

<Test nhỏ nhất để học nhanh: sample, holdout, KPI, duration.>

### Message / Offer Angle

<Thông điệp, offer, creative hypothesis, objections.>

### Data / Tooling Needed

<Data columns, dashboard, export, Zalo OA, Metabase card, script, owner.>

### Anti-Patterns

<Những cách triển khai dễ sai hoặc trái với finding hiện tại.>

---

## Notes

<Ghi chú tự do. Nếu ghi chú lớn dần thành investigation, decision, hoặc plan, tách sang stage phù hợp và cập nhật lineage.>
