# ui-spec content migration wave 2 — M05/M08/M15/P01 + A-S01-024 report

**Date:** 2026-07-14 · **Plan:** `plans/260714-0822-ui-spec-content-migration-wave2/` · **Status:** DONE

## Shipped

**Item 1 (approved):** `A-S01-024` btn_claim_task — nút "Nhận" (Hàng Đợi Chung, `PATCH /tasks/{id}/assign-me`) vào contract S01 + content (btn primary, row move về Đã Claim).

**Item 2 — migrate 4 surface** (xóa samples/elements → content):
- **M05**: form tạo task đầy đủ — input tiêu đề, 4 select (khách/loại việc/priority/assignee), badge "ẩn khi máy chắc" (progressive disclosure), due date/giờ, actions Hủy/Lưu primary.
- **M08**: form log 6 bước — badge task context, select hình thức, chips SĐT, 4 outcome pill (đều map A-M08-005), reason chips (6 giá trị D2), textarea NỘI DUNG (ghi chú irritation-required), checklist 4 toggle, time inputs, floating contact_pref_banner.
- **M15**: tabs per-label actions (3 tab → A-M15-002/003/004), list kênh liên lạc ×3, nút vô hiệu/thêm kênh.
- **P01**: checklist action-queue (mode A session), purchase-context chips, 3 CTA; RFM 3 KPI + 3 segment badge; value metrics 2 hàng KPI (LTV hero); signals; rep insights list + 3 nút; freshness bar. (File có sửa đổi uncommitted sẵn của user — chỉ thay block samples/elements.)

## Verification

- validate 0 error/0 warning post-build; verify-runtime PASS (54 surfaces); npm test 28/28.
- chip-audit: 198 mapped / 58 unmapped toàn corpus — **M05/M08/M15/P01 vắng mặt trong unmapped body** (sạch); 58 còn lại thuộc surface chưa migrate.
- Vision QA M08 + P01 đạt checklist (form idioms, checklist, KPI grid, floating banner, diacritics).

## Tiến độ migrate tổng

Done: S01 S02 S03 S14 M05 M08 M15 P01 (8/54). Còn ~46 surface trên samples (58 unmapped nằm ở đó).

## Unresolved

1. Wave 3 chưa lên lịch — ứng viên: S15 Task Detail, S07 Tasks Board, M16, P02–P06, các overlay.
2. Chưa commit — dồn schema upgrade + wave 1 + wave 2 chờ anh review (nhắc: S14/P01 có sửa đổi uncommitted của anh trộn trong cùng file spec).
