# Phase 04 — Orphan-Actual Report

**Status:** NOT STARTED
**Depends on:** Phase 01 (account_code join)

## Context

Actual cash movement không match bất kỳ dòng budget nào (theo prefix-match, phase-01) hiện sẽ đơn giản không xuất hiện trong `mart_cashflow_budget_vs_actual` (join kiểu inner/left từ budget). Theo quyết định đã chốt (plan.md #9, khó khăn #1), các actual này cần **hiển thị riêng**, không âm thầm biến mất và không tự động gộp vào variance của dòng khác.

Nguồn gốc actual "mồ côi" — 2 loại, không phân biệt tự động (xem plan.md khó khăn #1):
1. Reserve/one_off spend rơi vào account chưa từng map (kỳ vọng, tự hết sau 1 tháng).
2. Account recurring thật sự bị bỏ sót, chưa từng có dòng budget nào cover (gap thật, cần review).

## Requirements

### 1. Mart mới — `mart_cashflow_unmapped_actuals.sql`

Grain: 1 row/(account_code, period_month, direction). Nguồn: `fact_cash_movement` LEFT JOIN toàn bộ budget account_code (mọi period_month có mặt trong seed, không chỉ tháng hiện tại) theo cùng logic prefix-match ở phase-01, giữ lại **chỉ những dòng KHÔNG có match** (actual_only).

```sql
WITH actuals AS (
    SELECT offset_account AS account_code, period_month, direction, SUM(amount) AS amount
    FROM {{ ref('fact_cash_movement') }}
    WHERE NOT is_internal_transfer AND offset_account IS NOT NULL
    GROUP BY 1, 2, 3
),
budget_codes AS (
    SELECT DISTINCT account_code, period_month, direction
    FROM {{ ref('seed_cashflow_budget') }}
    WHERE account_code IS NOT NULL AND account_code != ''
)
SELECT a.account_code, ga.account_name, a.period_month, a.direction, a.amount
FROM actuals a
LEFT JOIN budget_codes b
  ON  a.period_month = b.period_month AND a.direction = b.direction
  AND (a.account_code = b.account_code OR a.account_code LIKE b.account_code || '%')
LEFT JOIN {{ ref('dim_gl_account') }} ga ON ga.account_code = a.account_code
WHERE b.account_code IS NULL
```

Không filter theo materiality (không có ngưỡng "tiền nhỏ thì ẩn") — theo rule "no silent caps" (`.claude` global rule), mọi orphan hiện ra, dù nhỏ; finance tự quyết bỏ qua bằng mắt.

### 2. Hiển thị

**Chưa quyết** (xem plan.md §Câu hỏi mở #3) — 2 lựa chọn:
- (a) Tab/card riêng trong Metabase dashboard 114 (cùng chỗ Budget vs Actual) — cần thêm vào blueprint `docs/analytics-handbook/blueprints/metabase/finance_cashflow.md`.
- (b) Chỉ dừng ở mart, chưa gắn dashboard — chờ có dữ liệu orphan thật vài tháng để biết hình dạng thật (bao nhiêu dòng/tháng, số tiền lớn hay vụn) rồi mới thiết kế card đúng (bar? table?) thay vì đoán trước.

Đề xuất mặc định: (b) trước — dashboard hoá sau khi có dữ liệu thật, tránh thiết kế card cho 1 use case còn trừu tượng.

### 3. Không tự động phân loại reserve-spend vs gap thật

Không thêm cột "loại orphan" hay heuristic nào trong mart này — đúng quyết định plan.md khó khăn #1 (không tự suy diễn ý định). Nếu về sau finance muốn note lại 1 orphan là "đã biết, do mua X từ quỹ để dành" — đó là nhu cầu 1 cột ghi chú thủ công (Google Sheet riêng hoặc annotation Metabase), KHÔNG xây trong phase này (YAGNI — chưa có bằng chứng cần).

## Files

- **Create** `transformation/models/marts/finance/mart_cashflow_unmapped_actuals.sql`
- **Modify** `transformation/models/marts/finance/schema.yml` (hoặc file schema tương ứng thư mục `finance/`) — thêm test cơ bản (not null account_code, period_month)

## Tests / verify

- `dbt build --select mart_cashflow_unmapped_actuals` xanh.
- Query thủ công: actual account đã có budget cha → không xuất hiện trong mart này (đúng vì đã match).
- Query thủ công: actual account chưa từng có budget nào (dù cha hay con) → xuất hiện đúng.
- Verify tổng `SUM(amount)` của mart này + tổng `actual` trong `mart_cashflow_budget_vs_actual` = tổng `fact_cash_movement` (loại trừ internal transfer) — không có đồng nào bị đếm 2 lần hoặc mất.

## Risks & rollback

- Nếu Phase 01 đổi budget grain sai (double-count cha/con lọt qua vì phase-03 validation chưa chạy/bị bypass), mart này sẽ SAI theo hướng thiếu (actual bị match nhầm ở chỗ khác nên không rơi vào orphan) — coi đây như 1 kênh kiểm tra chéo cho phase-01/03, không chỉ là output cuối.
- Rollback: xoá mart mới, không ảnh hưởng gì khác (không có mart nào khác phụ thuộc ngược vào nó).
