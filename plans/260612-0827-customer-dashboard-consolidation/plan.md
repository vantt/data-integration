---
title: "Customer Dashboard Consolidation — 5→4 by Job + Customer sub-collection"
created: 2026-06-12
status: active
approach: parallel-build-then-retire
source: ../reports/customer-dashboard-portfolio-ia-evaluation-260612-0818-report.md
---

# Customer Dashboard Consolidation

> **Vấn đề:** 5 customer board chồng lấn nặng, tên "Customer X" không phân biệt, xé 2 collection → người dùng rối.
> **Giải:** gom còn **4 board theo JOB**, đặt trong sub-collection `Marketing & Customers › 👥 Customer`.
> **Cách làm (an toàn):** build MỚI song song → validate → mới xóa cũ. KHÔNG sửa in-place (tránh regress).

## Target — 4 board mới (theo job-to-be-done)

| Board mới | Cadence | Blueprint mới (file) | Gom nội dung từ |
|---|---|---|---|
| **A. Daily · Customer Action Queue [Retail]** | Daily | `customer_daily_action_queue.md` | #99 + watchlists #48 + "Activation Now" #102 |
| **B. Weekly · Customer Retention & Cohorts [Retail]** | Weekly | `customer_retention_cohorts.md` | #14 (cohort/waterfall) + retention bits #48 |
| **C. Monthly · Customer Intelligence [Cross]** | Monthly | `customer_intelligence.md` | #15 + segment/geo/acquisition #48 |
| **D. Monthly · Customer Profitability [Retail]** | Monthly | `customer_profitability.md` | #102 margin tabs (channel×margin, discount×margin, margin-negative) |

Tên dẫn bằng **cadence + job** → tự giải thích "khi nào / làm gì". Mỗi concept ở ĐÚNG 1 board (no overlap):
- call-list/dispatch → CHỈ A · cohort/retention → CHỈ B · value/segment/behavior → CHỈ C · margin → CHỈ D.

## Phases

| Phase | Việc | Trạng thái |
|---|---|---|
| **P0** | Plan + cleanup inventory (file này + [cleanup-inventory.md](./cleanup-inventory.md)) | ✅ done |
| **P1** | Tạo sub-collection `Marketing & Customers › 👥 Customer` + index text card | ✅ collection id **99** (location /52/); index card chờ P2 |
| **P2** | Build 4 board MỚI (A/B/C/D) vào sub-collection + index | ✅ A#103 B#105 C#106 D#104; collection desc = index |
| **P3** | Validate (dùng thử, đối chiếu số với board cũ, không thiếu insight) | 🔵 **CHỜ USER kiểm tra** — coverage diff done, 4 gap (G1-G4) đã backfill+verify |
| **P4** | Retire: archive 5 board + 100 card (97 exclusive + 3 orphan cũ, 0 orphan còn lại) + xóa 14 file + update registry + fix link | ✅ user duyệt "OK retire" 2026-06-12 |

> 🔒 **RETIRE GATE (hard):** P4 KHÔNG tự động. Chỉ thực thi khi **user tự kiểm tra 4 board mới ở P3 và xác nhận OK**. Đến P3 sẽ dừng lại, báo cáo, hỏi duyệt — không xóa gì trước khi có "OK retire".

> **#15 [Cross]:** chuyển về sub-collection Customer (cohesion) — bẻ nhẹ rule "L3→Analytics"; để shortcut ở Analytics nếu cần. (đã chốt hướng (a)).

## Lesson (deploy → nested collection)
Deploy script resolve collection theo **header** `## 📂 Collection: Parent > Child` (parser hỗ trợ ` > ` nested via parent field). Để board vào sub-collection `👥 Customer`, blueprint phải ghi `## 📂 Collection: Marketing & Customers > 👥 Customer` — KHÔNG chỉ "Marketing & Customers" (sẽ land top-level 52). `> **Collection ID:**` blockquote chỉ trang trí, script bỏ qua. → B/C/D dùng đúng nested header.

## Defaults đã chọn cho 3 open questions (user veto được)
1. **B & C: copy blueprint cũ → đổi tên + dedup** (nhanh, ít rủi ro, giữ cohort/heatmap #14 + intelligence #15 nguyên vẹn). A & D build mới thật (gom nhiều nguồn).
2. Sub-collection tên: **"👥 Customer"**.
3. **#15: chuyển hẳn** về sub-collection Customer; Analytics giữ shortcut/link nếu cần.

## Quyết định đã chốt (2026-06-12)
- Thứ tự: **sub-collection → build mới → validate → xóa cũ**. Cleanup list ghi TRƯỚC (P0).
- #48 retire hẳn (chia về A/B/C). #102 nội dung margin → board D; tab Activation Now → A.
- Build MỚI hoàn toàn (blueprint mới, tên file mới) — không sửa đè blueprint cũ; cũ sống tới khi P3 ổn.

## Open questions
1. B (Retention) và C (Intelligence) nội dung gần như #14/#15 — build lại từ đầu, hay copy blueprint cũ → đổi tên/dedup (tiết kiệm)? (khuyến nghị: copy-rename-dedup cho B/C; build mới thật cho A/D vì gom nhiều nguồn)
2. Sub-collection: tên hiển thị "👥 Customer" hay "Customer Analytics"?
3. Có cần giữ #15 ở Analytics dạng shortcut/link không, hay chuyển hẳn?
