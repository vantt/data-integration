# ui-spec content migration wave 1 — S01/S02/S03 report

**Date:** 2026-07-14 · **Plan:** `plans/260714-0757-ui-spec-content-migration-wave1/` · **Status:** DONE

## Shipped

**Schema/tooling (phát sinh có chủ đích):**
- `tabs` primitive nhận `actions: {label → action-id}` (per-tab contract) — cần cho S03 tab_bar 7 tab → 7 action (A-S03-004…018). Single-writer: `contentActionRefs` + `contentElementHasAction` mới trong `layout-schema.mjs`; renderer per-tab hoverable; chip-audit nhận actions map; docs §2b; test mới (9/9).
- GLYPH_MAP: thêm `＋`→`+` (cả `generate-ascii.mjs` + `ascii-normalize.mjs`, 2 bảng phải sync).
- CSS: `.wf-row > .wf-kpi` margin 14px — hết dính KPI ("8.2tr 3").

**Migration (xóa samples/elements, thay content + row_heights):**
- **S01**: sidebar nav, topbar CTA, kpi_strip 4 KPI, filter_bar (3 select + 2 input + 4 toggle mapped), task_list theo trục Đã Claim/Chưa Claim với 2 list lặp ghost + 8 btn quick-action mapped.
- **S02**: slot C01, search + 4 filter select, **table skeleton 6 cột × 5 dòng**, pagination + Tạo mới mapped.
- **S03**: `row_heights` main_col minmax(320px); tabs per-label actions; main_col = slot gạch chéo; 6 sidebar children (core_info/head_line KPI/contact/dates/tags) — chứng minh content trong child region chạy đúng (gridCellHtml route sẵn, không cần sửa renderer).

## Verification

- validate 0 error/0 warning (post-build); verify-runtime PASS (54 surfaces); npm test 28/28; unit tests 9+33+9 pass.
- chip-audit: 198 mapped/81 unmapped toàn corpus; **S01/S02/S03/S14 = 0 unmapped**.
- Vision QA 3 screenshot đạt checklist: table/list skeleton hiện mật độ, tabs ra tabs, slot rõ, KPI tách, diacritics sạch.

## Unresolved

1. Nút **"Nhận"** (Hàng Đợi Chung, `PATCH /tasks/{id}/assign-me`) có trong prose S01 + code nhưng contract CHƯA có interaction — hiện để dạng text trong list item. Cần quyết: thêm A-S01-024?
2. Tab mapped trong tab_bar render viền chip xanh (kế thừa `gc-inline-chip-mapped`) — đọc được nhưng hơi giống button; polish nếu anh thấy vướng khi review.
3. Còn 50 surface chưa migrate (81 unmapped còn lại nằm ở đó) — wave 2 đề xuất: M05/M08/M15 + P01.
4. Chưa commit (dồn 2 wave + upgrade schema đợi review).
