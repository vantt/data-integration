# Phase 05 — (Deferred) MISA budget/forecast scraper

## Trạng thái: DEFERRED
Chỉ làm nếu finance THỰC SỰ dùng module ngân sách/dự báo dòng tiền trong MISA (câu hỏi mở #3). Nếu không, CSV của ta (P4) là nguồn budget chính lâu dài — bỏ qua phase này.

## Mục tiêu
Đọc ngân sách + dự báo dòng tiền native của MISA → feed `fact_cashflow_budget` với `budget_source='misa'`, thay/bổ sung CSV thủ công.

## Context / ràng buộc (từ research)
- MISA AMIS CÓ module **Ngân sách** (lập kế hoạch thu/chi theo tháng/quý, theo phòng ban + nhóm) và **Dự báo dòng tiền** (chiếu thu/chi định kỳ + công nợ đến hạn).
- **KHÔNG có Open API cho budget** — chỉ export Excel/PDF hoặc scrape web (như pipeline ledger đang làm).
- Budget MISA granularity = **phòng ban/nhóm chi phí, không theo mã TK GL** → có thể lệch grain report; cần mapping.
- Nguồn: help.misa.vn ngân sách / dự báo dòng tiền.

## Requirements (khi kích hoạt)
1. Scraper web (tái dùng auth/cookie infra của `misa_*_web_downloader.py`) tải export ngân sách + dự báo dòng tiền.
2. Parser → chuẩn hóa về grain của `fact_cashflow_budget`; mapping phòng ban/nhóm MISA → `cashflow_line`.
3. Rows `budget_source='misa'`; report ưu tiên 'misa' > 'csv' hoặc filter chọn nguồn.
4. Dagster asset + schedule (theo tháng như ledger).

## Files (khi làm)
- `ingestion/src/misa_amis/misa_budget_web_downloader.py`
- `ingestion/run-misa-budget-download.py`
- parser + mapping seed `ref_misa_budget_line_mapping.csv`
- Dagster asset trong `orchestration/assets/misa_amis_assets.py`

## Rủi ro
- Granularity MISA (phòng ban) ≠ grain report (line/account) → mapping có thể mất mát/nhập nhằng.
- Scrape budget UI có thể khác luồng ledger (cần scout UI trước).
- Nếu finance không maintain budget trong MISA → data rỗng/cũ, tệ hơn CSV. Verify usage trước khi build.

## Điều kiện kích hoạt
- Xác nhận finance nhập budget đều trong MISA.
- Chấp nhận grain phòng ban/nhóm (hoặc có mapping rõ ràng sang line).
