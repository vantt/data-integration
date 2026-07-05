# Phase 03 — Sửa Scorecard lệch phạm vi (P1)

**Status: DONE** (2026-07-05) — 3 scorecards scoped to `coverage='both'`, new "Ngoài kế hoạch" card added, A3 table distinguishes coverage, deployed via `/deploy-metabase-blueprint` script. Verified: 192,445,945 (both) + 5,896,263,331 (actual_only) = 6,088,709,276 (old unscoped total) — no money lost. Bonus fix: corrected a pre-existing `🔘`/`📝` emoji mismatch in this blueprint that was silently corrupting all text-card positions.

## Vấn đề

Budget phủ 5/15 cashflow_line; mart có 54 dòng `coverage='actual_only'` (Thuế, tạm ứng, tồn kho, nội bộ...). Các card scorecard trong blueprint `finance_cashflow_budget.md` sum tất cả rows:

- "Tổng thực tế" (L165), "Chênh lệch" (L197), "Tỷ lệ thực hiện" (L229) — so kế hoạch 5 dòng với thực tế ~15 dòng → attainment % vô nghĩa, lộ ngay báo cáo T7 đầu tiên.

## Thay đổi (blueprint là source of truth — sửa blueprint rồi redeploy, KHÔNG patch tay Metabase)

**File:** `docs/analytics-handbook/blueprints/metabase/finance_cashflow_budget.md`

1. Card "Tổng thực tế", "Chênh lệch", "Tỷ lệ thực hiện": thêm `WHERE coverage = 'both'` (giữ filter `[[AND {{period_month}}]] [[AND {{cashflow_line}}]]`). Đổi description: "trong phạm vi kế hoạch".
2. **Thêm card mới** "Ngoài kế hoạch" (scalar): `SELECT COALESCE(SUM(actual_amount),0) FROM ... WHERE coverage = 'actual_only'` — để tiền ngoài plan không biến mất khỏi tầm nhìn.
3. Bảng chênh lệch (A3): thêm cột `coverage` hoặc sort `coverage='both'` lên trên — dòng actual_only hiển thị nhưng phân biệt rõ.
4. Bar chart A2: giữ nguyên (so theo line, lệch phạm vi tự hiển thị trực quan).
5. Cập nhật text card "Source Freshness BvA" caveats cho khớp scope mới.

## Deploy

Dùng skill `/deploy-metabase-blueprint` (memory: không patch manual). Layout thêm 1 card → điều chỉnh grid section A.

## Verify

- T7: "Tỷ lệ thực hiện" chỉ phản ánh 5 line có plan; "Ngoài kế hoạch" = tổng actual_only T7.
- Tổng: `both.actual + actual_only.actual` = tổng actual cũ (không mất tiền).
- Filter period/cashflow_line vẫn hoạt động trên card mới.

## Ghi chú thiết kế

Về dài hạn, cách sửa gốc là budget đủ các dòng vật chất (finance thêm dần vào sheet). Card "Ngoài kế hoạch" lớn bất thường = tín hiệu nên thêm line vào budget — ghi điều này vào description của card.
