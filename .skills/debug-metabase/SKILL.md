# Skill: debug-metabase

Debug số liệu sai trên Metabase dashboard bằng cách kiểm tra từng card, phát hiện vấn đề, và giải thích bằng tiếng Việt.

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

### Bước 1 — Summary

Chạy script không có flag để lấy row count tất cả cards.

### Bước 2 — Hỏi user chọn card

Sau khi đọc summary output, dùng **`AskUserQuestion`** để hỏi user:
- Liệt kê tất cả cards với emoji trạng thái (⚠️/❌/✓) và tên
- multiSelect: true để chọn nhiều card
- Card 0 rows hoặc error → đánh dấu "(đáng ngờ)" trong description

**Format:**
```
question: "Card nào bạn muốn debug chi tiết?"
header: "Chọn card"
multiSelect: true
options: [label="<card_id>: <tên card>", description="Tab: X | Rows: Y | <ghi chú vấn đề>"]
```

### Bước 3 — Deep-dive từng card được chọn

```bash
... node .skills/debug-metabase/scripts/metabase-dashboard-debugger.js "$ARGUMENTS" --card <card_id>
```

### Bước 4 — Phân tích và giải thích

**Filter analysis:**
- `scope` filter → loại trừ channel nào? SQL dùng `channel_code =` hay `channel_brand =` hay `market =`?
- `date` filter → date range là gì? SQL dùng `date_key BETWEEN` hay `ordered_at >=`? ICT hay UTC?
- `category` filter → map vào column nào trong fact table?
- Card có parameter mapping không? Nếu không → card show ALL data

**Data quality signals:**
- 0 rows → filter quá hẹp? hay thiếu data gốc?
- `(không có filter)` trên một parameter → card bỏ qua filter này
- SQL template dùng `{{variable}}` nhưng không có mapping → biến không được thay thế

**Common issues trong stack này:**
- `date_key` là ICT date integer (YYYYMMDD) → filter sai nếu dùng timestamp
- `status IN ('CANCELLED','VOIDED')` phải được exclude trong revenue cards
- `scope` có thể map vào `channel_code`, `channel_brand`, hoặc `market` — check SQL template
- US orders: `net_revenue` từ fact_orders có thể = 0, revenue thực ở `fact_us_shipment_economics`

**Báo cáo mỗi card:**
- Tóm tắt 1-2 câu: card làm gì, filter nào đang áp dụng
- Vấn đề phát hiện (nếu có) và nguyên nhân
- Gợi ý fix hoặc kiểm tra thêm
