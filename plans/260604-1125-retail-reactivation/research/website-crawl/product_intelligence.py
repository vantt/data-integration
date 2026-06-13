#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Product Intelligence Synthesis
Reads website caches (finejapanvietnam + jpcshop) and cross-references
with DuckDB internal data to produce a unified Product Intelligence table
and 5 key findings (a-e).

Data anomaly handling:
- price=0 on web -> product "unavailable" / delisted on that site
- compare_at_price > 10x price -> compare_at artifact, discard for discount calc
  (e.g. VCST21004L001 fjvn has compare=49.4M vs real price ~2.8M)
- For discount %, use the best (non-anomalous) site data available.
"""
import os, sys, json, re
sys.stdout.reconfigure(encoding="utf-8")
import duckdb

BASE     = r"D:\Vantt\app\data-integration"
FJVN_JSON = BASE + r"\plans\260604-1125-retail-reactivation\research\website-crawl\products-all.json"
JPCS_JSON = BASE + r"\plans\260604-1125-retail-reactivation\research\website-crawl\jpcshop\products-all.json"
DB_PATH   = BASE + r"\app_data\data_lake\serving\standalone\sapo_export_latest.duckdb"
OUT_MD    = BASE + r"\plans\260604-1125-retail-reactivation\research\website-crawl\product-intelligence-synthesis-260613.md"

SKU_REGEX = re.compile(r'V[A-Z]{2,3}\d{5}[A-Z]\d{3}')

# ─── helpers ──────────────────────────────────────────────────────────────────
def fmt_vnd(v):
    if v is None or (isinstance(v, float) and v != v): return "N/A"
    return f"{v/1_000_000:.1f}M"

def fmt_pct(v):
    if v is None or (isinstance(v, float) and v != v): return "N/A"
    return f"{v:.1f}%"

def clean_discount(price, compare):
    """Return real discount% only when data looks valid (ratio <= 5x)."""
    if not price or not compare or compare <= price:
        return 0.0, False
    ratio = compare / price
    if ratio > 5:  # anomalous compare_at (data entry error)
        return 0.0, True   # True = anomaly flag
    return round((compare - price) / compare * 100, 1), False

# ─── 1. Load website caches ───────────────────────────────────────────────────
def load_site(path, site_label):
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    products = raw if isinstance(raw, list) else raw.get("products", [])
    rows = []
    for p in products:
        sku = None
        variants = p.get("variants", [])
        if variants:
            sku = variants[0].get("sku") or None
        if not sku:
            content = p.get("content", "") or ""
            m = SKU_REGEX.search(content)
            if m:
                sku = m.group(0)

        price   = p.get("price") or 0
        compare = p.get("compare_at_price_max") or p.get("compare_at_price") or 0
        disc, anomaly = clean_discount(price, compare)
        available = price > 0  # price=0 means not purchasable/out of stock

        rows.append({
            "site":          site_label,
            "name":          p.get("name", ""),
            "sku":           sku,
            "vendor":        p.get("vendor", ""),
            "price":         price,
            "compare_price": compare,
            "discount_pct":  disc,
            "available":     available,
            "compare_anomaly": anomaly,
        })
    return rows

fjvn_rows = load_site(FJVN_JSON, "finejapanvietnam")
jpcs_rows = load_site(JPCS_JSON, "jpcshop")
all_web   = fjvn_rows + jpcs_rows

fjvn_skus  = {r["sku"] for r in fjvn_rows if r["sku"]}
jpcs_skus  = {r["sku"] for r in jpcs_rows if r["sku"]}
web_skus   = fjvn_skus | jpcs_skus
both_skus  = fjvn_skus & jpcs_skus

# Web lookup: sku -> list of site rows
web_by_sku: dict[str, list] = {}
for r in all_web:
    if r["sku"]:
        web_by_sku.setdefault(r["sku"], []).append(r)

print(f"[web] fjvn={len(fjvn_rows)} jpcs={len(jpcs_rows)} web_skus={len(web_skus)} both={len(both_skus)}")

# ─── 2. DuckDB queries ────────────────────────────────────────────────────────
con = duckdb.connect(DB_PATH, read_only=True)

econ = con.execute("""
    SELECT
        product_code                            AS sku,
        product_name,
        SUM(net_revenue)                        AS total_net_revenue,
        SUM(units_sold)                         AS total_units,
        AVG(realized_margin_pct)                AS avg_margin_pct,
        SUM(realized_gross_profit)              AS total_realized_gp,
        COUNT(DISTINCT snapshot_month)          AS months_active,
        MAX(snapshot_month)                     AS last_month,
        ANY_VALUE(top_channel_name)             AS top_channel,
        SUM(CASE WHEN is_slow_mover THEN 1 ELSE 0 END) AS slow_mover_months
    FROM mart_sku_economics_monthly
    GROUP BY product_code, product_name
    ORDER BY total_net_revenue DESC
""").fetchdf()

total_retail_rev = econ["total_net_revenue"].sum()
econ_max_month   = str(econ["last_month"].max())[:7]
print(f"[DB] econ SKUs={len(econ)} total_rev={total_retail_rev:,.0f} last_month={econ_max_month}")

dim = con.execute("""
    SELECT DISTINCT sku, category, brand_name, last_sold_price, is_active
    FROM dim_products
""").fetchdf()
dim_by_sku = {row["sku"]: row for _, row in dim.iterrows()}

# ─── 3. Entry-repeat rate ─────────────────────────────────────────────────────
print("[DB] Computing entry-repeat rate ...")
entry_repeat = con.execute("""
WITH valid_orders AS (
    SELECT o.order_id, o.customer_key,
           DATE_TRUNC('day', o.ordered_at AT TIME ZONE 'Asia/Ho_Chi_Minh') AS order_day
    FROM fact_orders o
    WHERE o.scope_retail = TRUE
      AND o.status NOT IN ('CANCELLED','DRAFT')
),
ranked AS (
    SELECT vo.customer_key, vo.order_id, vo.order_day,
           ROW_NUMBER() OVER (PARTITION BY vo.customer_key ORDER BY vo.order_day) AS order_rank
    FROM valid_orders vo
),
first_order_lines AS (
    SELECT fs.order_id, fs.product_key, fs.net_revenue,
           r.customer_key
    FROM fact_sales fs
    JOIN ranked r ON fs.order_id = r.order_id AND r.order_rank = 1
),
entry_skus AS (
    SELECT fo.customer_key,
           FIRST_VALUE(dp.sku) OVER (
               PARTITION BY fo.customer_key
               ORDER BY fo.net_revenue DESC
           ) AS entry_sku
    FROM first_order_lines fo
    JOIN dim_products dp ON fo.product_key = dp.product_key
    QUALIFY ROW_NUMBER() OVER (PARTITION BY fo.customer_key ORDER BY fo.net_revenue DESC) = 1
),
repeaters AS (
    SELECT customer_key
    FROM ranked
    GROUP BY customer_key
    HAVING COUNT(DISTINCT order_id) >= 2
)
SELECT
    es.entry_sku,
    COUNT(DISTINCT es.customer_key)                                       AS entry_customers,
    COUNT(DISTINCT CASE WHEN r.customer_key IS NOT NULL
                        THEN es.customer_key END)                         AS repeat_customers
FROM entry_skus es
LEFT JOIN repeaters r ON es.customer_key = r.customer_key
GROUP BY es.entry_sku
HAVING entry_customers >= 3
ORDER BY repeat_customers DESC
""").fetchdf()

entry_repeat["repeat_rate"] = (
    entry_repeat["repeat_customers"] / entry_repeat["entry_customers"] * 100
).round(1)
er_by_sku = {row["entry_sku"]: row for _, row in entry_repeat.iterrows()}
print(f"[DB] entry_repeat rows={len(entry_repeat)}")

# ─── 4. Build unified Product Intelligence records ────────────────────────────
econ_by_sku = {row["sku"]: row for _, row in econ.iterrows()}
all_skus    = set(econ_by_sku.keys()) | web_skus

records = []
for sku in all_skus:
    e   = econ_by_sku.get(sku)
    d   = dim_by_sku.get(sku)
    er  = er_by_sku.get(sku)
    wb  = web_by_sku.get(sku, [])

    on_fjvn = any(w["site"] == "finejapanvietnam" for w in wb)
    on_jpcs = any(w["site"] == "jpcshop" for w in wb)
    on_web  = len(wb) > 0

    # Best web price: prefer available (price>0), prefer fjvn, fallback jpcs
    # For discount use the row with the cleanest compare (no anomaly)
    web_price = None
    web_disc  = 0.0
    web_avail = False
    # Priority: non-anomaly available > non-anomaly unavailable > anomaly
    candidates = sorted(wb, key=lambda w: (
        0 if (w["available"] and not w["compare_anomaly"]) else
        1 if (not w["available"] and not w["compare_anomaly"]) else 2
    ))
    if candidates:
        best = candidates[0]
        web_price = best["price"] if best["available"] else None
        web_disc  = best["discount_pct"]
        web_avail = best["available"]

    # Availability flags
    fjvn_avail = any(w["available"] for w in wb if w["site"] == "finejapanvietnam")
    jpcs_avail = any(w["available"] for w in wb if w["site"] == "jpcshop")

    name = (e["product_name"] if e is not None else None) or \
           (d["brand_name"] if d is not None else None) or \
           (wb[0]["name"] if wb else sku)
    cat  = d["category"] if d is not None else None

    records.append({
        "sku":             sku,
        "name":            name,
        "category":        cat,
        "on_fjvn":         on_fjvn,
        "on_jpcs":         on_jpcs,
        "on_web":          on_web,
        "fjvn_avail":      fjvn_avail,
        "jpcs_avail":      jpcs_avail,
        "web_price":       web_price,
        "web_disc_pct":    web_disc,
        "total_rev":       float(e["total_net_revenue"]) if e is not None else 0.0,
        "total_units":     float(e["total_units"])       if e is not None else 0.0,
        "avg_margin_pct":  float(e["avg_margin_pct"])    if e is not None else None,
        "months_active":   int(e["months_active"])       if e is not None else 0,
        "last_month":      str(e["last_month"])[:7]      if e is not None else None,
        "entry_customers": int(er["entry_customers"])    if er is not None else 0,
        "repeat_rate":     float(er["repeat_rate"])      if er is not None else None,
        "last_sold_price": float(d["last_sold_price"])   if d is not None and d["last_sold_price"] else None,
        "is_active":       bool(d["is_active"])          if d is not None else None,
    })

records.sort(key=lambda r: r["total_rev"], reverse=True)
for i, r in enumerate(records):
    r["rev_rank"] = i + 1

# ─── 5. Findings ─────────────────────────────────────────────────────────────
# (a) Gateway SKUs (entry>=5, repeat>=20%) absent from web
gateway_candidates = sorted(
    [r for r in records if r["entry_customers"] >= 5 and r["repeat_rate"] is not None
     and r["repeat_rate"] >= 20 and not r["on_web"]],
    key=lambda r: r["entry_customers"] * r["repeat_rate"], reverse=True
)

# (b) Dead-end on web: repeat_rate<=15% (or not in DB for repeat = unknown)
# Flag: present on web but low retention signal
deadend_on_web = sorted(
    [r for r in records if r["on_web"] and r["repeat_rate"] is not None and r["repeat_rate"] <= 15],
    key=lambda r: r["total_rev"], reverse=True
)
# Also flag web SKUs with NO internal data (catalog starvation / phantom listings)
web_no_db = [r for r in records if r["on_web"] and r["total_rev"] == 0]

# (c) Deep discount >30% on web (cleaned data only)
deep_disc_web = sorted(
    [r for r in records if r["on_web"] and r["web_disc_pct"] > 30 and r["web_price"] is not None],
    key=lambda r: r["web_disc_pct"], reverse=True
)
# Unavailable (price=0) on fjvn but listed
unavailable_fjvn = [r for r in records if r["on_fjvn"] and not r["fjvn_avail"]]

# (d) Revenue coverage
web_present_rev = sum(r["total_rev"] for r in records if r["on_web"])
coverage_pct    = web_present_rev / total_retail_rev * 100 if total_retail_rev else 0
not_on_web_top  = [r for r in records if not r["on_web"] and r["total_rev"] > 0][:12]

# (e) Web price vs internal realized price
price_gap = sorted(
    [r for r in records if r["on_web"] and r["web_price"] and r["last_sold_price"] and r["last_sold_price"] > 0],
    key=lambda r: abs(r["web_price"] - r["last_sold_price"]) / r["last_sold_price"], reverse=True
)

# ─── 6. Render Markdown ──────────────────────────────────────────────────────
L = []
A = L.append

A("# Product Intelligence Synthesis — 2026-06-13")
A("")
A(f"**Sources:** finejapanvietnam (15 SKU) + jpcshop (8 SKU) web caches | DuckDB `sapo_export_latest` (economics up to {econ_max_month})")
A(f"**Web SKUs:** {len(web_skus)} total ({len(both_skus)} on both sites, {len(unavailable_fjvn)} unavailable/price=0 on fjvn)")
A(f"**DB economics:** {len(econ)} SKUs | **Total retail net revenue:** {fmt_vnd(total_retail_rev)}")
A("")

# Cross-site price table
A("## Cross-site SKUs & Price Comparison")
A("")
A("| SKU | fjvn price | jpcs price | fjvn disc% | jpcs disc% | fjvn avail |")
A("|-----|-----------|-----------|-----------|-----------|-----------|")
for sku in sorted(both_skus):
    fw = next((w for w in all_web if w["sku"] == sku and w["site"] == "finejapanvietnam"), None)
    jw = next((w for w in all_web if w["sku"] == sku and w["site"] == "jpcshop"), None)
    fp = f"{fw['price']:,.0f}" if fw and fw["available"] else ("0/unavail" if fw else "-")
    jp = f"{jw['price']:,.0f}" if jw and jw["available"] else "-"
    fd = f"{fw['discount_pct']:.0f}%" if fw and not fw["compare_anomaly"] else ("anomaly" if fw else "-")
    jd = f"{jw['discount_pct']:.0f}%" if jw else "-"
    fa = "Y" if fw and fw["available"] else "NO"
    A(f"| {sku} | {fp} | {jp} | {fd} | {jd} | {fa} |")
A("")
A("> Note: fjvn VCSL19001H010 compare_at=11.25M (10x of actual price) — data entry error; disc% shown from jpcs.")
A("> Note: VCSL21002H010 and VCST21003L001 have price=0 on fjvn (unavailable/sold-out).")
A("")

# Main product intelligence table
top_skus   = {r["sku"] for r in records[:30]} | web_skus
table_rows = sorted([r for r in records if r["sku"] in top_skus],
                    key=lambda r: r["total_rev"], reverse=True)

A("## Product Intelligence Table")
A("")
A("Columns: `fjvn`/`jpcs` = listed (Y) or not (-); `avail` = purchasable on fjvn; `disc%` = cleaned web discount; `margin%` = avg realized_margin_pct; `rr%` = entry-repeat rate; `EC` = entry customer count")
A("")
A("| # | SKU | Name (short) | Cat | fjvn | jpcs | avail | disc% | Rev (M VND) | margin% | EC | rr% |")
A("|---|-----|-------------|-----|------|------|-------|-------|------------|---------|-----|-----|")
for r in table_rows:
    short = r["name"][:42] + "…" if r["name"] and len(r["name"]) > 42 else (r["name"] or "")
    cat_s = (r["category"] or "")[:16]
    on_f  = "Y" if r["on_fjvn"] else "-"
    on_j  = "Y" if r["on_jpcs"] else "-"
    av    = "Y" if r["fjvn_avail"] else ("-" if not r["on_fjvn"] else "NO")
    disc  = f"{r['web_disc_pct']:.0f}%" if r["web_disc_pct"] else "-"
    rev   = fmt_vnd(r["total_rev"]) if r["total_rev"] else "—"
    mg    = fmt_pct(r["avg_margin_pct"])
    ec    = str(r["entry_customers"]) if r["entry_customers"] else "-"
    rr    = fmt_pct(r["repeat_rate"])
    A(f"| {r['rev_rank']} | {r['sku']} | {short} | {cat_s} | {on_f} | {on_j} | {av} | {disc} | {rev} | {mg} | {ec} | {rr} |")
A("")

# ── Finding (a) ───────────────────────────────────────────────────────────────
A("## Finding a — Gateway SKUs absent from both D2C sites")
A("")
A(f"**{len(gateway_candidates)} SKUs** with ≥5 entry customers and repeat rate ≥20% are listed on NEITHER finejapanvietnam NOR jpcshop.")
A("")
if gateway_candidates:
    A("| SKU | Name | Category | EC | rr% | Rev (M) | margin% | Rev rank |")
    A("|-----|------|---------|-----|-----|---------|---------|---------|")
    for r in gateway_candidates[:15]:
        short = r["name"][:50] + "…" if r["name"] and len(r["name"]) > 50 else (r["name"] or "")
        A(f"| {r['sku']} | {short} | {r['category'] or ''} | {r['entry_customers']} | {fmt_pct(r['repeat_rate'])} | {fmt_vnd(r['total_rev'])} | {fmt_pct(r['avg_margin_pct'])} | {r['rev_rank']} |")
    A("")
    top5_missing_rev = sum(r["total_rev"] for r in gateway_candidates[:5])
    A(f"**Top 5 gateway-absent SKUs combined revenue: {fmt_vnd(top5_missing_rev)}**")
else:
    A("_No qualifying gateway SKUs found._")
A("")

# ── Finding (b) ───────────────────────────────────────────────────────────────
A("## Finding b — Web catalog quality: dead-end + phantom listings")
A("")
if deadend_on_web:
    A(f"**{len(deadend_on_web)} web SKU(s)** with repeat_rate ≤15% (low retention signal):")
    A("")
    A("| SKU | Name | disc% | rr% | EC | Rev (M) | Category |")
    A("|-----|------|-------|-----|-----|---------|---------|")
    for r in deadend_on_web[:10]:
        short = r["name"][:48] + "…" if r["name"] and len(r["name"]) > 48 else (r["name"] or "")
        A(f"| {r['sku']} | {short} | {r['web_disc_pct']:.0f}% | {fmt_pct(r['repeat_rate'])} | {r['entry_customers']} | {fmt_vnd(r['total_rev'])} | {r['category'] or ''} |")
else:
    A("All web SKUs with repeat rate data have repeat_rate >15%. No clear dead-ends detected at this threshold.")
A("")
if web_no_db:
    A(f"**{len(web_no_db)} web SKU(s) with zero revenue in DB** (phantom/new/non-Sapo):")
    for r in web_no_db:
        A(f"- `{r['sku']}` — {r['name'][:60]}")
A("")
if unavailable_fjvn:
    A(f"**{len(unavailable_fjvn)} fjvn SKU(s) listed but price=0 (unavailable/sold-out):**")
    for r in unavailable_fjvn:
        short = r["name"][:55]
        A(f"- `{r['sku']}` — {short} | rr%={fmt_pct(r['repeat_rate'])} | rev={fmt_vnd(r['total_rev'])}")
A("")

# ── Finding (c) ───────────────────────────────────────────────────────────────
A("## Finding c — Deep discount (>30%) x realized margin")
A("")
A("Using cleaned discount data (compare_at anomalies discarded). fjvn price=0 SKUs excluded.")
A("")
if deep_disc_web:
    A("| SKU | Name | Sites | Web disc% | Web price | margin% | Rev (M) | Assessment |")
    A("|-----|------|-------|-----------|-----------|---------|---------|-----------|")
    for r in deep_disc_web:
        short = r["name"][:42] + "…" if r["name"] and len(r["name"]) > 42 else (r["name"] or "")
        sites = []
        if r["on_fjvn"] and r["fjvn_avail"]: sites.append("fjvn")
        if r["on_jpcs"] and r["jpcs_avail"]: sites.append("jpcs")
        site_str = "+".join(sites) if sites else "listed"
        mg = r["avg_margin_pct"]
        if mg is None: assess = "no margin data"
        elif mg < 5:   assess = "BELOW/AT COST"
        elif mg < 20:  assess = "thin margin"
        elif mg < 40:  assess = "acceptable"
        else:          assess = "healthy margin"
        A(f"| {r['sku']} | {short} | {site_str} | {r['web_disc_pct']:.0f}% | {r['web_price']:,.0f} | {fmt_pct(mg)} | {fmt_vnd(r['total_rev'])} | {assess} |")
else:
    A("_No web SKUs with >30% discount (after anomaly filtering)._")
A("")
A("**Note on VCST21003L001 and VCSL21002H010:** these have price=0 on fjvn (unavailable). Their jpcs discount is 50% and 0% respectively — not included in margin-risk analysis.")
A("")

# ── Finding (d) ───────────────────────────────────────────────────────────────
A("## Finding d — D2C catalog revenue coverage")
A("")
A(f"| Metric | Value |")
A(f"|--------|-------|")
A(f"| Total internal retail net revenue | {fmt_vnd(total_retail_rev)} |")
A(f"| Revenue covered by web-listed SKUs | {fmt_vnd(web_present_rev)} ({coverage_pct:.1f}%) |")
A(f"| Revenue NOT on any D2C site | {fmt_vnd(total_retail_rev - web_present_rev)} ({100-coverage_pct:.1f}%) |")
A(f"| DB SKUs not on web | {len(not_on_web_top)} shown below (top 12 by rev) |")
A("")
A("### Top revenue SKUs absent from both D2C sites")
A("")
A("| SKU | Name | Rev (M) | Rev rank | margin% | rr% | Category |")
A("|-----|------|---------|----------|---------|-----|---------|")
for r in not_on_web_top:
    short = r["name"][:50] + "…" if r["name"] and len(r["name"]) > 50 else (r["name"] or "")
    A(f"| {r['sku']} | {short} | {fmt_vnd(r['total_rev'])} | {r['rev_rank']} | {fmt_pct(r['avg_margin_pct'])} | {fmt_pct(r['repeat_rate'])} | {r['category'] or ''} |")
A("")

# ── Finding (e) ───────────────────────────────────────────────────────────────
A("## Finding e — Web price vs internal last-sold price")
A("")
A("Both prices are VAT-inclusive. `last_sold_price` from dim_products = last recorded Sapo transaction price.")
A("")
if price_gap:
    A("| SKU | Name | Web price | Last sold | Delta% | Notes |")
    A("|-----|------|-----------|-----------|--------|-------|")
    for r in price_gap:
        short = r["name"][:42] + "…" if r["name"] and len(r["name"]) > 42 else (r["name"] or "")
        delta = (r["web_price"] - r["last_sold_price"]) / r["last_sold_price"] * 100
        note = "web HIGHER" if delta > 10 else ("web lower" if delta < -10 else "close")
        A(f"| {r['sku']} | {short} | {r['web_price']:,.0f} | {r['last_sold_price']:,.0f} | {delta:+.1f}% | {note} |")
else:
    A("_Insufficient data._")
A("")

# ── Summary ───────────────────────────────────────────────────────────────────
A("## Summary of Key Numbers")
A("")
A("| Metric | Value |")
A("|--------|-------|")
A(f"| Web products fjvn / jpcs | {len(fjvn_rows)} / {len(jpcs_rows)} |")
A(f"| Web SKUs total (union) | {len(web_skus)} |")
A(f"| SKUs on BOTH sites | {len(both_skus)} |")
A(f"| fjvn SKUs unavailable (price=0) | {len(unavailable_fjvn)} |")
A(f"| DB economics SKUs | {len(econ)} |")
A(f"| Economics date range | 2024-06 to {econ_max_month} |")
A(f"| Total retail net revenue | {fmt_vnd(total_retail_rev)} |")
A(f"| D2C web revenue coverage | {fmt_vnd(web_present_rev)} ({coverage_pct:.1f}%) |")
A(f"| Gateway SKUs absent from web (≥5 EC, ≥20% rr) | {len(gateway_candidates)} |")
A(f"| Dead-end SKUs on web (rr ≤15%) | {len(deadend_on_web)} |")
A(f"| Web SKUs with zero DB revenue (phantoms) | {len(web_no_db)} |")
A(f"| Deep-discount SKUs on web (>30%, cleaned) | {len(deep_disc_web)} |")
A("")

A("## Unresolved questions / caveats")
A("")
A("- `avg_margin_pct` = simple average across snapshot months, not revenue-weighted; seasonally skewed SKUs may show distorted margin.")
A("- `VTSC20001L001` (top gateway absent, rev 816.9M) — SKU with `(*)` prefix in name; verify if it is a bundle/pack SKU vs. single unit before prioritising for listing.")
A("- Entry-repeat rate: 'COR1' appeared as entry_sku in top results — likely an old/non-standard SKU code without dim_products mapping; excluded from main table.")
A("- jpcshop has no `data-fgotracking` HTML tags; SKU extracted from `variants[0].sku` directly.")
A("- PVN147/PVN148/PVN149/PVN150/PVN151 on fjvn are non-standard SKU codes (no `V` prefix pattern match) — likely non-Fine-Japan or promotional bundles; no DB economics row found.")
A("- H010 SKUs (VTSL24009H010, VTSL21001H010) use `realized_margin_pct` which has the 2026 COGS repoint correction applied — values should be trustworthy.")
A("- Web price vs last_sold_price gap analysis: if last_sold_price reflects a B2B/wholesale transaction, comparison to D2C web price may be misleading.")
A("")

os.makedirs(os.path.dirname(OUT_MD), exist_ok=True)
with open(OUT_MD, "w", encoding="utf-8") as f:
    f.write("\n".join(L))
print(f"\n[done] Written: {OUT_MD}")

# ── Console digest ────────────────────────────────────────────────────────────
print(f"\n=== PRODUCT INTELLIGENCE DIGEST ===")
print(f"Web: fjvn={len(fjvn_rows)} jpcs={len(jpcs_rows)} | web_skus={len(web_skus)} | both={len(both_skus)}")
print(f"DB:  {len(econ)} econ SKUs | total_rev={fmt_vnd(total_retail_rev)}")
print(f"Coverage: {fmt_vnd(web_present_rev)} / {fmt_vnd(total_retail_rev)} = {coverage_pct:.1f}%")
print(f"\n(a) Gateway absent ({len(gateway_candidates)} SKUs, entry>=5, rr>=20%):")
for r in gateway_candidates[:10]:
    print(f"    {r['sku']:20s} EC={r['entry_customers']:4d} rr={fmt_pct(r['repeat_rate']):>6s} rev={fmt_vnd(r['total_rev']):>8s} mg={fmt_pct(r['avg_margin_pct']):>7s} | {r['name'][:50]}")
print(f"\n(b) Dead-end on web ({len(deadend_on_web)} SKUs, rr<=15%):")
for r in deadend_on_web[:5]:
    print(f"    {r['sku']:20s} disc={r['web_disc_pct']:.0f}% rr={fmt_pct(r['repeat_rate'])} rev={fmt_vnd(r['total_rev'])}")
print(f"     Unavailable (price=0) on fjvn: {[r['sku'] for r in unavailable_fjvn]}")
print(f"     Phantom (zero DB rev): {[r['sku'] for r in web_no_db]}")
print(f"\n(c) Deep discount >30% on web (cleaned):")
for r in deep_disc_web:
    print(f"    {r['sku']:20s} disc={r['web_disc_pct']:.0f}% mg={fmt_pct(r['avg_margin_pct'])} web_price={r['web_price']:,.0f}")
print(f"\n(d) Coverage: {coverage_pct:.1f}% of retail rev on web")
print(f"    Top absent SKUs by rev:")
for r in not_on_web_top[:6]:
    print(f"    {r['sku']:20s} rev={fmt_vnd(r['total_rev'])} rr={fmt_pct(r['repeat_rate'])} rank={r['rev_rank']}")
print(f"\n(e) Web vs internal price gaps:")
for r in price_gap[:8]:
    delta = (r["web_price"] - r["last_sold_price"]) / r["last_sold_price"] * 100
    print(f"    {r['sku']:20s} web={r['web_price']:,.0f} last_sold={r['last_sold_price']:,.0f} delta={delta:+.1f}%")
