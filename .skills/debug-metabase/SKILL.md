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

### Bước 4 — Blueprint & Contract lookup

Sau khi có dashboard name từ script output, tìm blueprint tương ứng:

```bash
grep -rl "<dashboard name>" docs/analytics-handbook/blueprints/
```

Nếu không match bằng tên → thử từ khóa chính (ví dụ: "Yesterday", "Retail", "CEO"):

```bash
grep -ril "<keyword>" docs/analytics-handbook/blueprints/
```

Khi tìm được blueprint file:

1. **Đọc frontmatter** — lấy `primary_scope` và `uses_concepts`
2. **Đọc `## Semantic Contract`** — scope, layer, concepts declared
3. **Tìm section của card** — `grep -n "#### Question: <card name>" <blueprint>`  
   Đọc SQL trong section đó (blueprint SQL = SQL chuẩn)
4. **Đọc contract definition** cho từng concept được dùng:
   - Segments: `docs/analytics-handbook/semantic/segments.md`
   - Metrics: `docs/analytics-handbook/semantic/metrics.md`
   - Rules: `docs/analytics-handbook/semantic/rules.md`

**Nếu không tìm thấy blueprint:** ghi nhận "không có blueprint" và bỏ qua bước này. Không bịa contract.

---

### Bước 5 — Phân tích và giải thích

Với mỗi card đã deep-dive, báo cáo theo cấu trúc:

#### 0. Giới thiệu card (từ blueprint)

Đọc section tương ứng trong blueprint trước khi phân tích live data. Trình bày:

- **Tên card + blueprint file** (hoặc "không có blueprint")
- **Mục đích**: Domain Reference description — card này đo lường / hiển thị gì?
- **Scope đã khai báo**: `primary_scope` + `uses_concepts` từ frontmatter của blueprint
- **Filter dự kiến**: WHERE conditions trong blueprint SQL (scope, date window, exclusions)
- **Viz type dự kiến**: `display` từ blueprint metabase-viz block

Ví dụ format:
> **Net Revenue** · `ceo_weekly_pulse.md`
> - Mục đích: Hero metric — tổng net revenue tuần này (Mon-to-date) kèm WoW comparison
> - Scope: `scope_sales AND is_active_order` · concepts: `net_revenue`, `is_active_order`
> - Filter: ordered_at trong tuần hiện tại; exclude CANCELLED qua `is_active_order`
> - Viz: scalar (primary value + WoW column)

Nếu không có blueprint: ghi "Không có blueprint — phân tích từ live SQL." và bỏ qua phần này.

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

#### 4b. Contract compliance (nếu có blueprint)

So sánh live SQL với blueprint SQL + semantic contract definitions:

**Checklist từng concept trong `uses_concepts`:**

| Concept | Contract says | Live SQL dùng | Status |
|---|---|---|---|
| `scope_retail` | `WHERE scope_retail` (pre-computed) | ... | ✅/⚠️/❌ |
| `net_revenue` | `SUM(net_revenue)` | ... | ✅/⚠️/❌ |
| ... | ... | ... | ... |

**Status legend:**
- ✅ Compliant — live SQL dùng đúng pre-computed column/formula
- ⚠️ Diverged từ blueprint — live SQL khác blueprint SQL nhưng chưa rõ có vi phạm contract không
- ❌ Vi phạm contract — re-derive thủ công thay vì dùng pre-computed, hoặc dùng sai formula

**Các vi phạm thường gặp:**
- `customer_type = 'RETAIL' AND channel_key IN (...)` thay vì `scope_retail` → anti-pattern, thiếu status exclusion
- `total_price / 1.08` thay vì `net_revenue` → sai formula VAT
- `total_collected` thay vì `net_revenue` trong P&L card → VAT vẫn embedded

**Nếu không có blueprint nhưng có thể suy luận:**  
Xét SQL của card, đề xuất concept nào nên apply và tại sao. Ví dụ: "Card lọc `customer_type = 'RETAIL'` thủ công → nên dùng `scope_retail` theo semantic contract `segments.md#scope_retail`."

**Nếu blueprint không có `## Semantic Contract`:**  
Ghi nhận "blueprint chưa có contract" và đề xuất contract nào phù hợp dựa trên context của dashboard (scope, layer, metrics used).
