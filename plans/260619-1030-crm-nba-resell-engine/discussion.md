# NBA Re-sell Engine — Design Discussion

> Status: **DISCUSSION / DESIGN** (chưa implement). Centerpiece tài liệu để thảo luận tiếp.
> Date: 2026-06-19 · Branch: main · Owner: Van
> Liên quan: `plan.md` (lộ trình), scout report (hiện trạng code)

---

## 1. Vấn đề & tầm nhìn

Warehouse tổng hợp dữ liệu → sản xuất **bộ insight tái bán** (nhiều hướng tiếp cận, xếp theo ưu tiên).
CRM dựa trên **kịch bản (rules)** định sẵn → gợi ý **bước tiếp theo** cho từng khách.
Mục tiêu: khi CS tiếp cận một khách, có ngay **cái nhìn tổng quát** — biết *mục tiêu cao nhất với người này là gì* và *việc cần làm tiếp theo*.

Ví dụ điển hình: ưu tiên lấy số điện thoại; không được thì lấy qua email (thang liên lạc tuần tự).

Đây là một **Next Best Action (NBA) engine** đặt trên nền **customer intelligence**.

---

## 2. Hiện trạng code (đã có ~60%)

| Tầng | Trạng thái |
|---|---|
| **Signals** (warehouse `dim_customers`) | ✅ Gần đủ — RFM, `customer_status`, `lifecycle_stage`, `next_purchase_signal`, `predicted_next_purchase_date`, `avg_days_between_orders`, `discount_sensitivity`, `channel_preference`, margin, affinity, `is_contactable`, `contact_quality` |
| **Decision v0** (`mart_customer_action_queue`) | ⚠️ Có 6 action types (CALL_NOW / REORDER_NUDGE / REORDER_PREEMPT / WIN_BACK / SECOND_ORDER / HIGH_CANCEL_RISK) + `priority_rank` + `rationale_vi` + `value_at_stake` — **nhưng logic quyết định đang hard-code trong SQL CASE (sai chỗ)** |
| **Serving → CRM** | ✅ `reverse_etl_warehouse_to_crm.py` → cache.db (`wh_customer_insight`, `wh_action_queue`) |
| **CRM S03 (Customer 360)** | ✅ FastAPI + Jinja2 + HTMX; Value & Behavior panel (P01), M08 unified contact log (đang design), `crm_activity`, `crm_note`, `crm_party_insight` |
| **Orchestration + Feedback** | ❌ `crm_action_state` mới ở migration; M08 outcome chưa nối ngược warehouse; consent per-channel chưa có |

**Mâu thuẫn cốt lõi:** chính tầm nhìn nói "warehouse ra insight, CRM rules ra quyết định" — nhưng code hiện đặt quyết định trong warehouse SQL. Công việc thực sự = **kéo tầng quyết định ra khỏi SQL, đưa vào CRM**.

---

## 3. Kiến trúc đích: pipeline quyết định 3 chặng ("hybrid+")

Quyết định của Van: warehouse làm **tối đa năng lực** (nó nhanh) cho phần *điểm nền*; CRM thêm **lớp chấm điểm phụ linh hoạt** cho phần warehouse không làm được; rồi **rule engine** chốt hành động.

```
① WAREHOUSE              ② CRM SCORING (phụ)          ③ RULE ENGINE
   chấm điểm NỀN          điều chỉnh LINH HOẠT         chọn HÀNH ĐỘNG
   population-wide         live state + định tính       discrete → action
   "quan trọng cỡ nào     "ngay lúc này, với           "vậy làm gì,
    xét theo lịch sử?"      context sống, đổi sao?"       qua kênh nào?"
   → base_priority_score   → final_score                → action + alt + reason
   → candidate objectives  → adjustment reasons         → contactability ladder
```

**Vì sao tách warehouse khỏi quyết định cuối** (3 lý do gắn với setup thực tế):
1. Rules đổi hàng tuần (business chỉnh ngưỡng); signals ổn định. Rebuild dbt mỗi lần đổi rule = quá chậm.
2. Quyết định cần **state sống** warehouse mù: vừa M08 sáng nay, task mở, đã dismiss/snooze, `consent_contact=false`.
3. Thang liên lạc tuần tự ("Zalo trước, 2 ngày không đọc thì gọi") là logic **có trạng thái**, bất khả thi bằng SQL snapshot daily.

**Vì sao warehouse vẫn làm tối đa** (đúng instinct Van): warehouse là **vua của "điểm tương đối toàn dân"** (percentile, rank, cohort baseline) — nó thấy CẢ tập khách cùng lúc; CRM chỉ thấy 1 khách mỗi lần. Churn-vs-cohort, value percentile, overdue-severity (số σ vượt chu kỳ) → bắt buộc warehouse.

---

## 4. Phép thử ranh giới (logic này đặt ở chặng nào?)

| Câu hỏi | CÓ → chặng |
|---|---|
| Cần CẢ tập khách để tính? (percentile, rank, cohort) | ① Warehouse |
| Là tổng hợp ổn định trên lịch sử? (RFM, affinity, margin) | ① Warehouse |
| Cần STATE hôm nay? (vừa M08, task mở, dismiss, snooze, consent) | ② CRM scoring |
| Cần dữ liệu ĐỊNH TÍNH rep nhập? (`crm_party_insight`) | ② CRM scoring |
| Có trọng số/ngưỡng business chỉnh hàng tuần? | ② CRM scoring |
| Là "if X then DO Y" sinh hành động rời rạc? | ③ Rule engine |

Phép thử này giữ 3 chặng không lấn nhau khi hệ thống lớn lên.

---

## 5. Mẫu hiệu quả: "điểm nền + điều chỉnh"

CRM KHÔNG tính lại từ đầu. Warehouse làm 80% nặng, CRM chỉ cộng/trừ delta mỏng:

```
② final_score = base_priority_score          (warehouse, ổn định)
              − vừa liên lạc trong 7d         (live)
              − đang có task mở               (live)
              + rep insight "advocate/loyal"  (định tính)
              × consent_gate (0 nếu DNC)      (live)
              × campaign_suppression          (live, tránh đụng blast)
```

Khách "lạnh" (chưa có hoạt động CRM) → `final_score ≈ base_score` → vẫn xếp hạng được ngay, không cần state. Graceful degradation.

---

## 6. Phân vai theo signals thực tế

### ① Warehouse `dim_customers` / `mart_*` (đẩy tối đa)
- **Đã có:** RFM, `next_purchase_signal`, `avg_days_between_orders`, `predicted_next_purchase_date`, margin, `discount_sensitivity`, `channel_preference`, affinity (`top_affinity_product`)
- **Thêm mới (warehouse làm được mà chưa làm):** `value_percentile`, `churn_score` (vs cohort), `overdue_severity` (số σ vượt chu kỳ), `base_priority_score`, `value_at_stake`
- **Candidate objectives + điểm nền** → `mart_customer_action_queue` **đổi vai** thành "ứng viên đã chấm điểm", KHÔNG phải quyết định cuối

### ② CRM scoring layer (mới, thuần app) — fusion
- Đọc: warehouse score + `crm_action_state` (dismiss/snooze) + `crm_activity` (vừa gọi?) + `crm_party_insight`/`crm_note` (định tính) + consent per-channel
- Trọng số **tunable qua config** (sửa nhanh, không rebuild dbt) → `final_score` + danh sách lý do điều chỉnh

### ③ Rule engine (mới, config-driven)
- `final_score` + objective ladder + contactability ladder → **1 action chính + phương án thay thế + reason code đầy đủ**
- Declarative, priority-ordered, first-match-wins, lưu dạng DATA (bảng/config CRM), KHÔNG hard-code, KHÔNG ML ở v1 (YAGNI — minh bạch > tinh vi)

---

## 7. Objective Ladder (thang mục tiêu)

Nguyên tắc: **mục tiêu ưu tiên cao nhất CHƯA bị chặn sẽ thắng.** Map vào cột `dim_customers`:

```
T0  NỀN TẢNG LIÊN LẠC    ← chặn mọi thứ khác
    if not is_contactable OR contact_quality='masked'
    → Mục tiêu: thu thập/xác minh kênh liên lạc

T1  RỦI RO / QUAN HỆ
    if value_group∈(VIP,GOLD) AND customer_status='At Risk'  → GIỮ CHÂN (ưu tiên tối đa)
    if customer_status='Churned'                             → WIN-BACK
    if frequency=1                                            → ĐẨY ĐƠN THỨ 2 (onboard)

T2  TÁI BÁN ĐÚNG THỜI ĐIỂM   ← lõi chiến lược tái bán
    if next_purchase_signal='OVERDUE'   → REORDER NUDGE
    if next_purchase_signal='DUE_SOON'  → REORDER PREEMPT (đón đầu)

T3  TĂNG TRƯỞNG
    if status='Active' AND có affinity   → UPSELL/CROSS-SELL (top_affinity_product)
```

Tín hiệu vàng cho tái bán: `predicted_next_purchase_date` + `avg_days_between_orders` → gọi *trước* khi khách hết hàng (đón đầu), không đợi churned mới win-back.

**OPEN:** thứ tự ưu tiên cứng giữa các tier — VIP-at-risk có LUÔN thắng overdue-reorder không? (xem §14)

---

## 8. Contactability Ladder (thang liên lạc)

Logic *bên trong* một action, **có state**:

```
Để thực hiện action cần liên lạc:
  1. có primary_phone hợp lệ & consent_phone?  → gọi
  2. không → có email & consent_email?          → soạn email xin callback
  3. không → có zalo_uid?                        → nhắn Zalo
  4. không có kênh nào                           → action đổi thành "thu thập liên lạc" (về T0)
```

Cần lưu state "đã thử kênh nào / bao lâu chưa phản hồi" trong `crm_action_state` để fallback tuần tự hoạt động qua nhiều ngày.

**OPEN:** schema state cho fallback tuần tự (xem §14).

---

## 9. Ví dụ end-to-end (1 khách qua 3 chặng)

```
KH "Chị A":
① WAREHOUSE → value_percentile=96 (VIP), churn_score=0.78, overdue_severity=2.3σ,
   base_priority=82, value_at_stake=4.2tr,
   candidates=[GIỮ_CHÂN(78), TÁI_BÁN_skincare(64)]
   reason: "VIP · trễ 45d (thường 30d) · skincare 70%"

② CRM SCORING → base 82 − 0 (chưa liên lạc gần) + 8 (rep insight: advocate)
   × consent_phone=OK = final 90 → đứng đầu hàng đợi rep hôm nay
   reason +: "rep đánh dấu advocate → ưu tiên giữ"

③ RULE ENGINE → objective=GIỮ_CHÂN; có phone hợp lệ + chưa gọi 7d
   → ACTION: 📞 Gọi ngay, ưu đãi skincare
   → fallback: Zalo → email
   reason đầy đủ ghép từ cả 3 chặng → hiện cho CS
```

---

## 10. Explainability — output xuyên suốt (không phải tầng 4)

Mỗi chặng nối thêm một mảnh "why"; CS thấy **chuỗi lý do hoàn chỉnh**. Điều kiện sống còn để CS tin & làm theo. `rationale_vi` (string template hiện tại) → tách thành **reason fragments có cấu trúc** để 3 chặng ghép lại.

```
{ objective, action, channel,
  why: ["VIP", "At Risk 45d", "skincare 70%", "rep: advocate"],
  value_at_stake, confidence }
```

---

## 11. Màn hình CS (gắn vào S03 / panel P01)

```
┌─ KH: Chị A  ·  🟡 VIP · At Risk · 🔴 churn cao ────────────┐
│ MỤC TIÊU CAO NHẤT:  ① Giữ chân  ② Tái bán skincare        │
├───────────────────────────────────────────────────────────┤
│ 👉 VIỆC CẦN LÀM:  📞 Gọi ngay — 09xx                       │
│    Vì sao? VIP, 45 ngày chưa mua (thường 30d), rủi ro ~4.2tr ▾│
│    [ Gọi ngay ]  [ Soạn Zalo ]  [ Bỏ qua ]  [ Hoãn 3d ]   │
├─ Phương án khác: email ưu đãi · tặng điểm loyalty ─────────┤
│ Tín hiệu: recency 45d · 12 đơn · 18tr · skincare 70% ──────┤
└───────────────────────────────────────────────────────────┘
```

- **[Gọi ngay]** mở thẳng M08 → CS ghi `outcome` → ghi `crm_action_state`
- CS luôn **chủ động** (gợi ý, không ép); có override + "không liên quan" để học lại

---

## 12. Data contracts giữa các chặng (nhẹ)

- **① → ②** (cache.db row/khách): signals + `base_priority_score` + `candidate_objectives[]` mỗi cái `{objective, base_score, value_at_stake, reason_fragments[]}`
- **② scoring**: + `crm_action_state` + `crm_party_insight` + `crm_activity` + consent → `scored_candidates[]` với `final_score` + `adjustment_reasons[]`
- **③ rules**: + contactability + ladder config → `{primary_action, alternatives[], full_reason}`

---

## 13. Rủi ro gắn với THỰC TẾ dữ liệu

1. **`fact_payments` rỗng** → KHÔNG xây objective dựa công nợ/AR/cashflow; chỉ dùng order signals.
2. **`customer_type` migration dở** (chỉ ~3 WHOLESALE thật) → đừng phân nhánh chiến lược theo RETAIL/WHOLESALE cho data cũ; mặc định RETAIL.
3. **Contact masked** (`source_contact_quality='masked'` từ sàn) → nhiều khách marketplace không có SĐT thật → **T0 (thu thập liên lạc) áp đảo**, không phải tái bán. Cold-start phải xử lý tử tế.
4. **Consent per-channel chưa có** → cần trước khi để CS gọi hàng loạt (DNC / pháp lý).
5. **Đừng đụng campaign blast** → đừng để CS gọi người vừa nhận email chiến dịch (campaign_suppression ở chặng ②).

---

## 14. Quyết định thiết kế còn mở (để bàn tiếp)

1. **Trọng số chặng ②** — cố định trong config, hay cho business chỉnh qua UI? `final_score` cộng tuyến tính (dễ giải thích) hay có nhân/gate (mạnh hơn, khó debug)?
2. **Objective ladder** — chốt danh sách mục tiêu cuối + thứ tự ưu tiên CỨNG giữa tier (VIP-at-risk có luôn thắng overdue-reorder?).
3. **Contactability ladder state** — schema lưu "đã thử kênh nào, bao lâu chưa phản hồi" trong `crm_action_state`.
4. **Cold-start khách masked** — có tách luồng riêng "thu thập liên lạc" khỏi luồng tái bán không?
5. **Rules representation** — DB table (sửa runtime, cần UI) vs YAML/config file (đơn giản, deploy lại)?
6. **Tần suất refresh** — base score nightly đủ chưa, hay cần intra-day cho action queue?

---

## 15. Quyết định đã chốt

- ✅ Kiến trúc **hybrid+ 3 chặng** (warehouse tối đa → CRM scoring phụ → rule engine).
- ✅ Warehouse làm tối đa năng lực (population-relative scoring); CRM phủ lớp linh hoạt mỏng.
- ✅ Heuristic minh bạch ở v1, KHÔNG ML cho tầng gợi ý (YAGNI).
- ✅ Explainability xuyên suốt 3 chặng (reason fragments có cấu trúc).
- ✅ **Task/Action UX** (§18): NBA card → 2 CTA [Gọi ngay] + [Đặt lịch]; M08 → "Lên lịch theo dõi" cho positive outcomes.
- ✅ Hiện tại: **bàn thiết kế trước**, chưa implement.

---

## 16. KIỂM CHỨNG DỮ LIỆU THỰC TẾ (2026-06-19) — đổi chẩn đoán

Query `main_marts.dim_customers` (read-only, data tươi: đơn mới nhất 2026-06-18). N=7563.

### Contactability & buckets
| Nhóm | Số KH | % |
|---|---|---|
| **Liên lạc được** (`is_contactable`, real) | 4138 | 55% |
| **Masked** (sàn, không SĐT thật) | 3425 | 45% |
| → A: contactable + repeat(>1) | **1236** | prime NBA |
| → A: contactable + one-time | 2496 | second-order target |
| → A: contactable + 0 đơn | 406 | |
| → B: masked + repeat(>1) | **433** | identity-capture, detect được |
| → C: masked + one-time | 1800 | suppress / passive |
| → masked + 0 đơn | 1192 | |

**Tin tốt:** masked KHÔNG phá identity resolution — 433 khách masked vẫn gom về 1 id với order_count>1. Bucket B tồn tại, detect được.

### Chất lượng base contactable (4138) — phũ phàng
- Theo value: **89% BRONZE** (3696). VIP+GOLD chỉ **155** (3.7%).
- Theo status: **88% CHURNED** (3649). Active chỉ **24**, At-Risk 59.

### Funnel math (recency_days, data tươi)
| recency | KH |
|---|---|
| 0–30d | 116 |
| 31–90d | 148 |
| 91–365d | 498 |
| **365d+** | **5203 (69%)** |
| chưa có đơn | 1598 |

- order_count: 0=1598, **1=4296 (57%)**, 2-3=1190, 4-9=368, 10+=111 → chỉ **22% mua lặp**.
- Khách distinct mua/tháng (6 tháng qua): **~20–83** (tháng 6: 77).

### Chẩn đoán mới (bằng chứng, không phải giả định)
Đây **KHÔNG phải** bài toán "tối ưu reactivation cho VIP at-risk" (chỉ ~83 người). Đây là:
1. **Một nghĩa địa**: 69% mua 1 lần >1 năm trước rồi biến mất. Win-back ROI âm (research: drift >90d cứng lại, 365+ ≈ chết) → 1 phát rẻ rồi suppress.
2. **Lõi giá trị mỏng nhưng thật**: 1236 repeat+contactable (155 GOLD/VIP) → NBA + CS touch đáng tiền Ở ĐÂY.
3. **Rò rỉ ở đỉnh phễu**: ~77 khách mới/tháng, nhiều masked. 433 masked đã chứng minh mua lặp dù ta không liên lạc.

→ **Trọng tâm chiến lược KHÔNG phải reactivation, mà là ACTIVATION (đẩy đơn 2 cho khách mới) + IDENTITY CAPTURE (chặn rò rỉ).** Khớp research: "bán ế" = kẹt ở activation, không phải mất khách trung thành.

### Hệ quả YAGNI cho engine
**Đừng xây engine 3 chặng cho 7563.** Nó chỉ đáng cho **lõi ~1200–1500** (recent + valuable + repeat-contactable). 6000 còn lại = rule đơn giản (one-shot hoặc suppress). Identity-capture (QR insert + Zalo OA — đã có hạ tầng) là funnel ROI cao nhất, **tách khỏi** engine CRM.

### Ladder v2 (thay §7, theo data)
```
B0  IDENTITY CAPTURE (funnel ops/marketing, KHÔNG phải CS-action)
    masked (B+C) → QR insert + Zalo OA follow → convert sang A
B1  ACTIVATION / ĐƠN THỨ 2   ← lõi tăng trưởng
    A + one-time + recent (≤90d) → đẩy đơn 2 trong cửa sổ 60–90d
B2  PROTECT CORE
    A + GOLD/VIP + active/repeat (155 + lõi 1236) → CS touch cao, NBA thật
B3  CHEAP WIN-BACK
    A + churned 91–365d (recoverable) → 1 phát ưu đãi rồi suppress
B4  SUPPRESS
    365d+ graveyard (5203) → không đốt tiền; chờ organic
```

### Khuyến nghị thứ tự bàn (cập nhật)
Bàn **#2 + #4 GỘP, TRƯỚC** — và bắt đầu từ *funnel math* (ladder v2), không từ scoring. #1 (trọng số) và #3 (contactability state) là chi tiết downstream, hoãn.

---

## 17. Probe vòng 2 (2026-06-19) — đường biên lõi + Shopee identity (CHỐT)

### Goal 1 — Đường biên lõi engine: chọn **Def-B = 1,263**
| Định nghĩa | Engine count | Static pool |
|---|---|---|
| Def-A: contactable + repeat(>1) | 1,236 | 6,327 |
| **Def-B: contactable + (repeat OR recency≤90)** ← chốt | **1,263** | 6,300 |
| Def-C: + value≥SILVER | 1,349 | 6,214 |
| Live pulse recency≤90 (any) | 264 | — |
| Live pulse + contactable | **83** | — |

- Def-A là **bẫy dormancy**: 85.6% (1,058) churned >365d, chỉ 56 active. Def-C thêm 86 khách nhưng 92–97% churned → one-shot tốt hơn ongoing.
- → **Boundary = Def-B (1,263).** Nhưng phần lớn vẫn dormant: chỉ **live sub-core ~83–264** cần NBA scoring *liên tục*; phần dormant = one-shot win-back.

### Goal 2 — Shopee masked identity: **RESOLVES, KHÔNG vỡ**
- 2,926 khách Shopee distinct; **603 (20.6%) mua lặp dưới 1 customer_id ổn định**; 346/603 masked.
- Sapo gán `CUZN*****` ổn định; phone/email NULL nhưng record bền qua nhiều đơn, qua cả shop splits (FJV+JPC → cùng `customer_key`). Top masked repeater: **36 đơn / 1 record**.
- → **masked ≠ fragmented.** order_count / recency / value của khách masked **đáng tin**. 433 masked-repeat là khách lặp thật, chỉ không liên lạc trực tiếp được.

### Hệ quả & sequencing (đề xuất — chờ Van chốt)
- **Đường chuyển sạch:** masked-repeat (346 Shopee) → identity capture (QR/Zalo) → kế thừa ngay full history → nhảy thẳng vào engine core. Vì identity resolves, capture xong là có liền RFM/value.
- **Tiering thực tế của base:**
  | Tier | ~Size | Cơ chế |
  |---|---|---|
  | Live core | ~83 | Full NBA, CS high-touch, scoring liên tục — engine 3 chặng đáng ở đây |
  | Dormant-valuable | ~1,180 | One-shot win-back rồi suppress (rule tĩnh) |
  | Masked-repeat | 433 | Identity-capture track (Zalo/QR + in-platform Shopee) |
  | Graveyard / one-time-masked | ~6,000 | Suppress |
- **YAGNI sequencing:** funnel rẻ-ROI-cao (**identity capture + activation đơn-2**) làm TRƯỚC → tăng active base → engine 3 chặng đáng đầu tư SAU. Hiện engine chỉ phục vụ ~83 người → chưa cần bộ scoring tinh vi để xếp hạng 83 người. Engine **không phải Phase-1**.

Chi tiết số liệu: `plans/reports/data-probe-core-boundary-shopee-masked-identity-260619-1054-report.md`.

---

## 18. QUYẾT ĐỊNH — Task/Action UX (2026-06-19)

### Vấn đề
`action_queue` đã nói "làm gì" nhưng CS phải bấm "→ Tạo task" generic để chuyển sang task mới làm được — friction không cần thiết, không rõ intent.

### Phân tích
| Concept | `wh_action_queue` | `crm_task` |
|---|---|---|
| Ai tạo | Warehouse (daily batch) | CS tạo / auto |
| Bất biến | ✅ read-only | ❌ mutable |
| Owner / due_at | ❌ | ✅ |
| Status tracking | dismiss/snooze only | open→doing→done |

Hai thứ không trùng nhau — nhưng UX không làm rõ sự khác biệt.

### Quyết định chốt

**A. NBA card (c360_insight_panel.html)** — thay "→ Tạo task" bằng 2 CTA rõ intent:
- **[Gọi ngay]** → mở M08 với party_id pre-set → CS ghi outcome → action tự đánh dấu "Đã xử lý"
- **[📅 Đặt lịch]** → inline date picker → POST `/customers/{party_id}/tasks` với `source=action_queue`, `source_ref=action_id`, `title` auto từ action_type → task hiện trong Tasks panel

**B. M08 "Lên lịch theo dõi"** — extend pattern "Hẹn lại" (đã có):
- Hiện thêm section sau positive outcomes (answered, met, replied): checkbox unchecked by default + date picker + quick-fill (+7d, +14d, +30d)
- Submit → tạo `crm_task` source=manual, party_id, due_at, title auto: "Theo dõi: [party_name]"
- Backend: `schedule_followup_at` field trong `handle_log_activity`

**C. Scoring chặng ② (§5)** — task mở là input:
- `final_score -= open_task_penalty` nếu `crm_task WHERE party_id=? AND status IN ('open','doing')` tồn tại → không leo đầu queue khi đã có lịch

### Không thay đổi
- M05 vẫn giữ cho tạo task thủ công không liên quan action_queue
- M08 "Hẹn lại" + "Tạo task nhắc tự động" (callback) giữ nguyên

