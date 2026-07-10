# Activity Log: API mịn theo field + tích hợp streamline vào Call-Cockpit — thiết kế UX

> 2026-07-10. Nguồn đọc trực tiếp: `modal_log_activity.html` (M08, ~470 dòng), `screen_customer_360_activity.py` (POST /log-activity), `S14-call-mode-cockpit.md`, `activity.py` (enum). Liên quan: plan `260709-1638-crm-outreach-effort-report`, Sprint Gọi Ra 45 ngày.

---

## I. Chẩn đoán — vì sao form nặng và "compete" với cockpit

**M08 hiện là 1 form gộp 3 công việc khác bản chất:**

| Công việc | Tính chất | Tần suất sprint |
|---|---|---|
| A. Ghi nhanh TRONG cuộc gọi (outcome, lý do, note nháp, hẹn lại) | thời gian thực, chia sẻ attention với cuộc nói chuyện | 50 lần/tuần |
| B. Chốt phiên SAU cúp máy (đóng task/action, next step) | <10 giây, disposition | 50 lần/tuần |
| C. Ghi hành chính (bổ sung quá khứ, sửa note, email/visit, đơn liên quan, visibility/pin, insight) | không gấp, cần form đầy đủ | <5% |

Vì API chỉ có **1 POST tất-cả-hoặc-không** (20 field + 7 side-effect: activity, note, insight, callback task, followup task, complete task, bulk resolve), UI buộc phải thu thập tất cả cùng lúc → 6 step, tràn màn hình. Tệ nhất: submit xong `HX-Redirect` sang **tab timeline** — rep đang trong phiên gọi/queue bị văng khỏi ngữ cảnh, phải tự mò về worklist.

**Cockpit không "compete" — nó delegate sai chỗ:** outcome_bar của S14 (A-S14-009) chỉ mở M08 modal, che luôn script/talking-points đúng lúc rep có thể còn cần nhìn. Trong khi chính spec S14 đã vẽ ý đúng: `[ghi chú tạm…] [✓Gọi được][✗Không nghe][⏳Hẹn lại][🛒Đã mua]` — inline, không modal. Implementation chưa theo kịp spec.

**Bug/gap phát hiện khi đọc:**
1. 🔴 UI M08 chỉ có 4 outcome pill (answered/no_answer/callback/refused) — **thiếu `busy` và `wrong_number`** dù `CONTACT_OUTCOMES_CALL` có đủ 6. Sprint không ghi được "sai số" (KPI làm sạch tệp) qua UI. Fix 30 phút, làm ngay trước sprint.
2. Auto-claim nằm trong POST — nếu sau này tạo draft lúc mở cockpit thì auto-claim phải dời về finalize (không claim khách chỉ vì mở màn hình).
3. Cockpit đã có tiền lệ API mịn đúng hướng: `POST /customers/{id}/custom-field-inline`, `POST /tags/inline` (whitelist, swap 1 dòng, không re-render panel) — thiết kế dưới đây tổng quát hóa pattern này cho chính activity.

---

## II. Nguyên tắc thiết kế

**"Log-as-you-go, confirm-at-the-end, form-only-for-exceptions."**

- Phiên gọi = bản nháp activity sống. Mọi thứ gõ/bấm trong cockpit tự lưu dần vào nháp (PATCH từng field).
- Cúp máy = chốt disposition 1-2 chạm ngay trên cockpit, không modal.
- M08 = form ngoại lệ/hành chính + "ngăn kéo nâng cao" của CHÍNH bản ghi đó — không phải đường ghi thứ hai.
- **Một đường ghi duy nhất:** cockpit PATCH và M08 POST phải cùng đi qua ActivityService + side-effect executor chung. (Bài học `party_insights` factory: UI wired, backend không — 2 đường ghi là mầm divergence.)

---

## III. API — draft + PATCH theo field + finalize

```
1. POST /api/parties/{party_id}/call-sessions
   → tạo draft activity {status:'draft', channel_type:'call', started_at, task_id?, channel_identity_id?}
   → trả activity_id. Idempotent: (staff, party) có draft mở → trả lại draft đó.
   Gọi khi: vào full-screen cockpit / bấm nút Gọi trên identity_bar (kèm identity đã chọn).

2. PATCH /api/activities/{activity_id}
   body: subset bất kỳ của {contact_outcome, outcome_reason, body, callback_at,
          related_order_code, occurred_at, channel_identity_id,
          custom_fields.zalo_connected, custom_fields.*}
   → autosave mỗi lần commit field (blur/bấm pill). Validate enum theo channel_type.
   → 200 + fragment nhỏ (hoặc 204). KHÔNG side-effect nào ở đây.

3. POST /api/activities/{activity_id}/finalize
   body: {complete_task_ids[], resolve_action_ids[], create_callback_task?,
          schedule_followup_at?, save_as_note?{...}, promote_insight?{...}}
   → 409 nếu chưa có contact_outcome. Idempotent. Chạy toàn bộ side-effect tại đây
     (kể cả auto-claim dời từ POST cũ về). KHÔNG redirect — trả fragment outcome_bar
     "✓ đã chốt" + enable [Khách kế →].
```

**Lợi ích ăn theo (miễn phí):**
- `contact_duration_s` = finalize_at − started_at → **tự đo, không cần staff nhập** → giải luôn câu hỏi mở #6 của plan 260709-1638 (conversations_count không cần proxy).
- "Log outcome 100%" của sprint được enforce bằng cấu trúc: [Khách kế →] chỉ enable sau finalize.
- Zalo-connect = 1 PATCH `custom_fields.zalo_connected` (khớp phase-01 mục 1b).

**Vòng đời draft (chống rác):** 1 draft mở duy nhất per (staff, party); mở lại cockpit → adopt draft cũ; draft có outcome mà quên chốt → auto-finalize khi bấm Khách kế; draft KHÔNG outcome → chip đỏ "phiên chưa chốt" trên worklist, 1 click resume/hủy. Không bao giờ tự bịa outcome.

**Tương thích ngược:** giữ `POST /customers/{id}/log-activity` cho M08 standalone — bên trong gọi create+patch+finalize qua cùng service. Không big-bang.

---

## IV. UX cockpit — Disposition Strip (outcome_bar v2, không modal)

Sticky đáy cockpit, 2 dòng, là fragment riêng (tôn trọng invariant S14: chỉ swap sub-region, không re-render `#s14-panel-root`):

```
┌────────────────────────────────────────────────────────────────────┐
│ [ghi chú nháp — autosave PATCH body............] [☑ Kết bạn Zalo]  │
│ [✓ Đã nghe] [✗ Không bắt] [☎ Bận] [⏳ Hẹn lại] [🚫 Từ chối] [☠ Sai số] │
└────────────────────────────────────────────────────────────────────┘
```

Bấm outcome → mở rộng inline NGAY DƯỚI pill (không modal):

| Outcome | Mở rộng inline | Số chạm điển hình |
|---|---|---|
| ✗ Không bắt / ☎ Bận | không có gì thêm → [Lưu & Khách kế →] | **2 chạm** |
| ☠ Sai số | đánh dấu identity invalid (nối A-S14-023) | 2-3 chạm |
| ⏳ Hẹn lại | chip giờ (mặc định +2h · chiều nay · mai sáng) + "tạo task nhắc" mặc định ✓ | 3 chạm |
| ✓ Đã nghe | reason pills (tùy chọn) + chip theo dõi +7/+14/+30 + [🛒 Đã mua → nhập mã đơn] | 2-4 chạm |
| 🚫 Từ chối | reason pills (bắt buộc, server enforce) + pill leo thang "🚫 Đừng gọi nữa" (`do_not_contact`, khớp phase-01 1c) | 3 chạm |

So với hiện tại (mở modal → 6 step → submit → văng timeline → mò về worklist ≈ 6-8 tương tác + mất ngữ cảnh ×2): **case phổ biến nhất của sprint (không bắt máy) còn đúng 2 chạm.**

Những gì biến mất khỏi luồng gọi vì **suy ra được** (đây là 40% form M08): hình thức (=call), kênh (=số đã bấm Gọi ở identity_bar, PATCH lúc tạo session), thời gian (=started_at), direction (=out). Talking-points tick + reason "đã nói" tick (A-S14-025) đã là cơ chế gom bulk-resolve sẵn có — finalize tiêu thụ set đó, không hỏi lại.

Nút `[⋯ Chi tiết]` cuối strip → mở M08 **pre-filled từ draft** (đơn liên quan, save-as-note, insight, sửa occurred_at) — M08 trở thành ngăn kéo nâng cao của cùng bản ghi, hết "compete".

### IV.b Bar không chật — state machine theo 3 pha (bổ sung 2026-07-10, thảo luận UX)

Lo ngại "bar chật" chỉ đúng nếu mọi phần tử tồn tại đồng thời — điều không xảy ra. Bar đổi nội dung theo pha (khớp 3 pha TRƯỚC/TRONG/SAU của spec S14):

```
T0 TRƯỚC (1 hàng ~52px):
│ [📞 Gọi 0983***35 ▾ số khác]                  [⋯ Ghi thủ công] │
   bấm 📞 = tạo draft + timer; [⋯] = mở M08 (ngoại lệ)

T1 TRONG (1 hàng — KHÔNG có outcome pills, chưa cúp máy chưa cần):
│ ⏱ 01:24 · [nháp autosave PATCH body…] ☑Zalo [■ Kết thúc] │

T2 SAU — disposition (2 hàng ~96px):
│ ⏱ 04:10 · "nháp đã gõ"                        [sửa nháp] │
│ [✓ Nghe][🛒 Mua][⏳ Hẹn lại][✗ Không bắt][☎ Bận][🚫 Từ chối][☠ Sai số] │
   pill cần thêm info → SHEET mọc LÊN TRÊN (~180px), pills thu về icon:
┌─ Lý do từ chối (bắt buộc) ─────────────────────────────────┐
│ [Còn hàng][Chờ KM][Giá][Không hợp][Kích ứng][Mua chỗ khác] │
│ [🚫 Đừng gọi nữa]                 [Lưu & Khách kế → (9/31)] │
├────────────────────────────────────────────────────────────┤
│ [✓][🛒][⏳][✗][☎][🚫•][☠]                                   │

T3 ĐÃ CHỐT (1 hàng):
│ ✓ Đã lưu: Từ chối (còn hàng) · 04:10      [Khách kế → 10/31] │
```

Lập luận không gian:
1. **Số đo:** 7 pill ≈ 700-750px; S14 desktop-only, full-width ≥1200px → 1 hàng dư chỗ. Cao tối đa (sheet mở) ~180px / viewport 800-1080px.
2. **Sheet che đúng thứ đã "chết":** sheet mọc lên che guardrails/trust_footer cột trái — thời điểm đó cuộc gọi đã kết thúc, script hết vai trò. Không gian tái phân bổ theo pha.
3. **Van xả:** màn hẹp → pills wrap 2 hàng; **phím tắt 1-7 chọn outcome + Enter = Lưu & Khách kế** (rep 50 call/tuần sống bằng bàn phím).

Phương án B đã cân nhắc — **takeover cột trái** (swap vùng talk_track thành panel disposition sau cúp máy, không gian vô hạn) — KHÔNG chọn vì: (a) mắt mất điểm neo cố định → phá muscle memory qua 50 call/tuần; (b) bar sticky là điểm kết thúc tự nhiên của luồng đọc; (c) re-render vùng lớn vs sheet chỉ là 1 fragment nhỏ (đúng invariant HTMX S14). Chỉ dùng nếu disposition phình field (mà không nên để phình).

Chi tiết chống-lỗi: **không auto-advance** sang khách kế sau lưu — [Khách kế →] to + Enter nhưng phải chủ động (rep cần thở/ghi thêm/khách gọi lại).

---

## V. Khi nào dùng form M08 riêng — quy tắc 1 câu

> **"Trong phiên gọi → không mở form. Ngoài phiên gọi → form."**

M08 standalone còn lại đúng các việc: (1) ghi bổ sung quá khứ (gọi bằng máy cá nhân hồi sáng, viếng thăm hôm qua — cần occurred_at lùi); (2) ghi email/FB/Zalo mang tính hành chính ngoài phiên; (3) sửa note / note-only (mode đã tách sẵn); (4) entry từ timeline C360, header hồ sơ. Giữ redirect về timeline cho các entry này — đúng ngữ cảnh của chúng.

**Quy tắc load dữ liệu (chốt 2026-07-10):** M08 mặc định luôn tạo bản ghi MỚI — **không bao giờ tự load "log gần nhất" để sửa** (anti-pattern: rep tưởng ghi mới hóa ra ghi đè lịch sử). Chỉ pre-fill khi trỏ đích danh: (a) `[⋯ Chi tiết]` từ cockpit → load DRAFT phiên hiện tại (2 view / 1 bản ghi); (b) `[sửa]` trên confirmation T3 hoặc ✏️ trên 1 dòng timeline → edit đúng activity đó. **Gap hiện tại: M08 chỉ có mode `edit_note`, chưa có `edit_activity`** — log sai outcome hôm nay không sửa được qua UI; P1 thêm mode này (dùng chính PATCH API) + chính sách: sửa tự do trong ngày (trước export 02:30 ICT), sau đó sửa phải ghi audit vào custom_fields để không làm mềm số liệu mart.

**Sửa chính M08 (hết tràn màn hình, làm được ngay không cần API mới):**
1. **Đảo thứ tự — outcome lên ĐẦU.** Hiện form bắt đầu bằng metadata (hình thức → kênh) rồi mới tới kết quả; nhưng outcome mới là field quyết định mọi section còn lại. Disposition-first.
2. Progressive disclosure: hình thức+kênh thu về 1 dòng compact đã điền sẵn (bấm mới mở); Step 5 (save-as-note) + insight + Step 6 (thời gian/đơn) gộp vào 1 accordion "Nâng cao" đóng mặc định.
3. Thêm 2 pill thiếu: `busy`, `wrong_number` (mục I.1).
4. Bỏ HX-Redirect khi được mở từ cockpit (trả fragment); giữ redirect khi mở từ timeline.

---

## VI. Lộ trình build (không block sprint gọi)

| Phase | Nội dung | Cỡ | Ghi chú |
|---|---|---|---|
| **P0 — trước ngày gọi đầu** | (a) thêm pill busy + wrong_number + purchased (enum mới); (b) outcome_bar bấm ✗/☎/☠ POST thẳng /log-activity với default (không modal — 3 case không cần note); (c) M08 đảo outcome-first + accordion "Nâng cao" | 1-2 ngày | không đổi API, ăn ngay 70% pain của sprint |
| **P1** | Draft + PATCH + finalize (mục III); cockpit tạo session lúc vào; duration tự đo | 3-5 ngày | mở khóa conversations_count không cần nhập tay |
| **P2** | Disposition strip đầy đủ (reason inline, hẹn-lại chip, Zalo connect, do_not_contact, Đã mua+mã đơn); M08 xuống vai ngăn kéo/ngoại lệ | 3-4 ngày | cập nhật spec S14 (outcome_bar v2) + spec M08 cùng commit |

Điều kiện kiến trúc xuyên suốt: mọi phase dùng chung ActivityService + side-effect executor (extract từ handler POST hiện tại — hiện 7 side-effect nằm rải trong handler 150 dòng); PATCH validate enum server-side theo `CONTACT_OUTCOMES_BY_CHANNEL_TYPE` sẵn có.

---

## Quyết định đã chốt (user, 2026-07-10)
1. **Draft tạo khi bấm nút Gọi** trên identity_bar (không tạo lúc mở cockpit, không lazy) — kênh/SĐT ghi luôn vào draft, không draft rác.
2. **"Đã mua" = thêm enum `purchased` VÀ vẫn ghi `related_order_code`.** Hệ quả kỹ thuật (bắt buộc làm cùng lúc, không được quên):
   - Thêm `"purchased"` vào `CONTACT_OUTCOMES_CALL` (`activity.py`) — không yêu cầu reason.
   - `purchased` là outcome DƯƠNG mạnh nhất: tính là reach + conversation; follow-up section hiện như answered; pill mở input mã đơn (khuyến khích, không bắt buộc).
   - **Mọi filter `contacts_reached` phải gồm `purchased`** — mart_staff_performance_weekly + bất kỳ dashboard nào đếm reach (đã đồng bộ vào plan 260709-1638 phase-00).
   - Nên thêm pill "🛒 Đã mua" vào M08 ngay ở P0 (rẻ, sprint đếm được đơn-từ-cuộc-gọi từ ngày 1, không cần chờ P2 strip).
3. **Đa kênh trong 1 phiên = 2 activity riêng** — chốt no_answer xong strip hiện nút phụ [＋Nhắn Zalo] (tái dùng A-S14-026); grain reach-rate kênh gọi sạch.
4. **Scope: P0 trước sprint (1-2 ngày), P1-P2 làm khi sprint đang chạy tuần 1-2.**

## Câu hỏi còn lại
- Tỷ lệ dùng thật của save-as-note/insight/visibility trong M08 — chờ 2 tuần data sprint (outcome_notes_count) rồi quyết cắt hẳn hay giữ trong accordion "Nâng cao".
