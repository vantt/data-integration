# Design: Staff Identity Architecture — CRM + Warehouse

> Phiên bản: 2026-06-30 | Tác giả: Van Tran

---

## 1. Vấn đề và bối cảnh

Hệ thống hiện tại có 3 nguồn nhân viên riêng biệt, không có bridge dứt khoát:

- **Sapo** quản lý sales transaction (orders, sellers) với integer `account_id`
- **Lark** là SSO/HR với `lark_user_id` (`ou_...`)
- **CRM app** dùng UUID nội bộ, có `staff_id` (= Sapo account_id) trong schema **nhưng chưa wire**

Hậu quả:
- `mart_crm_activity_log` có `staff_user_id` (UUID) → không join được `dim_staff` → báo cáo cross-system bị broken
- `crm_task`, `crm_activity` biết assignee theo UUID nhưng warehouse không biết đó là seller nào
- Không thể tính KPI "doanh số theo nhân viên CRM" từ warehouse

---

## 2. Identity Landscape

```
┌─────────────────────────────────────────────────────────────────────┐
│  NGUỒN NGOÀI                                                        │
│                                                                     │
│  ┌──────────────────┐        ┌──────────────────┐                  │
│  │   SAPO (POS)     │        │  LARK / CF Access │                  │
│  │                  │        │                  │                  │
│  │  account_id INT  │        │  lark_user_id    │                  │
│  │  email           │        │  (ou_...)        │                  │
│  │  full_name       │        │  email           │                  │
│  └────────┬─────────┘        └────────┬─────────┘                  │
│           │ email (at provision)      │ lark_user_id + email        │
│           ▼                           ▼                             │
│  ┌──────────────────────────────────────────────────┐              │
│  │               CRM APP (SQLite)                   │              │
│  │                                                  │              │
│  │  user_id        TEXT  PK  (UUID)  ← all CRM FKs │              │
│  │  staff_id       INT        ← Sapo account_id    │              │
│  │  email          TEXT UNIQUE    ← lookup key only│              │
│  │  lark_user_id   TEXT           ← Lark API only  │              │
│  │  full_name      TEXT                            │              │
│  │  role           TEXT                            │              │
│  └──────────────────────────┬───────────────────────┘              │
│                             │ staff_id (INTEGER) — BRIDGE          │
│                             ▼                                       │
│  ┌──────────────────────────────────────────────────┐              │
│  │             WAREHOUSE (DuckDB)                   │              │
│  │                                                  │              │
│  │  dim_staff:                                      │              │
│  │    staff_key    INT    (surrogate PK)            │              │
│  │    staff_id     INT    (= Sapo account_id)       │              │
│  │    email        TEXT                             │              │
│  │    crm_user_id  TEXT   ← THÊM MỚI (UUID)        │              │
│  │                                                  │              │
│  │  fact_orders:                                    │              │
│  │    seller_staff_key → dim_staff.staff_key        │              │
│  │    creator_staff_key → dim_staff.staff_key       │              │
│  └──────────────────────────────────────────────────┘              │
└─────────────────────────────────────────────────────────────────────┘
```

**Quy tắc phân tầng:**
- UUID: FK nội bộ CRM (bất biến)
- `staff_id` (INT): bridge CRM ↔ Sapo ↔ Warehouse
- `email`: chỉ dùng tại provision time để lookup, không bao giờ là FK
- `lark_user_id`: chỉ dùng cho Lark API runtime, không join

---

## 3. Quyết định thiết kế

### D1 — UUID là PK nội bộ CRM (không thay đổi)

**Quyết định:** `crm_app_user.user_id` (UUID) là PK cho tất cả FK trong CRM.

**Lý do:**
- CRM tạo nhiều entity trước khi biết `staff_id` (ví dụ: invite user chưa có Sapo account)
- UUID tránh phụ thuộc vào external system khi tạo record
- Sapo có thể tạo lại account với `account_id` khác → UUID bền hơn làm PK

**Không làm:** Không dùng `staff_id` hay `lark_user_id` làm PK hay FK trong CRM.

---

### D2 — `staff_id` INTEGER là bridge CRM ↔ Sapo

**Quyết định:** `crm_app_user.staff_id` = Sapo `account_id`, là cột duy nhất nối CRM với Sapo/Warehouse.

**Lý do:**
- `staff_id` đã có trong schema, chỉ cần wire
- Warehouse `dim_staff.staff_id` cũng là Sapo account_id → join path đã rõ
- Integer key → join nhanh hơn text join theo email

**Ràng buộc:** `UNIQUE INDEX ON crm_app_user(staff_id) WHERE staff_id IS NOT NULL` — một Sapo account chỉ map 1 CRM user.

---

### D3 — Email là lookup key tại provision time

**Quyết định:** Email chỉ dùng để resolve `staff_id` và `lark_user_id` khi tạo/cập nhật CRM user. Không bao giờ dùng email làm FK hoặc join key trong warehouse.

**Lý do:**
- Email có thể thay đổi (đổi tên công ty, corporate rename)
- JOIN theo email ở serving layer tạo coupling mong manh
- Provision-time lookup có thể retry; runtime join không có fallback

---

### D4 — `crm_user_id` thêm vào `dim_staff`

**Quyết định:** Thêm cột `crm_user_id TEXT` vào `dim_staff` dbt model, load từ CRM export.

**Lý do:**
- Cho phép warehouse query `crm_activity` theo `dim_staff` mà không cần CRM join
- Reverse lookup: từ `staff_key` → `crm_user_id` → filter CRM tables
- Không tạo circular dependency vì warehouse chỉ đọc từ CRM export, không write ngược

**Không làm:** Không thêm `staff_key` vào CRM SQLite — warehouse key là ephemeral surrogate.

---

### D5 — `lark_user_id` là runtime-only

**Quyết định:** `lark_user_id` chỉ dùng khi gọi Lark API (send message, lookup calendar). Không join bất kỳ table nào theo `lark_user_id`.

**Lý do:**
- `lark_user_id` không có trong warehouse
- Lark API có rate limit → không phù hợp làm join key
- CF Access JWT đã có cả `email` + `lark_user_id` → dùng email để map về UUID tại auth middleware

---

## 4. Cross-System Join Patterns

### Before (broken)

```sql
-- mart_crm_activity_log có staff_user_id (UUID) nhưng không map được dim_staff
SELECT
    a.staff_user_id,   -- UUID — dead end trong warehouse
    SUM(o.net_revenue) AS revenue
FROM mart_crm_activity_log a
-- KHÔNG THỂ JOIN dim_staff vì không có crm_user_id ở đó
JOIN fact_orders o ON ???  -- không có bridge
```

### After (fixed)

```sql
-- Pattern 1: CRM activity → Warehouse orders (via staff_id)
SELECT
    u.full_name,
    u.role,
    SUM(o.net_revenue) AS revenue
FROM crm_app_user u                              -- CRM
JOIN dim_staff ds ON ds.staff_id = u.staff_id   -- bridge
JOIN fact_orders o ON o.seller_staff_key = ds.staff_key
WHERE o.date_key BETWEEN :start AND :end
GROUP BY 1, 2;

-- Pattern 2: Warehouse-only (dim_staff → crm_activity via crm_user_id)
SELECT
    ds.email,
    COUNT(a.activity_id) AS activity_count,
    SUM(o.net_revenue) AS revenue
FROM dim_staff ds
LEFT JOIN mart_crm_activity_log a ON a.staff_user_id = ds.crm_user_id
LEFT JOIN fact_orders o ON o.seller_staff_key = ds.staff_key
GROUP BY 1;

-- Pattern 3: Task performance by staff
SELECT
    u.full_name,
    COUNT(t.task_id) AS tasks_completed
FROM crm_task t
JOIN crm_app_user u ON u.user_id = t.assignee_user_id
WHERE t.status = 'done'
  AND t.staff_id IS NOT NULL   -- chỉ lấy user đã wire Sapo
GROUP BY 1;
```

### Join Chain tổng quát

```
crm_task.assignee_user_id (UUID)
  → crm_app_user.user_id
  → crm_app_user.staff_id (INT)
  = dim_staff.staff_id
  → dim_staff.staff_key
  → fact_orders.seller_staff_key
```

---

## 5. Implementation Roadmap

### Phase 1 — Wire `staff_id` trong CRM app (P0, 1-2 ngày)

**Mục tiêu:** `crm_app_user.staff_id` được populate tại provision và có thể cập nhật.

Các bước:
1. Thêm `staff_id` vào `CrmAppUser` entity model (nếu chưa có)
2. Expose `staff_id` qua repository layer (`upsert`, `find_by_staff_id`)
3. Service method `CrmUserService.resolve_staff_id(email)`:
   - Query DuckDB `dim_staff WHERE email = ?` (read_only=True)
   - Trả về `staff_id` INT hoặc `None`
4. Gọi `resolve_staff_id` tại provision endpoint (POST /users, PUT /users/:id)
5. Migration: `CREATE UNIQUE INDEX idx_crm_user_staff_id ON crm_app_user(staff_id) WHERE staff_id IS NOT NULL`

**Validation:** `SELECT user_id, staff_id, email FROM crm_app_user WHERE staff_id IS NOT NULL` → kiểm tra coverage.

---

### Phase 2 — `StaffIdResolver` service (P0, cùng sprint)

```python
# Pseudo-code
class StaffIdResolver:
    def __init__(self, duckdb_path: str):
        self._path = duckdb_path

    def resolve(self, email: str) -> int | None:
        with duckdb.connect(self._path, read_only=True) as con:
            row = con.execute(
                "SELECT staff_id FROM main_marts.dim_staff WHERE email = ?",
                [email]
            ).fetchone()
        return row[0] if row else None
```

- Inject vào provision handler, không dùng ở request path thông thường
- Cache TTL 5 phút nếu provision volume lớn (hiện tại không cần)

---

### Phase 3 — `dim_staff` thêm `crm_user_id` (P1, 1 ngày)

**File:** `transformation/models/marts/dim_staff.sql` (hoặc tương đương)

```sql
-- Thêm LEFT JOIN với CRM export
LEFT JOIN crm_user_export cue
    ON cue.staff_id = s.staff_id   -- join theo staff_id (INT)
```

Yêu cầu:
- CRM export chạy định kỳ (daily hoặc on-change) → file CSV/Parquet trong ingestion layer
- dbt model `stg_crm_users` đọc export đó
- Không dùng live SQLite read trong dbt (tránh lock + deployment coupling)

**Migration warehouse:** Vì `dim_staff` là dimension có `staff_key` surrogate, thêm cột không cần full-refresh nếu dùng `dbt run --select dim_staff`. Kiểm tra xem có incremental hay không.

---

### Phase 4 — `mart_staff_performance` (P2, future)

Cross-system reporting mart:

```sql
-- mart_staff_performance (daily grain)
SELECT
    ds.staff_key,
    ds.staff_id,
    ds.crm_user_id,
    ds.full_name,
    date_key,
    COUNT(DISTINCT o.order_code)  AS orders_count,
    SUM(o.net_revenue)            AS revenue,
    COUNT(DISTINCT a.activity_id) AS crm_activities,
    COUNT(DISTINCT t.task_id)     AS tasks_completed
FROM dim_staff ds
LEFT JOIN fact_orders o      ON o.seller_staff_key = ds.staff_key
LEFT JOIN mart_crm_activity_log a ON a.staff_user_id = ds.crm_user_id
    AND a.activity_date = o.date_key  -- nếu cần daily grain
LEFT JOIN crm_task t         ON t.assignee_user_id = ds.crm_user_id
    AND t.completed_date_key = o.date_key
GROUP BY 1, 2, 3, 4, 5
```

Không triển khai cho đến khi Phase 1-3 stable và `crm_user_id` coverage đủ cao (>80% active staff).

---

## 6. Edge Cases

### Staff không có Sapo account

Ví dụ: support staff, manager chỉ dùng CRM.

- `crm_app_user.staff_id = NULL` → hợp lệ, không vi phạm constraint
- Không xuất hiện trong `fact_orders` join chain (NULL không match)
- `mart_staff_performance`: LEFT JOIN trả về `orders_count = 0` → bình thường
- **Không nên** tạo synthetic Sapo account chỉ để fill `staff_id`

---

### Staff rời công ty (offboarding)

- Sapo: account bị deactivate, `account_id` giữ nguyên trong historical orders
- CRM: set `is_active = FALSE` (hoặc equivalent) — **không xóa** user để giữ FK integrity
- `dim_staff`: add `is_active BOOLEAN`, `deactivated_at TIMESTAMPTZ`
- Historical reports: vẫn join được qua `staff_key` → tính đúng doanh số cũ
- **Không làm:** Không NULL-out `staff_id` khi offboard — phá vỡ historical joins

---

### Email thay đổi

- CRM `email` là `UNIQUE NOT NULL` → update email → `StaffIdResolver` dùng email mới để re-resolve `staff_id`
- Nếu `staff_id` đã có và Sapo account cũng đổi email → không cần re-resolve (đã có `staff_id`)
- Nếu email đổi và `staff_id = NULL` → trigger re-provision để lookup lại

---

### Duplicate Sapo account (nhân viên tạo 2 Sapo accounts)

- `UNIQUE INDEX` trên `staff_id` ngăn 2 CRM users map cùng `staff_id`
- Resolution: deactivate account cũ trong Sapo, map `staff_id` về account canonical
- **Không** tạo composite logic trong warehouse để merge 2 `staff_id`

---

### Staff có trong Sapo nhưng chưa có CRM account

- `dim_staff.crm_user_id = NULL` → bình thường khi LEFT JOIN
- Không tạo phantom CRM user
- `mart_staff_performance`: revenue có, CRM activities = 0

---

## 7. Những gì KHÔNG làm và tại sao

| Không làm | Lý do |
|---|---|
| Dùng email làm FK hoặc JOIN key | Email có thể thay đổi; JOIN chậm hơn INT; tạo fragile coupling |
| Thêm `staff_key` (surrogate) vào CRM SQLite | Warehouse surrogate key là ephemeral, rebuild sau full-refresh → FK invalid |
| JOIN theo `lark_user_id` trong warehouse | Lark ID không có trong warehouse; Lark API không phải query engine |
| Live read DuckDB trong dbt models | Lock contention; deployment coupling; dbt nên đọc từ staged exports |
| Xóa CRM user khi offboard | FK integrity trong `crm_task`, `crm_activity`; historical audit cần |
| Tạo synthetic Sapo account cho non-sales staff | Pollutes Sapo data; quản lý phức tạp khi Sapo sync |
| `mart_staff_performance` trước khi Phase 1-3 done | Garbage in → garbage out; `crm_user_id` coverage thấp → misleading KPIs |
| Merge 2 Sapo accounts trong warehouse | Domain complexity không tương xứng với lợi ích; fix ở source (Sapo) |

---

## 8. Acceptance Criteria

Phase 1 done khi:
- [ ] `crm_app_user.staff_id` populated cho ≥90% active staff
- [ ] `UNIQUE INDEX` tồn tại và enforce
- [ ] `StaffIdResolver` có unit test với mock DuckDB response

Phase 2 done khi:
- [ ] `dim_staff.crm_user_id` không null cho cùng ≥90% active staff
- [ ] Query Pattern 2 (warehouse-only) trả đúng kết quả vs. manual check

Phase 3 done khi:
- [ ] `mart_crm_activity_log JOIN dim_staff ON crm_user_id` trả kết quả không rỗng
- [ ] Không có `staff_user_id` nào bị drop (LEFT JOIN coverage ≥90%)
