# Skill: debug-metabase

Hai use case:
- **Explain**: tại sao card X đang hiện giá trị Y? Trace filters → SQL thực tế → rows → giải thích logic.
- **Debug**: tìm vấn đề khi số liệu trông sai — 0 rows, filter bị miss, scope không đúng, v.v.

## Script

```
.skills/debug-metabase/scripts/metabase-dashboard-debugger.js
```

### Cách chạy

```bash
METABASE_URL="http://127.0.0.1:3001" METABASE_API_KEY="$(grep METABASE_API_KEY .env.docker | cut -d= -f2- | tr -d '\"')" \
  node .skills/debug-metabase/scripts/metabase-dashboard-debugger.js "$ARGUMENTS"
```

### Flags

| Flag | Tác dụng |
|------|----------|
| (none) | Summary: row count tất cả cards |
| `--card <id>` | Deep-dive: SQL template, mappings, kết quả |
| `--all` | Deep-dive tất cả cards (verbose) |
| `--no-cache` | Bỏ qua cache, fetch lại từ API |

### Cache

Dashboard metadata (params, tabs, cards, SQL templates) được cache tại `.cache/metabase/dashboard-<id>.json` với TTL 24h. Query execution luôn fresh. Dùng `--no-cache` khi dashboard vừa thay đổi cấu trúc.

## Flow

### Bước 1 — Xác định card cần xem

Nếu `$ARGUMENTS` đã chứa `--card <id>` → bỏ qua summary, deep-dive luôn (Bước 3).

Nếu chưa biết card → chạy summary:

```bash
METABASE_URL="http://127.0.0.1:3001" METABASE_API_KEY="$(grep METABASE_API_KEY .env.docker | cut -d= -f2- | tr -d '\"')" \
  node .skills/debug-metabase/scripts/metabase-dashboard-debugger.js "$ARGUMENTS"
```

### Bước 2 — Hỏi user chọn card

Dùng **`AskUserQuestion`** sau khi đọc summary:
- Liệt kê tất cả cards với emoji trạng thái (⚠️/❌/✓) và tên
- `multiSelect: true`
- Card 0 rows hoặc error → đánh dấu "(đáng ngờ)" trong description

**Format:**
```
question: "Card nào bạn muốn xem chi tiết?"
header: "Chọn card"
multiSelect: true
options: [label="<card_id>: <tên card>", description="Tab: X | Rows: Y | <ghi chú>"]
```

### Bước 3 — Deep-dive từng card được chọn

```bash
METABASE_URL="http://127.0.0.1:3001" METABASE_API_KEY="$(grep METABASE_API_KEY .env.docker | cut -d= -f2- | tr -d '\"')" \
  node .skills/debug-metabase/scripts/metabase-dashboard-debugger.js "$ARGUMENTS" --card <card_id>
```

### Bước 4 — Phân tích và giải thích

Với mỗi card đã deep-dive, luôn báo cáo theo cấu trúc sau:

#### 1. Filters đang có hiệu lực
Liệt kê từng parameter mapping:
- Tên filter (slug) + giá trị đang active
- SQL column bị filter (ví dụ: `channel_code = 'SHOPEE_VN'`)
- Nếu card **không có** parameter mapping → ghi rõ "card này không bị ảnh hưởng bởi dashboard filters — show ALL data"

#### 2. SQL thực tế đang chạy
Trình bày SQL sau khi đã substitute filters. Giải thích ngắn:
- Bảng/join chính là gì
- WHERE conditions thực tế
- Aggregation: SUM/COUNT gì, GROUP BY gì

#### 3. Kết quả
- Tổng rows trả về
- Sample rows (nếu có)
- **Giải thích giá trị**: "Con số X này là tổng [metric] của [scope] trong [date range], bao gồm/loại trừ [điều kiện]"

#### 4. Đánh giá — Explain hoặc Debug

**Nếu use case là Explain** (user muốn hiểu tại sao có giá trị này):
- Xác nhận giá trị hợp lý: logic SQL + filters dẫn đến kết quả như thế nào
- Liệt kê các caveat quan trọng (ví dụ: "đã exclude CANCELLED", "date là ICT", "chỉ tính net_revenue từ fact_orders")
- Nếu phát hiện điều gì bất thường → mention nhưng không phán định là bug

**Nếu use case là Debug** (user thấy số sai):
- 0 rows → filter quá hẹp? thiếu data gốc?
- `(không có filter)` trên parameter → card bỏ qua filter, show ALL data
- SQL template có `{{variable}}` nhưng không có mapping → biến không được thay thế

**Common issues trong stack này:**
- `date_key` là ICT date integer (YYYYMMDD) → filter sai nếu dùng timestamp
- `status IN ('CANCELLED','VOIDED')` phải được exclude trong revenue cards
- `scope` có thể map vào `channel_code`, `channel_brand`, hoặc `market` — check SQL template
- US orders: `net_revenue` từ fact_orders có thể = 0, revenue thực ở `fact_us_shipment_economics`
