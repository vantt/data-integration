# Chiến Lược Định Thời và Điều Phối Pipeline (Pipeline Scheduling & Orchestration Strategy)

Tài liệu này quy định cách thức định thời (scheduling) và điều phối (orchestration) cho hệ thống DLT Pipelines nhập liệu từ Sapo vào Data Lake, nhắm tới mục tiêu xây dựng **Unified Transaction Log** đầy đủ và chính xác.

## 1. Mục Tiêu

Đảm bảo dữ liệu được thu thập **đầy đủ (Completeness)**, **đúng thứ tự (Sequencing)** và **kịp thời (Freshness)** trước khi các quy trình hạ nguồn (Downstream Transformation) bắt đầu.

Hệ thống kết hợp sức mạnh của 3 luồng dữ liệu (Data Streams):

1.  **Webhook**: Real-time snapshot (Độ trễ thấp).
2.  **History Log**: Event log polling (Độ tin cậy cao về sự kiện).
3.  **Batch Sync**: Quét định kỳ (Cơ chế tự sửa lỗi / Healing).

## 2. Vai Trò và Tần Suất (Roles & Frequency)

| Pipeline Component              | Loại Hình      | Tần Suất (Scheduling)            | Vai Trò Chính (Role)                                                                                                          | Payload Strategy                                                  |
| :------------------------------ | :------------- | :------------------------------- | :---------------------------------------------------------------------------------------------------------------------------- | :---------------------------------------------------------------- |
| **Webhook Consumer**            | Real-time Push | **Continuous** (hoặc mỗi 1 phút) | **Primary Source**. Cung cấp dữ liệu nhanh nhất và chính xác tại thời điểm sự kiện xảy ra.                                    | Sử dụng trực tiếp Payload từ Webhook Event.                       |
| **History Log Poller**          | Event Pull     | **Mỗi 10 phút**                  | **Gap Filler**. Phát hiện các sự kiện mà Webhook có thể đã bỏ lỡ (do lỗi mạng hoặc quá tải). Bù đắp "lỗ hổng" dữ liệu.        | Payload là trạng thái _tại thời điểm chạy pipeline_ (Late State). |
| **Batch Sync** (Reconciliation) | Batch Pull     | **Daily (02:00 AM)**             | **Reconciliation**. Quét lại toàn bộ dữ liệu (hoặc active window) để đảm bảo tính nhất quán cuối cùng (Eventual Consistency). | Snapshot mới nhất từ API.                                         |

## 3. Cơ Chế Điều Phối (Orchestration Logic)

### 3.1. Nguyên Tắc "Safe Watermark"

Để đảm bảo tính toàn vẹn cho các quy trình xử lý hạ nguồn (HOP 2 -> HOP 3), chúng ta áp dụng cơ chế **Safe Watermark**.

Dữ liệu của khung giờ $H$ (ví dụ: 08:00 - 09:00) chỉ được coi là **SẴN SÀNG (READY)** để xử lý khi:

1.  Thời gian thực tế $> H + \text{Buffer Time}$ (Khuyến nghị: 15 phút).
2.  `History Log Pipeline` đã hoàn tất thành công ít nhất một lần sau mốc $H$.

**Ví dụ:** Job tổng hợp doanh thu giờ 08:00-09:00 sẽ chạy vào lúc **09:15**, sau khi đảm bảo History Log (chạy lúc 09:10) đã quét xong các log cuối cùng của khung giờ đó.

### 3.2. Chiến Lược Hợp Nhất (Merge & Deduplication)

Khi có nhiều bản ghi cho cùng một `entity_id` trong cùng một khoảng thời gian, thứ tự ưu tiên (Priority) để chọn "Truth" như sau:

1.  **Webhook Source**: Ưu tiên cao nhất cho thuộc tính tại thời điểm đó (Point-in-time correctness).
2.  **History Log Source**: Dùng để xác nhận "có sự kiện xảy ra". Nếu thiếu Webhook, History Log sẽ đóng vai trò thay thế (fallback), dù payload có thể bị trễ (drift).
3.  **Batch Sync**: Dùng để ghi đè trạng thái cuối cùng (Final State) nếu có sai lệch lớn.

### 4. Kế Hoạch Triển Khai & Cải Tiến

#### A. Cải tiến `Batch Sync`

Cần chuyển đổi logic của `run_orders_batch.py` từ quét theo `created_on` (hiện tại) sang quét theo `updated_on` hoặc `modified_on`.

- **Lý do**: Logic hiện tại chỉ lấy đơn mới tạo, bỏ sót các đơn hàng cũ được cập nhật trạng thái.
- **Giải pháp**:
  - **Daily Mode**: Quét các đơn có `updated_on` trong 24h qua.
  - **Healing Mode**: Quét full hoặc window 30 ngày (Weekly/Monthly).

#### B. Cải tiến `History Log`

Giữ nguyên tần suất 10 phút. Đảm bảo logic "Overlap" hoạt động đúng để không bỏ sót sự kiện ở ranh giới các lần chạy (đã xử lý bằng `min_overlap_items`).

#### C. Cải tiến `Webhook`

Triển khai cơ chế **ACK** (Acknowledge) chắc chắn hơn (e.g., ghi vào state trước khi ACK với Cloudflare) để tránh mất msg khi pipeline crash giữa chừng.

## 5. Kết Luận

Mô hình **Hybrid (Push-Pull)** này tối ưu hóa được cả độ trễ (nhờ Webhook) và độ tin cậy (nhờ Log & Batch). Việc tuân thủ "Safe Watermark" là chìa khóa để Data Warehouse không bị tính toán sai do dữ liệu về trễ.
