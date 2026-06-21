# Phase 04 — CS Surface trên S03 (Customer 360)

> Status: ⛔ BLOCKED (chờ P3)
> Phụ thuộc: P3 · Context: [`discussion.md`](./discussion.md) §11, §10

## Mục tiêu

Hiển thị cho CS trên màn hình S03: **mục tiêu cao nhất** + **việc cần làm tiếp theo** + lý do minh bạch + CTA nối thẳng M08. CS chủ động (gợi ý, không ép).

## Phạm vi (locked) — mở rộng panel P01

```
CALL_NOW · 💰 4.2tr
VIP · 45 ngày chưa mua · skincare 70%
[ Gọi ngay ]   [ 📅 Đặt lịch ]
```

- **[Gọi ngay]** → mở M08 unified contact log → CS ghi outcome → "Đã xử lý ✓" badge.
- **[📅 Đặt lịch]** → inline date picker → tạo `crm_task` (`source=action_queue`, `source_ref=action_id`) → badge chuyển thành "🗓 Đã lên lịch [ngày]".
- Sau khi log M08 thành công → hiện option **"Lên lịch theo dõi"** (date picker + quick-fill +7d/+14d/+30d).
- **[Bỏ qua]/[Hoãn]** ghi `crm_action_state` (chuẩn bị feedback loop P5).
- Reason hiển thị = chuỗi ghép từ 3 chặng (expandable) — phase sau khi P3 xong.

> **Quyết định UX:** xem `discussion.md §18`

## Related code files

- Sửa: `crm/src/adapters/inbound/web/screen_customer_360.py` + template panel P01 (HTMX fragment)
- Nối: M08 modal (Ghi nhận tiếp xúc)
- i18n: theo plan `260618-1050-crm-i18n-json-locale` (chuỗi VN)

## Todo (draft)

- [ ] **[Ưu tiên 1]** NBA card: thay "→ Tạo task" bằng [Gọi ngay] + [📅 Đặt lịch] inline — `c360_insight_panel.html`
- [ ] **[Ưu tiên 1]** M08: thêm "Lên lịch theo dõi" section cho positive outcomes (answered/met/replied) — `modal_log_activity.html`
- [ ] **[Ưu tiên 1]** Backend: handle `schedule_followup_at` trong `handle_log_activity` — `screen_customer_360.py`
- [ ] Panel "Mục tiêu cao nhất" + reason expander (chờ P3)
- [ ] Bỏ qua/Hoãn → crm_action_state (chờ P3)
- [ ] Phương án thay thế + signals strip (chờ P3)

## Success criteria

- CS mở 1 khách → thấy ngay mục tiêu + việc cần làm + lý do, không cần đọc số liệu thô.
- Mọi action có CTA hành động được; dismiss/snooze lưu state.

## Open

- UX chi tiết (vị trí trong P01 vs panel mới) — chốt khi P3 xong.
