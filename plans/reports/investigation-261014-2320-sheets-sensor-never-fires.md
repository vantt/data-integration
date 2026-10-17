# `ingest_sheets_modified_sensor` không bao giờ phát hiện sheet đổi (14/10/2026)

## Kết luận

Sensor không phát hiện được thay đổi nào vì **cả ba link export CSV công khai đều trả HTTP 401**.
Các Google Sheet không còn để chế độ "ai có link đều xem được"; reader đã chuyển sang đọc bằng
service account (`ingestion/src/gsheet_auth.py`, plan `260707-1201-google-sheets-service-account`),
còn sensor vẫn tải link công khai không xác thực. Lỗi bị nuốt im lặng, nên trên Dagster chỉ thấy
"Cold start" mãi mãi. Việc sync sheet theo lịch vẫn chạy bình thường; chỉ mất phần phát hiện thay
đổi trong vòng 5 phút. Không liên quan tới deploy của Đợt 1: 400 tick gần nhất (từ 13/10 13:33,
trước mọi deploy hôm 14/10) đều như vậy.

## Bằng chứng (chỉ đọc)

- Lịch sử tick (GraphQL, 400 tick gần nhất): tất cả `SKIPPED`, lý do
  `Cold start — recorded baseline for []`, không run nào được bắn.
- Fetch từ trong `data_platform` bằng đúng URL sensor dùng (chỉ in trạng thái, không in URL):
  `targets` 401, `marketing_spend` 401, `us_shipment_prices` 401; cả ba trả trang HTML của
  `docs.google.com` (~9 KB), không phải CSV.

## Vì sao lỗi im lặng

`orchestration/sensors/sheets_modified_sensor.py`:

1. `_fetch_sheet_hash()` bắt mọi exception và trả `None` (comment ghi "add explicit alerting later
   only if that becomes a pain point").
2. Khi mọi sheet đều lỗi, `current` rỗng. Cursor trước đó cũng rỗng (`{}`), nên nhánh "cold start"
   chạy: ghi cursor `{}` và trả `SkipReason("Cold start ...")`.
3. Tick sau đọc lại cursor `{}` → lại là cold start. Nhánh báo `fetch errors` chỉ chạy khi cursor
   đã có hash, nên không bao giờ tới.

## Hướng sửa (đề xuất, chưa làm)

1. **Đọc qua service account** như reader: lấy nội dung tab bằng `gsheet_auth` (Sheets API) rồi
   hash, hoặc dùng Drive API `files.get(fields=modifiedTime)` cho từng sheet (một request nhẹ, nhưng
   `modifiedTime` đổi cả khi chỉ sửa định dạng — lý do thiết kế ban đầu chọn hash nội dung). Đề xuất
   hash nội dung qua Sheets API để giữ hành vi "chỉ bắn khi dữ liệu đổi".
2. **Không nuốt lỗi khi mọi sheet đều hỏng:** cold start chỉ ghi baseline khi có ít nhất một hash;
   khi tất cả lỗi thì trả `SkipReason` nêu tên sheet lỗi và mã HTTP, và sau N tick lỗi liên tiếp thì
   cảnh báo (hoặc để sensor raise để `health_alert_*` thấy).
3. Test: fetch trả 401 cho mọi sheet → SkipReason có "fetch errors", không ghi cursor rỗng.

Thay đổi chạm `orchestration/sensors/` và cách xác thực Google, không đổi số liệu; đi qua gate M
và runbook như các thay đổi code khác. Lưu ý quota Sheets API: 3 sheet × 12 lần/giờ = 36 request/giờ,
nhỏ so với hạn mức mặc định.

## Câu hỏi cho user

1. Sửa theo hướng 1 (hash nội dung qua Sheets API bằng service account) và 2 (không nuốt lỗi) chứ?
   Hay bỏ hẳn sensor, chỉ dùng lịch sync hiện có?
