"""Reusable mart checksum harness (verification-protocol T3).
Lock-free: reads newest rolling parquet per mart. Order-independent fingerprint.
Usage: python checksum.py            -> prints checksums for the P0 mart set
       python checksum.py m1 m2 ...  -> only those marts
COUNT(*) catches row add/drop; bit_xor(hash(row-json)) catches any value change.
"""
import duckdb, glob, os, sys

EXPORT = r"app_data\data_lake\export\marts\rolling"
P0_MARTS = [
    "dim_products", "dim_sku_alias", "dim_price_lists",
    "fact_variant_prices_snapshot", "fact_order_returns", "fact_order_costs",
    "fact_orders", "mart_inventory_health",
]

marts = sys.argv[1:] or P0_MARTS
con = duckdb.connect()
for m in marts:
    files = sorted(glob.glob(os.path.join(EXPORT, m, "*.parquet")), key=os.path.getmtime)
    if not files:
        print(f"{m}: MISSING"); continue
    p = files[-1].replace("\\", "/")
    try:
        n, chk = con.execute(
            f"SELECT COUNT(*), bit_xor(hash(to_json(t))) FROM read_parquet('{p}') t"
        ).fetchone()
        print(f"{m}: rows={n} chk={chk} file={os.path.basename(p)}")
    except Exception as e:
        print(f"{m}: ERROR {e}")
