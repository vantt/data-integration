# Tài Liệu Bản Chất Dữ Liệu Nguồn Sapo

Tài liệu này mô tả chi tiết cách lấy dữ liệu (channels) từ Sapo cho các entities: **Orders**, **Customers**, và **Accounts** (Nhân viên), bao gồm các endpoints, phương thức query và bản chất sắp xếp dữ liệu.

## 1. Orders (Đơn Hàng)

### Channels

#### A. JSON API (Batch Sync)

Dùng để đồng bộ hàng loạt hoặc initial load.

- **URL/Host**: `GET /admin/orders.json`
- **Query Parameters**:
  - `page`: Số trang (1, 2, 3...)
  - `limit`: Số lượng item mỗi trang (thường là 50 hoặc 100)
  - `sort_by`: `modified_on desc` (Sắp xếp theo thời gian sửa đổi giảm dần)
- **Bản chất Query/Sort**:
  - API hỗ trợ filter cơ bản (status, order dates...).
  - **Lưu ý**: Sapo API có giới hạn về sort theo thời gian sửa đổi. Code hiện tại đang cố gắng dùng `sort_by=modified_on desc` để hỗ trợ incremental sync.
  - **Payload**: Trả về toàn bộ thông tin đơn hàng (nested JSON) bao gồm line items, fulfillments, billing address, v.v.

#### B. Webhook (Real-time)

Dùng để nhận sự kiện thay đổi tức thời.

- **URL/Host**: Endpoint nội bộ của bạn (e.g., `https://<your-domain>/webhook/sapo/orders`)
- **Events**: `order/create`, `order/update`, `order/cancelled`, `order/delete`.
- **Payload**: JSON chứa thông tin đơn hàng tại thời điểm sự kiện.

#### C. History Log API (Gap Filling)

Dùng để phát hiện các thay đổi bị miss bởi webhook.

- **URL/Host**: `GET /admin/settings/get_logs`
- **Logic**:
  1.  Lấy log hoạt động (`rootType=Order`).
  2.  Lấy `rootId` (Entity ID).
  3.  Gọi lại API chi tiết đơn hàng: `GET /admin/orders/{id}.json`.

---

## 2. Customers (Khách Hàng)

### Channels

#### A. JSON API (Batch Sync - Search Endpoint)

Sử dụng endpoint tìm kiếm để có khả năng filter tốt hơn.

- **URL/Host**: `GET /admin/customers/doSearch.json`
- **Query Parameters**:
  - `page`: Số trang.
  - `limit`: Số lượng item.
  - `sort`: `created_on,desc` (Sắp xếp theo thời gian sửa đổi mới nhất).
  - `condition_type`: `must`.
- **Bản chất Query/Sort**:
  - Endpoint này cho phép sort theo `created_on` tốt hơn endpoint list chuẩn `/admin/customers.json`.
  - Hỗ trợ incremental loading dựa trên `created_on`.
  - Lưu ý: không hỗ trợ sort theo modified_on (điều này là quan trọng và có thể gây ra nhược điểm cho incremental sync)

#### B. History Log API (Gap Filling)

Dùng để phát hiện các thay đổi bị miss bởi webhook.

- **URL/Host**: `GET /admin/settings/get_logs`
- **Logic**:
  1.  Lấy log hoạt động (`rootType=Customer`).
  2.  Lấy `rootId` (Entity ID).
  3.  Gọi lại API chi tiết khách hàng: `GET /admin/customers/{id}.json`.

#### C. Webhook (Real-time)

- **Events**: `customers/create`, `customers/update`. (Note: Sapo thường gộp customer events hoặc cấu hình riêng).
- **Payload**: JSON chứa thông tin khách hàng tại thời điểm sự kiện.

---

## 3. Accounts (Nhân Viên / User)

### Channels

#### A. JSON API (Batch Sync)

Dùng để lấy danh sách nhân viên.

- **URL/Host**: `GET /admin/accounts.json`
- **Query Parameters**:
  - `page`: Số trang.
  - `limit`: Số lượng item.
- **Bản chất Query/Sort**:
  - **Sort**: Mặc định thường là theo ID hoặc tên, API này **không hỗ trợ mạnh về sort theo modified_on** như Orders hay Customers.
  - **Incremental**: Code hiện tại vẫn check trường `modified_on` của từng item trả về để filter, nhưng việc fetch data phải duyệt qua danh sách (hoặc toàn bộ nếu số lượng ít) do không đảm bảo API trả về đúng thứ tự sửa đổi.
  - **Volume**: Thường số lượng accounts ít (< vài trăm), nên có thể load toàn bộ mỗi lần chạy hoặc chấp nhận scan hết.

#### B. History Log API (Gap Filling)

Dùng để phát hiện các thay đổi bị miss bởi webhook.

- **URL/Host**: `GET /admin/settings/get_logs`
- **Logic**:
  1.  Lấy log hoạt động (`rootType=Account`).
  2.  Lấy `rootId` (Entity ID).
  3.  Gọi lại API chi tiết nhân viên: `GET /admin/accounts/{id}.json`.

#### C. Webhook (Real-time)

- **Events**: `accounts/create`, `accounts/update`. (Note: Sapo thường gộp account events hoặc cấu hình riêng).
- **Payload**: JSON chứa thông tin nhân viên tại thời điểm sự kiện.

---

## 4. Tổng Hợp Ma Trận Channels

| Entity        | Channel Chính | Endpoint                         | Sort Nature        | Lưu ý                                                                         |
| :------------ | :------------ | :------------------------------- | :----------------- | :---------------------------------------------------------------------------- |
| **Orders**    | JSON API      | `/admin/orders.json`             | `modified_by desc` | Dùng để sync lịch sử và daily batch.                                          |
|               | Webhook       | Listener                         | N/A                | Dùng cho real-time updates.                                                   |
| **Customers** | JSON API      | `/admin/customers/doSearch.json` | `modified_on,desc` | Dùng endpoint `doSearch` thay vì list chuẩn.                                  |
|               | Webhook       | Listener                         | N/A                | Real-time updates.                                                            |
| **Accounts**  | JSON API      | `/admin/accounts.json`           | Default (ID/Alpha) | Số lượng ít, thường crawl toàn bộ hoặc scan page. Không sort chuẩn theo time. |

## 5. History Log API (Dùng chung cho tất cả)

Đây là kênh dự phòng quan trọng để đảm bảo tính toàn vẹn dữ liệu.

- **URL Base**: `/admin/settings/get_logs`
- **Sort**: API trả về log mới nhất trước (DESC theo thời gian log).
- **Cách hoạt động**:
  - Crawler duyệt ngược thời gian (Page 1 -> Page N).
  - Dựa vào `occurAt` để xác định điểm dừng (incremental checkpoint).
  - **Gap Filling**: Khi phát hiện log change, hệ thống tự động suy diễn endpoint chi tiết (ví dụ: `/admin/orders/123.json`) để lấy dữ liệu mới nhất.
