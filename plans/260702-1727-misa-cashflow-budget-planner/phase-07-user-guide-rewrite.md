# Phase 07 — Viết lại User Guide khớp sheet thật (P0)

**Status: DONE** (2026-07-05) — §2/§4/FAQ rewritten to match the matrix sheet + auto-sync process; verified zero leftover "Download CSV"/"lưu đè seed" references; top-of-file note points to `validate-budget-sheet.gs` as source of truth.

## Mục tiêu

`docs/analytics-handbook/guides/finance-budget-user-guide.md` hiện mô tả sheet long-format + quy trình "download CSV → save đè seed" — sai với sheet matrix thật, làm theo sẽ fail. Viết lại toàn bộ §2 (Duy trì budget) + FAQ liên quan theo quy trình mới của phase-06.

## Phụ thuộc

Phase-06 xong (quy trình mới mới chốt được). Có thể draft song song, publish sau khi phase-06 E2E pass.

## Nội dung phải sửa

| Mục hiện tại | Vấn đề | Thay bằng |
|---|---|---|
| §2 Bước 1 — bảng cột long-format (`cashflow_line, period_month, direction=inflow/outflow...`) | Sheet thật là matrix: cột A–F + cặp `[Gợi ý Tx][Budget Tx]`; Chiều = Thu/Chi | Mô tả matrix layout đúng theo `.gs`; hướng dẫn "thêm tháng mới" = thêm cặp cột tháng (hoặc đã có sẵn 12 tháng) |
| §2 Bước 2 — "File → Download CSV → lưu đè seed" | Export matrix không load được vào dbt | Xóa hẳn. Quy trình mới: edit sheet → sync tự chạy 02:30 hàng đêm (hoặc lệnh manual 1 dòng cho refresh ngay) |
| §2 Bước 3 — docker exec + dbt seed/build | Finance không làm được; nightly build đã tự pick up | Ghi chú: chỉ cần khi muốn thấy số NGAY; còn lại T+1 tự động |
| FAQ "Thêm dòng tiền mới" | Nói thêm vào `__REF` là xong | Bổ sung: line mới phải tồn tại trong `dim_gl_account.cashflow_line` (taxonomy MISA) — thêm tự do vào `__REF` sẽ bị sync reject; quy trình = báo kỹ thuật thêm taxonomy trước |
| §4 Lịch vận hành | Khớp với lịch re-pull mới (phase-09): sổ MISA chốt ~ngày 10 → review variance sau ngày 10 | Cập nhật bảng lịch |

## Giữ nguyên

§1 (đọc dashboard), FAQ đọc-hiểu variance/reserve — đúng rồi.

## Verify

- Đưa guide cho 1 người không phải engineer làm theo từ đầu (hoặc tự walkthrough từng bước literal) — không bước nào chết.
- Mọi tên tab/cột trong guide khớp `.gs` constants (`BI_COL`, `AP_COL`, `TAB_*`).

## Risks

- Guide và `.gs` drift tiếp trong tương lai → thêm 1 dòng đầu guide: "Cấu trúc sheet: nguồn sự thật là `scripts/budget/validate-budget-sheet.gs`".
