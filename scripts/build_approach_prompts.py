#!/usr/bin/env python3
"""build_approach_prompts.py — Bước 1 của quy trình TAY sinh approach-script.

Cohort (gating SQL trên dim_customers) → ráp prompt (template v2 + data khách) →
ghi 1 file `{out}/{customer_id}.txt` mỗi khách. Tên file = customer_id để biết
output GPT phải lưu thành `{customer_id}.json`.

Chạy trên HOST (cần duckdb). Ví dụ:
  python scripts/build_approach_prompts.py
  python scripts/build_approach_prompts.py --recency 365 --limit 50
  python scripts/build_approach_prompts.py --ids 895489673,603264280
"""
from __future__ import annotations
import argparse, glob, json, re, sys
from datetime import date
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_MD = ROOT / "plans" / "260624-1917-customer-insight-prompt-template" / "customer-insight-prompt-template.md"
PARQUET_GLOB = "app_data/data_lake/export/marts/rolling/dim_customers/*.parquet"

# Cột đưa vào customer_json (khớp input contract của template)
COLS = ["customer_id","full_name","phone","is_contactable","contact_quality","customer_type",
    "geo_region","value_group","lifetime_value","order_count","lifecycle_stage","customer_status",
    "recency_days","avg_days_between_orders","next_purchase_signal","discount_sensitivity",
    "channel_preference","payment_behavior","product_affinity","last_purchased_product",
    "last_purchased_sku","top_affinity_product","top_affinity_sku","second_affinity_product",
    "is_margin_negative","avg_order_contribution_margin_pct","loyalty_points","birth_date","gender",
    # Benchmark percentile columns (populated when benchmark_status='ranked', else NULL)
    # *_phrase = ready-made Vietnamese phrase for LLM to verbalize — do NOT expose raw *_pct numbers to the customer
    "benchmark_status",
    "lv_all_rankable_pct","lv_all_rankable_bucket","lv_all_rankable_phrase",
    "lv_in_value_group_pct","lv_in_value_group_bucket","lv_in_value_group_phrase",
    "clv_all_rankable_pct","clv_all_rankable_bucket","clv_all_rankable_phrase",
    "clv_vs_rankable_median"]

# Gating cohort — KHỚP retail-ai-outreach-cohort.sql (khách retail đáng chạy)
GATE = """
  customer_type='RETAIL' AND is_contactable=TRUE AND contact_quality<>'masked'
  AND COALESCE(acquisition_source,'')<>'Đại Lý'
  AND is_margin_negative=FALSE AND COALESCE(avg_order_contribution_margin_pct,0)>0
  AND order_count>=2 AND top_affinity_sku IS NOT NULL AND recency_days<={recency}
  AND (value_group IN ('VALUE_VIP','VALUE_GOLD') OR next_purchase_signal IN ('DUE_SOON','OVERDUE'))
"""

def load_template() -> str:
    md = TEMPLATE_MD.read_text(encoding="utf-8")
    after = md.split("## PHẦN 1", 1)[1]
    return re.search(r"```text\s*\n(.*?)\n```", after, re.S).group(1)

def mask_phone(p):
    if not p: return p
    s = str(p); return s[:4] + "*"*max(0, len(s)-6) + s[-2:] if len(s) > 6 else "***"

def fill(t: str, customer: dict, data_as_of: str) -> str:
    return (t.replace("{{data_as_of}}", data_as_of)
             .replace("{{customer_json}}", json.dumps(customer, ensure_ascii=False, indent=2))
             .replace("{{recent_notes}}", "[]")
             .replace("{{recent_convos}}", "[]")
             .replace("{{tags}}", "[]"))

def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # Windows console (cp1252)
    except Exception:
        pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="approach_prompts", help="thư mục ghi prompt")
    ap.add_argument("--recency", type=int, default=270, help="ngưỡng recency_days cohort")
    ap.add_argument("--limit", type=int, default=0, help="giới hạn số khách (0=không)")
    ap.add_argument("--ids", default="", help="danh sách customer_id (bỏ qua gating)")
    ap.add_argument("--mask-phone", action="store_true", help="che SĐT trong prompt")
    args = ap.parse_args()

    files = sorted(glob.glob(str(ROOT / PARQUET_GLOB)))
    if not files:
        sys.exit(f"Không thấy parquet: {PARQUET_GLOB}")
    src = f"read_parquet('{files[-1]}')"  # snapshot mới nhất
    con = duckdb.connect(":memory:")
    sel = ", ".join(COLS)
    if args.ids.strip():
        idlist = ",".join(f"'{x.strip()}'" for x in args.ids.split(",") if x.strip())
        where = f"customer_id IN ({idlist})"
    else:
        where = GATE.format(recency=args.recency)
    sql = f"SELECT {sel} FROM {src} WHERE {where}"
    if args.limit > 0:
        sql += f" ORDER BY lifetime_value DESC LIMIT {args.limit}"
    rows = con.execute(sql).fetchdf()
    con.close()

    template = load_template()
    out = ROOT / args.out; out.mkdir(parents=True, exist_ok=True)
    today = date.today().isoformat()
    n = 0
    for _, r in rows.iterrows():
        c = {}
        for k, v in r.to_dict().items():
            if v is None or (isinstance(v, float) and v != v): c[k] = None
            elif k == "phone" and args.mask_phone: c[k] = mask_phone(v)
            elif hasattr(v, "item"): c[k] = v.item()
            else: c[k] = v if isinstance(v, (int, float, bool)) else str(v)
        c["consent_contact"] = "allowed"  # chính sách: mặc định liên hệ được
        cid = c["customer_id"]
        (out / f"{cid}.txt").write_text(fill(template, c, today), encoding="utf-8")
        n += 1
    print(f"Ghi {n} prompt -> {out}/  (template v2, đặt tên theo customer_id)")
    print("Bước 2: dán từng .txt vào GPT, lưu output approach_out/{customer_id}.json")
    print("Bước 3: python scripts/load_approach_scripts.py --src approach_out/")

if __name__ == "__main__":
    main()
