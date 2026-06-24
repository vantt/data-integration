# Phase 2 — Locale Files

**Status:** Todo  
**Effort:** ~3h (scan all 39 templates + generate EN translations)

## Overview

Generate `vi.json` and `en.json` by scanning all string sources. Keys use dot-notation domain namespacing.

## Files to create

```
crm/src/adapters/inbound/web/locales/
├── vi.json
└── en.json
```

## Key taxonomy (domain → keys)

### `common` — universal UI words
```json
"common": {
  "back": "Quay lại",
  "save": "Lưu",
  "cancel": "Hủy",
  "create": "Tạo",
  "edit": "Sửa",
  "delete": "Xóa",
  "confirm": "Xác nhận",
  "search": "Tìm kiếm",
  "loading": "Đang tải...",
  "all": "Tất cả",
  "none": "-- Không có --",
  "unknown": "Không rõ",
  "empty_dash": "—",
  "required_mark": "*"
}
```

### `nav` — navigation labels
```json
"nav": {
  "customers": "Khách hàng",
  "orders": "Đơn hàng",
  "tasks": "Công việc",
  "inbox": "Hộp thư",
  "segments": "Phân khúc",
  "campaigns": "Chiến dịch",
  "worklist": "Danh sách việc",
  "settings": "Cài đặt",
  "dedup": "Gộp trùng"
}
```

### `field` — form field labels (shared across forms)
```json
"field": {
  "name": "Tên",
  "phone": "Số điện thoại",
  "email": "Email",
  "address": "Địa chỉ",
  "note": "Ghi chú",
  "channel": "Kênh",
  "status": "Trạng thái",
  "assignee": "Người phụ trách",
  "schedule": "Lên lịch",
  "tags": "Tags",
  "type": "Loại",
  "date": "Ngày",
  "objective": "Mục tiêu"
}
```

### `action` — button / CTA labels
```json
"action": {
  "log_activity": "Ghi log",
  "create_task": "Tạo task",
  "assign_staff": "Gán NV",
  "add_tag": "Thêm tag",
  "add_note": "Thêm ghi chú",
  "close_conv": "Đóng hội thoại",
  "reopen_conv": "Mở lại",
  "change_staff": "Đổi NV",
  "merge": "Gộp",
  "promote": "Promote insight"
}
```

### `customer` — customer domain
```json
"customer": {
  "section_title": "Khách hàng",
  "detail_title": "Chi tiết khách hàng",
  "id_label": "Mã KH",
  "tenure_label": "Thời gian",
  "contact_section": "Liên Lạc",
  "basic_info_section": "Thông Tin Cơ Bản",
  "kpi_section": "Chỉ Số",
  "empty_state_title": "Không tìm thấy khách hàng",
  "list_empty": "Chưa có khách hàng nào"
}
```

### `order` — order domain
```json
"order": {
  "section_title": "Đơn hàng",
  "empty_state": "Chưa có đơn hàng",
  "detail_title": "Chi tiết đơn",
  "code_label": "Mã đơn",
  "items_tab": "Sản phẩm",
  "financial_tab": "Tài chính",
  "operations_tab": "Vận hành",
  "context_tab": "Ngữ cảnh",
  "action_tab": "Hành động",
  "verdict.positive": "Có lãi",
  "verdict.negative": "Lỗ",
  "verdict.neutral": "Hòa vốn"
}
```

### `task` — task domain
```json
"task": {
  "section_title": "Công việc",
  "empty_state": "Chưa có task",
  "board_title": "Bảng công việc",
  "status.open": "Chưa bắt đầu",
  "status.doing": "Đang làm",
  "status.done": "Hoàn thành",
  "status.cancelled": "Đã hủy"
}
```

### `campaign` — campaign domain
```json
"campaign": {
  "section_title": "Chiến dịch",
  "section_eyebrow": "CHIẾN DỊCH",
  "create_title": "Tạo chiến dịch",
  "edit_title": "Sửa chiến dịch",
  "empty_state_title": "Chưa có chiến dịch nào",
  "empty_state_sub": "Tạo chiến dịch đầu tiên từ một segment.",
  "target_empty_title": "Chưa có target",
  "target_empty_sub": "Segment có 0 member hoặc chiến dịch chưa kích hoạt.",
  "col.name": "Tên",
  "col.channel": "Kênh",
  "col.rate": "Rate",
  "col.status": "Trạng thái",
  "col.objective": "Objective"
}
```

### `segment` — segment domain
```json
"segment": {
  "section_title": "Phân khúc",
  "empty_state": "Chưa có phân khúc"
}
```

### `inbox` — inbox/conversation domain
```json
"inbox": {
  "section_title": "Hộp thư",
  "empty_messages": "Chưa có tin nhắn",
  "conv_closed": "Hội thoại đã đóng",
  "read_only_v1": "Chế độ chỉ đọc (v1)",
  "unlinked_customer": "Chưa link khách",
  "search_hint": "Nhập tên hoặc SĐT để tìm..."
}
```

### `insight` — insight panel
```json
"insight": {
  "section_title": "Phân tích",
  "no_data": "Chưa có dữ liệu",
  "last_order_label": "Đơn gần nhất",
  "recency_label": "Recency",
  "frequency_label": "Frequency",
  "monetary_label": "Monetary"
}
```

### `time` — relative time formatting
```json
"time": {
  "just_now": "vừa xong",
  "n_seconds_ago": "{n} giây trước",
  "n_minutes_ago": "{n} phút trước",
  "n_hours_ago": "{n} giờ trước",
  "n_days_ago": "{n} ngày trước",
  "n_months_ago": "{n} tháng trước",
  "n_years_ago": "{n} năm trước"
}
```

### `geo` — geographic region labels
```json
"geo": {
  "hcmc": "HCMC",
  "hanoi": "Hà Nội",
  "mekong": "Mekong",
  "central": "Miền Trung",
  "other": "Khác"
}
```

### `badge` — tooltip hints (mirrors badge_catalog domains)
```json
"badge": {
  "order_status": {
    "completed": "Đơn đã hoàn tất",
    "finalized": "Đơn đã chốt",
    "processing": "Đang xử lý",
    "confirmed": "Đã xác nhận, chờ xuất kho",
    "pending": "Chờ xác nhận",
    "draft": "Nháp — chưa xác nhận",
    "archived": "Lưu trữ",
    "cancelled": "Đã hủy",
    "returned": "Đã hoàn trả",
    "voided": "Vô hiệu"
  },
  "payment_status": {
    "paid": "Đã thanh toán đủ",
    "partial": "Thanh toán một phần",
    "unpaid": "Chưa thanh toán",
    "refunded": "Đã hoàn tiền",
    "voided": "Giao dịch bị hủy"
  },
  "fulfillment_status": {
    "delivered": "Đã giao hàng thành công",
    "received": "Đã nhận hàng",
    "packed": "Đã đóng gói, chờ lấy hàng",
    "shipping": "Đang vận chuyển",
    "unshipped": "Chưa xuất kho",
    "returned": "Hàng bị hoàn trả",
    "restocked": "Hàng hoàn kho",
    "cancelled": "Vận chuyển bị hủy"
  },
  "value_group": {
    "VIP": "VIP — khách hàng giá trị đặc biệt cao",
    "GOLD": "GOLD — khách hàng giá trị cao",
    "SILVER": "SILVER — khách hàng giá trị trung bình",
    "BRONZE": "BRONZE — khách hàng mới hoặc giá trị cơ bản"
  },
  "customer_status": {
    "active": "Đang hoạt động — có giao dịch gần đây",
    "at_risk": "Có nguy cơ rời bỏ — lâu chưa mua",
    "churned": "Đã rời bỏ — không còn hoạt động"
  },
  "purchase_signal": {
    "OVERDUE": "Quá hạn mua lại theo dự đoán",
    "DUE_SOON": "Sắp đến hạn mua lại",
    "ON_TRACK": "Đang trong chu kỳ mua bình thường"
  },
  "action_type": {
    "CALL_NOW": "Gọi ngay — khách có nguy cơ rời bỏ cao",
    "REORDER_NUDGE": "Nhắc tái đặt hàng — sắp đến chu kỳ",
    "WIN_BACK": "Tái kích hoạt — đã lâu không mua",
    "UPSELL": "Upsell — tiềm năng nâng hạng",
    "CROSS_SELL": "Cross-sell — đề xuất sản phẩm bổ sung",
    "COLLECT_FEEDBACK": "Thu thập phản hồi từ khách"
  },
  "customer_type": {
    "RETAIL": "Khách lẻ",
    "WHOLESALE": "Khách buôn / B2B",
    "PARTNER": "Đối tác"
  },
  "party_status": {
    "active": "Hồ sơ đang hoạt động",
    "inactive": "Hồ sơ không hoạt động",
    "at_risk": "Có nguy cơ rời bỏ",
    "churned": "Đã rời bỏ",
    "merged": "Đã gộp vào hồ sơ khác"
  },
  "task_status": {
    "open": "Chưa bắt đầu",
    "doing": "Đang thực hiện",
    "done": "Đã hoàn thành",
    "cancelled": "Đã hủy"
  },
  "conv_status": {
    "open": "Đang mở — chờ phản hồi",
    "closed": "Đã đóng",
    "pending": "Chờ xử lý"
  },
  "campaign_status": {
    "draft": "Nháp",
    "active": "Đang chạy",
    "completed": "Đã hoàn thành",
    "paused": "Tạm dừng",
    "archived": "Đã lưu trữ"
  },
  "campaign_target": {
    "pending": "Chờ gửi",
    "sent": "Đã gửi",
    "responded": "Đã phản hồi",
    "converted": "Đã chuyển đổi",
    "opted_out": "Đã từ chối"
  }
}
```

### `error` — error / 404 messages
```json
"error": {
  "customer_not_found": "Không tìm thấy khách hàng",
  "conv_not_found": "Không tìm thấy hội thoại",
  "segment_not_found": "Segment không tìm thấy",
  "campaign_not_found": "Chiến dịch không tìm thấy",
  "candidate_not_found": "Không tìm thấy candidate",
  "contact_not_found": "Không tìm thấy kênh liên lạc",
  "confirm_required": "Xác nhận bắt buộc",
  "create_failed": "Lỗi tạo khách hàng",
  "save_tags_failed": "Lỗi lưu tags"
}
```

## en.json — full English translations

All keys above with English values. Key differences:
- `time.*` uses English phrasing: `"{n} seconds ago"`, `"just now"`
- `geo.hanoi` → `"Hanoi"`, `geo.central` → `"Central"`, `geo.other` → `"Other"`
- `order.verdict.positive` → `"Profitable"`, `.negative` → `"Loss"`, `.neutral` → `"Break-even"`
- Badge hints translated naturally (no need to be literal)
- `common.none` → `"-- None --"`

## Implementation steps

1. Run scan script against all 39 templates + Python files to catch any missed strings
2. Write `vi.json` from taxonomy above (complete)
3. Write `en.json` with English values
4. Validate: `t("badge.order_status.completed")` → "Đơn đã hoàn tất" (vi), "Order completed" (en)

## Notes

- `badge.*` keys mirror badge_catalog domains exactly → `bdg_tip_filter` can auto-construct key as `f"badge.{domain}.{key}"`
- `time.*` format strings use `{n}` placeholder → `t("time.n_hours_ago").format(n=2)` → "2 giờ trước"
- Proper nouns kept as-is: "VIP", "GOLD", "SILVER", "BRONZE" (not translated)
- Vietnamese province names in `_GEO_*` sets are input data matchers, NOT translated
