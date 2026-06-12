# Guide: Chọn BI Tool — Metabase vs Evidence.dev

> Tài liệu này định nghĩa tiêu chí chọn deployment tool cho analytics artifacts.
> Dùng khi tạo playbook mới (field `**Tool:**`) hoặc khi quyết định migrate dashboard hiện có.
> Mọi logic nghiệp vụ vẫn tham chiếu từ `domains/`; tài liệu này chỉ cover deployment decision.
>
> **3 tools đang deployed**: Metabase (`bi.lan.fwg.vn`), Rill (`rill.lan.fwg.vn`), Evidence.dev (planned).

---

## Quick Decision Table

| Câu hỏi | Trả lời | Tool |
|---------|---------|------|
| User cần tự do slice/dice theo nhiều dimension (ad-hoc)? | Có | Rill |
| Analyst self-serve exploration, không cần fixed layout? | Có | Rill |
| Metrics đã định nghĩa, muốn explore tự do? | Có | Rill |
| Có filter interactive phức tạp trên fixed dashboard? | Có | Metabase |
| Cadence là daily hoặc real-time, layout cố định? | Có | Metabase |
| Cần email alert / subscription? | Có | Metabase |
| Ops team dùng dashboard có layout cố định? | Có | Metabase |
| Parquet mart nguồn > 250MB và không phải Rill? | Có | Metabase |
| Report dạng document / narrative (text + chart)? | Có | Evidence |
| Cadence weekly / monthly, shareable? | Có | Evidence |
| Export PDF / print là yêu cầu chính? | Có | Evidence |
| Audience là executive / external stakeholder? | Có | Evidence |

**Default**: Không chắc → chọn **Metabase**.

---

## Tiêu chí chi tiết

### 0. Rill — Exploration Tool (tầng riêng)

Rill khác 2 tools còn lại về mặt paradigm: không phải fixed dashboard, không phải static report — mà là **metrics explorer**.

- **Blueprint format**: YAML (không phải Markdown như Metabase/Evidence)
- **Blueprint path**: `blueprints/rill/*.yaml`
- **Playbook location**: `playbooks/rill/` (subfolder riêng, structure khác)
- **Điểm mạnh**: Slice/dice tự do theo bất kỳ dimension nào, time comparison built-in, pivot, DuckDB-native nên query parquet rất nhanh
- **Điểm yếu**: Không có fixed layout, không email alert, không customize text/narrative
- **Dùng khi**: Analyst cần tự khám phá data, metrics đã định nghĩa nhưng câu hỏi chưa biết trước, ad-hoc exploration

Rill playbooks dùng field `**Metrics View:**` thay vì `**Tool:**` vì chúng có structure riêng biệt (xem `playbooks/rill/` cho examples).

### 1. Interactivity Level

- **Metabase**: Full interactive — date picker, category dropdown, drill-through card, URL filter params. Đã có `DateBound` + `CategoryDrop` patterns hoàn chỉnh.
- **Evidence**: Filter cơ bản qua SQL template `${inputs.param}`. **Không có cross-filtering** (click bar → filter chart khác). Filter stability còn bug đang được fix (GitHub #1566). Phù hợp cho explore nhẹ, không phù hợp cho operational drill-down.

### 2. Data Freshness

- **Metabase**: Query live — luôn có data mới nhất mỗi lần load.
- **Evidence**: Point-in-time — cần rebuild site để có data mới. Phù hợp khi data refresh theo chu kỳ (daily cron export parquet → rebuild site). Không phù hợp nếu user cần data intraday.

### 3. Data Size

- **Metabase**: Không giới hạn — query server-side DuckDB/PostgreSQL.
- **Evidence (DuckDB WASM)**: Practical limit **~250MB per parquet file** trước khi filter lag noticeably. WASM memory ceiling là 4GB, nhưng 10M+ rows để lại memory footprint lớn. HTTP range requests được support nhưng single-threaded WASM thường làm full-download nhanh hơn range-request trên file > 500MB.
  - **Rule cho project này**: Mart file nào > 250MB → không dùng Evidence client-side WASM. Dùng Evidence data loaders (server-side export tại build time) thay thế.

### 4. Report Format

- **Metabase**: Dashboard grid cố định (18-column). Không kiểm soát typography, spacing, layout ngoài grid.
- **Evidence**: Full HTML page — kiểm soát typography, layout, mix text + chart tự do. Có `PageBreak` component, PDF export built-in (top-right menu), CSV per-component. Phù hợp báo cáo executive dạng document.

### 5. Alert & Subscription

- **Metabase**: Native email alerts (threshold-based), dashboard subscription (scheduled email). Quan trọng cho ops team cần push notification.
- **Evidence**: Không có alert native. Cần external cron + custom notification nếu muốn.

### 6. Sharing & Embedding

- **Metabase**: Internal link (cần login). Enterprise plan mới có signed embedding.
- **Evidence**: Static URL — copy link là share được. Có thể host trên Netlify/GitHub Pages miễn phí. Embeddable trong `<iframe>` mà không cần license.

---

## Decision Tree

```
User cần tự do explore (ad-hoc, không biết câu hỏi trước)?
├── Có → RILL
└── Không (layout/format đã biết trước)
    ├── Cần cross-filter / drill-down trên fixed dashboard?
    │   ├── Có → METABASE
    │   └── Không
    │       ├── Mart > 250MB?
    │       │   ├── Có → METABASE (hoặc Evidence + data loader)
    │       │   └── Không
    │       │       ├── Cần email alert?
    │       │       │   ├── Có → METABASE
    │       │       │   └── Không
    │       │       │       ├── Cadence daily ops, fixed layout?
    │       │       │       │   ├── Có → METABASE
    │       │       │       │   └── Không → EVIDENCE
```

---

## Playbook Archetype → Tool Mapping

| Archetype | Typical Use Case | Default Tool |
|-----------|-----------------|-------------|
| Operational Cockpit | Daily ops, store manager, intraday monitoring | Metabase |
| Executive Pulse | Weekly/monthly CEO/CFO scorecard | Evidence |
| Exploratory Tool | Ad-hoc drill-down, analyst self-serve, dimensional pivot | **Rill** |
| Report Document | Shareable monthly report, investor brief | Evidence |
| Reconciliation Monitor | Daily data quality check, ops-only | Metabase |
| Channel Analytics | Weekly/monthly marketing report | Evidence |
| Metrics Explorer | Free-form analysis, metrics defined but questions unknown | **Rill** |

---

## Evidence.dev: Khi nào dùng Data Loaders thay WASM

Nếu mart > 250MB nhưng vẫn muốn dùng Evidence (vì report format phù hợp):

```python
# src/data/daily-revenue.parquet.py  ← chạy tại build time, không phải runtime
import duckdb
conn = duckdb.connect("path/to/olap.duckdb", read_only=True)
# Pre-aggregate xuống < 50MB trước khi bake vào static site
conn.execute("COPY (SELECT date_key, channel, sum(revenue) as revenue FROM fact_orders GROUP BY 1,2) TO '/dev/stdout' (FORMAT PARQUET)")
```

Data loader chạy server-side khi build → output parquet nhỏ → browser load nhanh. Phù hợp cho mart lớn nhưng chỉ cần aggregate view.

---

## Nguồn tham khảo

- Evidence.dev Docs: Filters, Exports, Queries — docs.evidence.dev
- DuckDB-WASM memory issue: github.com/duckdb/duckdb-wasm/issues/1904
- DuckDB-WASM range requests: github.com/duckdb/duckdb-wasm/discussions/1944
- Evidence filter bug: github.com/evidence-dev/evidence/issues/1566
