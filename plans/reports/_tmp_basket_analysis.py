"""
Basket analysis: items per order, top pairs, discount motivation
Retail active orders only. All orders (not just first order).
max_discount_rate is stored on 0-100 scale (percent), NOT 0-1.
"""
import duckdb

DB = "/app/var/data_lake/serving/olap.duckdb"
con = duckdb.connect(DB, read_only=True)

SEP = "=" * 80

# ── 0. Sanity: check max_discount_rate scale ─────────────────────────────────
print(SEP)
print("0. DISCOUNT RATE SANITY CHECK")
print(SEP)
probe = con.execute("""
    SELECT MIN(max_discount_rate), MAX(max_discount_rate), ROUND(AVG(max_discount_rate), 2),
           COUNT(*) FILTER (WHERE max_discount_rate > 1) AS above_1_pct,
           COUNT(*) FILTER (WHERE max_discount_rate = 0) AS exactly_zero,
           COUNT(*) FILTER (WHERE max_discount_rate IS NULL) AS null_count,
           COUNT(*) AS total
    FROM main_marts.fact_orders
    WHERE scope_retail = TRUE AND is_active_order = TRUE
""").fetchone()
print(f"  min={probe[0]}  max={probe[1]}  avg={probe[2]}  above_1={probe[3]}  zero={probe[4]}  null={probe[5]}  total={probe[6]}")

# Actual discount values for non-zero orders
probe2 = con.execute("""
    SELECT ROUND(AVG(max_discount_rate), 1) AS avg_among_discounted,
           COUNT(*) AS n_discounted
    FROM main_marts.fact_orders
    WHERE scope_retail = TRUE AND is_active_order = TRUE AND max_discount_rate > 0
""").fetchone()
print(f"  Among discounted: n={probe2[1]}  avg_disc={probe2[0]}%")

# ── 1. Basket size distribution ──────────────────────────────────────────────
print()
print(SEP)
print("1. BASKET SIZE: # distinct products per retail order")
print(SEP)

rows = con.execute("""
    WITH order_items AS (
        SELECT fs.order_id,
               COUNT(DISTINCT fs.product_key) AS n_products,
               SUM(fs.net_revenue)            AS order_rev,
               fo.max_discount_rate
        FROM main_marts.fact_sales fs
        JOIN main_marts.fact_orders fo ON fo.order_id = fs.order_id
        WHERE fo.scope_retail = TRUE AND fo.is_active_order = TRUE
        GROUP BY fs.order_id, fo.max_discount_rate
    )
    SELECT
        n_products,
        COUNT(*)                                           AS orders,
        ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 1) AS pct,
        ROUND(AVG(order_rev), 0)                           AS avg_rev,
        ROUND(AVG(max_discount_rate), 1)                   AS avg_disc_pct,
        ROUND(SUM(CASE WHEN max_discount_rate > 0 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) AS pct_with_disc
    FROM order_items
    GROUP BY n_products
    ORDER BY n_products
""").fetchall()

print(f"  {'items':>5}  {'orders':>6}  {'%':>5}  {'avg_rev':>10}  {'avg_disc%':>9}  {'%_disc':>7}")
for r in rows:
    avg_rev  = f"{r[3]:>10,.0f}" if r[3] is not None else f"{'N/A':>10}"
    avg_disc = f"{r[4]:>8.1f}%" if r[4] is not None else f"{'N/A':>8}"
    pct_disc = f"{r[5]:>6.1f}%" if r[5] is not None else f"{'N/A':>6}"
    print(f"  {r[0]:>5}  {r[1]:>6}  {r[2]:>5}  {avg_rev}  {avg_disc}  {pct_disc}")

# ── 2. Single vs multi-item: discount presence ───────────────────────────────
print()
print(SEP)
print("2. SINGLE vs MULTI-ITEM: discount presence")
print(SEP)

rows2 = con.execute("""
    WITH order_items AS (
        SELECT fs.order_id,
               COUNT(DISTINCT fs.product_key) AS n_products,
               fo.max_discount_rate,
               fo.net_revenue
        FROM main_marts.fact_sales fs
        JOIN main_marts.fact_orders fo ON fo.order_id = fs.order_id
        WHERE fo.scope_retail = TRUE AND fo.is_active_order = TRUE
        GROUP BY fs.order_id, fo.max_discount_rate, fo.net_revenue
    )
    SELECT
        CASE WHEN n_products = 1 THEN '1 item' ELSE '2+ items' END AS basket_type,
        COUNT(*)                                   AS orders,
        ROUND(AVG(max_discount_rate), 1)           AS avg_disc_pct,
        ROUND(SUM(CASE WHEN max_discount_rate > 0 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) AS pct_discounted,
        ROUND(AVG(net_revenue), 0)                 AS avg_order_value
    FROM order_items
    GROUP BY basket_type
    ORDER BY basket_type
""").fetchall()

for r in rows2:
    aov = f"{r[4]:,.0f}" if r[4] is not None else "N/A"
    print(f"  {r[0]}: orders={r[1]}  avg_disc={r[2]}%  pct_with_disc={r[3]}%  avg_order_value={aov}")

# ── 3. Top product pairs (ALL retail orders) ─────────────────────────────────
print()
print(SEP)
print("3. TOP PRODUCT PAIRS (all retail orders — any order rank)")
print(SEP)

rows3 = con.execute("""
    WITH order_lines AS (
        SELECT fs.order_id, p.product_name,
               fs.net_revenue                       AS line_rev,
               fo.max_discount_rate                 AS order_disc_rate,
               fo.net_revenue                       AS order_rev
        FROM main_marts.fact_sales fs
        JOIN main_marts.dim_products  p  ON p.product_key  = fs.product_key
        JOIN main_marts.fact_orders   fo ON fo.order_id    = fs.order_id
        WHERE fo.scope_retail = TRUE AND fo.is_active_order = TRUE
    )
    SELECT
        a.product_name   AS product_a,
        b.product_name   AS product_b,
        COUNT(DISTINCT a.order_id)                                    AS co_orders,
        ROUND(AVG(a.order_rev + b.line_rev), 0)                       AS avg_order_rev,
        ROUND(AVG(a.order_disc_rate), 1)                              AS avg_disc_pct,
        ROUND(SUM(CASE WHEN a.order_disc_rate > 0 THEN 1 ELSE 0 END)
              * 100.0 / COUNT(*), 1)                                   AS pct_discounted
    FROM order_lines a
    JOIN order_lines b ON b.order_id = a.order_id AND b.product_name > a.product_name
    GROUP BY a.product_name, b.product_name
    HAVING COUNT(DISTINCT a.order_id) >= 5
    ORDER BY co_orders DESC
    LIMIT 40
""").fetchall()

print(f"  {'Product A':<42} {'Product B':<42} {'co_orders':>9} {'avg_rev':>10} {'disc%':>6} {'%disc':>6}")
for r in rows3:
    disc  = f"{r[4]:>5.1f}%" if r[4] is not None else f"{'N/A':>5}"
    pdisc = f"{r[5]:>5.1f}%" if r[5] is not None else f"{'N/A':>5}"
    print(f"  {r[0][:42]:<42} {r[1][:42]:<42} {r[2]:>9} {r[3]:>10,.0f} {disc} {pdisc}")

# ── 4. Discount on which product drives bundling? ────────────────────────────
print()
print(SEP)
print("4. DISCOUNT DISTRIBUTION: where does discount land in entry+premium orders?")
print(SEP)

ENTRY_PAT = """(
    p.product_name ILIKE '%UV Care%'
    OR p.product_name ILIKE '%Calcium%'
    OR p.product_name ILIKE '%Coix%'
    OR p.product_name ILIKE '%Metabo%'
)"""

PREM_PAT = """(
    p.product_name ILIKE '%Cordyceps%'
    OR p.product_name ILIKE '%Shark Cartilage%'
    OR p.product_name ILIKE '%Natto Kinase%'
    OR p.product_name ILIKE '%Fucoidan%'
    OR p.product_name ILIKE '%Royal Reishi%'
    OR p.product_name ILIKE '%Hyaluron%'
)"""

rows4 = con.execute(f"""
    WITH co_orders AS (
        SELECT DISTINCT fs.order_id
        FROM main_marts.fact_sales fs
        JOIN main_marts.dim_products p ON p.product_key = fs.product_key
        JOIN main_marts.fact_orders fo ON fo.order_id = fs.order_id
        WHERE fo.scope_retail = TRUE AND fo.is_active_order = TRUE
          AND {ENTRY_PAT}
        INTERSECT
        SELECT DISTINCT fs2.order_id
        FROM main_marts.fact_sales fs2
        JOIN main_marts.dim_products p2 ON p2.product_key = fs2.product_key
        JOIN main_marts.fact_orders fo2 ON fo2.order_id = fs2.order_id
        WHERE fo2.scope_retail = TRUE AND fo2.is_active_order = TRUE
          AND {PREM_PAT.replace('p.', 'p2.').replace('fs.', 'fs2.')}
    ),
    line_roles AS (
        SELECT
            co.order_id,
            CASE WHEN {ENTRY_PAT} THEN 'entry'
                 WHEN {PREM_PAT} THEN 'premium'
                 ELSE 'other' END AS role,
            fs.net_revenue,
            fs.distributed_discount_amount
        FROM co_orders co
        JOIN main_marts.fact_sales fs  ON fs.order_id = co.order_id
        JOIN main_marts.dim_products p ON p.product_key = fs.product_key
    )
    SELECT
        role,
        COUNT(*)                                          AS line_count,
        ROUND(AVG(net_revenue), 0)                        AS avg_line_rev,
        ROUND(AVG(distributed_discount_amount), 0)        AS avg_disc_on_line,
        ROUND(SUM(distributed_discount_amount)
              / NULLIF(SUM(net_revenue + distributed_discount_amount), 0) * 100, 1) AS disc_share_pct
    FROM line_roles
    WHERE role != 'other'
    GROUP BY role
    ORDER BY role
""").fetchall()

print(f"  {'Role':<10} {'lines':>6}  {'avg_line_rev':>12}  {'avg_disc':>9}  {'disc_share%':>11}")
for r in rows4:
    print(f"  {r[0]:<10} {r[1]:>6}  {r[2]:>12,.0f}  {r[3]:>9,.0f}  {r[4]:>11.1f}%")

# ── 5. Entry SKU discounted vs full price → basket size impact ────────────────
print()
print(SEP)
print("5. ENTRY SKU: discounted vs full price — does discount drive bundling?")
print(SEP)

rows5 = con.execute(f"""
    WITH entry_orders AS (
        SELECT
            fo.order_id,
            p.product_name                                      AS entry_sku,
            fo.max_discount_rate,
            fo.net_revenue                                      AS order_rev,
            COUNT(DISTINCT fs_all.product_key) OVER (PARTITION BY fo.order_id) AS basket_size
        FROM main_marts.fact_orders fo
        JOIN main_marts.fact_sales fs    ON fs.order_id = fo.order_id
        JOIN main_marts.dim_products p   ON p.product_key = fs.product_key
        JOIN main_marts.fact_sales fs_all ON fs_all.order_id = fo.order_id
        WHERE fo.scope_retail = TRUE AND fo.is_active_order = TRUE
          AND {ENTRY_PAT}
    )
    SELECT
        entry_sku,
        CASE WHEN max_discount_rate > 0 THEN 'discounted' ELSE 'full price' END AS price_type,
        COUNT(DISTINCT order_id)               AS orders,
        ROUND(AVG(basket_size), 1)             AS avg_basket_size,
        ROUND(AVG(order_rev), 0)               AS avg_order_rev,
        ROUND(AVG(max_discount_rate), 1)       AS avg_disc_pct
    FROM entry_orders
    GROUP BY entry_sku, price_type
    ORDER BY entry_sku, price_type
""").fetchall()

print(f"  {'Entry SKU':<42} {'price_type':<12} {'orders':>6}  {'avg_basket':>10}  {'avg_rev':>10}  {'avg_disc%':>9}")
for r in rows5:
    avg_bskt = f"{r[3]:>10.1f}" if r[3] is not None else f"{'N/A':>10}"
    avg_rev  = f"{r[4]:>10,.0f}" if r[4] is not None else f"{'N/A':>10}"
    avg_disc = f"{r[5]:>8.1f}%" if r[5] is not None else f"{'N/A':>8}"
    print(f"  {r[0][:42]:<42} {r[1]:<12} {r[2]:>6}  {avg_bskt}  {avg_rev}  {avg_disc}")

con.close()
print("\nDone.")
