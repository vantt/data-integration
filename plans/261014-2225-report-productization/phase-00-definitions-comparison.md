---
phase: 0
title: "Bảng so sánh định nghĩa 3 nguồn (metrics.md, Rill, blueprint); mỗi chỗ lệch là một quyết định riêng"
status: pending
priority: P1
effort: "1.5d"
dependencies: ["Đợt 1 phase 7"]
---

# Phase 00: Bảng so sánh định nghĩa

> **Yêu cầu bắt buộc của user (13/10/2026): làm tới đâu, thiết kế và tài liệu hoá chi tiết tới đó.** Trước khi làm: ghi phạm vi và cách so vào mục "Analytics (report)" mới của `docs/architecture/modules.md`. Trong lúc làm: bảng so sánh và sổ quyết định được cập nhật cùng lúc với từng lần đối chiếu, không dồn về cuối.
>
> **Tài liệu phải cập nhật trong phase này:** `plans/261014-2225-report-productization/definitions-comparison.md` (bảng so sánh, bản ghi trạng thái), `plans/261014-2225-report-productization/definition-decisions.md` (sổ quyết định, mỗi chỗ lệch một dòng), `docs/architecture/modules.md` (mục "Analytics (report)": mục đích, ranh giới, nguồn sự thật tương lai là registry), `docs/analytics-handbook/semantic/metrics.md` (chỉ thêm banner trỏ tới bảng so sánh và nói registry sẽ là nguồn chuẩn).

## Mục tiêu

Trước khi viết registry, biết chính xác mỗi chỉ tiêu đang được tính thế nào ở ba nơi và chỗ nào ra số khác nhau. Mỗi chỗ lệch là một quyết định có đổi số, user duyệt riêng; người làm registry không tự chọn (thiết kế §4 ①, "Bước 0 bắt buộc").

Phase này **không đổi code và không đổi số**. Nó sinh hai tài liệu và một danh sách quyết định chờ user.

## Nguồn đối chiếu

| Nguồn | Vị trí | Ghi chú |
|---|---|---|
| Văn bản | `docs/analytics-handbook/semantic/metrics.md` (2612 dòng, ~56 chỉ tiêu), `semantic/rules.md`, `semantic/segments.md` | Có quy ước ngầm (scope, VAT, US) |
| Rill | `rill/metrics/*.yaml` (~53 measure), `rill/models/orders_enriched.sql` | `orders_enriched.sql:79-83` tự tính lại `scope_*` (lỗi đã biết) |
| Blueprint đang chạy | `docs/analytics-handbook/blueprints/metabase/*.md` (45 file), ưu tiên `ceo_weekly_pulse.md` (30 question) | Mốc là blueprint đã deploy, không phải design spec (thiết kế §7) |
| Cột mart | `transformation/models/core/marts/sales/fact_orders.sql:182-186` (`gross_revenue` gồm VAT, `net_revenue` = `total_amount − vat_amount`), `fact_order_economics.sql`, `fact_order_returns.sql`, `core/marts/fact_targets.sql` | Mart là nơi định nghĩa thật; ba nguồn trên là cách đọc nó |

## Các bước

1. Lập danh sách chỉ tiêu: hợp của id trong `metrics.md`, tên measure Rill, và cột/biểu thức xuất hiện trong SQL của blueprint (grep `SUM(`, `COUNT(`, tên cột tiền). Ghép các tên khác nhau cùng nghĩa vào một dòng.
2. **Làm trước nhóm Weekly Pulse** (phase 01 cần): mọi chỉ tiêu mà 30 question của `ceo_weekly_pulse.md` dùng, gồm cả quirk đã biết: `Total Orders` chỉ lọc `scope_sales`, không lọc `is_active_order`, trong khi doanh thu có lọc (hội đồng tooling §1); "MTD GMV vs Target" có `goal = 600,000,000` cứng trong viz.
3. Với mỗi chỉ tiêu, ghi 3 cột định nghĩa (biểu thức, bộ lọc, trục thời gian, xử lý NULL, mẫu số nếu là tỉ số) và cột "lệch?".
4. Với mỗi chỗ lệch, đo **số mẫu** trên một bản chụp chỉ đọc (chép file catalog `app_data/data_lake/serving/olap.duckdb` sang thư mục tạm rồi mở `read_only`, cùng cách container Evidence đang làm): tháng đã đóng gần nhất và tuần đã đóng gần nhất, giá trị theo từng định nghĩa và chênh lệch tuyệt đối/tương đối.
5. Ghi vào `definition-decisions.md` một dòng cho mỗi chỗ lệch: mô tả, số mẫu, các lựa chọn, đề xuất, "đổi số FJ?" (có/không, dashboard nào bị ảnh hưởng), trạng thái `chờ user`. Không gộp nhiều chỗ lệch vào một dòng.
6. **Bảng đổi tên** theo quyết định 1: tên cũ → id mới → số mẫu, tối thiểu: `net_revenue` (mart, metrics.md, Rill) → `net_sales`; `refund_amount`/`return_amount` → `returns_amount`; `net_revenue` mới (= `net_sales − returns_amount`) là id mới, chưa có ở đâu. Bảng này là đầu vào cho trường `legacy_names` của registry (phase 01).
7. **Hai lỗi số đã biết** (Rill `scope_*`, `channel_net_profit` dùng `COALESCE(cogs_amount, 0)`): chỉ ghi một dòng tham chiếu "đang sửa ở session thực thi sau Đợt 1, qua gate S" kèm trạng thái lúc ghi. Không đề xuất sửa lại, không đo lại.
8. Gửi user danh sách quyết định theo nhóm (Weekly Pulse trước). Phase 01 chỉ cần quyết định của nhóm Weekly Pulse; các nhóm khác có thể chốt muộn hơn, trước phase 10.

## Quy tắc khi user chưa chốt

Registry ở phase 01 **tái tạo đúng định nghĩa blueprint đang chạy** cho mọi chỉ tiêu Weekly Pulse (để thí điểm so được 0 lệch), bất kể quyết định cuối. Quyết định đổi số đã duyệt chỉ được áp ở phase 09, sau khi thí điểm đóng, mỗi quyết định một commit, qua gate S, kèm danh sách dashboard/card bị đổi số đã được user duyệt.

## Files

- Tạo: `plans/261014-2225-report-productization/definitions-comparison.md`, `plans/261014-2225-report-productization/definition-decisions.md`.
- Sửa: `docs/architecture/modules.md` (mục mới), `docs/analytics-handbook/semantic/metrics.md` (banner, không đổi nội dung định nghĩa).
- Không sửa code, dbt, Rill, blueprint.

## Verification

- Mọi question có dữ liệu của `ceo_weekly_pulse.md` (24/30; 6 card meta là chu kỳ báo cáo và độ tươi) có dòng tương ứng trong bảng.
- Mỗi chỗ lệch có số mẫu đo được (không ghi "ước lượng"), có trạng thái trong sổ quyết định.
- Bản chụp DuckDB tạm đã xoá sau khi đo; không truy vấn nào mở `olap.duckdb` gốc ở chế độ ghi.

## Đổi số?

Không. Phase chỉ sinh tài liệu và danh sách quyết định.

## Rủi ro

| Rủi ro | Giảm thiểu |
|---|---|
| Bảng quá lớn (45 blueprint) làm chậm phase 01 | Làm nhóm Weekly Pulse trước, nhóm khác song song với phase 01–05 |
| Số mẫu đo trên bản chụp đang thay đổi (lịch `*/3`) | Chỉ đo kỳ đã đóng; ghi giờ chụp |
| User chốt muộn | Registry theo blueprint đang chạy, quyết định áp ở phase 09 |

## Rollback

Không có thay đổi chạy. Revert commit tài liệu nếu cần.
