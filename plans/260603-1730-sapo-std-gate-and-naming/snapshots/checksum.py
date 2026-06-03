"""Reusable mart checksum harness (verification-protocol T3).
Lock-free: reads newest rolling parquet per mart. Order-independent fingerprint.

Two modes:
  Whole-row (default) — catches ANY change incl. column renames (to_json includes names):
    python checksum.py [m1 m2 ...]
  Per-column, NAME-AGNOSTIC (for RENAME steps) — fingerprint = sorted multiset of each
  column's value-checksum, so a pure rename (same values, new name) compares EQUAL:
    python checksum.py --percol [m1 m2 ...]

Use --percol to prove a column rename changed only the NAME, not any VALUE.
COUNT(*) always catches row add/drop.
"""
import duckdb, glob, os, sys

EXPORT = r"app_data\data_lake\export\marts\rolling"
P0_MARTS = [
    "dim_products", "dim_sku_alias", "dim_price_lists",
    "fact_variant_prices_snapshot", "fact_order_returns", "fact_order_costs",
    "fact_orders", "mart_inventory_health",
]

args = sys.argv[1:]
percol = "--percol" in args
marts = [a for a in args if not a.startswith("--")] or P0_MARTS
con = duckdb.connect()
for m in marts:
    files = sorted(glob.glob(os.path.join(EXPORT, m, "*.parquet")), key=os.path.getmtime)
    if not files:
        print(f"{m}: MISSING"); continue
    p = files[-1].replace("\\", "/")
    try:
        if percol:
            # one bit_xor(hash(col)) per source column -> sort the values (drop names)
            row = con.execute(
                f"SELECT COUNT(*) AS n, bit_xor(hash(COLUMNS(*))) FROM read_parquet('{p}')"
            ).fetchone()
            n = row[0]
            colfp = sorted(str(v) for v in row[1:])  # name-agnostic multiset
            print(f"{m}: rows={n} percol={colfp} file={os.path.basename(p)}")
        else:
            n, chk = con.execute(
                f"SELECT COUNT(*), bit_xor(hash(to_json(t))) FROM read_parquet('{p}') t"
            ).fetchone()
            print(f"{m}: rows={n} chk={chk} file={os.path.basename(p)}")
    except Exception as e:
        print(f"{m}: ERROR {e}")
