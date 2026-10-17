---
phase: 5
title: "Quy trình restate: đổi luật kéo theo full-refresh phía sau"
status: pending
priority: P2
effort: "0.5d"
dependencies: [4]
---

# Phase 5: Quy trình restate

> **Yêu cầu bắt buộc của user (13/10/2026): làm tới đâu, thiết kế và tài liệu hoá chi tiết tới đó.** Tài liệu đi cùng commit với code.
>
> **Tài liệu phải cập nhật trong phase này:** `docs/operations/deployment.md` (mục mới "Đổi luật phân loại", ngay sau "Refactor deploys"); `docs/architecture/taxonomy-engine.md` (restate trong MVP: cơ chế, `ruleset_version`, giới hạn); `transformation/docs/TAXONOMY.md` §7 (cột "Khi đổi luật" của `int_customer_entry_attributes` trỏ tới quy trình); `transformation/AGENTS.md` mục "Classification rules" (đổi seed luật là thay đổi có đổi số, cần gate S và user duyệt).

## Mục tiêu

Restate là chế độ duy nhất của MVP: luật hiện hành áp cho mọi kỳ. Model `table`/`external` tự tính lại mỗi lần build; model incremental lưu nhãn thì không. Phase này viết quy trình bắt buộc để mỗi lần đổi luật sau pilot kéo theo full-refresh mọi model phía sau `lbl_<domain>`, và kiểm quy trình trên shadow. Pilot không đổi luật nên không chạy restate trên prod.

## Bối cảnh đã kiểm

- Model incremental duy nhất phụ thuộc giá trị `customer_type` của bản `dim_customers`: `transformation/models/core/marts/intermediate/int_customer_entry_attributes.sql` (lọc `WHERE customer_type = 'RETAIL'` L24, chỉ thêm khách chưa có L120–128). `dim_customers` là `external` nên tính lại toàn bộ (`TAXONOMY.md` §7).
- Phía sau bản blob (`fact_orders`, `int_customer_benchmarks`) có các model incremental đọc `fact_orders` (`int_customer_metrics`, `int_customer_discount_metrics`, `int_customer_entry_attributes`); chúng không lưu `scope_*` theo grep 14/10, nhưng quy tắc an toàn đơn giản là full-refresh **mọi** hậu duệ.
- Dagster không có job chạy `dbt build --full-refresh`: `pipeline_batch_fullrefresh_job` (`orchestration/definitions.py` L111–115) chỉ đặt tag `full_refresh` để connector reset cursor (`orchestration/connectors/sapo_v2/assets.py` L97–98); asset dbt luôn gọi `dbt build` (`orchestration/assets/dbt.py` L133).
- Gate S bước 7 chạy full-refresh hai bên rồi so golden, nên mọi thay đổi luật đi qua gate S đã được kiểm nhánh incremental.

## Quy trình đổi luật (nội dung mục mới trong `deployment.md`)

1. Sửa seed luật trên nhánh; chạy `check_taxonomy_rules.py`.
2. Shadow: `gate.sh S --allow-code-change`. Golden **sẽ** báo khác biệt (đây là thay đổi có đổi số); đọc `keyed-diff`, lập danh sách bảng/cột/số khoá đổi, cộng `monitor_taxonomy_unmapped` trước và sau.
3. User duyệt danh sách đổi (bắt buộc; quy tắc "không đổi số trừ khi được duyệt rõ").
4. Deploy theo runbook "Refactor deploys" bước 1–4 (chụp schedule, dừng `data_platform`, commit seed đang sống, fast-forward).
5. Trước khi start lại, full-refresh phía sau domain trong một container chạy một lần cùng mount với `data_platform` (container chính đang dừng nên không tranh khoá DuckDB): `dbt build --select lbl_<domain>+ --full-refresh`. Lệnh `docker compose run` chính xác (entrypoint, thư mục làm việc, biến môi trường dbt) chốt ở bước 2 của phase này. [UNVERIFIED]
6. Start, kiểm như runbook bước 6–7; ghi `ruleset_version` mới (đọc từ `monitor_taxonomy_parity_log`).
7. Không làm trong khung 02:30–04:00.

## Files

- Modify: `docs/operations/deployment.md` — mục "Đổi luật phân loại".
- Modify: `docs/architecture/taxonomy-engine.md`, `transformation/docs/TAXONOMY.md` §7, `transformation/AGENTS.md`.
- Không có file code.

## Các bước

1. Viết mục runbook như trên.
2. Xác định lệnh chạy dbt một lần trên prod: đọc `docker-compose.yml` (service `data_platform`: image, volume, `working_dir`, env) và lệnh start (chạy `dbt deps` và `dbt parse` trước `dagster dev`, theo runbook bước 5) để viết lệnh `docker compose run --rm --no-deps data_platform <lệnh dbt>` đúng thư mục `transformation/` và profile. Thử lệnh đó trên shadow bằng `run-shadow.sh` (cùng image) với một thay đổi luật giả.
3. Diễn tập trên shadow với `--vars '{taxonomy_engine_customer_type: true}'` ở mọi lệnh dbt (khi biến tắt, `lbl_customer_type+` không chứa mart nào nên quy trình chỉ có nghĩa sau khi chuyển cột), với một thay đổi luật giả, không commit: đổi priority để một nhóm khách đổi nhãn; build thường (không full-refresh) thấy `int_customer_entry_attributes` giữ nhãn cũ; chạy `dbt build --select lbl_customer_type+ --full-refresh` thấy bảng đó khớp với lần build từ đầu (so bằng `golden_snapshot.py keyed-diff` hoặc `EXCEPT`). Ghi kết quả vào commit message của phase.
4. Commit tài liệu.

## Verification

- Gate: `scripts/shadow/gate.sh M` (chỉ tài liệu; mọi bước pass).
- Diễn tập bước 3: không full-refresh thì lệch, có full-refresh thì 0 khác biệt so với build từ đầu.

## Đổi số?

**Không.** Chỉ tài liệu; diễn tập trên shadow và không commit thay đổi luật.

## Rollback

Revert commit tài liệu.

## Rủi ro

| Rủi ro | Giảm thiểu |
|---|---|
| Người đổi luật quên full-refresh | Runbook là đường duy nhất lên prod; `AGENTS.md` ghi bắt buộc; gate S đã kiểm nhánh incremental trước deploy |
| Full-refresh kéo dài thời gian dừng container | Gate S full-refresh mất khoảng 2–3 phút trên shadow; dự trù gấp đôi trên prod; chọn giờ thấp điểm ngoài 02:30–04:00 |
| Restate đổi số các kỳ đã dùng để chốt thưởng | Câu hỏi mở 4 của `plan.md` phải có câu trả lời trước lần đổi luật đầu tiên |

## Effort

0.5 ngày.
