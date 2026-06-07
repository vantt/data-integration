# Debug Metabase Dashboard

Debug số liệu sai trên Metabase dashboard bằng cách kiểm tra từng card, phát hiện vấn đề, và giải thích bằng tiếng Việt.

## Flow

### Bước 1 — Chạy summary để lấy danh sách cards

```bash
METABASE_URL="http://127.0.0.1:3001" METABASE_API_KEY="$(grep METABASE_API_KEY .env.docker | cut -d= -f2- | tr -d '\"')" \
  node scripts/debug/metabase-dashboard-debugger.js "$ARGUMENTS"
```

Đọc output, tổng hợp danh sách cards với:
- `card_id`, tên card, tab
- Row count (0 rows = ⚠️, error = ❌, có data = ✓)
- Ghi chú vấn đề sơ bộ (ví dụ: "0 rows khi có filter scope")

### Bước 2 — Hỏi user muốn debug card nào

Sau khi đọc summary output, dùng **`AskUserQuestion`** để hỏi user:
- Liệt kê tất cả cards với emoji trạng thái (⚠️/❌/✓) và tên
- Cho phép chọn nhiều cards (multiSelect: true)
- Nếu có card nào rõ ràng có vấn đề (0 rows hoặc error), đánh dấu "(đáng ngờ)" trong tên

**Format câu hỏi:**
```
question: "Card nào bạn muốn debug chi tiết?"
header: "Chọn card"
multiSelect: true
options: [mỗi card là một option, label = "card_id: tên card", description = "Tab: X | Rows: Y | [ghi chú vấn đề nếu có]"]
```

### Bước 3 — Deep-dive từng card được chọn

Với mỗi card_id user chọn, chạy:

```bash
METABASE_URL="http://127.0.0.1:3001" METABASE_API_KEY="$(grep METABASE_API_KEY .env.docker | cut -d= -f2- | tr -d '\"')" \
  node scripts/debug/metabase-dashboard-debugger.js "$ARGUMENTS" --card <card_id>
```

### Bước 4 — Phân tích và giải thích

Với mỗi card đã deep-dive, phân tích:

**Filter analysis:**
- `scope` filter → loại trừ channel nào? SQL dùng `channel_code =` hay `channel_brand =` hay `market =`?
- `date` filter → date range là gì? SQL dùng `date_key BETWEEN` hay `ordered_at >=`? ICT hay UTC?
- `category` filter → map vào column nào trong fact table?
- Card có parameter mapping không? Nếu không → card show ALL data, không bị ảnh hưởng bởi dashboard filter

**Data quality signals:**
- 0 rows → filter quá hẹp? hay thiếu data gốc?
- `(không có filter)` trên một parameter → card bỏ qua filter này
- SQL template dùng `{{variable}}` nhưng không có mapping → biến không được thay thế

**Common issues trong stack này:**
- `date_key` là ICT date integer (YYYYMMDD), không phải timestamp → filter sai nếu dùng timestamp
- `status IN ('CANCELLED','VOIDED')` phải được exclude trong revenue cards
- `scope` có thể map vào `channel_code`, `channel_brand`, hoặc `market` — check SQL template
- US orders: `net_revenue` từ fact_orders có thể = 0, revenue thực ở `fact_us_shipment_economics`

**Báo cáo mỗi card:**
- Tóm tắt 1-2 câu: card đang làm gì, filter nào đang áp dụng
- Vấn đề phát hiện (nếu có) và nguyên nhân
- Gợi ý fix hoặc kiểm tra thêm

## User Arguments

$ARGUMENTS
