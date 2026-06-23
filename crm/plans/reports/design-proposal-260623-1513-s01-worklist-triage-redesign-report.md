# S01 Worklist — Triage Redesign Proposal

**Date:** 2026-06-23 · **Surface:** S01 Worklist/Dashboard · **Status:** proposal (design-confirmed, pre-plan)
**Problem:** màn hình "over" — quá nhiều item, rep ngợp. Focus: sắp xếp / filter / trình bày.

---

## 1. Chẩn đoán gốc rễ (verified)

| # | Vấn đề | Bằng chứng |
|---|--------|-----------|
| a | Không LIMIT / không phân trang — đổ toàn bộ AQ + task mở | `screen_worklist.py:66-113` `_load_worklist_data` gọi `list_all_action_queue()` + `list_tasks("","open")` |
| b | Không sort thật — 2 vòng lặp phẳng nối tiếp theo thứ tự DB | `worklist_fragment.html:81` (actions) rồi `:181` (tasks); spec hứa sort due_at+priority (`S01` dòng 19) |
| c | Mọi dòng cùng trọng số thị giác, không phân nhóm | template không có grouping; C03 spec nói màu theo urgency nhưng impl chỉ đổi badge |
| d | **Bug: filter "Người nhận" chết** — `filter_assignee` nhận vào nhưng không dùng | `_load_worklist_data` thân hàm không tham chiếu `filter_assignee`; `list_tasks("","open")` bỏ qua. AQ vốn không có cột owner |
| e | Trộn 2 loại việc khác bản chất; dấu ✓ nghĩa ngược nhau | action ✓ = dismiss (`:89`); task ✓ = done (`:191`) |

### Data lifecycle (verified — đổi cách thiết kế ranking)

`upsert_action_queue` (`sqlite_upsert.py:118-174`) = **signal-based full replacement**:
- Upsert batch hôm nay → rồi `DELETE ... WHERE (customer_key,action_type) NOT IN (batch)` (`:162-170`).
- `generated_date` cập nhật mỗi ngày (`:134`); `pending_since` giữ nguyên (`:139`).

**Hệ quả:** AI action còn trong list ⇒ warehouse vẫn tái khẳng định valid tới sync gần nhất. Action hết valid (KH đã mua/churn) → warehouse ngừng phát → CRM xoá ở sync kế. ⇒ **Không có "zombie action quá hạn" tích tụ ở layer data.** `pending_since` = độ *dai dẳng* (bị bỏ quên), KHÔNG phải deadline. Staleness thật chỉ xảy ra khi *sync ngừng chạy* (`today−generated_date` tăng) — đã có `is_stale>24h` badge xử lý mức màn hình.

→ **Tách 2 chế độ vòng đời:**
- **AI action (`wh_action_queue`)**: tự dọn. Validity do warehouse quyết. KHÔNG xây per-type expiry phía CRM (YAGNI — tránh double-count, tránh giấu action warehouse còn endorse).
- **Task thủ công (`crm_task`)**: có `due_at` thật, KHÔNG bị signal-replace → overdue thật & treo mãi tới done/cancelled. **Đây mới là chỗ "quá hạn không còn valid" thực sự.**

---

## 2. Design decisions đã chốt

- Nhóm theo **băng urgency (deadline-driven)**, không nhóm theo action_type.
- Ngưỡng neglect: **`pending_since ≥ 7 ngày`**, **1 ngưỡng chung** mọi action_type.
- Action treo lâu → Băng 3 *collapse*, **không auto-mutate** (rep tự xử).
- Task overdue → Băng 0, **luôn hiện**, chỉ "Dời hạn / Dọn" thủ công (không auto-snooze cam kết người).

---

## 3. Mô hình ranking (A1) — băng theo deadline TRƯỚC, priority/value TRONG băng

Thay "priority đơn thuần" bằng **urgency = áp lực thời gian × priority** để task low-priority *sắp breach due_at* không bị task high-priority *không bó thời gian* chôn.

**Gán băng (xét theo thứ tự, dừng ở match đầu):**
1. Task thủ công & `due_at < hôm nay(ICT)` → **Băng 0 🔴 Quá hạn**
2. `due_at = hôm nay` HOẶC `priority=urgent(2)` HOẶC `snoozed_until ≤ hôm nay` (vừa thức) → **Băng 1 ⏰ Hôm nay/Khẩn**
3. Action & `pending_since ≥ 7 ngày` (không urgent) → **Băng 3 💤 Treo lâu** (collapse)
4. Còn lại → **Băng 2 📋 Trong hạn**

**Sort trong băng:**
| Băng | Sort |
|------|------|
| 0 Quá hạn | quá hạn lâu nhất trước (`due_at` asc) → value↓ |
| 1 Hôm nay/Khẩn | priority↓ → value↓ → action_type tier |
| 2 Trong hạn | priority↓ → value↓ → action_type tier → `pending_since` asc (nhẹ) |
| 3 Treo lâu | value↓ (rep ghé vào thì giá trị cao trước) |

**action_type tier (tie-break):** `CALL_NOW > WIN_BACK > UPSELL ≈ CROSS_SELL > REORDER_NUDGE > COLLECT_FEEDBACK`

**Neglect nudge:** trong Băng 2, action `pending_since` 1–6 ngày hiện badge mờ "đã chờ N ngày" (nhắc nhẹ, chưa demote).

> Trả lời lo ngại: deadline lái item lên Băng 0/1 ⇒ item giá trị nhỏ nhưng *sắp/đã quá hạn* không bị priority cao chôn. Overdue không tự biến mất (cam kết người) nhưng gom riêng + nút dời hạn. Action treo lâu không nag vô hạn → rớt Băng 3.

---

## 4. Filter (B)

| Ưu tiên | Filter | Ghi chú |
|---------|--------|---------|
| 🔴 | Sửa "Người nhận" chết + gắn owner thật | cần owner per-customer (xem Open Q) |
| 🔴 | Lọc `action_type` (multi-select chips) | "sáng nay chỉ gọi" |
| 🟡 | Ô tìm tên KH / SĐT | |
| 🟡 | Toggle "Chỉ giá trị cao" (≥ ngưỡng) | |
| 🟢 | Active-filter count + "Xóa filter" | C05 spec đã hỗ trợ, chỉ chưa render |

Tất cả filter giữ trong URL query (đúng pattern HTMX hiện tại) để bền qua refresh/SSE.

**Sort dropdown (cho user override default):** Đề xuất (banding) · Giá trị cao nhất · Sắp đến hạn · Theo loại — `?sort=...`.

---

## 5. Trình bày (C) — trị "ngợp"

1. **Băng collapsible + đếm số.** Băng 0/1/2 mở sẵn; Băng 3 collapse sẵn. Đòn bẩy giảm tải lớn nhất.
2. **Cap ~10 dòng/băng + "Xem thêm (N)".**
3. **Phân cấp thị giác theo băng:** viền trái màu (coral Băng 0/1, mặc định Băng 2, mờ Băng 3).
4. **Thanh tiến độ "Đã xong 3/15".**
5. **Tách control:** action = "✕ Bỏ qua"; task = checkbox done (đừng dùng chung ✓).
6. KPI strip: sửa lệch hiện tại (value_total chỉ tính actions, p1_count chỉ tính tasks) → tính nhất quán trên list gộp.

### Wireframe

```
┌─ Việc cần làm hôm nay ───────────── [↻ Làm mới] [+ Tạo task] ┐
│ [Mở 32] [Giá trị 84.2tr] [Khẩn 3]   ▓▓▓░░ Đã xong 3/32        │
│ 🔎 Tìm KH...  Loại:[Gọi][Mua lại][Upsell]  Sắp xếp:[Đề xuất▾] │
│ Người nhận:(Của tôi)(Tất cả)  Ưu tiên:(All)(Cao)(Khẩn) ✕Xóa   │
│──────────────────────────────────────────────────────────────│
│ 🔴 QUÁ HẠN (2)                                            ▾   │
│  ┃ Task  Gọi lại anh C   quá hạn 3 ngày     [Dời hạn][Dọn][360]│
│ ⏰ HÔM NAY / KHẨN (3)                                     ▾   │
│  ┃ CALL_NOW  Nguyễn Văn A  💰2.4tr          [Gọi][⏰][360]    │
│ 📋 TRONG HẠN (24)                             Xem thêm    ▾   │
│  │ WIN_BACK  Trần Thị B  💰1.8tr · đã chờ 3 ngày [Gọi][⏰][360]│
│ 💤 TREO LÂU (8)                                           ▸   │
│──────────────────────────────────────────────────────────────│
│ Cache cập nhật 07:15 ICT ✓                                    │
└──────────────────────────────────────────────────────────────┘
```

---

## 6. Effort tiers

- **Quick wins (không đổi schema):** ranking banding server-side · sửa filter assignee chết · collapse+count+cap+"xem thêm" · tách dismiss/done · progress bar · sửa KPI. → ~80% cảm giác "over".
- **Vừa:** filter action_type · search · sort dropdown · value threshold.
- **Lớn (cần data):** owner per-customer cho "Của tôi" đúng nghĩa · phân trang server thật.

Banding tính ở `_load_worklist_data` (Python, server-rendered) — dùng ICT cho mốc "hôm nay" (nhất quán với pipeline TZ; tránh sai biên 0h–7h).

---

## Open questions

1. **Owner data:** có `owner` per-customer trong CRM chưa? Nếu chưa → tạm ẩn filter "Của tôi" tới khi có owner model (Quick wins không phụ thuộc cái này).
2. **Cap N/băng:** 10 ok? Băng 3 có cap riêng (vd 5) không?
3. **Snoozed/dismissed actions:** reader hiện có lọc `status != dismissed/snoozed` trước khi render chưa? (cần verify `list_all_action_queue` để Băng 1 "vừa thức" hoạt động đúng) — chưa kiểm trong vòng này.
4. Triển khai: làm thẳng **Quick wins** trước, hay viết full plan đa-phase rồi mới code?
