# dbt-Metabase Integration Guide

## 1. Tổng quan

Tích hợp này hoạt động theo **2 chiều**:

| Chiều | Tool | Mục đích |
|---|---|---|
| Metabase → dbt | `exposures.yml` | Lineage: card nào dùng mart nào |
| dbt → Metabase | `export_models` | Push descriptions từ schema.yml lên Metabase field metadata |

---

## 2. Architecture

```
dbt manifest (main_marts.fact_orders)
        │
        │  DEFAULT_SCHEMA patch = "main_marts"
        ▼
dbt-metabase wrapper scripts
        │
        │  schema_filter=["main_marts"]
        ▼
olap.duckdb
  ├── main.fact_orders          ← view gốc (Metabase SQL cards dùng)
  └── main_marts.fact_orders    ← alias view (dbt-metabase dùng để resolve lineage)
        │
        ▼
Metabase (port 3001)  ←  METABASE_API_KEY in .env.local
```

**Tại sao cần `main_marts` alias:**
- dbt manifest đặt tên model là `main_marts.fact_orders` (target=`main` + `+schema: marts`)
- Metabase SQL cards dùng bare name: `FROM fact_orders` (không có schema prefix)
- dbt-metabase SQL parser map bare name → `DEFAULT_SCHEMA` — mặc định hardcode `"PUBLIC"`
- Patch `DEFAULT_SCHEMA = "main_marts"` + tạo alias schema trong `olap.duckdb` → parser resolve đúng

**Script tạo alias views:** `scripts/provisioning/bootstrap_serving_views.py`
- Tạo `main_marts` schema trong `olap.duckdb`
- Với mỗi mart: `CREATE OR REPLACE VIEW main_marts.{table} AS SELECT * FROM main.{table}`
- An toàn khi chạy lúc Metabase đang up (Metabase dùng `read_only=true` → không lock file)

---

## 3. Operations

### Quick reference

| Tác vụ | Lệnh |
|---|---|
| Regenerate exposures.yml | `C:\Python314\python.exe tools/run-dbt-metabase-exposures.py` |
| Push descriptions → Metabase | `C:\Python314\python.exe tools/run-dbt-metabase-models.py` |
| Rebuild alias views | `docker compose exec data_platform python scripts/provisioning/bootstrap_serving_views.py` |
| Restart Dagster sau schema.yml change | `docker restart data_platform` |

---

### 3.1 Regenerate `exposures.yml`

**Khi nào:** Thêm/xóa Metabase card, thay đổi SQL của card hiện có.

```powershell
# Từ thư mục gốc D:/Vantt/app/data-integration
C:\Python314\python.exe tools/run-dbt-metabase-exposures.py
```

Output: `transformation/exposures.yml` — **gitignored**, regenerate mỗi khi cần.

**Verify:** Mở file và kiểm tra `depends_on` không rỗng:
```yaml
# Đúng
depends_on:
  - ref('fact_orders')
  - ref('dim_customers')

# Sai — DEFAULT_SCHEMA chưa được patch
depends_on: []
```

---

### 3.2 Push descriptions lên Metabase

**Khi nào:** Sau khi sửa `description:` trong `transformation/models/**/schema.yml`.

```powershell
C:\Python314\python.exe tools/run-dbt-metabase-models.py
```

Flags tùy chọn:
```
--manifest PATH      # mặc định: transformation/target/manifest.json
--database NAME      # mặc định: Sapo
--order-fields       # giữ thứ tự column theo dbt project
```

Script tự động:
- `sync_timeout=0` — bỏ qua bước sync Metabase (staging tables không tồn tại trong `olap.duckdb`)
- `schema_filter=["main_marts"]` — chỉ push mart tables
- Exclude `dim_customers_base`, `int_customer_metrics` — intermediate models, không có trong `olap.duckdb`

**Expected warning (không phải lỗi):**
```
[warn] Non-critical ... — descriptions were still written
```
Nguyên nhân: FK references đến `dim_customers_base` không được serve. Descriptions vẫn được ghi đúng.

---

### 3.3 Thêm descriptions vào schema.yml

```yaml
# transformation/models/marts/core/schema.yml
models:
  - name: fact_orders
    description: "Order-level fact table. Granularity: 1 row per order."
    columns:
      - name: order_id
        description: "Sapo order ID (primary key)."
      - name: net_revenue
        description: "Revenue sau VAT. Công thức: total_collected − vat_amount."
```

Sau khi sửa:
1. Rebuild manifest: `docker compose exec data_platform dbt compile` (hoặc `dbt build`)
2. Push lên Metabase: `C:\Python314\python.exe tools/run-dbt-metabase-models.py`
3. Restart Dagster: `docker restart data_platform`

---

## 4. Troubleshooting

### 4.1 Dagster KeyError sau khi sửa schema.yml

**Triệu chứng:**
```
KeyError: 'test.data_integration.not_null_fact_orders_order_id.xxxx'
```

**Nguyên nhân:** Dagster pre-parse dbt manifest lúc container khởi động. Thêm test node mới → node ID không có trong manifest cũ trong memory.

**Fix:**
```powershell
docker restart data_platform
```

---

### 4.2 `depends_on: []` trong exposures.yml

**Nguyên nhân:** Chạy `dbt-metabase` CLI trực tiếp thay vì wrapper script — DEFAULT_SCHEMA = "PUBLIC" không match `main_marts`.

**Fix:** LUÔN dùng wrapper:
```powershell
# ĐÚNG
C:\Python314\python.exe tools/run-dbt-metabase-exposures.py

# SAI — tuyệt đối không dùng
dbt-metabase exposures ...
```

---

### 4.3 Models sync timeout

**Triệu chứng:**
```
MetabaseStateError: Unable to sync models with Metabase
```

**Nguyên nhân:** Default sync loop chờ staging/source tables xuất hiện trong Metabase — nhưng `olap.duckdb` chỉ chứa mart tables.

**Fix:** Wrapper đã set `sync_timeout=0` mặc định. Nếu vẫn lỗi, kiểm tra `--sync-timeout 0` được truyền đúng.

---

### 4.4 `main_marts` schema missing trong olap.duckdb

**Triệu chứng:** `exposures.yml` có `depends_on` đúng nhưng lineage vẫn trống trong dbt docs.

**Fix:** Rebuild alias views:
```powershell
docker compose exec data_platform python scripts/provisioning/bootstrap_serving_views.py
```

---

## 5. Rill Exposures

File `transformation/models/exposures_rill.yml` — **committed vào git**, quản lý thủ công.

Rill không có API để dbt-metabase scrape, nên dependencies được khai báo tĩnh. Mỗi exposure map: Rill explore → metrics_view → dbt mart tables.

**Khi nào update:** Thêm mart table mới vào Rill explore, hoặc tạo explore mới.

```yaml
# Ví dụ thêm explore mới
- name: rill_my_new_dashboard
  type: dashboard
  maturity: medium
  url: http://rill.lan.fwg.vn/my_new_dashboard
  depends_on:
    - ref('fact_orders')
    - ref('dim_products')
  owner:
    name: Analytics Team
    email: tetnu26@gmail.com
```

Rill exposures không cần regenerate — edit trực tiếp file và commit.

---

## 6. Credentials

Cả hai wrapper scripts đọc từ `.env.local` tại project root.

```bash
# .env.local
METABASE_URL=http://127.0.0.1:3001
METABASE_API_KEY=mb_xxxxxxxxxxxx
```

Fallback auth: `METABASE_USERNAME` / `METABASE_PASSWORD` nếu không có API key.
