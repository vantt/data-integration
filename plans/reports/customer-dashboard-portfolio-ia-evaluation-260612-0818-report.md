# Customer Dashboard Portfolio — IA Evaluation & Proposal

> Đánh giá 5 customer dashboards (live), chẩn đoán chồng lấn, đề xuất tổ chức lại theo
> job-to-be-done. Advisory — chưa thực thi. 2026-06-12.

## 1. Hiện trạng (5 board, 2 collection)

| # | Tên | Coll | Cards | Tabs | Scope |
|---|---|---|---|---|---|
| 99 | Customer Action Queue | 52 Mkt&Cust | 10 | 1 | Retail |
| 48 | Customer Operational | 52 | 24 | 3 | Retail |
| 14 | Customer Retention & Lifecycle | 52 | 34 | 3 | Retail |
| 102 | Retail Activation Cockpit | 52 | 17 | 3 | Retail |
| 15 | Customer Intelligence Monthly | 93 Analytics | 30 | 3 | Cross |

→ customer board bị **xé ra 2 collection** (52 và 93) → đã gây "rối không biết board nào".

## 2. Chẩn đoán chồng lấn (gốc của sự rối)

Cùng 1 khái niệm lặp ở nhiều board:

| Concept | Có ở board |
|---|---|
| Status/Segment Distribution (pie) | 48, 15, (14 lifecycle) |
| MAU / Active rate | 48, 15, 14 |
| New / Churn / Acquisition trend | 48, 15, 14 |
| One-Time Buyer Rate, Repeat Rate | 15, 14 |
| **Segment × Status matrix** | 48 + 14 (trùng nguyên) |
| **At-Risk / Reactivation watchlist** | 48, 14, 99, 102 (4 board!) |
| **Next Purchase Signal / OVERDUE** | 48, 14, 99, 102 (4 board!) |
| **Action queue / call-list** | 99 + 102 "Activation Now" (trùng — tôi mới tạo) |
| Discount Sensitivity | 15 + 102 (trùng) |
| Channel revenue/acquisition | 48, 15, 102 |
| Cohort heatmap / layer cake | 14 (DUY NHẤT — nội dung mạnh thật) |

**Kết luận:** chỉ có ~4 JOB thật, nhưng bị bôi qua 5 board. Board phân biệt bằng tên "Customer X" mơ hồ, không nói LÀM GÌ / KHI NÀO.

## 3. Vấn đề cụ thể theo từng board

- **#48 Operational — yếu nhất, không có job riêng:** tab1 trùng #14/#15, tab3 trùng #99/#102, chỉ geo (top provinces) là hơi riêng. → ứng viên RETIRE.
- **#102 Cockpit (mới):** giá trị riêng = **margin lens** (channel margin × retention, discount × margin, margin-negative). Nhưng tab "Activation Now" = trùng #99; tab discount = trùng #15. → REFOCUS chỉ giữ margin.
- **#99 Action Queue:** job rõ nhất (dispatch — gọi ai hôm nay). Giữ làm board operational DUY NHẤT.
- **#14 Retention:** sâu nhất, có cohort/waterfall độc quyền. Giữ làm board retention DUY NHẤT.
- **#15 Intelligence [Cross]:** strategic monthly, value/segment/behavior. Nằm ở Analytics theo rule "L3 Cross → Analytics" — đúng rule nhưng tách khỏi cụm customer → góp phần rối.

## 4. Đề xuất: 4 board theo JOB-TO-BE-DONE (từ 5 → 4)

| Board (job) | Cadence | Audience | Gộp từ | Bỏ đi |
|---|---|---|---|---|
| **A. Daily Action Queue** (gọi ai hôm nay) | Daily | CS/Sales | #99 + watchlists của #48 + "Activation Now" của #102 | — |
| **B. Retention & Cohorts** (khách có quay lại?) | Weekly | Mkt/CS lead | #14 + retention bits #48 | — |
| **C. Customer Intelligence** (value/segment/behavior) | Monthly | CEO/CMO | #15 + segment/geo/acquisition #48 | — |
| **D. Profitability & Margin** (margin-gate activation) | Monthly | CMO/Finance-mkt | #102 refocus (chỉ margin) | tab Activation Now → A; discount distribution để C |
| ~~#48 Operational~~ | — | — | **RETIRE** (chia về A/B/C) | — |

**Naming** (gốc của "tên không phân biệt"): dẫn bằng CADENCE + JOB, không phải "Customer X":
- `Daily · Customer Action Queue [Retail]`
- `Weekly · Customer Retention & Cohorts [Retail]`
- `Monthly · Customer Intelligence [Cross]`
- `Monthly · Customer Profitability [Retail]`

(Cadence trong tên = đúng nguyên tắc guide §2.)

## 5. Collection — có nên làm collection Customer riêng?

**KHÔNG nên top-level mới** — vi phạm nguyên tắc tổ chức-theo-audience (guide §2): customer board phục vụ Marketing/CS = cùng audience marketing-channel board. Guide chỉ cho tách khi "CS team >15 người, KPI riêng" — chưa tới.

**NÊN: sub-collection `Marketing & Customers › 👥 Customer`** — đúng tiền lệ Operations (Daily/Periodic sub-split cùng audience, khác workflow). Coll 52 đang 7 board (3 mkt + 4 customer) → gần ngưỡng 8; cụm customer là workflow riêng. Sub-collection gom 4 board customer về 1 chỗ → giải trực tiếp "rối/scattered".

**Quyết định mở — #15 [Cross]:**
- (a) Chuyển #15 về sub-collection Customer (cohesion: mọi board customer 1 chỗ) — bẻ nhẹ rule "L3→Analytics".
- (b) Giữ #15 ở Analytics (đúng rule scope) — chấp nhận customer board ở 2 nơi.
→ Khuyến nghị (a): cohesion quan trọng hơn rule scope cho trải nghiệm người dùng; Analytics để link/shortcut.

**Thêm:** 1 text card "Customer — Bắt đầu từ đâu" ghim đầu sub-collection: bảng "cần X → mở board Y".

## 6. Open decisions (cần user chốt)
1. RETIRE hẳn #48, hay STRIP thành "Daily Health" tab trong board A? (retire = gọn hơn; strip = giữ geo/pulse riêng)
2. Gộp #99 + health-glance thành 1 "Daily Cockpit" 2 tab, hay giữ #99 thuần dispatch + board health riêng?
3. #102: đồng ý bỏ tab "Activation Now" (chuyển về A) + giữ chỉ margin? (board này vừa build theo yêu cầu — cần buy-in trước khi cắt)
4. #15: chuyển về sub-collection Customer (a) hay giữ Analytics (b)?
5. Sub-collection Customer: làm ngay, hay chỉ rename+consolidate board trước rồi tính collection sau?

## 7. Thứ tự đề xuất (nếu duyệt)
Consolidate/refocus board (giải overlap) **trước** → rename (giải tên) → sub-collection (giải scattered) → index card. Collection là bước cuối, rẻ; giá trị lớn nhất ở consolidate.
