---
phase: 5
title: "Thí điểm Weekly Pulse trên Evidence: so số tự động, 4 chu kỳ tuần đã đóng liên tiếp, tin tóm tắt cho người dùng thật"
status: pending
priority: P1
effort: "1d công + 4 tuần lịch"
dependencies: [4]
---

# Phase 05: Thí điểm Weekly Pulse

> **Yêu cầu bắt buộc của user (13/10/2026): làm tới đâu, thiết kế và tài liệu hoá chi tiết tới đó.** Trước khi code: ghi phương pháp so số (mốc, `as_of`, dung sai, cổng) vào `analytics/README.md`. Trong lúc làm: kết quả mỗi chu kỳ ghi vào sổ thí điểm ngay khi có.
>
> **Tài liệu phải cập nhật trong phase này:** `analytics/README.md` (mục "So số"); `plans/261014-2225-report-productization/pilot-log.md` (sổ thí điểm: mỗi ngày một dòng kết quả, mỗi chu kỳ một kết luận); `orchestration/reports/README.md` (job so số); `docs/analytics-handbook/playbooks/ceo_weekly_pulse.md` (ghi bản Evidence là bản chính sau khi đạt).

## Mục tiêu

Chứng minh trên dữ liệu thật rằng chuỗi registry → spec v2 → renderer Evidence → build sau nightly ra **đúng số của dashboard đang chạy**. Cổng nghiệm thu: **cả 30 card khớp; 4 chu kỳ tuần đã đóng liên tiếp khớp, trong đó có một lần qua ranh giới tháng** (thiết kế §7, quyết định 3). Đồng thời so với trang Evidence Weekly Pulse cũ (`evidence/pages/ceo-weekly-pulse/index.md`) để giải thích mọi khác biệt của bản cũ.

## Phương pháp so số

- **Mốc:** SQL của 30 question trong blueprint đang chạy (hoặc bản capture nếu phase 02 thấy lệch). Trích bằng chính `markdown_parser` (`node` script `analytics/compare/dump_blueprint_ir.js` gọi `.skills/metabase-automation/lib/markdown_parser.js`) ra `analytics/compare/baselines/ceo_weekly_pulse.json`, kèm sha256 của file blueprint; harness từ chối chạy khi blueprint đổi mà baseline chưa sinh lại.
- **Thời điểm:** thay `current_date` trong SQL mốc bằng `DATE '<as_of>'` (cửa sổ mốc thành `[đầu tuần của as_of, as_of + 1 ngày)`, tức dữ liệu đến hết `as_of`) và `now()` (3 chỗ) bằng `TIMESTAMP '<as_of> 23:59:59'`, sao cho cửa sổ mốc trùng cửa sổ bản Evidence có `as_of` = hôm qua. Harness dừng với lỗi nếu SQL có hàm thời gian khác (`current_timestamp`, `today()`…). Vào sáng thứ Hai, `as_of` = Chủ nhật: tuần đến nay là trọn tuần vừa đóng và kỳ so là trọn tuần trước (`ceo_weekly_pulse.md:95-104`), đúng "chu kỳ tuần đã đóng".
- **Dữ liệu:** cả hai bên chạy trên **cùng một bản chụp** (chép catalog `olap.duckdb` một lần, mở `read_only`), cách nhau vài giây.
- **Bên mới:** SQL đã biên dịch của từng card (chính là source của trang) với `as_of` literal, cộng một kiểm tra rằng file source trong bản build hiện tại có cùng hash với SQL đã biên dịch.
- **So:** theo cặp `card_id` ↔ `baseline_name` (phase 02). Số nguyên và chuỗi: bằng tuyệt đối. Số thực (AOV, tỉ lệ): sai số tương đối ≤ 1e-9. Thứ tự dòng: sắp theo khoá khai báo. Card meta (chu kỳ báo cáo, độ tươi): so chuỗi kỳ hiển thị.
- **Trang Evidence cũ:** chạy 11 truy vấn của trang cũ cùng `as_of`; khác biệt chỉ ghi lại và giải thích (bản cũ gộp KPI, thiếu khối Profitability), không chặn cổng.

## Hàng rào trong lúc thí điểm

- Không một lần ghi nào vào Metabase (dashboard Weekly Pulse cũ giữ nguyên tới phase 14).
- Trang mới ở khu vực `dieu-hanh`, chỉ nhóm thử nghiệm có tài khoản cho tới khi chu kỳ 1 khớp.
- Harness chạy mỗi ngày sau build (job `report_compare_job` trong `orchestration/reports/compare.py`), lưu `app_data/data_lake/report_build/compare/<as_of>.json`; lệch → thẻ Lark kênh cảnh báo. Không dựa vào xem bằng mắt.
- Không deploy thay đổi taxonomy làm đổi nhãn mà Weekly Pulse lọc trong thời gian so (thiết kế bộ máy phân loại chạy song song được, miễn không đổi `scope_sales`).
- Nếu session khác deploy sửa lỗi `channel_net_profit` trong lúc thí điểm: hai bên vẫn đọc cùng cột mart nên vẫn so được; ghi ngày deploy vào sổ thí điểm vì số Net Profit đổi giữa các chu kỳ.

## Tin tóm tắt (quyết định 6)

Sau khi chu kỳ 1 khớp: chuyển `message.channels` của Weekly Pulse từ kênh thử sang nhóm chat do user chỉ định; thẻ chi phí chỉ vào nhóm có `can_view_cost: true`. Gửi sáng thứ Hai sau build. Kênh Zalo/Telegram để Đợt 8.

## Các bước

1. Viết harness `analytics/compare/` (CLI `python -m analytics compare --report ceo_weekly_pulse --as-of YYYY-MM-DD`) và job Dagster; test với **mốc so với chính nó** (SQL blueprint so SQL blueprint) phải khớp 100% trước khi so bản mới (hội đồng ops §8.1).
2. **Backtest** trên 4 tuần đã đóng trong quá khứ (có ranh giới tháng) để sửa lệch sớm. Mỗi lệch: tìm nguyên nhân (registry, compiler, spec), sửa, ghi vào sổ. Tối đa 2 vòng sửa cho mỗi chỉ tiêu (điều kiện dừng).
3. Deploy job so số (runbook `data_platform`, giờ user duyệt).
4. Chạy thật 4 thứ Hai liên tiếp. Chu kỳ nào lệch thì đếm lại từ đầu sau khi sửa.
5. Người dùng chính của Weekly Pulse xem bản mới và đồng ý (ghi tên, ngày).
6. Đóng thí điểm: cập nhật playbook, báo user kết quả và đề xuất chuyển người dùng sang bản Evidence (phần tắt bản Metabase làm ở phase 14 cùng các report định kỳ khác).

## Files

- Tạo: `analytics/compare/{__init__,harness}.py`, `analytics/compare/dump_blueprint_ir.js`, `analytics/compare/baselines/ceo_weekly_pulse.json` (sinh ra), `orchestration/reports/compare.py`, test tương ứng, `plans/261014-2225-report-productization/pilot-log.md`.
- Sửa: `tenants/fine_japan/analytics/profile.yml` (kênh tin thật), `analytics/README.md`, `orchestration/reports/README.md`, `docs/analytics-handbook/playbooks/ceo_weekly_pulse.md`.

## Verification (cổng nghiệm thu)

- 4 file `compare/<as_of>.json` của 4 Chủ nhật liên tiếp: 30/30 card `match`; ít nhất một tuần có ngày đầu và ngày cuối khác tháng, hoặc `as_of` là ngày cuối tháng.
- Render và build lại trên cùng bản chụp ra cùng hash (tất định).
- Không có ghi nào vào Metabase trong thời gian thí điểm (kiểm `updated_at` của dashboard Weekly Pulse cũ và các card của nó trước/sau).
- Tỉ lệ card `inline_sql` ≤ 30%.
- Công sức phase 00–05 ≤ 24 ngày công.

## Điều kiện dừng (một điều đúng là dừng)

Builder/job ghi ra ngoài thư mục của nó hoặc có ghi vào Metabase; một chỉ tiêu vẫn lệch sau 2 vòng sửa mà không giải thích được bằng quyết định đã duyệt; > 30% card cần `inline_sql`; công sức vượt 24 ngày công; sự cố prod truy được về việc này; render/build lại vẫn ra kết quả khác. Khi dừng: FJ giữ blueprint Metabase và trang Evidence cũ; khu vực `dieu-hanh` gỡ khỏi `report_site`; công cụ chỉ dùng cho khách mới; báo cáo nguyên nhân cho user trước khi làm tiếp.

## Đổi số?

Không. So số; không đổi dashboard nào.

## Rollback

Tắt job so số và tin (stop sensor/schedule trong Dagster UI), gỡ khu vực khỏi hồ sơ rồi sinh lại `Caddyfile`. Không có dữ liệu nào bị đổi.
