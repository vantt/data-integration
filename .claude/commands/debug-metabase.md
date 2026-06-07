# Debug Metabase Dashboard

Chạy debug script để lấy SQL thực tế + kết quả của từng card trong dashboard, sau đó phân tích và giải thích bằng tiếng Việt dễ hiểu.

## Steps

1. **Chạy debug script** với dashboard URL (summary mode trước):
   ```bash
   METABASE_URL="http://127.0.0.1:3001" METABASE_API_KEY="$(grep METABASE_API_KEY .env.docker | cut -d= -f2- | tr -d '\"')" \
     node scripts/debug/metabase-dashboard-debugger.js "$ARGUMENTS"
   ```
   Nếu thấy card nào 0 rows hoặc số lạ, deep-dive thêm:
   ```bash
   METABASE_URL="http://127.0.0.1:3001" METABASE_API_KEY="$(grep METABASE_API_KEY .env.docker | cut -d= -f2- | tr -d '\"')" \
     node scripts/debug/metabase-dashboard-debugger.js "$ARGUMENTS" --card <card_id>
   ```

2. **Đọc output** và phân tích:
   - Với mỗi card: so sánh SQL template vs SQL thực tế sau substitute
   - Kiểm tra parameter mappings — card nào nhận filter, card nào không
   - Phát hiện cards trả về 0 rows hoặc số liệu bất thường
   - Giải thích tác động của từng filter lên kết quả

3. **Báo cáo** bằng ngôn ngữ đơn giản, tập trung vào:
   - Filter nào đang được áp dụng và nó loại trừ dữ liệu nào
   - Card nào có vấn đề và tại sao
   - Gợi ý kiểm tra thêm nếu cần (ví dụ: chạy SQL trực tiếp với điều kiện khác)

## Phân tích cần làm

Khi đọc output của script, hãy chú ý:

**Filter analysis:**
- `scope` filter → loại trừ channel nào? SQL dùng `channel_code =` hay `channel_brand =` hay `market =`?
- `date` filter → date range là gì? SQL dùng `date_key BETWEEN` hay `ordered_at >=`? ICT hay UTC?
- `category` filter → map vào column nào trong fact table?

**Data quality signals:**
- Card trả về 0 rows → filter quá hẹp? hay thiếu data?
- Card không có parameter mapping → không bị ảnh hưởng bởi dashboard filter (có thể là bug)
- `(không có filter)` trên một parameter → card đang show ALL data thay vì filtered

**Common issues trong stack này:**
- `date_key` là ICT date integer (YYYYMMDD), không phải timestamp → filter sai nếu dùng timestamp
- `status IN ('CANCELLED','VOIDED')` phải được exclude trong revenue cards
- `scope` có thể map vào `channel_code`, `channel_brand`, hoặc `market` — check SQL template
- Shopee orders: `net_revenue` từ fact_orders có thể = 0, revenue thực ở fact_us_shipment_economics

## User Arguments

$ARGUMENTS
