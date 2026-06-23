"""seed_hug_deadstock_resell_campaign.py — idempotent seed for the "deadstock-resell" Hug campaign.

Creates (or updates) the Hug campaign that drives the HUG leg of the dead-stock
targeting engine. Audience = contactable customers (route_channel=HUG) from
wh_deadstock_target: strategic tier eligible AND voucher_eligible AND NOT holdout.

Run ONCE after deploy (or re-run to update; upsert_campaign is idempotent):
    python -m crm.sync.seed_hug_deadstock_resell_campaign
    python crm/sync/seed_hug_deadstock_resell_campaign.py [--crm-db PATH]

Pre-conditions:
    1. crm.db exists and has crm_hug_campaign table (CRM app has been started).
    2. HUG_WORKER_URL is set if you want the campaign pushed to the Cloudflare edge.
       If unset, the campaign is saved locally only (push skipped, no crash).

Campaign design decisions (see PLAN-004 P2):
    - Targeting: tier IN [LIVE_CORE, SECOND_ORDER, DORMANT_VALUABLE, LAPSED_VALUABLE]
      (NOT MASKED_REPEAT — those go via Shopee-native leg separately)
    - is_contactable: [1]  (real phone; Hug can reach them)
    - Voucher eligibility is pre-filtered in wh_deadstock_target; the edge campaign
      doesn't need a voucher_eligible attr because all HUG rows are already eligible
      (voucher_eligible=FALSE buyers excluded from HUG outreach at data layer).
    - Holdout: excluded at data layer (is_holdout=0); campaign touches treatment group only.
    - destination_type: cf_pages (Hug landing with voucher reveal)
    - offer_ref: set to 'deadstock-resell-voucher' (must match Hug voucher config)
    - priority: 200 (lower priority than retention campaigns — clearance, not growth)
    - status: 'paused' on seed (activate manually after verifying voucher is configured)
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import sqlite3
import sys


_DEFAULT_CRM_DB = os.environ.get("CRM_DB_PATH", "crm/data/crm.db")

# Campaign row to upsert.
_CAMPAIGN_ROW = {
    "campaign_id": "deadstock-resell",
    "name": "Thanh lý SKU ế — own-brand FJV",
    "targeting": json.dumps({
        # Contactable customers only (real phone → Hug can reach via Zalo OA)
        "is_contactable": [1],
        # 4 eligible tiers for Hug leg (MASKED_REPEAT goes Shopee-native)
        "tier": ["LIVE_CORE", "SECOND_ORDER", "DORMANT_VALUABLE", "LAPSED_VALUABLE"],
    }, ensure_ascii=False),
    "destination_type": "cf_pages",
    # Voucher reveal page; update URL to actual CF Pages deployment path
    "destination_url": "/voucher/deadstock-resell",
    "offer_ref": "deadstock-resell-voucher",
    "priority": 200,
    # Start paused: activate after verifying voucher config + min-order guard
    "status": "paused",
    # No schedule_end set — perpetual until manually archived
    "schedule_start": None,
    "schedule_end": None,
    "quota_total": None,
}


def _open_crm_db(path: str) -> sqlite3.Connection:
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"crm.db not found at: {path}. "
            "Start the CRM app first so it initialises the schema."
        )
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def seed(crm_db: str) -> None:
    """Upsert the deadstock-resell campaign row into crm.db."""
    # Import CRM-internal modules (repo root must be in sys.path)
    repo_root = str(pathlib.Path(__file__).resolve().parent.parent.parent)
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)

    crm_src = os.path.join(repo_root, "crm", "src")
    if crm_src not in sys.path:
        sys.path.insert(0, crm_src)

    from hug.campaign_repository import upsert_campaign  # noqa: PLC0415

    conn = _open_crm_db(crm_db)
    try:
        saved = upsert_campaign(conn, _CAMPAIGN_ROW)
        print(f"Campaign seeded: {saved['campaign_id']} (status={saved['status']})")
        print("Next steps:")
        print("  1. Configure voucher 'deadstock-resell-voucher' in Hug voucher engine")
        print("     (set min-order threshold + SKU-guard to exclude negative-margin SKUs)")
        print("  2. Update destination_url to actual CF Pages voucher reveal path")
        print("  3. Activate campaign: POST /hug/campaign/deadstock-resell/status {status: active}")
        print("  4. Push to edge: campaign_push.push_all() or CRM admin UI → save + push")
    finally:
        conn.close()


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Seed Hug 'deadstock-resell' campaign (idempotent).")
    p.add_argument(
        "--crm-db",
        default=_DEFAULT_CRM_DB,
        help=f"Path to crm.db (default: {_DEFAULT_CRM_DB})",
    )
    return p.parse_args(argv)


if __name__ == "__main__":
    args = _parse_args()
    try:
        seed(crm_db=args.crm_db)
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
