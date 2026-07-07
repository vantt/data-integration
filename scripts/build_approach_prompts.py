#!/usr/bin/env python3
"""build_approach_prompts.py — Bước 1 của quy trình TAY sinh approach-script.

Cohort (gating SQL trên dim_customers) → ráp prompt (template v2 + data khách) →
ghi 1 file `{out}/{customer_id}.txt` mỗi khách. Tên file = customer_id để biết
output GPT phải lưu thành `{customer_id}.json`.

Chạy trên HOST (cần duckdb) hoặc trong container `data_platform` (phase 05
auto-gen, `generate_approach_scripts.py` import module này) — `_data_lake_root()`
tự nhận biết môi trường qua env `DBT_DATA_LAKE_PATH`. Ví dụ:
  python scripts/build_approach_prompts.py
  python scripts/build_approach_prompts.py --recency 365 --limit 50
  python scripts/build_approach_prompts.py --ids 895489673,603264280
"""
from __future__ import annotations
import argparse, glob, json, os, re, sys
from datetime import date
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_MD = ROOT / "plans" / "260624-1917-customer-insight-prompt-template" / "customer-insight-prompt-template.md"
# Đường dẫn relative tới data-lake root (không phải ROOT) — join qua _data_lake_root().
PARQUET_GLOB = "export/marts/rolling/dim_customers/*.parquet"
ACTION_QUEUE_GLOB = "export/marts/rolling/mart_customer_sku_action_queue/*.parquet"


def _data_lake_root() -> Path:
    """Env DBT_DATA_LAKE_PATH (set trong .env.docker, container data_platform)
    khi chạy trong container; fallback ROOT/app_data/data_lake khi chạy trên HOST
    (env thường unset ở đó)."""
    env = os.environ.get("DBT_DATA_LAKE_PATH")
    return Path(env) if env else ROOT / "app_data" / "data_lake"

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
    "clv_in_value_group_pct","clv_in_value_group_bucket","clv_in_value_group_phrase",
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

def fill(t: str, customer: dict, data_as_of: str, recent_notes: list | None = None) -> str:
    notes_json = json.dumps(recent_notes or [], ensure_ascii=False, indent=2)
    return (t.replace("{{data_as_of}}", data_as_of)
             .replace("{{customer_json}}", json.dumps(customer, ensure_ascii=False, indent=2))
             .replace("{{recent_notes}}", notes_json)
             .replace("{{recent_convos}}", "[]")
             .replace("{{tags}}", "[]"))

def fetch_cohort(args) -> list[dict]:
    """Cohort từ snapshot dim_customers mới nhất → list dict khách (đã sanitize).

    args cần: ids, recency, limit, mask_phone (chuẩn add_cohort_args).
    """
    lake = _data_lake_root()
    files = sorted(glob.glob(str(lake / PARQUET_GLOB)))
    if not files:
        sys.exit(f"Không thấy parquet: {lake / PARQUET_GLOB}")
    con = duckdb.connect(":memory:")
    sel = ", ".join(COLS)
    if args.ids.strip():
        idlist = ",".join(f"'{x.strip()}'" for x in args.ids.split(",") if x.strip())
        where = f"customer_id IN ({idlist})"
    else:
        where = GATE.format(recency=args.recency)
        # Cohort actionable (phase 05 auto-gen): giới hạn thêm xuống khách đang
        # có ít nhất 1 hàng trong mart_customer_sku_action_queue (wh_sku_action_queue).
        if getattr(args, "cohort_from_queue", False):
            queue_files = sorted(glob.glob(str(lake / ACTION_QUEUE_GLOB)))
            if not queue_files:
                sys.exit(f"Không thấy parquet: {lake / ACTION_QUEUE_GLOB}")
            # dim_customers.customer_id is VARCHAR, mart_customer_sku_action_queue.customer_id is INTEGER — cast to match.
            where = (f"({where}) AND CAST(customer_id AS VARCHAR) IN "
                     f"(SELECT CAST(customer_id AS VARCHAR) FROM read_parquet('{queue_files[-1]}'))")
    sql = f"SELECT {sel} FROM read_parquet('{files[-1]}') WHERE {where}"
    if args.limit > 0:
        sql += f" ORDER BY lifetime_value DESC LIMIT {args.limit}"
    rows = con.execute(sql).fetchdf()
    con.close()

    customers = []
    for _, r in rows.iterrows():
        c = {}
        for k, v in r.to_dict().items():
            if v is None or (isinstance(v, float) and v != v): c[k] = None
            elif k == "phone" and args.mask_phone: c[k] = mask_phone(v)
            elif hasattr(v, "item"): c[k] = v.item()
            else: c[k] = v if isinstance(v, (int, float, bool)) else str(v)
        c["consent_contact"] = "allowed"  # chính sách: mặc định liên hệ được
        customers.append(c)
    return customers


def add_cohort_args(ap: argparse.ArgumentParser) -> None:
    """Flags cohort + history dùng chung giữa builder và generator."""
    ap.add_argument("--recency", type=int, default=270, help="ngưỡng recency_days cohort")
    ap.add_argument("--limit", type=int, default=0, help="giới hạn số khách (0=không)")
    ap.add_argument("--ids", default="", help="danh sách customer_id (bỏ qua gating)")
    ap.add_argument("--mask-phone", action="store_true", help="che SĐT trong prompt")
    ap.add_argument("--no-history", action="store_true", help="bỏ read-back notes/activities từ crm.db")
    ap.add_argument("--crm-db", default="", help="đường dẫn crm.db có sẵn (bỏ qua docker cp)")
    ap.add_argument("--cohort-from-queue", action="store_true",
                     help="chỉ giữ khách đang có action trong mart_customer_sku_action_queue "
                          "(cohort actionable, phase 05 auto-gen)")


def fetch_history(customers: list[dict], args) -> dict[int, list]:
    """Read-back WS-A1: notes/activities thật từ CRM thay hardcode []."""
    if args.no_history:
        return {}
    from crm_history_reader import fetch_recent_notes
    ids = [int(c["customer_id"]) for c in customers]
    history = fetch_recent_notes(ids, crm_db=args.crm_db or None)
    print(f"Read-back: {sum(len(v) for v in history.values())} notes/activities cho {len(history)}/{len(ids)} khách")
    return history


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # Windows console (cp1252)
    except Exception:
        pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="approach_prompts", help="thư mục ghi prompt")
    add_cohort_args(ap)
    args = ap.parse_args()

    customers = fetch_cohort(args)
    history = fetch_history(customers, args)

    template = load_template()
    out = ROOT / args.out; out.mkdir(parents=True, exist_ok=True)
    today = date.today().isoformat()

    n = 0
    for c in customers:
        cid = c["customer_id"]
        (out / f"{cid}.txt").write_text(
            fill(template, c, today, recent_notes=history.get(int(cid))), encoding="utf-8")
        n += 1
    print(f"Ghi {n} prompt -> {out}/  (template v2, đặt tên theo customer_id)")
    print("Bước 2: dán từng .txt vào GPT, lưu output approach_out/{customer_id}.json")
    print("Bước 3: python scripts/load_approach_scripts.py --src approach_out/")

if __name__ == "__main__":
    main()
