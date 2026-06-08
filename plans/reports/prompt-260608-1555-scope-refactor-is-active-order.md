# Agent Prompt: Scope Semantic Refactor — Tách `is_active_order` khỏi `scope_*`

## Mục tiêu

Refactor semantic scope trong toàn bộ data pipeline theo thiết kế mới:

| Concept | Định nghĩa cũ | Định nghĩa mới |
|---|---|---|
| `scope_sales` | `is_sales_channel AND status != 'CANCELLED'` | `is_sales_channel` (pure channel classification) |
| `scope_retail` | `scope_sales AND customer_type = 'RETAIL'` | `is_sales_channel AND customer_type = 'RETAIL'` |
| `scope_b2b` | `scope_sales AND customer_type IN (WHOLESALE, PARTNER)` | `is_sales_channel AND customer_type IN (WHOLESALE, PARTNER)` |
| `is_active_order` | *(không tồn tại)* | `status != 'CANCELLED'` (mới, tách riêng) |

**Lý do thiết kế:** `scope_*` là segmentation (đơn do mình bán, cho đối tượng khách nào) — không phụ thuộc status. `is_active_order` là status gate riêng biệt — chỉ áp dụng khi tính revenue/doanh thu, không áp dụng khi đếm tất cả đơn.

**Hệ quả:**
- Revenue cards: `WHERE scope_retail AND is_active_order`
- Order count cards: `WHERE scope_retail` (bao gồm cả cancelled)
- Cancelled count cards: `WHERE scope_retail AND NOT is_active_order`

---

## Môi trường

- **Working directory:** `D:\Vantt\app\data-integration`
- **OS:** Windows 11, shell PowerShell (dùng Bash tool cho POSIX scripts)
- **Dagster container:** `data_platform` (docker exec để chạy)
- **Metabase:** `http://127.0.0.1:3001`, API key từ `.env.docker` key `METABASE_API_KEY`
- **Sub-agents:** Dùng model `sonnet` cho tất cả sub-agents
- **Reports:** `D:\Vantt\app\data-integration\plans\reports\`

---

## Yêu cầu thực thi

- Chia thành **bước atomic**, mỗi bước hoàn chỉnh trước khi sang bước tiếp
- Tại mỗi bước **có ảnh hưởng tới dbt model hoặc Dagster pipeline**, bắt buộc chạy Dagster run thực tế và xác nhận không có lỗi trước khi tiếp tục
- Dùng **sub-agents sonnet** để xử lý song song các tác vụ độc lập (scan blueprints, update docs, etc.)
- Không giả định — đọc file thực tế trước khi sửa
- Không sửa blueprint mà không đọc SQL context của card đó trước

---

## Bước 1 — Scan toàn pipeline (READ-ONLY)

Spawn **3 sub-agents sonnet song song**:

### Sub-agent A: Scan dbt models
- Đọc `transformation/models/marts/sales/fact_orders.sql` — ghi nhận exact lines định nghĩa scope_sales, scope_retail, scope_b2b
- Đọc `transformation/models/marts/sales/fact_order_economics.sql` — ghi nhận chỗ nào pass scope columns xuống
- Grep toàn bộ `transformation/` cho `scope_sales|scope_retail|scope_b2b|is_active_order` — liệt kê file và line numbers
- Output: danh sách file/line cần sửa trong dbt layer

### Sub-agent B: Scan blueprints & classify SQL patterns
- Grep `docs/analytics-handbook/blueprints/**/*.md` cho `scope_retail|scope_sales|scope_b2b`
- Với mỗi blueprint file tìm được, đọc **tất cả SQL blocks** trong file đó
- Phân loại từng card SQL vào 1 trong 3 nhóm:
  - **`revenue`** — có `SUM(net_revenue)`, `SUM(gross_revenue)`, `SUM(total_collected)`, `AVG(`, `ROUND(` revenue metrics → cần thêm `AND o.is_active_order`
  - **`count_all`** — chỉ `COUNT(*)` hoặc `COUNT(DISTINCT order_id)` không kèm revenue → KHÔNG thêm is_active_order (đếm tất cả đơn kể cả cancelled)
  - **`count_cancelled`** — đang filter `status = 'CANCELLED'` → đổi thành `AND NOT o.is_active_order`
  - **`ambiguous`** — không rõ, cần human decision
- Output: classification table dạng `| blueprint_file | card_name | nhóm | lý_do |`

### Sub-agent C: Scan semantic docs & Rill
- Đọc `docs/analytics-handbook/semantic/segments.md` — full content
- Đọc `docs/analytics-handbook/AGENTS.md` — section scope hierarchy (grep "scope_sales|scope_retail|Scope Hierarchy")
- Đọc `docs/analytics-handbook/blueprints/rill/*.yaml` — grep scope references
- Output: danh sách sections cần update trong docs + rill files

**Tổng hợp:** Sau khi 3 sub-agents hoàn thành, tổng hợp thành scan report tại `plans/reports/scout-260608-scope-refactor.md`. Liệt kê bất kỳ `ambiguous` card nào để xử lý riêng.

---

## Bước 2 — Cập nhật `fact_orders.sql`

**Chỉ sửa `transformation/models/marts/sales/fact_orders.sql`**, không sửa file nào khác ở bước này.

Thay đổi:
```sql
-- CŨ
COALESCE(ch.is_sales_channel, false)
    AND orders.status != 'CANCELLED'               AS scope_sales,
COALESCE(ch.is_sales_channel, false)
    AND orders.status != 'CANCELLED'
    AND COALESCE(cu2.customer_type, 'RETAIL') = 'RETAIL'           AS scope_retail,
COALESCE(ch.is_sales_channel, false)
    AND orders.status != 'CANCELLED'
    AND COALESCE(cu2.customer_type, 'RETAIL') IN ('WHOLESALE', 'PARTNER') AS scope_b2b

-- MỚI
COALESCE(ch.is_sales_channel, false)                               AS scope_sales,
COALESCE(ch.is_sales_channel, false)
    AND COALESCE(cu2.customer_type, 'RETAIL') = 'RETAIL'           AS scope_retail,
COALESCE(ch.is_sales_channel, false)
    AND COALESCE(cu2.customer_type, 'RETAIL') IN ('WHOLESALE', 'PARTNER') AS scope_b2b,
orders.status != 'CANCELLED'                                       AS is_active_order
```

Sau khi sửa, cập nhật comment block trên section đó cho rõ ràng.

### ✅ Dagster run bắt buộc sau Bước 2

```bash
docker exec data_platform dagster asset materialize \
  --select "fact_orders" \
  -f orchestration/definitions.py
```

Nếu lệnh trên không work, thử các alternative:
- `docker exec data_platform dagster asset materialize --select fact_orders`
- Check Dagster logs: `docker logs data_platform --tail 100`
- Hoặc trigger qua Dagster GraphQL API tại `http://127.0.0.1:3000` (check port thực tế trong `.env.docker` hoặc `docker-compose.yml`)

**Không tiếp tục Bước 3 nếu Dagster run thất bại.** Debug và fix trước.

---

## Bước 3 — Cập nhật `fact_order_economics.sql`

Đọc file `transformation/models/marts/sales/fact_order_economics.sql`, xác định chỗ nào pass `scope_sales`/`scope_retail` từ fact_orders xuống. Model này kế thừa các columns từ fact_orders qua JOIN — cần kiểm tra xem có chỗ nào hard-code lại status filter không, hay chỉ SELECT columns.

Nếu chỉ pass-through columns → không cần sửa logic, chỉ cần đảm bảo `is_active_order` cũng được SELECT qua nếu cần.

### ✅ Dagster run bắt buộc sau Bước 3

Materialize `fact_order_economics` và verify không có lỗi.

---

## Bước 4 — Cập nhật Semantic Docs

Spawn **2 sub-agents sonnet song song**:

### Sub-agent A: Cập nhật `segments.md`
Sửa `docs/analytics-handbook/semantic/segments.md`:

1. **Scope Hierarchy diagram** — update để reflect cấu trúc mới:
```
all_orders
    └── scope_sales  (is_sales_channel=true)
            ├── scope_retail  (+ customer_type=RETAIL)
            ├── scope_b2b     (+ customer_type IN WHOLESALE, PARTNER)
            └── [STAFF, KOL]

is_active_order  (status != 'CANCELLED') — cross-cutting, áp dụng độc lập với scope
```

2. **`scope_sales` section** — update Definition, Rule, Intent, Anti-patterns
3. **`scope_retail` section** — update Definition, Rule (bỏ status filter)
4. **`scope_b2b` section** — update Definition, Rule (bỏ status filter)
5. **Thêm section `is_active_order` mới** — theo format giống các section khác:
   - Definition: "Đơn hàng chưa bị huỷ — status gate cho revenue calculations"
   - Rule: `status != 'CANCELLED'`
   - Intent: Dùng kết hợp với scope_* khi tính revenue metrics. Không dùng khi đếm tổng số đơn.
   - When to Use: `WHERE scope_retail AND is_active_order` cho revenue; `WHERE scope_retail` cho tổng đơn
   - Anti-patterns: đừng embed vào scope definition, đừng dùng `status != 'CANCELLED'` inline
   - Used In: mọi revenue card

### Sub-agent B: Cập nhật `AGENTS.md`
Sửa section scope hierarchy trong `docs/analytics-handbook/AGENTS.md` (grep "scope_sales|Scope Hierarchy") để reflect definitions mới.

---

## Bước 5 — Cập nhật Blueprints

Dựa trên classification table từ Bước 1 Sub-agent B, spawn **sub-agents sonnet** để xử lý blueprints theo batch (tối đa 4 blueprints/agent để tránh context quá lớn).

**Với mỗi blueprint:**

### `revenue` cards
Thêm `AND o.is_active_order` vào WHERE clause sau `AND o.scope_retail` (hoặc `scope_sales`, `scope_b2b`):
```sql
-- CŨ
WHERE date(o.ordered_at) = current_date - INTERVAL '1 day'
  AND o.scope_retail

-- MỚI
WHERE date(o.ordered_at) = current_date - INTERVAL '1 day'
  AND o.scope_retail
  AND o.is_active_order
```

### `count_all` cards
**Không thêm** `is_active_order` — đây là intent đúng (đếm tất cả đơn kể cả cancelled).

### `count_cancelled` cards
Đổi `AND o.status = 'CANCELLED'` thành `AND NOT o.is_active_order`:
```sql
-- CŨ
WHERE ... AND o.status = 'CANCELLED' AND c.customer_type = 'RETAIL'

-- MỚI
WHERE ... AND o.scope_retail AND NOT o.is_active_order
```

### Semantic Contract sections
Với mỗi blueprint có `## Semantic Contract`, cập nhật:
- `uses_concepts` — thêm `is_active_order` nếu blueprint có revenue cards
- Contract body — cập nhật compliance table và notes

**Lưu ý đặc biệt:**
- Blueprint `b2b_*`: dùng `scope_b2b` thay `scope_retail` — xử lý tương tự
- Blueprint `ceo_*`: dùng `scope_sales` — revenue cards thêm `AND is_active_order`
- `ambiguous` cards từ Bước 1: đọc kỹ SQL, quyết định theo intent, ghi note lý do

---

## Bước 6 — Deploy Blueprints lên Metabase

Sau khi tất cả blueprints được cập nhật, deploy:

```bash
# Deploy từng blueprint có thay đổi
METABASE_URL="http://127.0.0.1:3001" \
METABASE_API_KEY="$(grep METABASE_API_KEY .env.docker | cut -d= -f2- | tr -d '\"')" \
  node .skills/metabase-automation/scripts/deploy_from_markdown.js <blueprint.md>
```

Deploy theo thứ tự: blueprints ít phụ thuộc trước, CEO/executive dashboards sau.

**Ghi nhận:** Log lại các card nào được update vs skip, bất kỳ warning nào từ deploy script.

---

## Bước 7 — Verify End-to-End

Spawn **sub-agent sonnet**:

Chạy debug-metabase cho dashboard Yesterday's Sales (dashboard 42) để verify Total Orders và Net Revenue cho kết quả đúng:

```bash
METABASE_URL="http://127.0.0.1:3001" \
METABASE_API_KEY="$(grep METABASE_API_KEY .env.docker | cut -d= -f2- | tr -d '\"')" \
  node .skills/debug-metabase/scripts/metabase-dashboard-debugger.js \
  "http://bi.lan.fwg.vn/dashboard/42-yesterdays-sales-retail?tab=123" \
  --card 1221 --no-cache
```

Verify:
- Total Orders count **bao gồm** cancelled orders (= old Total Orders + Cancelled Orders)
- Net Revenue count **không đổi** (vì revenue cards đã thêm is_active_order)
- Cancelled Orders card vẫn chạy đúng

---

## Bước 8 — Commit

Commit với message:

```
refactor(semantic): split is_active_order from scope_* definitions

scope_sales/retail/b2b now represent pure channel+segment classification.
is_active_order (status != 'CANCELLED') added as separate pre-computed gate.
Revenue cards explicitly use scope_retail AND is_active_order.
Order count cards use scope_retail only (includes cancelled).
```

---

## Output mong đợi

1. `plans/reports/scout-260608-scope-refactor.md` — scan report từ Bước 1
2. Tất cả dbt models đã pass Dagster run
3. `segments.md` updated với is_active_order section
4. Tất cả blueprints classified và updated
5. Metabase deployed và verified
6. Commit sạch

## Unresolved / cần human decision trước khi tiếp tục

- **New Customers, Returning Customers cards**: Nên đếm customers có đơn cancelled không? (Current logic dùng scope_retail nên sẽ include cancelled sau refactor — có thể không đúng intent). Nếu không có hướng dẫn rõ từ user, default: **thêm `AND is_active_order`** vì customer analytics thường chỉ tính đơn thực sự hoàn thành.
- **`[STAFF, KOL]` orders**: scope_sales mới sẽ include STAFF/KOL orders bị cancelled — có thể tăng số lượng trong All-scope dashboards. Verify với business context.
